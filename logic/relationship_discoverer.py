import logging

logger = logging.getLogger(__name__)

class BoundedRelationshipDiscovery:
    def __init__(self, schema_graph: dict, selected_tables: dict):
        """
        selected_tables: {"STUDENT": "students", "ACADEMIC": "academic_records", ...}
        """
        self.schema_graph = schema_graph
        self.selected_tables = {k: v for k, v in selected_tables.items() if v}
        self.discovery_scope = set(self.selected_tables.values())
        self.join_paths = {}

    def run_discovery(self):
        self._build_discovery_scope()
        self._resolve_all_join_paths()
        return self.join_paths, self.discovery_scope

    def _build_discovery_scope(self):
        """Builds discovery scope to a maximum of 2 hops from selected tables."""
        hop1 = set()
        
        # Hop 1
        for tbl in self.discovery_scope:
            if tbl not in self.schema_graph["tables"]: continue
            t_data = self.schema_graph["tables"][tbl]
            # Outbound FKs
            for fk in t_data.get("foreign_keys", []):
                hop1.add(fk["ref_table"])
            # Inbound FKs
            for ref in t_data.get("referenced_by", []):
                hop1.add(ref["child_table"])
                
        hop1 = hop1 - self.discovery_scope
        hop2 = set()
        
        # Hop 2
        for tbl in hop1:
            if tbl not in self.schema_graph["tables"]: continue
            t_data = self.schema_graph["tables"][tbl]
            for fk in t_data.get("foreign_keys", []):
                hop2.add(fk["ref_table"])
            for ref in t_data.get("referenced_by", []):
                hop2.add(ref["child_table"])
                
        hop2 = hop2 - self.discovery_scope - hop1
        
        self.discovery_scope.update(hop1)
        self.discovery_scope.update(hop2)
        logger.debug(f"Discovery scope built. Total tables in scope: {len(self.discovery_scope)}")

    def _resolve_all_join_paths(self):
        stud_tbl = self.selected_tables.get("STUDENT")
        if not stud_tbl or stud_tbl not in self.schema_graph["tables"]:
            return

        for role, target_tbl in self.selected_tables.items():
            if role == "STUDENT": continue
            path = self._resolve_path(stud_tbl, target_tbl)
            self.join_paths[f"student_to_{role.lower()}"] = path

    def _resolve_path(self, stud_tbl: str, target_tbl: str) -> dict:
        """
        Tries Strategies A, B, C, D in order.
        """
        if not target_tbl or target_tbl not in self.schema_graph["tables"]:
            return {}

        tables = self.schema_graph.get("tables", {})
        table_a = stud_tbl
        table_b = target_tbl
        
        # Strategy A - Direct FK (B -> A)
        if table_b in tables:
            for fk in tables[table_b].get("foreign_keys", []):
                if fk.get("ref_table", "").lower() == table_a.lower():
                    logger.info("Join path %s→%s: strategy=%s, from_col=%s, to_col=%s", table_a, table_b, "DIRECT_FK", fk["column"], fk["ref_column"])
                    return {
                        "direct_fk": True,
                        "path": [{
                            "from_table": table_b,
                            "from_col": fk["column"],
                            "to_table": table_a,
                            "to_col": fk["ref_column"]
                        }]
                    }
        
        # Strategy B - Reverse FK (A -> B)
        if table_a in tables:
            for fk in tables[table_a].get("foreign_keys", []):
                if fk.get("ref_table", "").lower() == table_b.lower():
                    logger.info("Join path %s→%s: strategy=%s, from_col=%s, to_col=%s", table_a, table_b, "DIRECT_FK", fk["column"], fk["ref_column"])
                    return {
                        "direct_fk": True,
                        "path": [{
                            "from_table": table_a,
                            "from_col": fk["column"],
                            "to_table": table_b,
                            "to_col": fk["ref_column"]
                        }]
                    }
                    
        # Strategy C - Shared Column Name
        student_id_synonyms = {
            "student_id", "roll_no", "roll_number",
            "reg_no", "registration_no", "usn",
            "stud_id", "admission_no", "hallticket_no",
            "enrollment_no", "id"
        }
        
        if table_a in tables and table_b in tables:
            cols_a = {c.lower(): c for c in tables[table_a]["columns"].keys()}
            cols_b = {c.lower(): c for c in tables[table_b]["columns"].keys()}
            shared = set(cols_a.keys()) & set(cols_b.keys()) & student_id_synonyms
            if shared:
                shared_col_lower = list(shared)[0]
                actual_col_a = cols_a[shared_col_lower]
                actual_col_b = cols_b[shared_col_lower]
                logger.info("Join path %s→%s: strategy=%s, from_col=%s, to_col=%s", table_a, table_b, "SHARED_COLUMN", actual_col_b, actual_col_a)
                return {
                    "direct_fk": True,
                    "path": [{
                        "from_table": table_b,
                        "from_col": actual_col_b,
                        "to_table": table_a,
                        "to_col": actual_col_a
                    }]
                }
                
        # Strategy D - One-hop bridge table
        for bridge_table, bridge_data in tables.items():
            if bridge_table.lower() in (table_a.lower(), table_b.lower()):
                continue
            fk_targets = {
                fk["ref_table"].lower() 
                for fk in bridge_data.get("foreign_keys", [])
            }
            if table_a.lower() in fk_targets and table_b.lower() in fk_targets:
                fk_to_a = next(fk for fk in bridge_data["foreign_keys"] if fk["ref_table"].lower() == table_a.lower())
                fk_to_b = next(fk for fk in bridge_data["foreign_keys"] if fk["ref_table"].lower() == table_b.lower())
                logger.info("Join path %s→%s: strategy=%s, from_col=%s, to_col=%s", table_a, table_b, "BRIDGE_TABLE", "N/A", "N/A")
                return {
                    "direct_fk": False,
                    "path": [
                        {
                            "from_table": table_b,
                            "from_col": fk_to_b["ref_column"],
                            "to_table": bridge_table,
                            "to_col": fk_to_b["column"]
                        },
                        {
                            "from_table": bridge_table,
                            "from_col": fk_to_a["column"],
                            "to_table": table_a,
                            "to_col": fk_to_a["ref_column"]
                        }
                    ]
                }
                
        # No path found
        logger.warning(
            "No join path found between %s and %s. Tried: direct FK, reverse FK, shared column, bridge table.",
            table_a, table_b
        )
        logger.info("Join path %s→%s: strategy=%s, from_col=%s, to_col=%s", table_a, table_b, "NOT_FOUND", "N/A", "N/A")
        return {}
