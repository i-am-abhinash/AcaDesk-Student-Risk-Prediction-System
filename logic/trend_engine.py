"""
AcaDesk Trend Analyzer — Fixed
================================
Analyzes semester history data to determine trend status.

RULES (per Mandate 2, Issue 2):
  - Returns "Insufficient Data" when fewer than 2 records are present.
  - Never pads, extrapolates, or synthesizes data points.
  - "Insufficient Data" must propagate correctly — never silently
    converted to "Stable Performance".
"""

import numpy as np


class TrendAnalyzer:
    def __init__(self):
        pass

    def analyze_history(self, history_data: list) -> dict:
        """
        Analyzes semester history records and returns a trend report.

        Args:
            history_data: List of dicts with keys:
                'semester' (or 'semester_number'),
                'cgpa' (or 'cgpa_that_semester'),
                'attendance' (or 'attendance_that_semester'),
                'backlogs' (or 'backlogs_that_semester')

        Returns:
            dict with:
                trend_status: one of "Insufficient Data", "Stable Performance",
                              "Improving Performance", "Declining Performance",
                              "Critical Decline"
                trend_score: 0-100
                is_critical_drop: bool
                history_count: int
                reason: str (explains why if Insufficient Data)
                history: the sorted input records (with canonical keys)
        """
        if not history_data:
            return {
                "trend_status": "Insufficient Data",
                "trend_score": 50,
                "is_critical_drop": False,
                "history_count": 0,
                "reason": (
                    "No semester history is available for this student. "
                    "Trend analysis will become available after the completion "
                    "of their first semester. Current risk prediction is based "
                    "on real-time academic indicators only."
                ),
                "history": [],
                "cgpa_growth_pct": 0.0,
                "att_growth_pct": 0.0,
                "latest_cgpa": 0.0,
                "previous_cgpa": 0.0,
            }

        # Normalize keys: support both canonical and legacy naming
        normalized = []
        for h in history_data:
            normalized.append({
                "semester": int(
                    h.get("semester_number") or h.get("semester") or 0
                ),
                "cgpa": float(
                    h.get("cgpa_that_semester") or h.get("cgpa") or 0.0
                ),
                "attendance": float(
                    h.get("attendance_that_semester") or
                    h.get("attendance") or 0.0
                ),
                "backlogs": int(
                    h.get("backlogs_that_semester") or h.get("backlogs") or 0
                ),
            })

        # Sort by semester number
        sorted_history = sorted(normalized, key=lambda x: x["semester"])
        count = len(sorted_history)

        if count < 2:
            return {
                "trend_status": "Insufficient Data",
                "trend_score": 50,
                "is_critical_drop": False,
                "history_count": count,
                "reason": (
                    "Semester 1 Snapshot — insufficient history for trend analysis. "
                    "A minimum of two completed semesters is required to compute a "
                    "meaningful academic trend."
                ),
                "history": sorted_history,
                "cgpa_growth_pct": 0.0,
                "att_growth_pct": 0.0,
                "latest_cgpa": sorted_history[0]["cgpa"] if sorted_history else 0.0,
                "previous_cgpa": 0.0,
            }

        cgpas = [h["cgpa"] for h in sorted_history]
        atts = [h["attendance"] for h in sorted_history]
        bkls = [h["backlogs"] for h in sorted_history]

        # Latest vs previous drop
        cgpa_drop = cgpas[-2] - cgpas[-1]
        att_drop = atts[-2] - atts[-1]
        bkl_increase = bkls[-1] - bkls[-2]

        # Average growth rates
        cgpa_growth = float(np.mean(
            [(cgpas[i] - cgpas[i-1]) / max(cgpas[i-1], 0.1) * 100
             for i in range(1, len(cgpas))]
        ))
        att_growth = float(np.mean(
            [(atts[i] - atts[i-1]) / max(atts[i-1], 0.1) * 100
             for i in range(1, len(atts))]
        ))

        trend_status = "Stable Performance"
        is_critical_drop = False

        if cgpa_drop >= 1.5 or att_drop >= 15:
            trend_status = "Critical Decline"
            is_critical_drop = True
        elif cgpa_drop >= 0.5 or att_drop >= 5 or bkl_increase > 0:
            trend_status = "Declining Performance"
        elif cgpa_drop < -0.2 and bkl_increase <= 0 and att_drop <= 0:
            trend_status = "Improving Performance"
        else:
            trend_status = "Stable Performance"

        # Trend score
        if trend_status == "Critical Decline":
            trend_score = max(0, 30 - (cgpa_drop * 10))
        elif trend_status == "Declining Performance":
            trend_score = max(31, 50 - (cgpa_drop * 15))
        elif trend_status == "Improving Performance":
            trend_score = min(100, 70 + (abs(cgpa_drop) * 15) + (att_growth * 0.5))
        else:
            trend_score = 60

        trend_score = int(max(0, min(100, trend_score)))

        return {
            "trend_status": trend_status,
            "trend_score": trend_score,
            "is_critical_drop": is_critical_drop,
            "history_count": count,
            "reason": None,
            "cgpa_growth_pct": round(cgpa_growth, 2),
            "att_growth_pct": round(att_growth, 2),
            "latest_cgpa": cgpas[-1],
            "previous_cgpa": cgpas[-2],
            "history": sorted_history,
        }
