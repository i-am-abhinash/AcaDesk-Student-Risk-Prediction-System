import logging
import json

logger = logging.getLogger(__name__)

SYNONYMS = {
    "student_id": ["student_id", "roll_no", "roll_number", "reg_no", "registration_no", "regd_no", "admission_no", "usn", "htno", "stud_id", "enrollment_no", "id"],
    "full_name": ["name", "student_name", "full_name", "stud_name", "candidate_name", "sname", "s_name"],
    "department_fk": ["branch_id", "dept_id", "department_id", "program_id", "course_id", "dept_code", "branch_code"],
    "current_year": ["year", "academic_year", "current_year", "study_year", "yr", "year_id", "year_level", "class_id", "level_id", "programme_year", "year_of_study"],
    "email": ["email", "student_email", "mail", "email_id"],
    "attendance_pct": ["attendance", "attendance_pct", "att_pct", "attendance_percentage", "avg_attendance", "attendance_percent", "overall_attendance"],
    "internal_marks": ["marks", "internal_marks", "avg_marks", "ia_marks", "cia_marks", "internal_score", "sessional", "int_marks", "theory_marks"],
    "cgpa": ["cgpa", "gpa", "cumulative_gpa", "cgpa_value", "grade_points", "cum_gpa"],
    "backlogs": ["backlogs", "backlog_count", "arrears", "no_of_arrears", "pending_subjects", "failed_subjects", "supply_count", "arrear_count"],
    "semester": ["semester", "sem", "sem_no", "semester_no", "current_semester", "sem_number"],
    "mid_exam_score": ["mid_exam_score", "mid_marks", "midterm_score", "mid_score", "mid_exam"],
    "lab_performance": ["lab_performance", "lab_marks", "lab_score", "practical_marks", "lab_internal"],
    "assignment_marks": ["assignment_marks", "assignment_score", "assignments", "hw_marks"],
    "consecutive_absences": [],
    "tenth_percentage": ["tenth", "tenth_percentage", "ssc_pct", "tenth_pct", "x_pct", "class10_pct", "ssc_marks"],
    "inter_percentage": ["inter", "intermediate_percentage", "hsc_pct", "plus2_pct", "xii_pct", "class12_pct"],
    "diploma_percentage": ["diploma", "diploma_percentage", "polytechnic_pct", "poly_pct"],
    "parent_email": ["parent_email", "father_email", "guardian_email"],
    "parent_phone": ["parent_phone", "father_phone", "guardian_phone", "phone"],
    "admission_type": ["admission_type", "adm_type", "category"],
    "entrance_rank": ["rank", "entrance_rank", "cet_rank"]
}

