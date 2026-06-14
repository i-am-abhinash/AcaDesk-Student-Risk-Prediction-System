import numpy as np

class TrendAnalyzer:
    def __init__(self):
        pass

    def analyze_history(self, history_data):
        """
        Analyzes semester history data and determines the trend status across CGPA, Attendance, and Backlogs.
        history_data: list of dicts with 'semester', 'cgpa', 'attendance', 'backlogs'
        Returns a dictionary with comprehensive trend information.
        """
        if not history_data or len(history_data) < 2:
            return {
                "trend_status": "Stable",
                "trend_score": 50,
                "is_critical_drop": False,
                "msg": "Insufficient history for trend analysis",
                "history": history_data
            }

        # Sort by semester
        sorted_history = sorted(history_data, key=lambda x: x.get('semester', 0))
        
        cgpas = [float(h.get('cgpa', 0)) for h in sorted_history]
        atts = [float(h.get('attendance', 0)) for h in sorted_history]
        bkls = [float(h.get('backlogs', 0)) for h in sorted_history]
        
        # Calculate drops (Latest vs Previous)
        cgpa_drop = cgpas[-2] - cgpas[-1]
        att_drop = atts[-2] - atts[-1]
        bkl_increase = bkls[-1] - bkls[-2]
        
        # Calculate Average Growth / Decline Percentages
        cgpa_growth = np.mean([ (cgpas[i] - cgpas[i-1])/max(cgpas[i-1], 1)*100 for i in range(1, len(cgpas)) ])
        att_growth = np.mean([ (atts[i] - atts[i-1])/max(atts[i-1], 1)*100 for i in range(1, len(atts)) ])
        
        trend_status = "Stable Performance"
        is_critical_drop = False
        
        # Determine Status
        if cgpa_drop >= 1.5 or att_drop >= 15:
            trend_status = "Critical Decline"
            is_critical_drop = True
        elif cgpa_drop >= 0.5 or att_drop >= 5 or bkl_increase > 0:
            trend_status = "Declining Performance"
        elif cgpa_drop < -0.2 and bkl_increase <= 0 and att_drop <= 0:
            trend_status = "Improving Performance"
        else:
            trend_status = "Stable Performance"
            
        # Calculate Trend Score (0-100, where 100 is best improving, 0 is critical decline)
        trend_score = 50
        
        if trend_status == "Critical Decline":
            trend_score = max(0, 30 - (cgpa_drop * 10))
        elif trend_status == "Declining Performance":
            trend_score = max(31, 50 - (cgpa_drop * 15))
        elif trend_status == "Improving Performance":
            trend_score = min(100, 70 + (abs(cgpa_drop) * 15) + (att_growth * 0.5))
        else:
            trend_score = 60 # Stable is good

        trend_score = int(max(0, min(100, trend_score)))
            
        return {
            "trend_status": trend_status,
            "trend_score": trend_score,
            "is_critical_drop": is_critical_drop,
            "cgpa_growth_pct": round(cgpa_growth, 2),
            "att_growth_pct": round(att_growth, 2),
            "latest_cgpa": cgpas[-1],
            "previous_cgpa": cgpas[-2],
            "history": sorted_history
        }

