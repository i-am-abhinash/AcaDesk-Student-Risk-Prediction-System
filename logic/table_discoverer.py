import logging
import time

logger = logging.getLogger(__name__)

class TableConfidenceScorer:
    """Scores tables for specific required roles based on metadata."""
    
    @staticmethod
    def score_student_table(t_name, t_data) -> int:
        score = 0
        name_lower = t_name.lower()
        cols = {c.lower() for c in t_data.get("columns", {}).keys()}
        
        # Exact match
        if name_lower in ["student", "students", "student_master", "student_info"]:
            score += 50
        elif "student" in name_lower or "stud" in name_lower:
            score += 30
        elif any(kw in name_lower for kw in ["learner", "pupil", "candidate"]):
            score += 20
            
        # Columns
        if any(c in cols for c in ["name", "full_name", "student_name"]):
            score += 15
        if any(c in cols for c in ["roll_no", "registration_no", "student_id", "usn"]):
            score += 15
            
        # Row count
        rows = t_data.get("row_count", 0)
        if 50 <= rows <= 500000:
            score += 10
            
        # FK pointing to a department-like table
        fks = t_data.get("foreign_keys", [])
        for fk in fks:
            ref_tbl = fk["ref_table"].lower()
            if any(kw in ref_tbl for kw in ["dept", "department", "branch", "program"]):
                score += 10
                break
                
        logger.debug("Scored %s for STUDENT: %d", t_name, score)
        return score

    @staticmethod
    def score_academic_table(t_name, t_data, s_rows) -> int:
        score = 0
        name_lower = t_name.lower()
        cols_dict = t_data.get("columns", {})
        cols = {c.lower() for c in cols_dict.keys()}
        
        if name_lower in ["academic_records", "marks", "results", "grades", "exam_results", "academic"]:
            score += 50
        elif any(kw in name_lower for kw in ["mark", "grade", "result", "exam", "score", "academic"]):
            score += 30
            
        if any(c in cols for c in ["gpa", "cgpa", "marks", "score", "grade", "result", "percentage"]):
            score += 20
            
        fks = t_data.get("foreign_keys", [])
        for fk in fks:
            ref_tbl = fk["ref_table"].lower()
            if "student" in ref_tbl or "stud" in ref_tbl:
                score += 15
                break
                
        # Numeric columns
        has_numeric = False
        for c_info in cols_dict.values():
            dt = c_info["data_type"].lower()
            if "int" in dt or "float" in dt or "decimal" in dt or "double" in dt or "numeric" in dt:
                has_numeric = True
                break
        if has_numeric:
            score += 10
            
        # Row count
        rows = t_data.get("row_count", 0)
        if s_rows > 0 and rows > s_rows * 1.5:
            score += 10
            
        logger.debug("Scored %s for ACADEMIC: %d", t_name, score)
        return score

    @staticmethod
    def score_attendance_table(t_name, t_data, s_rows) -> int:
        score = 0
        name_lower = t_name.lower()
        cols_dict = t_data.get("columns", {})
        cols = {c.lower() for c in cols_dict.keys()}
        
        if name_lower in ["attendance", "daily_attendance", "attendance_log", "attendance_record"]:
            score += 50
        elif any(kw in name_lower for kw in ["attend", "present", "absent"]):
            score += 30
            
        if any(c in cols for c in ["status", "present_flag", "attendance_status", "att_status"]):
            score += 20
            
        has_date = False
        for c_info in cols_dict.values():
            dt = c_info["data_type"].lower()
            if "date" in dt or "time" in dt:
                has_date = True
                break
        if has_date:
            score += 15
            
        fks = t_data.get("foreign_keys", [])
        for fk in fks:
            ref_tbl = fk["ref_table"].lower()
            if "student" in ref_tbl or "stud" in ref_tbl:
                score += 15
                break
                
        rows = t_data.get("row_count", 0)
        if s_rows > 0 and rows >= s_rows * 10:
            score += 10
            
        logger.debug("Scored %s for ATTENDANCE: %d", t_name, score)
        return score

    @staticmethod
    def score_department_table(t_name, t_data) -> int:
        score = 0
        name_lower = t_name.lower()
        cols = {c.lower() for c in t_data.get("columns", {}).keys()}
        
        if name_lower in ["departments", "branch", "branches", "department", "dept", "programs", "courses"]:
            score += 50
        elif any(kw in name_lower for kw in ["dept", "branch", "department", "program"]):
            score += 30
            
        if any(c in cols for c in ["name", "title"]):
            score += 15
            
        rows = t_data.get("row_count", 0)
        if 1 <= rows <= 100:
            score += 20
            
        ref_by = t_data.get("referenced_by", [])
        for ref in ref_by:
            child = ref["child_table"].lower()
            if "student" in child or "stud" in child:
                score += 20
                break
                
        logger.debug("Scored %s for DEPARTMENT: %d", t_name, score)
        return score


