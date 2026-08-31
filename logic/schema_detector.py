"""
AcaDesk Schema Intelligence Layer — Layer 2
=============================================
Introspects a college ERP schema using INFORMATION_SCHEMA.

PRIMARY API: demand_driven_discover(connection)
  Uses the Data Demand Manifest to execute a single bounded
  INFORMATION_SCHEMA query, score table candidates, and produce
  a validated mapping in < 5 seconds on any database size.

SECONDARY API: validate_stored_mapping(connection, mapping)
  Validates a stored mapping against the live ERP schema.
  Called by SyncWorker before every cache sync to catch stale mappings
  and attempt automatic column re-discovery.

DEPRECATED: detect_schema() (original full-scan approach)
  Preserved as fallback but not called by any new code paths.

Architecture constraints:
  - This layer runs ONLY at setup time OR on admin-triggered re-detect.
  - It does NOT run at every query. validate_stored_mapping() is the
    exception — it is lightweight and runs once per session startup.
  - No raw user input ever reaches a query builder through this layer.
  - All table and column names are validated against INFORMATION_SCHEMA
    before they are stored in erp_configs.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from logic.demand_manifest import (
    ALL_ROLES,
    ALL_SYNONYMS,
    SYNONYM_TO_FIELD,
    STUDENT_MASTER_FIELDS,
    ACADEMIC_RECORDS_FIELDS,
    BRANCH_MASTER_FIELDS,
)

_log = logging.getLogger(__name__)

# Standard AcaDesk view names (VIEW STRATEGY)
VIEW_STUDENT  = "vw_acadesk_student"
VIEW_ACADEMIC = "vw_acadesk_academic"
VIEW_BRANCH   = "vw_acadesk_branch"

# Minimum required score for a table to be eligible for a role
MIN_ELIGIBLE_SCORE = 20  # Must match at least 2 required fields


# ---------------------------------------------------------------------------
# Result Types
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Aggregate result of validate_stored_mapping()."""
    is_valid: bool
    missing_columns: List[Tuple[str, str, str]]  # (table, column, purpose)
    correctable: bool  # True if re-discovery can fix it
    error_message: str


@dataclass
class FieldValidationResult:
    """Validation outcome for a single stored mapping field."""
    mapping_key: str          # e.g. "col_id"
    stored_value: str         # The column name as stored in erp_configs
    is_valid: bool            # True if column exists in ERP right now
    is_required: bool         # True if this field is required for AcaDesk
    rediscovered_value: str = ""  # If re-discovered, the new column name
    error_msg: str = ""           # Human-readable error if invalid


@dataclass
class MappingValidationResult:
    """Aggregate result of validate_stored_mapping()."""
    is_fully_valid: bool = True
    has_required_failures: bool = False
    field_results: List[FieldValidationResult] = field(default_factory=list)
    corrected_mapping: Dict[str, str] = field(default_factory=dict)
    error_summary: str = ""


# ---------------------------------------------------------------------------
# SchemaDetector
# ---------------------------------------------------------------------------