class ColumnResolver:
    def __init__(self, conn, schema_graph: dict, discovery_scope: set, selected_tables: dict, join_paths: dict):
        self.conn = conn
        self.schema_graph = schema_graph
        self.discovery_scope = discovery_scope
        self.selected_tables = selected_tables
        self.join_paths = join_paths
        self.consumed_columns = set() # table.column
        self.mapping = {}

    def run_resolution(self):
        # Resolve fields in order
        fields_to_resolve = [
            ("student_id", "STUDENT"), ("full_name", "STUDENT"), ("department_fk", "STUDENT"),
            ("current_year", "STUDENT"), ("email", "STUDENT"),
            ("semester", "ACADEMIC"), ("cgpa", "ACADEMIC"), ("internal_marks", "ACADEMIC"),
            ("backlogs", "ACADEMIC"), ("mid_exam_score", "ACADEMIC"), ("lab_performance", "ACADEMIC"),
            ("assignment_marks", "ACADEMIC"), ("tenth_percentage", "ACADEMIC"),
            ("inter_percentage", "ACADEMIC"), ("diploma_percentage", "ACADEMIC"),
            ("attendance_pct", "ATTENDANCE"), ("consecutive_absences", "ATTENDANCE"),
            ("parent_email", "STUDENT"), ("parent_phone", "STUDENT"), ("admission_type", "STUDENT")
        ]
        
        for field, target_role in fields_to_resolve:
            res = self._resolve_field(field, target_role)
            self.mapping[field] = res
            
        # Extended features
        ext = self._build_extended_features()
        self.mapping["extended_features_json"] = json.dumps(ext)
        return self.mapping

    def _resolve_field(self, field: str, target_role: str):
        target_tbl = self.selected_tables.get(target_role)
        if not target_tbl:
            target_tbl = self.selected_tables.get("STUDENT") # Fallback
            
        synonyms = SYNONYMS.get(field, [])
        
        result = {"method": "ABSENT"}

        # 1. DIRECT
        try:
            direct_res = self._try_direct(field, target_tbl, synonyms)
            if direct_res:
                self._consume(target_tbl, direct_res["column"])
                
                # 2. FK_LOOKUP
                if direct_res["column"].endswith("_id") or direct_res["column"].endswith("_code"):
                    try:
                        lookup = self._try_fk_lookup(target_tbl, direct_res["column"])
                        if lookup:
                            return lookup
                    except Exception as e:
                        logger.debug("FK_LOOKUP failed for %s: %s", field, e)
                return direct_res
        except Exception as e:
            logger.debug("DIRECT failed for %s: %s", field, e)
            
        # 3. STUDENT_LINKED
        if field in ["parent_email", "parent_phone", "admission_type", "entrance_rank"]:
            try:
                linked = self._try_student_linked(field, synonyms)
                if linked: return linked
            except Exception as e:
                logger.debug("STUDENT_LINKED failed for %s: %s", field, e)
            
        # 4. DERIVED_AGGREGATE
        if field in ["attendance_pct", "cgpa", "backlogs", "current_year"]:
            try:
                derived = self._try_derived(field)
                if derived: return derived
            except Exception as e:
                logger.debug("DERIVED failed for %s: %s", field, e)
            
        # 5. ABSENT
        critical_fields = ["student_id", "full_name", "department_fk"]
        important_fields = ["current_year", "attendance_pct", "cgpa", "backlogs"]
        
        if field in critical_fields:
            logger.warning("CRITICAL field '%s' could not be resolved", field)
        elif field in important_fields:
            logger.info("IMPORTANT field '%s' not found, prediction will use reduced feature set", field)
        else:
            logger.debug("SUPPLEMENTARY field '%s' absent", field)
            
        return result

    def _consume(self, tbl: str, col: str):
        self.consumed_columns.add(f"{tbl}.{col}")

    def _try_direct(self, field: str, tbl: str, synonyms: list):
        if not tbl or tbl not in self.schema_graph["tables"]: return None
        cols = self.schema_graph["tables"][tbl]["columns"]
        
        for syn in synonyms:
            for c_name in cols.keys():
                if c_name.lower() == syn:
                    logger.debug(f"Resolved {field} directly: {tbl}.{c_name}")
                    return {"method": "DIRECT", "table": tbl, "column": c_name}
        return None

    def _try_fk_lookup(self, tbl: str, col: str):
        # Check if tbl.col is an FK
        fks = self.schema_graph["tables"][tbl].get("foreign_keys", [])
        for fk in fks:
            if fk["column"].lower() == col.lower():
                ref_tbl = fk["ref_table"]
                ref_pk = fk["ref_column"]
                if ref_tbl in self.schema_graph["tables"]:
                    # Find display column
                    r_cols = self.schema_graph["tables"][ref_tbl]["columns"]
                    display_col = None
                    for c_name, c_info in r_cols.items():
                        if c_info["column_key"] != "PRI" and "char" in c_info["data_type"].lower():
                            if c_name.lower() in ["name", "title", "description", "branch_name", "dept_name"]:
                                display_col = c_name
                                break
                    if not display_col:
                        # Pick first non-pk char col
                        for c_name, c_info in r_cols.items():
                            if c_info["column_key"] != "PRI" and "char" in c_info["data_type"].lower():
                                display_col = c_name
                                break
                                
                    if display_col:
                        self._consume(ref_tbl, display_col)
                        return {
                            "method": "FK_LOOKUP",
                            "table": tbl,
                            "column": col,
                            "ref_table": ref_tbl,
                            "ref_pk": ref_pk,
                            "ref_display": display_col
                        }
        return None

    def _try_student_linked(self, field: str, synonyms: list):
        stud_tbl = self.selected_tables.get("STUDENT")
        if not stud_tbl: return None
        
        # Search hop1/hop2 tables that have FK to student
        for tbl in self.discovery_scope:
            if tbl == stud_tbl or tbl not in self.schema_graph["tables"]: continue
            
            fks = self.schema_graph["tables"][tbl].get("foreign_keys", [])
            has_fk = None
            for fk in fks:
                if fk["ref_table"] == stud_tbl:
                    has_fk = fk
                    break
                    
            if has_fk:
                cols = self.schema_graph["tables"][tbl]["columns"]
                for syn in synonyms:
                    for c_name in cols.keys():
                        if c_name.lower() == syn:
                            self._consume(tbl, c_name)
                            return {
                                "method": "STUDENT_LINKED",
                                "table": tbl,
                                "column": c_name,
                                "fk_to_student": has_fk["column"]
                            }
        return None

    def _sample_col(self, tbl: str, col: str):
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT DISTINCT {col} FROM {tbl} WHERE {col} IS NOT NULL LIMIT 30")
            rows = cursor.fetchall()
            cursor.close()
            return [r[0] for r in rows if r[0] is not None]
        except Exception as e:
            logger.error(f"Sample error for {tbl}.{col}: {e}")
            return []

    def _try_derived(self, field: str):
        stud_tbl = self.selected_tables.get("STUDENT")
        
        if field == "attendance_pct":
            att_tbl = self.selected_tables.get("ATTENDANCE")
            if not att_tbl or att_tbl not in self.schema_graph["tables"]: return None
            
            join_path = self.join_paths.get("student_to_attendance")
            if not join_path or not join_path.get("direct_fk"): return None
            stud_fk = join_path["path"][0]["from_col"]
            
            cols = self.schema_graph["tables"][att_tbl]["columns"]
            status_col = None
            for syn in ["status", "att_status", "attendance_status", "present_flag", "is_present"]:
                if syn in cols:
                    status_col = syn
                    break
                    
            if status_col:
                samples = self._sample_col(att_tbl, status_col)
                present_vals = []
                for s in samples:
                    s_str = str(s).lower()
                    if s_str in ["p", "present", "1", "y", "yes", "true"]:
                        present_vals.append(s)
                if present_vals:
                    return {
                        "method": "DERIVED_AGGREGATE",
                        "recipe": "attendance_pct",
                        "table": att_tbl,
                        "student_fk": stud_fk,
                        "status_col": status_col,
                        "present_values": present_vals
                    }
                    
        elif field == "cgpa":
            ac_tbl = self.selected_tables.get("ACADEMIC")
            if not ac_tbl or ac_tbl not in self.schema_graph["tables"]: return None
            
            join_path = self.join_paths.get("student_to_academic")
            if not join_path: return None
            
            cols = self.schema_graph["tables"][ac_tbl]["columns"]
            score_col = None
            for syn in ["gpa_points", "grade_points", "score", "points"]:
                if syn in cols:
                    score_col = syn
                    break
            
            if score_col:
                weight_col = None
                for syn in ["credits", "credit_hours", "weight", "units"]:
                    if syn in cols:
                        weight_col = syn
                        break
                return {
                    "method": "DERIVED_AGGREGATE",
                    "recipe": "cgpa",
                    "table": ac_tbl,
                    "join_path": join_path,
                    "score_col": score_col,
                    "weight_col": weight_col
                }
                
        elif field == "backlogs":
            ac_tbl = self.selected_tables.get("ACADEMIC")
            if not ac_tbl or ac_tbl not in self.schema_graph["tables"]: return None
            
            join_path = self.join_paths.get("student_to_academic")
            if not join_path: return None
            
            cols = self.schema_graph["tables"][ac_tbl]["columns"]
            grade_col = None
            for syn in ["grade", "result", "status", "exam_status"]:
                if syn in cols:
                    grade_col = syn
                    break
            
            if grade_col:
                samples = self._sample_col(ac_tbl, grade_col)
                fail_vals = []
                for s in samples:
                    s_str = str(s).lower()
                    if s_str in ["f", "fail", "failed", "backlog", "arrear", "ra", "detained", "u", "0", "ab", "absent"]:
                        fail_vals.append(s)
                if fail_vals:
                    return {
                        "method": "DERIVED_AGGREGATE",
                        "recipe": "backlogs",
                        "table": ac_tbl,
                        "join_path": join_path,
                        "grade_col": grade_col,
                        "fail_values": fail_vals
                    }

        elif field == "current_year":
            # Source B logic only for simplicity
            ac_tbl = self.selected_tables.get("ACADEMIC")
            if ac_tbl and ac_tbl in self.schema_graph["tables"]:
                cols = self.schema_graph["tables"][ac_tbl]["columns"]
                if "semester" in cols:
                    return {
                        "method": "DERIVED_AGGREGATE",
                        "recipe": "current_year",
                        "table": ac_tbl,
                        "sem_col": "semester"
                    }
        return None

    def _build_extended_features(self):
        catalog = []
        for tbl in self.discovery_scope:
            if tbl not in self.schema_graph["tables"]: continue
            cols = self.schema_graph["tables"][tbl]["columns"]
            for c_name, c_info in cols.items():
                if f"{tbl}.{c_name}" in self.consumed_columns: continue
                if c_info["column_key"] == "PRI": continue
                
                dt = c_info["data_type"].lower()
                is_numeric = any(t in dt for t in ["int", "float", "double", "decimal", "numeric"])
                is_short_text = "char" in dt or "varchar" in dt
                
                if is_numeric or is_short_text:
                    label = self._guess_label(c_name)
                    catalog.append({
                        "table": tbl,
                        "column": c_name,
                        "data_type": dt,
                        "potential_label": label
                    })
        logger.info("Extended features found: %s", [f["potential_label"] for f in catalog])
        return catalog

    def _guess_label(self, c_name: str) -> str:
        c_lower = c_name.lower()
        if "placement" in c_lower: return "Placement Score"
        if "disciplin" in c_lower: return "Disciplinary Record"
        if "certif" in c_lower: return "Certification Count"
        if "project" in c_lower: return "Project Evaluation"
        if "intern" in c_lower: return "Internship Record"
        if "skill" in c_lower: return "Skill Assessment"
        if "research" in c_lower: return "Research Credits"
        if "hack" in c_lower or "contest" in c_lower: return "Competition Score"
        return "Unknown Academic Attribute"
