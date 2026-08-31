import re
import math
from logic.logger import get_logger

_log = get_logger(__name__)

class ColumnSampler:
    def __init__(self, connection, db_name: str):
        """
        Takes an active mysql.connector connection.
        """
        self.connection = connection
        self.db_name = db_name

    def sample_all_candidate_tables(self, candidate_tables: list[str], sample_size: int = 5) -> dict:
        """
        Returns a dict:
        {
          "table_name": {
            "column_name": {
              "samples": [val1, val2, val3, val4, val5],
              "data_type": "varchar|int|float|date|...",
              "null_pct": 0.12,
              "distinct_count": 8,
              "inferred_role": "student_id|name|..."
            }
          }
        }
        """
        results = {}
        if not self.connection or not self.connection.is_connected():
            return results

        cursor = self.connection.cursor(dictionary=True)
        
        for table in candidate_tables:
            results[table] = {}
            # Get columns and data types for this table
            try:
                cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s", (self.db_name, table))
                columns = cursor.fetchall()
            except Exception as e:
                _log.error(f"Failed to get columns for table {table}: {e}")
                continue
                
            for col_info in columns:
                col_name = col_info["COLUMN_NAME"]
                data_type = col_info["DATA_TYPE"]
                
                sampled_data = self._sample_column(cursor, table, col_name, data_type, sample_size)
                results[table][col_name] = sampled_data
                
        cursor.close()
        return results

    def _sample_column(self, cursor, table: str, column: str, data_type: str, sample_size: int) -> dict:
        """Fetch sample values and compute metadata."""
        samples = []
        null_pct = 0.0
        distinct_count = 0
        inferred_role = "unknown"
        
        try:
            # Fetch non-null sample values using LIMIT to avoid full table scans
            # We fetch sample_size * 3 and deduplicate in Python, or use DISTINCT with LIMIT
            # To be completely safe with large tables without indexing, we use a simple LIMIT
            query = f"SELECT `{column}` FROM `{table}` WHERE `{column}` IS NOT NULL LIMIT {sample_size * 3}"
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Deduplicate and return first sample_size unique values
            unique_vals = []
            seen = set()
            for row in rows:
                val = row[column]
                if val not in seen:
                    seen.add(val)
                    unique_vals.append(val)
                    if len(unique_vals) >= sample_size:
                        break
            samples = unique_vals

            # Only do aggregate queries if we got some samples, to save time on empty tables
            if samples:
                # Count nulls and distinct. Note: we still need to be careful with large tables, 
                # but we rely on MySQL's optimizer. To strictly bound it, we could sample a subset,
                # but standard practice is a full count if small enough.
                null_query = f"SELECT SUM(CASE WHEN `{column}` IS NULL THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS null_pct, COUNT(DISTINCT `{column}`) as distinct_count FROM `{table}`"
                cursor.execute(null_query)
                agg = cursor.fetchone()
                if agg:
                    null_pct = float(agg.get("null_pct") or 0.0)
                    distinct_count = int(agg.get("distinct_count") or 0)
                    
            inferred_role = self._infer_role(column, data_type, samples)
            
        except Exception as e:
            _log.warning(f"Sampling failed for {table}.{column}: {e}")
            samples = []
            inferred_role = "unknown"

        return {
            "samples": samples,
            "data_type": data_type,
            "null_pct": round(null_pct, 4),
            "distinct_count": distinct_count,
            "inferred_role": inferred_role
        }

    def _infer_role(self, col_name: str, data_type: str, samples: list) -> str:
        """
        Infer the semantic role of a column from its name, type, and sample values.
        Returns one of: student_id, name, email, phone, year, branch_id, branch_name, 
        semester, attendance_pct, marks, cgpa, backlogs, date, id, percentage, unknown
        """
        col_lower = col_name.lower()
        if not samples:
            return "unknown"
            
        # Helper to check if all samples are numeric
        def is_numeric(s):
            try:
                for v in s: float(v)
                return True
            except (ValueError, TypeError):
                return False

        # Helper to check if all samples are integer
        def is_int(s):
            try:
                for v in s: 
                    if float(v) != int(float(v)): return False
                return True
            except (ValueError, TypeError):
                return False
                
        # Primary signal: Name matching
        if "cgpa" in col_lower or "gpa" in col_lower:
            return "cgpa"
        if "attend" in col_lower:
            return "attendance_pct"
        if "email" in col_lower:
            return "email"
        if "phone" in col_lower or "mobile" in col_lower or "contact" in col_lower:
            return "phone"
        if "name" in col_lower and "branch" not in col_lower and "dept" not in col_lower:
            return "name"
        if "branch" in col_lower or "dept" in col_lower or "department" in col_lower:
            if is_numeric(samples): return "branch_id"
            return "branch_name"
        if "year" in col_lower:
            return "year"
        if "sem" in col_lower:
            return "semester"
        if "mark" in col_lower or "score" in col_lower:
            return "marks"
        if "backlog" in col_lower or "arrear" in col_lower:
            return "backlogs"
        if "date" in col_lower or "dob" in col_lower:
            return "date"
        if "roll" in col_lower or "reg" in col_lower or "student_id" in col_lower:
            return "student_id"
            
        # Secondary signal: Value based matching
        if is_numeric(samples):
            floats = [float(v) for v in samples]
            max_v = max(floats)
            min_v = min(floats)
            
            # If samples are all floats between 0-10: likely cgpa
            if max_v <= 10.0 and any(isinstance(v, float) or "." in str(v) for v in samples):
                return "cgpa"
            # If samples are all floats between 0-100 and it has percentage in the name
            if max_v <= 100.0 and ("pct" in col_lower or "percent" in col_lower):
                return "percentage"
            # If samples are all ints 0-10: likely backlogs or year or semester
            if is_int(samples) and max_v <= 10:
                if max_v <= 4: return "year"
                if max_v <= 8: return "semester"
                return "backlogs"
            # Unique integer IDs
            if is_int(samples) and len(set(samples)) == len(samples):
                return "id"
                
        # Text patterns
        str_samples = [str(v).lower() for v in samples]
        
        # Email regex
        if all(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", s) for s in str_samples):
            return "email"
            
        # 10-digit strings
        if all(re.match(r"^\d{10}$", s) for s in str_samples):
            return "phone"
            
        # Branch/Dept lookup words
        if any(word in " ".join(str_samples) for word in ["cse", "ece", "mech", "civil", "it"]):
            return "branch_name"
            
        if any(word in " ".join(str_samples) for word in ["year", "yr"]):
            return "year"

        return "unknown"
