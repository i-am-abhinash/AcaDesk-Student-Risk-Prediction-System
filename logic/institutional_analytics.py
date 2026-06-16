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
            branch_map = {bid: name for bid, name in branch_map.items() if str(bid) == str(target_branch_id)}
        
        # Removed debug log file writing
        
        if not all_students:
            return None
            
        # Group students by branch ID
        branch_groups = {}
        for s in all_students:
            bid = str(s.get('branch'))
            if bid not in branch_groups:
                branch_groups[bid] = []
            branch_groups[bid].append(s)
            
        # Fast Batch Risk Computation (AdvancedRiskPredictor routes internally)
        global_stats, branch_stats_raw = predictor.batch_analyze(all_students)
            
        # We need to iterate over all branches
        for branch_id, branch_name in branch_map.items():
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
            dept_stats["raw_health"] = health
            
            departments[branch_name] = dept_stats
            
        # Overall Institutional Health
        if total_students == 0:
            return None
            
        inst_health = sum(d["health_score"] for d in departments.values()) / len(departments)
        
        # Sort departments by Health Score, tie-break with raw health float, then alphabetically
        ranked_depts = sorted(departments.items(), key=lambda x: (x[1]["health_score"], x[1]["raw_health"], x[0]), reverse=True)
        
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
            return "Insufficient data to generate insights."
            
        if len(ranked_depts) == 1:
            dept_name, stats = ranked_depts[0]
            insight = f"Your department (**{dept_name}**) is currently monitoring {total_students} students with a health score of {stats['health_score']}/100. "
            if stats["High"] > 0:
                insight += f"There are {stats['High']} students at high risk. "
                if stats.get("top_drivers"):
                    drivers = ", ".join(stats["top_drivers"])
                    insight += f"The primary issues driving risk in your department are: {drivers}."
            else:
                insight += "Your department is maintaining stable risk levels with no high-risk students."
            return insight
            
        best_dept_name, best_stats = ranked_depts[0]
        worst_dept_name, worst_stats = ranked_depts[-1]
        
        insight = f"The institution currently monitors {total_students} students. "
        
        if worst_stats["High"] > 0:
            insight += f"The **{worst_dept_name}** department requires immediate management attention. It currently holds the lowest health score ({worst_stats['health_score']}/100) and has the highest concentration of at-risk students. "
            if worst_stats.get("top_drivers"):
                drivers = ", ".join(worst_stats["top_drivers"])
                insight += f"The primary systemic issues driving risk in {worst_dept_name} are: {drivers}. "
        else:
            insight += "All departments are currently maintaining stable risk levels. "
            
        insight += f"Conversely, **{best_dept_name}** is the top-performing department with an excellent health score of {best_stats['health_score']}/100."
        
        return insight
