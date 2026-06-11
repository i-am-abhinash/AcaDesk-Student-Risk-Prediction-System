import pandas as pd
import numpy as np

class InstitutionalAnalytics:
    @staticmethod
    def compute_dashboard_data(db, predictor, branch_map, target_branch_id=None):
        """
        Aggregates data for all given branches, computes risk scores and builds insights.
        If target_branch_id is provided, only computes data for that specific branch.
        """
        departments = {}
        total_students = 0
        overall_risk_counts = {"High": 0, "Medium": 0, "Low": 0}
        
        # Get all students at once
        all_students = db.get_all_students()
        
        # Filter if target_branch_id is specified
        if target_branch_id:
            all_students = [s for s in all_students if str(s.get('branch')) == str(target_branch_id)]
            branch_map = {name: bid for name, bid in branch_map.items() if str(bid) == str(target_branch_id)}
        
        with open("debug_institutional.txt", "w") as f:
            f.write(f"All students count: {len(all_students)}\n")
            f.write(f"Branch map: {branch_map}\n")
            if all_students:
                f.write(f"First student sample: {all_students[0]}\n")
        
        if not all_students:
            return None
            
        # Group students by branch ID
        branch_groups = {}
        for s in all_students:
            bid = str(s.get('branch'))
            if bid not in branch_groups:
                branch_groups[bid] = []
            branch_groups[bid].append(s)
            
        # Separate standard students from first-year students
        from logic.first_year_predictor import FirstYearPredictor
        first_year_predictor = FirstYearPredictor()
        
        standard_students = []
        first_year_students = []
        
        for s in all_students:
            syear_str = str(s.get('syear', '')).lower()
            if '1' in syear_str or 'first' in syear_str:
                first_year_students.append(s)
            else:
                standard_students.append(s)
                
        # Fast Batch Risk Computation
        global_stats_std, branch_stats_raw_std = predictor.batch_analyze(standard_students)
        global_stats_fy, branch_stats_raw_fy = first_year_predictor.batch_analyze(first_year_students)
        
        # Combine branch_stats_raw
        branch_stats_raw = {}
        for b_id in set(list(branch_stats_raw_std.keys()) + list(branch_stats_raw_fy.keys())):
            branch_stats_raw[b_id] = {
                "High": branch_stats_raw_std.get(b_id, {}).get("High", 0) + branch_stats_raw_fy.get(b_id, {}).get("High", 0),
                "Medium": branch_stats_raw_std.get(b_id, {}).get("Medium", 0) + branch_stats_raw_fy.get(b_id, {}).get("Medium", 0),
                "Low": branch_stats_raw_std.get(b_id, {}).get("Low", 0) + branch_stats_raw_fy.get(b_id, {}).get("Low", 0)
            }
            
        global_stats = {
            "High": global_stats_std.get("High", 0) + global_stats_fy.get("High", 0),
            "Medium": global_stats_std.get("Medium", 0) + global_stats_fy.get("Medium", 0),
            "Low": global_stats_std.get("Low", 0) + global_stats_fy.get("Low", 0)
        }
        
        # We need to iterate over all branches
        for branch_name, branch_id in branch_map.items():
            branch_id_str = str(branch_id)
            students = branch_groups.get(branch_id_str, [])
            if not students:
                continue
                
            total_students += len(students)
            
            # Fetch pre-computed risk levels for this branch
            b_stats = branch_stats_raw.get(branch_id, {"High": 0, "Medium": 0, "Low": 0})
            
            dept_stats = {
                "High": b_stats.get("High", 0), 
                "Medium": b_stats.get("Medium", 0), 
                "Low": b_stats.get("Low", 0),
                "attendance_sum": 0, "cgpa_sum": 0, "backlogs_sum": 0,
                "total": len(students)
            }
            overall_risk_counts["High"] += dept_stats["High"]
            overall_risk_counts["Medium"] += dept_stats["Medium"]
            overall_risk_counts["Low"] += dept_stats["Low"]
            
            for s in students:
                # Basic fields handling for averages
                att = float(s.get('attendance', s.get('avg_attendance', 0)) or 0)
                mrk = float(s.get('marks', s.get('avg_marks', 0)) or 0)
                bkl = int(s.get('backlogs', 0) or 0)
                
                dept_stats["attendance_sum"] += att
                dept_stats["cgpa_sum"] += mrk
                dept_stats["backlogs_sum"] += bkl
            
            # Compute Averages
            t = dept_stats["total"]
            dept_stats["avg_attendance"] = dept_stats["attendance_sum"] / t
            dept_stats["avg_cgpa"] = dept_stats["cgpa_sum"] / t
            dept_stats["avg_backlogs"] = dept_stats["backlogs_sum"] / t
            
            # Identify Top Risk Drivers using Heuristics instead of slow SHAP
            drivers = []
            if dept_stats["avg_attendance"] < 75: drivers.append("Low Attendance")
            if dept_stats["avg_backlogs"] > 1: drivers.append("High Backlogs")
            if dept_stats["avg_cgpa"] < 60: drivers.append("Low Academics")
            if not drivers: drivers.append("General Maintenance")
            
            dept_stats["top_drivers"] = drivers
            
            # Calculate Department Health Score (0-100)
            # Base 100
            # - High Risk % penalizes up to 40 points
            # - Medium Risk % penalizes up to 15 points
            # - Attendance drop below 75 penalizes up to 20 points
            # - High average backlogs penalizes up to 25 points
            high_pct = dept_stats["High"] / t
            med_pct = dept_stats["Medium"] / t
            
            health = 100
            health -= (high_pct * 40)
            health -= (med_pct * 15)
            if dept_stats["avg_attendance"] < 75:
                health -= min(20, (75 - dept_stats["avg_attendance"]))
            health -= min(25, dept_stats["avg_backlogs"] * 5)
            
            dept_stats["health_score"] = max(0, min(100, int(health)))
            
            departments[branch_name] = dept_stats
            
        # Overall Institutional Health
        if total_students == 0:
            return None
            
        inst_health = sum(d["health_score"] for d in departments.values()) / len(departments)
        
        # Sort departments by Health Score
        ranked_depts = sorted(departments.items(), key=lambda x: x[1]["health_score"], reverse=True)
        
        # Generate NLG Insight
        nlg_insight = InstitutionalNLG.generate_insight(ranked_depts, total_students)
        
        return {
            "total_students": total_students,
            "overall_risk_counts": overall_risk_counts,
            "institutional_health": int(inst_health),
            "ranked_departments": ranked_depts,
            "nlg_insight": nlg_insight
        }

class InstitutionalNLG:
    @staticmethod
    def generate_insight(ranked_depts, total_students):
        if not ranked_depts:
            return "Insufficient data to generate institutional insights."
            
        best_dept_name, best_stats = ranked_depts[0]
        worst_dept_name, worst_stats = ranked_depts[-1]
        
        insight = f"The institution currently monitors {total_students} students. "
        
        if worst_stats["High"] > 0:
            insight += f"The **{worst_dept_name}** department requires immediate management attention. It currently holds the lowest health score ({worst_stats['health_score']}/100) and has the highest concentration of at-risk students. "
            if worst_stats["top_drivers"]:
                drivers = ", ".join(worst_stats["top_drivers"])
                insight += f"The primary systemic issues driving risk in {worst_dept_name} are: {drivers}. "
        else:
            insight += "All departments are currently maintaining stable risk levels. "
            
        insight += f"Conversely, **{best_dept_name}** is the top-performing department with an excellent health score of {best_stats['health_score']}/100."
        
        return insight