class SchemaDetector:
    """
    Layer 2: Schema Intelligence.

    Primary usage (setup wizard):
        detector = SchemaDetector(host, port, db, user, pwd)
        ok, msg = detector.connect()
        if ok:
            result = detector.demand_driven_discover()
            # result is a flat mapping dict with 'strategy' key

    Validation usage (SyncWorker at session start):
        result = SchemaDetector.validate_stored_mapping(conn, mapping)
    """

    def __init__(self, host: str, port: int, db: str, user: str, pwd: str):
        self.host = host
        self.port = int(port)
        self.db = db
        self.user = user
        self.pwd = pwd
        self.conn = None

        # Legacy full-scan state (for deprecated detect_schema() only)
        self.tables: List[str] = []
        self.columns: Dict[str, List[dict]] = {}
        self.foreign_keys: List[dict] = []
        self._views: List[str] = []

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> Tuple[bool, str]:
        """Connects to the ERP database using the provided credentials."""
        try:
            import mysql.connector
            self.conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.db,
                user=self.user,
                password=self.pwd,
                connect_timeout=10,
            )
            return True, "Connected successfully"
        except Exception as e:
            _log.error(f"SchemaDetector connect failed: {e}")
            return False, str(e)

    def disconnect(self) -> None:
        """Closes the connection if open."""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
        except Exception:
            pass

    # ------------------------------------------------------------------
    # PRIMARY API — Demand-Driven Discovery
    # ------------------------------------------------------------------

    def demand_driven_discover(self, conn=None) -> dict:
        """
        Executes a targeted INFORMATION_SCHEMA scan using the Data Demand
        Manifest. Completes in < 5 seconds regardless of database size.

        Args:
            conn: Optional pre-existing MySQL connection. Uses self.conn if None.

        Returns:
            Flat mapping dict compatible with erp_configs, including 'strategy'
            and 'raw_result' keys. Returns error dict on failure.
        """
        connection = conn or self.conn
        if not connection:
            return {"error": "No database connection available."}
        
        db_name = self.db
        _log.info(f"[demand_driven_discover] Starting Phase 1 & 2 scan of '{db_name}'")
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # STEP 1: Check for AcaDesk views first (VIEW STRATEGY)
            cursor.execute("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'VIEW'
                AND LOWER(TABLE_NAME) IN (%s, %s, %s)
            """, (db_name, VIEW_STUDENT.lower(), VIEW_ACADEMIC.lower(), VIEW_BRANCH.lower()))
            found_views = {r["TABLE_NAME"].lower() for r in cursor.fetchall()}
            
            if all(v in found_views for v in [VIEW_STUDENT.lower(), VIEW_ACADEMIC.lower(), VIEW_BRANCH.lower()]):
                _log.info("AcaDesk SQL views detected — using VIEW STRATEGY.")
                cursor.close()
                return self._build_view_mapping()

            # ────────────────────────────────────────────────────────
            # PHASE 1 — FULL SCHEMA AWARENESS
            # ────────────────────────────────────────────────────────
            
            schema_graph = {
                "tables": {},
                "fk_pairs": set()
            }
            
            # QUERY 1 — All tables
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_ROWS, TABLE_TYPE
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            """, (db_name,))
            for row in cursor.fetchall():
                tname = row["TABLE_NAME"]
                schema_graph["tables"][tname] = {
                    "rows": row["TABLE_ROWS"] or 0,
                    "columns": {},
                    "primary_keys": [],
                    "foreign_keys": [],
                    "referenced_by": []
                }
                
            # QUERY 2 — All columns
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, 
                       COLUMN_KEY, IS_NULLABLE, ORDINAL_POSITION
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """, (db_name,))
            for row in cursor.fetchall():
                tname = row["TABLE_NAME"]
                if tname in schema_graph["tables"]:
                    cname = row["COLUMN_NAME"]
                    schema_graph["tables"][tname]["columns"][cname.lower()] = {
                        "name": cname,
                        "data_type": row["DATA_TYPE"],
                        "column_key": row["COLUMN_KEY"],
                        "is_nullable": row["IS_NULLABLE"] == "YES"
                    }
            
            # QUERY 3 — Foreign keys
            cursor.execute("""
                SELECT TABLE_NAME as child_table, COLUMN_NAME as child_column,
                       REFERENCED_TABLE_NAME as parent_table, REFERENCED_COLUMN_NAME as parent_column
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (db_name,))
            for row in cursor.fetchall():
                ctable = row["child_table"]
                ptable = row["parent_table"]
                ccol = row["child_column"]
                pcol = row["parent_column"]
                
                if ctable in schema_graph["tables"] and ptable in schema_graph["tables"]:
                    schema_graph["fk_pairs"].add((ctable, ptable))
                    schema_graph["tables"][ctable]["foreign_keys"].append({
                        "child_col": ccol,
                        "parent_table": ptable,
                        "parent_col": pcol
                    })
                    schema_graph["tables"][ptable]["referenced_by"].append({
                        "child_table": ctable,
                        "child_col": ccol,
                        "parent_col": pcol
                    })
                    
            # QUERY 4 — Primary keys
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND COLUMN_KEY = 'PRI'
            """, (db_name,))
            for row in cursor.fetchall():
                tname = row["TABLE_NAME"]
                cname = row["COLUMN_NAME"]
                if tname in schema_graph["tables"]:
                    schema_graph["tables"][tname]["primary_keys"].append(cname)

            cursor.close()

            # === END OF PHASE 1 — Set self.tables and self.columns immediately ===
            # This must happen before Phase 2 so wizard always receives schema data
            # even if Phase 2 fails.
            self.tables = sorted(list(schema_graph["tables"].keys()))
            self.columns = {}
            for _tbl_name, _tbl_data in schema_graph["tables"].items():
                self.columns[_tbl_name] = [
                    {
                        "COLUMN_NAME": _col_info["name"],
                        "DATA_TYPE": _col_info.get("data_type", ""),
                        "COLUMN_KEY": _col_info.get("column_key", "")
                    }
                    for _col_info in _tbl_data["columns"].values()
                ]
            _log.info(
                "[demand_driven_discover] Phase 1 complete. Found %d tables: %s",
                len(self.tables), self.tables
            )
            # Phase 2 begins below — any exception here does NOT clear self.tables or self.columns

            # ────────────────────────────────────────────────────────
            # PHASE 2 — TARGETED DATA RETRIEVAL MAPPING
            # ────────────────────────────────────────────────────────
            
            # STEP 1: Filter roles based on model manifest
            from logic.model_manifest import get_model_required_features
            model_features = get_model_required_features()
            
            filtered_roles = {}
            for role_name, fields in ALL_ROLES.items():
                if not model_features:
                    filtered_roles[role_name] = fields
                else:
                    filtered_fields = []
                    for f in fields:
                        if f.requirement_level == "CRITICAL":
                            filtered_fields.append(f)
                        elif any(syn in model_features for syn in f.synonyms):
                            filtered_fields.append(f)
                        elif f.purpose in model_features:
                            filtered_fields.append(f)
                    if filtered_fields:
                        filtered_roles[role_name] = filtered_fields
                        
            # Score every table against every filtered role
            role_scores = {r: [] for r in filtered_roles.keys()}
            
            for tname, tdata in schema_graph["tables"].items():
                lower_cols = set(tdata["columns"].keys())
                for role_name, field_specs in filtered_roles.items():
                    score = 0
                    matched_cols = {}
                    for fspec in field_specs:
                        found = False
                        for syn in fspec.synonyms:
                            if syn in lower_cols:
                                score += fspec.score_weight
                                matched_cols[fspec.purpose] = tdata["columns"][syn]["name"]
                                found = True
                                break
                        if not found and fspec.requirement_level == "CRITICAL":
                            score -= 5
                        elif found and fspec.requirement_level == "SUPPLEMENTARY":
                            score += fspec.score_weight
                    if score > 0:
                        t_lower = tname.lower()
                        if role_name == "STUDENT_MASTER" and ("student" in t_lower or "user" in t_lower or "profile" in t_lower):
                            score += 50
                        elif role_name == "ACADEMIC_RECORDS" and ("academic" in t_lower or "mark" in t_lower or "result" in t_lower or "risk" in t_lower or "grade" in t_lower or "exam" in t_lower):
                            score += 50
                        elif role_name == "BRANCH_MASTER" and ("branch" in t_lower or "dept" in t_lower or "department" in t_lower or "program" in t_lower or "course" in t_lower):
                            score += 50
                        elif role_name == "PARENT_CONTACTS" and ("parent" in t_lower or "guardian" in t_lower or "contact" in t_lower or "family" in t_lower):
                            score += 50
                            
                        role_scores[role_name].append((score, tname, matched_cols))
            
            # STEP 2: Select best candidate per role
            candidates = {}
            for role_name, scores in role_scores.items():
                if not scores:
                    candidates[role_name] = None
                    continue
                scores.sort(key=lambda x: x[0], reverse=True)
                best_score, best_tname, best_cols = scores[0]
                
                # Check if all CRITICAL fields are present directly or can be resolved
                missing_critical = []
                present_important = 0
                missing_important = []
                
                for fspec in ALL_ROLES[role_name]:
                    resolved = False
                    
                    if fspec.purpose in best_cols:
                        resolved = True
                    elif fspec.field_type == "FK_LOOKUP":
                        # FK_LOOKUP RESOLUTION ALGORITHM
                        for syn in fspec.synonyms:
                            if syn in schema_graph["tables"][best_tname]["columns"]:
                                fk_col_name = schema_graph["tables"][best_tname]["columns"][syn]["name"]
                                # check if this is a foreign key
                                for fk in schema_graph["tables"][best_tname]["foreign_keys"]:
                                    if fk["child_col"] == fk_col_name:
                                        ptable = fk["parent_table"]
                                        if fspec.lookup_hint and any(h in ptable.lower() for h in fspec.lookup_hint):
                                            # Look for display value
                                            pcols = schema_graph["tables"][ptable]["columns"]
                                            pval_col = None
                                            for val_hint in fspec.lookup_value_column_hints:
                                                if val_hint in pcols:
                                                    pval_col = pcols[val_hint]["name"]
                                                    break
                                            if not pval_col and pcols:
                                                pval_col = next(iter(pcols.values()))["name"]
                                            
                                            if pval_col:
                                                best_cols[fspec.purpose] = {
                                                    "type": "FK_LOOKUP",
                                                    "raw_column": fk_col_name,
                                                    "lookup_table": ptable,
                                                    "lookup_pk": fk["parent_col"],
                                                    "lookup_value_col": pval_col
                                                }
                                                resolved = True
                                                break
                            if resolved: break
                    
                    if not resolved and fspec.fallback_recipes:
                        # Process Fallback Recipes (DERIVED_AGGREGATE / STUDENT_LINKED_TABLE)
                        for recipe in fspec.fallback_recipes:
                            src_hints = recipe.get("source_table_hints", [])
                            # Find a matching table in schema
                            matched_table = None
                            for tbl in schema_graph["tables"].keys():
                                if any(h in tbl.lower() for h in src_hints):
                                    matched_table = tbl
                                    break
                            
                            if matched_table:
                                val_hints = recipe.get("value_column_hints", [])
                                matched_col = None
                                for col in schema_graph["tables"][matched_table]["columns"].keys():
                                    if any(h in col.lower() for h in val_hints):
                                        matched_col = schema_graph["tables"][matched_table]["columns"][col]["name"]
                                        break
                                
                                if matched_col:
                                    best_cols[fspec.purpose] = {
                                        "type": recipe["resolution_type"],
                                        "recipe": recipe,
                                        "resolved_table": matched_table,
                                        "resolved_column": matched_col
                                    }
                                    resolved = True
                                    break
                    
                    if resolved:
                        if getattr(fspec, "requirement_level", "") == "IMPORTANT":
                            present_important += 1
                    else:
                        req_level = getattr(fspec, "requirement_level", "SUPPLEMENTARY")
                        if req_level == "CRITICAL":
                            missing_critical.append(fspec.purpose)
                        elif req_level == "IMPORTANT":
                            missing_important.append(fspec.purpose)
                
                # Acceptance Rules
                if role_name == "ACADEMIC_RECORDS":
                    if missing_critical:
                        return {"error": f"CRITICAL fields missing for {role_name} in best table {best_tname}: {missing_critical}"}
                    if present_important == 0:
                        return {"error": f"ACADEMIC_RECORDS requires at least one IMPORTANT field, none found in {best_tname}"}
                elif role_name != "PARENT_CONTACTS":
                    if missing_critical:
                        return {"error": f"CRITICAL fields missing for {role_name} in best table {best_tname}: {missing_critical}"}
                
                candidates[role_name] = {"table": best_tname, "score": best_score, "cols": best_cols}
            
            s_cand = candidates.get("STUDENT_MASTER")
            a_cand = candidates.get("ACADEMIC_RECORDS")
            b_cand = candidates.get("BRANCH_MASTER")
            p_cand = candidates.get("PARENT_CONTACTS")

            if not s_cand or not a_cand:
                return {"error": "Could not find valid candidate tables for STUDENT_MASTER and ACADEMIC_RECORDS."}

            s_tbl = s_cand["table"]
            a_tbl = a_cand["table"]
            s_cols = s_cand["cols"]
            a_cols = a_cand["cols"]

            # STEP 3: Resolve join paths between roles
            # STUDENT_MASTER -> ACADEMIC_RECORDS
            col_academic_join = ""
            for fk in schema_graph["tables"][a_tbl]["foreign_keys"]:
                if fk["parent_table"] == s_tbl:
                    col_academic_join = fk["child_col"]
                    break
            
            if not col_academic_join:
                # fallback heuristics
                student_pk = schema_graph["tables"][s_tbl]["primary_keys"][0] if schema_graph["tables"][s_tbl]["primary_keys"] else "id"
                student_id_col = s_cols.get("student_id")
                a_columns = schema_graph["tables"][a_tbl]["columns"]
                
                # Check for columns named similarly to student_id synonyms
                for syn in STUDENT_MASTER_FIELDS[0].synonyms:
                    if syn in a_columns:
                        col_academic_join = a_columns[syn]["name"]
                        break
            
            # STUDENT_MASTER -> BRANCH_MASTER
            b_tbl = b_cand["table"] if b_cand else ""
            col_branch_fk = s_cols.get("branch_foreign_key")
            col_branch_pk = ""
            col_branch_name = ""
            col_branch_type = "DIRECT"
            
            if isinstance(col_branch_fk, dict):
                col_branch_type = "FK_LOOKUP"
                b_tbl = col_branch_fk["lookup_table"]
                col_branch_pk = col_branch_fk["lookup_pk"]
                col_branch_name = col_branch_fk["lookup_value_col"]
                col_branch_fk = col_branch_fk["raw_column"]
            elif col_branch_fk and isinstance(col_branch_fk, str):
                # Infer the lookup table name
                if col_branch_fk.endswith("_id"):
                    base_name = col_branch_fk[:-3]
                    possible_tables = [base_name + "s", base_name, base_name + "es"]
                    for pt in possible_tables:
                        if pt in schema_graph["tables"]:
                            b_tbl = pt
                            col_branch_pk = "id" if "id" in schema_graph["tables"][pt]["columns"] else next(iter(schema_graph["tables"][pt]["columns"]))
                            for c in schema_graph["tables"][pt]["columns"]:
                                if "name" in c or "title" in c or "desc" in c:
                                    col_branch_name = c
                                    break
                            col_branch_type = "FK_LOOKUP"
                            break
                            
            if not col_branch_pk and b_tbl:
                b_cols = b_cand["cols"] if b_cand else {}
                col_branch_type = "FK_LOOKUP"
                col_branch_pk = schema_graph["tables"][b_tbl]["primary_keys"][0] if schema_graph["tables"][b_tbl]["primary_keys"] else "id"
                col_branch_name = b_cols.get("branch_name", "name")

            # Year Handling
            year_col = s_cols.get("current_year", "")
            col_year_type = "DIRECT"
            col_year_lookup_table = ""
            col_year_lookup_pk = ""
            col_year_lookup_value = ""
            if isinstance(year_col, dict):
                col_year_type = year_col.get("type", "FK_LOOKUP")
                col_year_lookup_table = year_col.get("lookup_table", "")
                col_year_lookup_pk = year_col.get("lookup_pk", "")
                col_year_lookup_value = year_col.get("lookup_value_col", "")
                year_col = year_col.get("raw_column", str(year_col))

            # STUDENT_MASTER -> PARENT_CONTACTS
            p_tbl = p_cand["table"] if p_cand and "student_foreign_key" in p_cand["cols"] else ""
            col_parent_join = ""
            col_parent_email = ""
            col_parent_phone = ""
            if p_tbl:
                p_cols = p_cand["cols"]
                col_parent_join = p_cols.get("student_foreign_key", "")
                col_parent_email = p_cols.get("parent_email", "")
                col_parent_phone = p_cols.get("parent_phone", "")

            # STEP 4 & 5: Build mapping config and Unmapped Attribute Catalog
            import datetime
            mapping_extensions = {}
            extended_features = []
            
            def extract_extensions(cols_dict):
                for k, v in cols_dict.items():
                    if isinstance(v, dict) and v.get("type") in ("DERIVED_AGGREGATE", "STUDENT_LINKED_TABLE"):
                        mapping_extensions[k] = v
                        cols_dict[k] = "" # Flatten so legacy flat mapper skips it
            
            extract_extensions(s_cols)
            extract_extensions(a_cols)
            
            # Phase 5: Unmapped Attribute Catalog
            mapped_cols_in_tables = {s_tbl: set(), a_tbl: set()}
            for cols_dict, tbl in [(s_cols, s_tbl), (a_cols, a_tbl)]:
                for k, v in cols_dict.items():
                    if isinstance(v, str) and v: mapped_cols_in_tables[tbl].add(v)
                    elif isinstance(v, dict) and "raw_column" in v: mapped_cols_in_tables[tbl].add(v["raw_column"])
            
            for tbl in [s_tbl, a_tbl]:
                for col_name, col_data in schema_graph["tables"][tbl]["columns"].items():
                    if col_name not in mapped_cols_in_tables[tbl]:
                        t = col_data.get("type", "unknown").lower()
                        if any(dt in t for dt in ["int", "float", "double", "decimal", "varchar", "char", "enum"]):
                            if col_name.endswith("_id") or col_name == "id": continue
                            extended_features.append({
                                "table": tbl,
                                "column": col_name,
                                "type": col_data.get("type", "unknown"),
                                "distinct_count": col_data.get("distinct_values_count", 0)
                            })

            flat = {
                "strategy": "ADAPTER",
                "discovery_db_name": db_name,
                "discovery_timestamp": datetime.datetime.now().isoformat(),
                
                "tbl_student": s_tbl,
                "tbl_academic": a_tbl,
                "tbl_branch": b_tbl,
                "tbl_parent_contacts": p_tbl,
                
                "col_student_id": schema_graph["tables"][s_tbl]["primary_keys"][0] if schema_graph["tables"][s_tbl]["primary_keys"] else "id",
                "col_student_name": s_cols.get("full_name", ""),
                
                "col_student_year": year_col,
                "col_year_type": col_year_type,
                "col_year_lookup_table": col_year_lookup_table,
                "col_year_lookup_pk": col_year_lookup_pk,
                "col_year_lookup_value": col_year_lookup_value,
                
                "col_branch_fk": col_branch_fk,
                "col_branch_pk": col_branch_pk,
                "col_branch_name": col_branch_name,
                "col_branch_type": col_branch_type,
                
                "col_academic_join": col_academic_join,
                "col_attendance": a_cols.get("attendance_pct", ""),
                "col_internal_marks": a_cols.get("internal_marks", ""),
                "col_cgpa": a_cols.get("cgpa", ""),
                "col_backlogs": a_cols.get("backlog_count", ""),
                "col_semester": a_cols.get("semester", ""),
                "col_mid_exam": a_cols.get("mid_exam_score", ""),
                "col_lab_perf": a_cols.get("lab_performance", ""),
                "col_assign_marks": a_cols.get("assignment_marks", ""),
                "col_tenth": s_cols.get("tenth_percentage", a_cols.get("tenth_percentage", "")),
                "col_inter": s_cols.get("inter_percentage", a_cols.get("inter_percentage", "")),
                "col_diploma": s_cols.get("diploma_percentage", a_cols.get("diploma_percentage", "")),
                "col_cons_abs": a_cols.get("consecutive_absences", ""),
                "col_leave_freq": a_cols.get("leave_frequency", ""),
                
                "tbl_history": a_tbl,  # academic_records table is also semester history
                "col_student_join": col_academic_join,  # same join column
                
                "col_parent_join": col_parent_join,
                "col_parent_email": col_parent_email or s_cols.get("parent_email", ""),
                "col_parent_phone": col_parent_phone or s_cols.get("parent_phone", ""),
                
                "_student_count": schema_graph["tables"][s_tbl].get("rows", 0),
                "mapping_extensions": mapping_extensions,
                "extended_features": extended_features,
                "raw_result": {"status": "success", "message": "Phase 2 detection completed."} # Fallback for UI
            }
            
            # Diagnostic: log top candidates for each role
            for _role_name, _scored in role_scores.items():
                _top3 = sorted(_scored, key=lambda x: x[0], reverse=True)[:3]
                _log.info("[demand_driven_discover] Role %s top candidates: %s",
                          _role_name, [(score, tbl) for score, tbl, _ in _top3])

            _log.info(f"[demand_driven_discover] Complete. student={s_tbl}, academic={a_tbl}, branch={b_tbl}")
            return flat
        except Exception as e:
            _log.error(f"[demand_driven_discover] Error: {e}", exc_info=True)
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # SECONDARY API — Validate Stored Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def validate_stored_mapping(
        connection,
        mapping: dict,
        db_name: str
    ) -> ValidationResult:
        """
        Validates every table and column in a stored mapping against the live ERP.
        Handles both legacy mapping keys and new Phase 2 mapping keys.
        """
        missing = []
        
        # Helper to get the correct key based on mapping format
        def _get(*keys):
            for k in keys:
                if k in mapping and mapping[k]:
                    return mapping[k]
            return ""

        # Check required tables
        s_tbl = _get("tbl_student")
        a_tbl = _get("tbl_academic")
        b_tbl = _get("tbl_branch")
        
        # (Table_val, Column_val, Purpose)
        CHECKS = []
        
        if s_tbl:
            CHECKS.extend([
                (s_tbl, _get("col_student_id", "col_id"), "student_id"),
                (s_tbl, _get("col_student_name", "col_name"), "full_name"),
                (s_tbl, _get("col_branch_fk", "col_branch_join", "branch_fk_in_student"), "branch_foreign_key"),
                (s_tbl, _get("col_student_year", "col_year"), "current_year"),
            ])
            
        if a_tbl:
            CHECKS.extend([
                (a_tbl, _get("col_academic_join", "col_student_join"), "student_foreign_key"),
                (a_tbl, _get("col_semester", "col_semester"), "semester"),
                (a_tbl, _get("col_att", "col_attendance"), "attendance_pct"),
                (a_tbl, _get("col_marks", "col_internal_marks"), "internal_marks"),
                (a_tbl, _get("col_backlogs", "col_backlogs"), "backlog_count"),
            ])
            
        if b_tbl:
            CHECKS.extend([
                (b_tbl, _get("col_branch_pk", "branch_pk_in_branch_table", "col_branch_pk"), "branch_id"),
                (b_tbl, _get("col_branch_name", "branch_name_column", "col_branch_name"), "branch_name"),
            ])

        p_tbl = _get("tbl_parent_contacts", "tbl_parent_contacts")
        if p_tbl:
            CHECKS.extend([
                (p_tbl, _get("col_parent_student_join", "col_parent_join"), "student_foreign_key"),
                (p_tbl, _get("col_parent_email_in_tbl", "col_parent_email_in_tbl"), "parent_email"),
                (p_tbl, _get("col_parent_phone_in_tbl", "col_parent_phone_in_tbl"), "parent_phone"),
            ])

        if _get("year_field_type", "col_year_type") == "FK_LOOKUP":
            y_tbl = _get("year_lookup_table", "col_year_lookup_table")
            if y_tbl:
                CHECKS.extend([
                    (y_tbl, _get("year_lookup_pk", "col_year_lookup_pk"), "year_id_pk"),
                    (y_tbl, _get("year_lookup_value", "col_year_lookup_value"), "year_name_display"),
                ])

        # Parse mapping_extensions to skip extended fields
        ext_json_str = _get("mapping_extensions_json", "mapping_extensions")
        ext = {}
        if isinstance(ext_json_str, dict):
            ext = ext_json_str
        elif isinstance(ext_json_str, str) and ext_json_str:
            import json
            try: ext = json.loads(ext_json_str)
            except: pass

        try:
            cursor = connection.cursor(dictionary=True)
            for tbl_val, col_val, purpose in CHECKS:
                if not tbl_val or not col_val:
                    continue
                
                # If this field is handled by an extension, it doesn't live in the base table
                if purpose in ext:
                    continue
                
                cursor.execute("""
                    SELECT COUNT(*) as count FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
                """, (db_name, tbl_val, col_val))
                
                row = cursor.fetchone()
                if not row or row['count'] == 0:
                    missing.append((tbl_val, col_val, purpose))
            
            cursor.close()
        except Exception as e:
            return ValidationResult(False, [], False, f"Database error during validation: {str(e)}")

        is_valid = len(missing) == 0
        error_msg = ""
        if not is_valid:
            error_msg = f"Missing {len(missing)} required columns in ERP schema."

        return ValidationResult(
            is_valid=is_valid,
            missing_columns=missing,
            correctable=False,  # Phase 1/2 redesign handles correction differently now
            error_message=error_msg
        )

    @staticmethod
    def validate_stored_mapping_legacy(
        connection,
        mapping: dict,
        db_name: str,
    ) -> MappingValidationResult:
        """
        Original validation logic for compatibility with SyncWorker.
        """
        result = MappingValidationResult()
        result.corrected_mapping = dict(mapping)  # Start as copy

        # Map: mapping_key → (table_mapping_key, field_purpose, is_required)
        COL_SPEC = {
            "col_id":           ("tbl_student",  "student_id",          True),
            "col_name":         ("tbl_student",  "full_name",           True),
            "branch_fk_in_student":  ("tbl_student",  "branch_foreign_key",  True),
            "col_year":         ("tbl_student",  "current_year",        True),
            "col_email":        ("tbl_student",  "email",               False),
            "col_parent_phone": ("tbl_student",  "parent_phone",        False),
            "col_parent_email": ("tbl_student",  "parent_email",        False),
            "col_student_join": ("tbl_academic", "student_foreign_key", True),
            "col_att":          ("tbl_academic", "attendance_pct",      True),
            "col_marks":        ("tbl_academic", "internal_marks",      True),
            "col_backlogs":     ("tbl_academic", "backlog_count",       True),
            "col_cgpa":         ("tbl_academic", "cgpa",                False),
            "col_tenth":        ("tbl_academic", "tenth_percentage",    False),
            "col_inter":        ("tbl_academic", "inter_percentage",    False),
            "col_diploma":      ("tbl_academic", "diploma_percentage",  False),
            "col_lab_perf":     ("tbl_academic", "lab_performance",     False),
            "col_mid_exam":     ("tbl_academic", "mid_exam_score",      False),
            "col_cons_abs":     ("tbl_academic", "consecutive_absences", False),
            "col_leave_freq":   ("tbl_academic", "leave_frequency",     False),
            "col_assign_marks": ("tbl_academic", "assignment_marks",    False),
            "branch_name_column":  ("tbl_branch",   "branch_name",         True),
        }

        # Build purpose → synonyms lookup from manifest
        PURPOSE_SYNONYMS: Dict[str, List[str]] = {}
        for role_fields in ALL_ROLES.values():
            for fspec in role_fields:
                PURPOSE_SYNONYMS[fspec.purpose] = fspec.synonyms

        strategy = mapping.get("strategy", "ADAPTER")
        if strategy == "VIEW":
            # VIEW strategy uses fixed columns — always valid
            _log.debug("validate_stored_mapping: VIEW strategy, skipping validation.")
            return result

        try:
            cursor = connection.cursor(dictionary=True)

            # Load actual columns for each table from INFORMATION_SCHEMA
            tables_to_check = {
                k: mapping.get(k, "") for k in ["tbl_student", "tbl_academic", "tbl_branch"]
            }
            live_columns: Dict[str, set] = {}  # table_name → set of lowercase col names

            for role_key, tbl_name in tables_to_check.items():
                if not tbl_name:
                    live_columns[role_key] = set()
                    continue
                cursor.execute("""
                    SELECT LOWER(COLUMN_NAME) AS col
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """, (db_name, tbl_name))
                live_columns[role_key] = {r["col"] for r in cursor.fetchall()}

            cursor.close()

        except Exception as e:
            _log.error(f"validate_stored_mapping: INFORMATION_SCHEMA query failed: {e}")
            result.is_fully_valid = False
            result.error_summary = f"Cannot query INFORMATION_SCHEMA: {e}"
            return result

        # Validate each mapped column
        for mapping_key, (tbl_key, purpose, is_required) in COL_SPEC.items():
            stored_col = mapping.get(mapping_key, "")

            # Empty optional column — fine
            if not stored_col and not is_required:
                continue

            # Empty required column — try re-discovery
            actual_cols = live_columns.get(tbl_key, set())
            col_valid = stored_col.lower() in actual_cols if stored_col else False

            if col_valid:
                result.field_results.append(FieldValidationResult(
                    mapping_key=mapping_key,
                    stored_value=stored_col,
                    is_valid=True,
                    is_required=is_required,
                ))
                continue

            # Invalid or empty — attempt re-discovery
            synonyms = PURPOSE_SYNONYMS.get(purpose, [])
            rediscovered = next(
                (syn for syn in synonyms if syn in actual_cols),
                ""
            )

            if rediscovered:
                _log.info(
                    f"validate_stored_mapping: Auto-corrected '{mapping_key}': "
                    f"'{stored_col}' → '{rediscovered}'"
                )
                result.corrected_mapping[mapping_key] = rediscovered
                result.field_results.append(FieldValidationResult(
                    mapping_key=mapping_key,
                    stored_value=stored_col,
                    is_valid=False,
                    is_required=is_required,
                    rediscovered_value=rediscovered,
                ))
            else:
                tbl_name = mapping.get(tbl_key, "unknown")
                error_msg = (
                    f"The column configured for '{purpose}' ('{stored_col}') "
                    f"no longer exists in table '{tbl_name}'. "
                    f"Please run the Schema Detection Wizard to update the mapping."
                )
                _log.warning(f"validate_stored_mapping: {error_msg}")
                result.field_results.append(FieldValidationResult(
                    mapping_key=mapping_key,
                    stored_value=stored_col,
                    is_valid=False,
                    is_required=is_required,
                    error_msg=error_msg,
                ))
                if is_required:
                    result.has_required_failures = True
                    result.is_fully_valid = False

        if result.has_required_failures:
            failed = [
                f.mapping_key for f in result.field_results
                if not f.is_valid and f.is_required and not f.rediscovered_value
            ]
            result.error_summary = (
                f"Required ERP columns are missing or renamed: {', '.join(failed)}. "
                f"Please re-run the Schema Detection Wizard."
            )

        return result

    # ------------------------------------------------------------------
    # DEPRECATED — Full-scan approach (fallback only, not called by new code)
    # ------------------------------------------------------------------

    def scan_schema(self) -> bool:
        """
        DEPRECATED: Full database scan. Use demand_driven_discover() instead.
        Preserved for backward compatibility with the ERP wizard UI flow.
        """
        if not self.conn:
            return False
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s
        """, (self.db,))
        rows = cursor.fetchall()
        self.tables = [r["TABLE_NAME"] for r in rows]
        self._views = [r["TABLE_NAME"] for r in rows if r["TABLE_TYPE"] == "VIEW"]

        for table in self.tables:
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            """, (self.db, table))
            self.columns[table] = cursor.fetchall()

        cursor.execute("""
            SELECT TABLE_NAME as `table`, COLUMN_NAME as `column`,
                   REFERENCED_TABLE_NAME as ref_table,
                   REFERENCED_COLUMN_NAME as ref_column
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_SCHEMA = %s AND TABLE_SCHEMA = %s
        """, (self.db, self.db))
        self.foreign_keys = cursor.fetchall()
        cursor.close()
        _log.info(f"[scan_schema DEPRECATED] Scanned {len(self.tables)} tables/views.")
        return True

    def detect_schema(self) -> dict:
        """
        DEPRECATED: Uses full-scan data. Use demand_driven_discover() instead.
        Preserved for ERP wizard backward compatibility.
        """
        # Delegate to demand-driven if connection is available
        if self.conn:
            return self.demand_driven_discover(self.conn)
        return {"error": "No connection available"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_view_mapping(self) -> dict:
        """Produces the fixed mapping for the VIEW STRATEGY."""
        mapping = {
            "strategy": "VIEW",
            "tbl_student":      VIEW_STUDENT,
            "tbl_academic":     VIEW_ACADEMIC,
            "tbl_branch":       VIEW_BRANCH,
            "col_id":           "student_id",
            "col_name":         "full_name",
            "branch_fk_in_student":  "branch_id",
            "branch_name_column":  "branch_name",
            "col_year":         "current_year",
            "col_student_join": "student_id",
            "col_att":          "attendance_pct",
            "col_marks":        "internal_marks",
            "col_backlogs":     "backlog_count",
            "col_cgpa":         "cgpa",
            "col_tenth":        "tenth_percentage",
            "col_inter":        "inter_percentage",
            "col_diploma":      "diploma_percentage",
            "col_lab_perf":     "lab_performance",
            "col_mid_exam":     "mid_exam_score",
            "col_cons_abs":     "consecutive_absences",
            "col_leave_freq":   "leave_frequency",
            "col_assign_marks": "assignment_marks",
            "col_email":        "email",
            "col_parent_phone": "parent_phone",
            "col_parent_email": "parent_email",
        }
        mapping["raw_result"] = {
            "tbl_student":  {"name": VIEW_STUDENT,  "confidence": 100, "columns": {}},
            "tbl_academic": {"name": VIEW_ACADEMIC, "confidence": 100, "columns": {}},
            "tbl_branch":   {"name": VIEW_BRANCH,   "confidence": 100, "columns": {}},
        }
        return mapping

    def validate_flat_mapping(self, mapping: dict) -> Tuple[bool, str]:
        """
        Quick validation using the already-scanned self.columns dict.
        Used by ERP wizard after detect_schema() to confirm before saving.
        """
        table_fields = ["tbl_student", "tbl_academic", "tbl_branch"]
        col_to_table = {
            "col_id":           "tbl_student",
            "col_name":         "tbl_student",
            "branch_fk_in_student":  "tbl_student",
            "col_year":         "tbl_student",
            "col_email":        "tbl_student",
            "col_parent_phone": "tbl_student",
            "col_parent_email": "tbl_student",
            "col_student_join": "tbl_academic",
            "col_att":          "tbl_academic",
            "col_marks":        "tbl_academic",
            "col_backlogs":     "tbl_academic",
            "branch_name_column":  "tbl_branch",
        }
        known_tables = [t.lower() for t in self.tables]
        for tf in table_fields:
            tbl = mapping.get(tf, "")
            if tbl and tbl.lower() not in known_tables:
                return False, f"Table '{tbl}' does not exist in database."
        for col_field, tbl_field in col_to_table.items():
            col = mapping.get(col_field, "")
            tbl = mapping.get(tbl_field, "")
            if col and tbl:
                cols = [c["COLUMN_NAME"].lower() for c in self.columns.get(tbl, [])]
                if col.lower() not in cols:
                    return False, f"Column '{col}' does not exist in table '{tbl}'."
        return True, "Valid"
