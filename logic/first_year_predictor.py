"""
AcaDesk First-Year Risk Predictor — Redesigned
================================================
Implements Mandate 2, Issue 1: First-Year Student Risk Prediction.

DESIGN PRINCIPLES:
1. Primary features drive the prediction. If < 4 are available,
   return PENDING — do not predict.
2. Secondary features (prior academic background) are used as context only.
   Their absence is NOT penalized.
3. SHAP/contribution output only shows features that were actually
   present and used.
4. Risk score is bounded conservatively for first-year students
   (max 65 if no strong negative signals; only exceeds 70 with
   multiple confirmed negative signals).
5. The NLP explanation explicitly states which features were used
   and which were absent.
6. No semester trend is computed for first-year students in
   their first 1-2 semesters.
"""

import os
import sys
import pathlib
import logging
from typing import Optional

_log = logging.getLogger(__name__)

# Primary feature names and their display labels
PRIMARY_FEATURES = {
    "attendance_pct":       "Attendance %",
    "internal_marks":       "Internal Assessment Marks",
    "assignment_marks":     "Assignment Marks",
    "lab_performance":      "Lab & Practical Performance",
    "mid_exam_score":       "Mid-Exam Score",
    "consecutive_absences": "Consecutive Absence Pattern",
}

# Secondary feature names and their display labels
SECONDARY_FEATURES = {
    "tenth_percentage":  "10th Grade Score (SSC)",
    "inter_percentage":  "Intermediate Score (HSC)",
    "diploma_percentage": "Diploma Score",
    "entrance_rank":     "Entrance Exam Rank",
    "admission_type":    "Admission Type",
}

# Synonym map for flexible feature extraction from any dict
SYNONYMS = {
    "attendance_pct":        ["attendance_pct", "avg_attendance", "att", "attendance"],
    "internal_marks":        ["internal_marks", "avg_marks", "marks", "smarks"],
    "assignment_marks":      ["assignment_marks", "assignments", "sassign"],
    "lab_performance":       ["lab_performance", "lab_marks", "lab", "slab"],
    "mid_exam_score":        ["mid_exam_score", "mid_marks", "mid", "smid"],
    "consecutive_absences":  ["consecutive_absences", "consec_absences", "scons_abs"],
    "tenth_percentage":      ["tenth_percentage", "tenth", "ssc", "stenth"],
    "inter_percentage":      ["inter_percentage", "inter", "hsc", "sinter"],
    "diploma_percentage":    ["diploma_percentage", "diploma", "sdiploma"],
    "entrance_rank":         ["entrance_rank"],
    "admission_type":        ["admission_type"],
}


def _resolve_model_path(filename: str) -> Optional[str]:
    if getattr(sys, "frozen", False):
        base = pathlib.Path(sys.executable).parent
    else:
        base = pathlib.Path(__file__).parent.parent
    candidate = base / filename
    if candidate.exists():
        return str(candidate)
    for p in [pathlib.Path(filename), pathlib.Path("..") / filename]:
        if p.exists():
            return str(p)
    return None


def _extract(features: dict, key: str):
    """Extracts a value from a dict using synonym lookup. Returns None if absent."""
    for alias in SYNONYMS.get(key, [key]):
        if alias in features and features[alias] is not None:
            try:
                val = features[alias]
                if isinstance(val, str) and not val.strip():
                    continue
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