class LightweightMetadataScan:
    def __init__(self, conn, db_name: str):
        self.conn = conn
        self.db_name = db_name
        self.schema_graph = {"tables": {}}
        self.all_tables = []
        
    def run_scan(self):
        """Runs the lightweight scan and returns (all_tables, schema_graph). Must run in under 3s."""
        t_start = time.time()
        cursor = self.conn.cursor(dictionary=True)
        try:
            # QUERY 1 - Tables
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_ROWS
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = %s
                AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_ROWS DESC
            """, (self.db_name,))
            for r in cursor.fetchall():
                tname = r["TABLE_NAME"]
                self.schema_graph["tables"][tname] = {
                    "row_count": r["TABLE_ROWS"] or 0,
                    "columns": {},
                    "primary_keys": [],
                    "foreign_keys": [],
                    "referenced_by": []
                }
                self.all_tables.append(tname)
                
            self.all_tables.sort()
            
            # QUERY 2 - Columns
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_KEY
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """, (self.db_name,))
            for r in cursor.fetchall():
                tname = r["TABLE_NAME"]
                if tname in self.schema_graph["tables"]:
                    cname = r["COLUMN_NAME"]
                    self.schema_graph["tables"][tname]["columns"][cname] = {
                        "data_type": r["DATA_TYPE"],
                        "column_key": r["COLUMN_KEY"]
                    }
                    
            # QUERY 3 - Foreign Keys
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME,
                       REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (self.db_name,))
            for r in cursor.fetchall():
                tname = r["TABLE_NAME"]
                rtname = r["REFERENCED_TABLE_NAME"]
                cname = r["COLUMN_NAME"]
                rcname = r["REFERENCED_COLUMN_NAME"]
                
                if tname in self.schema_graph["tables"]:
                    self.schema_graph["tables"][tname]["foreign_keys"].append({
                        "column": cname,
                        "ref_table": rtname,
                        "ref_column": rcname
                    })
                if rtname in self.schema_graph["tables"]:
                    self.schema_graph["tables"][rtname]["referenced_by"].append({
                        "child_table": tname,
                        "child_column": cname,
                        "local_column": rcname
                    })
                    
            # QUERY 4 - Primary Keys
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND COLUMN_KEY = 'PRI'
            """, (self.db_name,))
            for r in cursor.fetchall():
                tname = r["TABLE_NAME"]
                if tname in self.schema_graph["tables"]:
                    self.schema_graph["tables"][tname]["primary_keys"].append(r["COLUMN_NAME"])
                    
        finally:
            cursor.close()
            
        # === PHASE 1 COMPLETE — SET IMMEDIATELY ===
        self.all_tables = sorted([t for t in self.schema_graph["tables"].keys()])
        logger.info("[Phase1] Complete. Found %d tables: %s", len(self.all_tables), self.all_tables[:10])
            
        elapsed = time.time() - t_start
        logger.info(f"LightweightMetadataScan completed in {elapsed:.3f} seconds.")
        return self.all_tables, self.schema_graph

    def score_tables(self) -> dict:
        """
        Returns top 3 candidates per entity.
        {
          "STUDENT": [{"table": "students", "confidence": 99}, ...],
          "ACADEMIC": [...],
          "ATTENDANCE": [...],
          "DEPARTMENT": [...]
        }
        """
        results = {
            "STUDENT": [],
            "ACADEMIC": [],
            "ATTENDANCE": [],
            "DEPARTMENT": []
        }
        
        try:
            # Estimate student table rows to help score other tables
            # We find the max student score first to get its row count
            s_scores = []
            for tname, tdata in self.schema_graph["tables"].items():
                s = TableConfidenceScorer.score_student_table(tname, tdata)
                s_scores.append((s, tname))
                
            s_scores.sort(key=lambda x: x[0], reverse=True)
            s_rows = 0
            if s_scores:
                best_s_table = s_scores[0][1]
                s_rows = self.schema_graph["tables"][best_s_table]["row_count"]
                
            for tname, tdata in self.schema_graph["tables"].items():
                # Get scores
                s_score = TableConfidenceScorer.score_student_table(tname, tdata)
                a_score = TableConfidenceScorer.score_academic_table(tname, tdata, s_rows)
                att_score = TableConfidenceScorer.score_attendance_table(tname, tdata, s_rows)
                d_score = TableConfidenceScorer.score_department_table(tname, tdata)
                
                if s_score > 0: results["STUDENT"].append({"table": tname, "confidence": min(s_score, 99)})
                if a_score > 0: results["ACADEMIC"].append({"table": tname, "confidence": min(a_score, 99)})
                if att_score > 0: results["ATTENDANCE"].append({"table": tname, "confidence": min(att_score, 99)})
                if d_score > 0: results["DEPARTMENT"].append({"table": tname, "confidence": min(d_score, 99)})
                
            # Sort and limit to top 3
            for k in results.keys():
                results[k].sort(key=lambda x: x["confidence"], reverse=True)
                results[k] = results[k][:3]
        except Exception as e:
            logger.error("Phase 2 scoring failed: %s", e, exc_info=True)
            
        return results