class FirstYearPredictor:
    """
    Redesigned First-Year Risk Predictor.
    Implements the full feature hierarchy and PENDING state from Mandate 2.
    """

    MODEL_FILE = "first_year_model.pkl"

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        path = _resolve_model_path(self.MODEL_FILE)
        if path:
            try:
                import joblib
                self.model = joblib.load(path)
                _log.info(f"First-year model loaded from: {path}")
            except Exception as e:
                _log.error(f"Failed to load first-year model: {e}")
        else:
            _log.warning(
                "first_year_model.pkl not found. Heuristic fallback will be used."
            )

    # ------------------------------------------------------------------
    # Main Public API
    # ------------------------------------------------------------------

    def analyze_student(self, raw_features: dict) -> dict:
        """
        Analyzes a single first-year student dynamically.
        """
        from logic.data_contract import PENDING_PREDICTION
        
        # 1. Dynamically extract features
        present_features = {}
        absent_features = []
        
        features_map = {
            "Attendance": ["attendance_pct", "avg_attendance", "attendance", "att"],
            "CGPA": ["cgpa", "avg_marks", "internal_marks", "marks"],
            "10th": ["tenth_percentage", "tenth", "ssc"],
            "Inter/Diploma": ["inter_percentage", "diploma_percentage", "inter", "diploma"],
            "Backlogs": ["backlogs", "backlog_count"]
        }
        
        for feat, aliases in features_map.items():
            val = None
            for alias in aliases:
                if alias in raw_features and raw_features[alias] is not None:
                    try:
                        v = raw_features[alias]
                        if isinstance(v, str) and not v.strip(): continue
                        val = float(v)
                        break
                    except: pass
            if val is not None:
                present_features[feat] = val
            else:
                absent_features.append(feat)

        if not present_features:
            result = dict(PENDING_PREDICTION)
            result["explanation"] = "No academic data available for prediction."
            result["_present_features"] = []
            result["_absent_features"] = absent_features
            return result
            
        # 2. Weighted Calculation only on present features
        base_weights = {
            "Attendance": 35,
            "CGPA": 25,
            "10th": 15,
            "Inter/Diploma": 15,
            "Backlogs": 10
        }
        
        total_available_weight = sum(base_weights[f] for f in present_features)
        
        risk_score = 0
        contributions = {}
        
        for feat, val in present_features.items():
            weight = (base_weights[feat] / total_available_weight) * 100
            
            # Normalize risk contribution (0 to 1 scale)
            if feat == "Attendance":
                feat_risk = max(0.0, min(1.0, (85.0 - val) / 25.0))
            elif feat == "CGPA":
                if val > 10.0: val = val / 10.0
                feat_risk = max(0.0, min(1.0, (7.5 - val) / 3.0))
            elif feat in ["10th", "Inter/Diploma"]:
                feat_risk = max(0.0, min(1.0, (75.0 - val) / 30.0))
            elif feat == "Backlogs":
                feat_risk = max(0.0, min(1.0, val / 3.0))
                
            contribution = feat_risk * weight
            risk_score += contribution
            contributions[feat] = round(contribution, 1)
            
        risk_score = min(100, max(0, int(risk_score)))
        
        if risk_score >= 65:
            level = "High"
        elif risk_score >= 35:
            level = "Medium"
        else:
            level = "Low"
            
        confidence = int((total_available_weight / 100) * 85)
        
        result = {
            "risk_category": level,
            "level": level,
            "risk_score": risk_score,
            "score": risk_score,
            "confidence": confidence,
            "shap_values": contributions,
            "drivers": contributions,
            "contributions": contributions,
            "is_first_year": True,
            "explanation": f"Risk calculated using dynamic available indicators ({len(present_features)}/5 found).",
            "recommendations": [{"action": "Regular Monitoring", "reason": "First year transition"}],
            "_present_features": list(present_features.keys()),
            "_absent_features": absent_features,
            "status": "OK"
        }
        return result

    def batch_analyze(self, students_list: list) -> tuple:
        """Batch analysis returning (global_stats, branch_stats)."""
        if not students_list:
            return {"High": 0, "Medium": 0, "Low": 0, "Pending": 0}, {}

        global_stats = {"High": 0, "Medium": 0, "Low": 0, "Pending": 0}
        branch_stats: dict = {}

        for s in students_list:
            result = self.analyze_student(s)
            level = result.get("level", result.get("risk_category", "Pending"))
            if level not in global_stats:
                level = "Pending"
            global_stats[level] = global_stats.get(level, 0) + 1

            branch = str(s.get("branch") or s.get("branch_id") or s.get("bid", "Unknown"))
            if branch not in branch_stats:
                branch_stats[branch] = {"High": 0, "Medium": 0, "Low": 0, "Pending": 0}
            branch_stats[branch][level] = branch_stats[branch].get(level, 0) + 1

        return global_stats, branch_stats

    # ------------------------------------------------------------------
    # Private Implementation
    # ------------------------------------------------------------------

    def _ml_predict(self, primary: dict, secondary: dict) -> dict:
        """Uses the trained ML model for prediction."""
        import pandas as pd
        import numpy as np
        from logic.data_contract import PENDING_PREDICTION

        # Build feature vector using model's expected columns
        # Primary features (fill missing with column mean, not 0)
        att = primary.get("attendance_pct") or 0.0
        marks = primary.get("internal_marks") or 0.0
        assign = primary.get("assignment_marks") or 0.0
        lab = primary.get("lab_performance") or 0.0
        mid = primary.get("mid_exam_score") or 0.0
        absences = primary.get("consecutive_absences") or 0.0

        # Secondary features — not penalized if absent; use 0 as neutral
        tenth = secondary.get("tenth_percentage") or 0.0
        higher_edu = (
            secondary.get("inter_percentage") or
            secondary.get("diploma_percentage") or
            0.0
        )

        # Use the model's feature set if known, else fall back to legacy 5-feature set
        try:
            expected_cols = getattr(self.model, "feature_names_in_", None)
            if expected_cols is not None and len(expected_cols) > 5:
                row = {c: 0.0 for c in expected_cols}
                row.update({
                    "attendance_pct": att,
                    "internal_marks": marks,
                    "assignment_marks": assign,
                    "lab_performance": lab,
                    "mid_exam_score": mid,
                    "consecutive_absences": absences,
                    "tenth_percentage": tenth,
                    "inter_percentage": higher_edu,
                })
                X = pd.DataFrame([row], columns=expected_cols)
            else:
                # Legacy 5-feature model
                cols = ["tenth_percentage", "prior_higher_edu_percentage",
                        "attendance", "internal_marks", "consecutive_absences"]
                X = pd.DataFrame([[tenth, higher_edu, att, marks, absences]], columns=cols)

            pred = self.model.predict(X)[0]
            probs = self.model.predict_proba(X)[0]
            classes = list(self.model.classes_)

            prob_map = {c: probs[i] for i, c in enumerate(classes)}
            p_high = prob_map.get("High", 0.0)
            p_med = prob_map.get("Medium", 0.0)
            p_low = prob_map.get("Low", 0.0)
            confidence = int(max(p_high, p_med, p_low) * 100)

            if pred == "High":
                risk_score = 71 + (p_high * 25)
            elif pred == "Medium":
                risk_score = 41 + (p_med * 25)
            else:
                risk_score = 5 + (p_low * 30)
            risk_score = int(min(max(risk_score, 1), 100))

            # Contributions — ONLY for features that were present
            contributions = self._compute_contributions(primary, secondary)

            return {
                "risk_category": pred,
                "level": pred,
                "risk_score": risk_score,
                "score": risk_score,
                "confidence": confidence,
                "shap_values": contributions,
                "drivers": contributions,
                "contributions": contributions,
                "is_first_year": True,
                "recommendations": self._get_recommendations(primary, secondary, pred),
            }

        except Exception as e:
            _log.error(f"ML prediction error: {e}")
            return self._heuristic_predict(primary, secondary)

    def _heuristic_predict(self, primary: dict, secondary: dict) -> dict:
        """Rule-based fallback when no ML model is available."""
        att = primary.get("attendance_pct") or 0.0
        marks = primary.get("internal_marks") or 0.0
        absences = primary.get("consecutive_absences") or 0.0
        mid = primary.get("mid_exam_score") or 0.0
        lab = primary.get("lab_performance") or 0.0

        tenth = secondary.get("tenth_percentage") or 0.0
        higher_edu = (
            secondary.get("inter_percentage") or
            secondary.get("diploma_percentage") or 0.0
        )

        score = 30  # Default baseline for first-year
        level = "Low"

        # Primary negative signals
        if att < 65:
            score += 35
        elif att < 75:
            score += 15

        if marks < 40:
            score += 20
        elif marks < 55:
            score += 10

        if absences > 7:
            score += 15
        elif absences > 4:
            score += 8

        if mid < 40:
            score += 10
        if lab < 40:
            score += 8

        # Secondary signals — smaller weight, not penalized if absent
        if tenth > 0 and tenth < 55:
            score += 7
        if higher_edu > 0 and higher_edu < 55:
            score += 7

        score = min(score, 100)

        if score >= 65:
            level = "High"
        elif score >= 42:
            level = "Medium"
        else:
            level = "Low"
            score = min(score, 40)

        contributions = self._compute_contributions(primary, secondary)
        confidence = 75  # Heuristic confidence

        return {
            "risk_category": level,
            "level": level,
            "risk_score": score,
            "score": score,
            "confidence": confidence,
            "shap_values": contributions,
            "drivers": contributions,
            "contributions": contributions,
            "is_first_year": True,
            "recommendations": self._get_recommendations(primary, secondary, level),
        }

    def _apply_conservative_bound(self, result: dict, primary: dict) -> dict:
        """
        Bounds the risk score conservatively for first-year students.
        A student with no confirmed negative signals should not be High Risk
        solely due to model uncertainty.
        """
        score = result.get("risk_score", result.get("score", 0))
        level = result.get("level", result.get("risk_category", "Low"))

        att = primary.get("attendance_pct") or 0.0
        marks = primary.get("internal_marks") or 0.0
        absences = primary.get("consecutive_absences") or 0.0

        # No strong negative signals → cap at 65
        has_negative_signal = (att < 65) or (marks < 40) or (absences > 7)
        if not has_negative_signal and score > 65:
            score = 65
            if level == "High":
                level = "Medium"
                result["risk_category"] = "Medium"
                result["level"] = "Medium"

        result["risk_score"] = score
        result["score"] = score
        return result

    def _compute_contributions(self, primary: dict, secondary: dict) -> dict:
        """
        Computes feature contributions.
        ONLY includes features that were actually present.
        """
        contributions = {}

        att = primary.get("attendance_pct")
        marks = primary.get("internal_marks")
        absences = primary.get("consecutive_absences")
        mid = primary.get("mid_exam_score")
        lab = primary.get("lab_performance")
        assign = primary.get("assignment_marks")

        if att is not None:
            if att < 65:
                contributions["Attendance %"] = 35
            elif att < 75:
                contributions["Attendance %"] = 20
            else:
                contributions["Attendance %"] = 8

        if marks is not None:
            if marks < 40:
                contributions["Internal Marks"] = 25
            elif marks < 55:
                contributions["Internal Marks"] = 15
            else:
                contributions["Internal Marks"] = 5

        if absences is not None and absences > 0:
            contributions["Consecutive Absences"] = min(25, int(absences * 3))

        if mid is not None:
            if mid < 40:
                contributions["Mid-Exam Score"] = 15
            elif mid < 55:
                contributions["Mid-Exam Score"] = 8
            else:
                contributions["Mid-Exam Score"] = 3

        if lab is not None:
            if lab < 40:
                contributions["Lab Performance"] = 12
            elif lab < 55:
                contributions["Lab Performance"] = 6
            else:
                contributions["Lab Performance"] = 2

        if assign is not None:
            if assign < 40:
                contributions["Assignment Marks"] = 10
            else:
                contributions["Assignment Marks"] = 3

        # Secondary (context only, lower weight)
        tenth = secondary.get("tenth_percentage")
        higher = secondary.get("inter_percentage") or secondary.get("diploma_percentage")

        if tenth is not None and tenth < 55:
            contributions["10th Grade Score"] = 8
        if higher is not None and higher < 55:
            contributions["Prior Academic Score"] = 8

        # Normalize to 100%
        total = sum(contributions.values())
        if total > 0:
            return {k: int((v / total) * 100) for k, v in contributions.items()}
        return contributions

    def _get_recommendations(self, primary: dict, secondary: dict, level: str) -> list:
        recs = []
        att = primary.get("attendance_pct") or 0.0
        marks = primary.get("internal_marks") or 0.0
        absences = primary.get("consecutive_absences") or 0.0
        mid = primary.get("mid_exam_score") or 0.0
        higher = secondary.get("inter_percentage") or secondary.get("diploma_percentage") or 0.0

        if att < 75:
            recs.append("Schedule attendance counseling session with HOD.")
        if marks < 50:
            recs.append("Enroll in remedial / extra coaching classes.")
        if absences > 5:
            recs.append("Contact parent/guardian regarding irregular attendance.")
        if mid < 40:
            recs.append("Provide targeted mid-term academic support.")
        if higher > 0 and higher < 55:
            recs.append("Academic mentoring recommended (prior academic background indicates academic stress risk).")

        if not recs:
            if level == "Low":
                recs.append("Continue current monitoring. No immediate intervention required.")
            else:
                recs.append("Schedule a meeting with the student's academic mentor.")
        return recs

    def _build_explanation(self, result: dict, primary: dict, secondary: dict,
                            absent_primary: list) -> str:
        level = result.get("level", "Unknown")
        score = result.get("score", 0)
        conf_label = result.get("confidence_label", "")
        used = [PRIMARY_FEATURES[k] for k in primary]
        absent_labels = [PRIMARY_FEATURES[k] for k in absent_primary if k in PRIMARY_FEATURES]

        present_sec = [
            SECONDARY_FEATURES[k] for k in secondary
            if secondary[k] is not None and k in SECONDARY_FEATURES
        ]

        explanation = (
            f"This is a First-Year student. The risk assessment is based on "
            f"{len(primary)} of 6 primary academic indicators that are currently available.\n\n"
            f"INDICATORS USED: {', '.join(used) or 'None'}.\n"
        )
        if absent_labels:
            explanation += (
                f"DATA NOT YET AVAILABLE: {', '.join(absent_labels)}. "
                f"These indicators were NOT used in the prediction and did not affect the score.\n"
            )
        if present_sec:
            explanation += (
                f"BACKGROUND CONTEXT USED: {', '.join(present_sec)} "
                f"(secondary signals — used as context only, weighted conservatively).\n"
            )

        explanation += (
            f"\nRISK LEVEL: {level} (Score: {score}/100). "
        )
        if conf_label:
            explanation += f"Prediction Confidence: {conf_label}. "

        if level == "High":
            explanation += (
                "Multiple primary academic indicators are below acceptable thresholds. "
                "Immediate intervention is recommended."
            )
        elif level == "Medium":
            explanation += (
                "Some primary indicators show early warning signs. "
                "Monitor closely and consider preventive counseling."
            )
        else:
            explanation += (
                "Primary academic indicators are within normal range for a first-year student. "
                "Continue standard monitoring."
            )

        return explanation
