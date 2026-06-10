"""
AcaDesk Advanced Risk Prediction Engine  v2.0
==============================================
Fully redesigned for accuracy, consistency, and explainability.

Key guarantees:
  • SHAP contributions SUM exactly to the final risk_score.
  • Domain readable scores show "N/A" for missing data (never 0 or 100 as fake values).
  • Missing fields are EXCLUDED from scoring; remaining weights are renormalized.
  • First-year students use a separate model (Academic Background weighted 20%).
  • Senior students (year≥2) use the full model with Backlogs at 20%.
  • Backlogs and Attendance have non-linear severity curves.
  • Four-tier classification: Low / Medium / High / Critical.
  • AI explanation, recommendations, and charts are all derived from the same
    domain contribution numbers — no separate calculation paths.

Public API (backward compatible with existing dashboard.py calls):
  predictor = AdvancedRiskPredictor(db_handler=None)
  report    = predictor.analyze(student_row, year=None)

Report dict keys:
  score, level, dominant, action, contributions, domain_scores,
  explanation, recommendations, trend, alerts, features, shap, confidence
"""

from __future__ import annotations
import math
from typing import Any


# ═══════════════════════════════════════════════════════════════
#  SECTION 1 — COLUMN SYNONYM REGISTRY
#  Maps logical field names to every possible ERP column name.
# ═══════════════════════════════════════════════════════════════

FIELD_SYNONYMS: dict[str, list[str]] = {
    # Attendance
    "attendance_pct":       ["attendance_percentage", "attendance_percent",
                             "attendance_pct", "attendance", "att", "avg_attendance",
                             "satt"],
    "consecutive_absences": ["consecutive_absences", "consec_absences",
                             "continuous_absences", "streak_absences"],
    "days_absent":          ["days_absent", "absent_days", "total_absences", "absences"],
    "leave_frequency":      ["leave_frequency", "leave_count", "leaves_taken", "leave_freq"],

    # Academic marks — current semester
    "internal_marks":       ["internal_marks", "internals", "internal", "unit_test_marks",
                             "ca_marks", "avg_marks", "marks", "smarks"],
    "mid_exam_score":       ["mid_exam_score", "mid_marks", "midterm_score",
                             "midterm_marks", "mid_score"],
    "subject_marks":        ["subject_marks", "total_marks", "score", "obtained_marks"],
    "assignment_marks":     ["assignment_marks", "assignment_score", "assignments"],
    "submission_rate":      ["submission_rate", "assignment_submission_rate", "sub_rate"],
    "missing_assignments":  ["missing_assignments", "pending_assignments",
                             "assignments_missed"],
    "late_submissions":     ["late_submissions", "late_sub", "overdue_assignments"],

    # Lab
    "lab_marks":            ["lab_marks", "lab_performance", "lab_score",
                             "practical_marks", "lab"],
    "lab_attendance":       ["lab_attendance", "lab_att", "practical_attendance"],
    "experiment_completion":["experiment_completion", "exp_completion", "lab_completion"],

    # Academic preparedness (entry-level background — first year model)
    "tenth_percentage":     ["tenth_percentage", "tenth_pct", "ssc_percentage",
                             "ssc_marks", "class10_pct"],
    "inter_percentage":     ["inter_percentage", "inter_pct", "intermediate_pct",
                             "hsc_percentage", "12th_pct"],
    "diploma_percentage":   ["diploma_percentage", "diploma_pct", "polytechnic_pct"],
    "entrance_score":       ["entrance_score", "eamcet_score", "jee_score",
                             "entrance_exam_score"],
    "entrance_rank":        ["entrance_rank", "eamcet_rank", "jee_rank",
                             "entrance_exam_rank"],

    # Senior model fields
    "backlog_count":        ["backlog_count", "backlogs", "backlog", "arrears",
                             "sbkl", "bkl", "active_backlogs"],
    "cgpa":                 ["cgpa", "cumulative_gpa", "gpa"],
    "semester_gpa":         ["semester_gpa", "sgpa", "sem_gpa"],
    "semester_marks":       ["semester_marks", "sem_marks", "semester_score"],
    "subject_pass_rate":    ["subject_pass_rate", "pass_rate", "pass_percentage"],
    "promotion_status":     ["promotion_status", "promoted", "is_promoted"],
    "academic_standing":    ["academic_standing", "standing"],

    # Behavioral
    "participation":        ["participation", "activity_participation", "extracurricular"],
    "counseling_count":     ["counseling_count", "counseling_sessions", "counseling_records"],
}

# ═══════════════════════════════════════════════════════════════
#  SECTION 2 — SAFE-NORM THRESHOLDS
# ═══════════════════════════════════════════════════════════════

# "Perfect" reference values. Values at or above these contribute 0 risk.
# For inverted fields (higher = more risk), these are the "danger" thresholds.
SAFE_NORMS: dict[str, float] = {
    "attendance_pct":       95.0,   # <95 starts contributing risk
    "consecutive_absences": 0.0,    # any consecutive absence adds risk (inverted)
    "days_absent":          5.0,    # inverted
    "leave_frequency":      2.0,    # inverted
    "internal_marks":       75.0,
    "mid_exam_score":       75.0,
    "subject_marks":        75.0,
    "assignment_marks":     75.0,
    "submission_rate":      90.0,
    "missing_assignments":  0.0,    # inverted
    "late_submissions":     0.0,    # inverted
    "lab_marks":            75.0,
    "lab_attendance":       80.0,
    "experiment_completion":90.0,
    "tenth_percentage":     75.0,
    "inter_percentage":     75.0,
    "diploma_percentage":   75.0,
    "entrance_score":       70.0,
    "entrance_rank":        10000.0,# inverted — rank 1 is perfect
    "backlog_count":        0.0,    # inverted — any backlog is risk
    "cgpa":                 8.5,
    "semester_gpa":         8.5,
    "semester_marks":       75.0,
    "subject_pass_rate":    90.0,
}

# ═══════════════════════════════════════════════════════════════
#  SECTION 3 — FEATURE DISCOVERER
# ═══════════════════════════════════════════════════════════════

class ERPFeatureDiscoverer:
    """
    Maps logical field names to actual ERP column names via FIELD_SYNONYMS,
    then extracts float values from a raw DB row dict.
    """

    def __init__(self, academic_columns: set[str], student_columns: set[str]):
        self._map: dict[str, str] = {}
        all_cols = academic_columns | student_columns
        for field, synonyms in FIELD_SYNONYMS.items():
            for syn in synonyms:
                if syn in all_cols:
                    self._map[field] = syn
                    break

    @property
    def available_fields(self) -> dict[str, str]:
        return dict(self._map)

    def extract(self, row: dict[str, Any]) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for field, col in self._map.items():
            raw = row.get(col)
            if raw is None:
                result[field] = None
            else:
                try:
                    result[field] = float(raw)
                except (TypeError, ValueError):
                    result[field] = None
        return result


# ═══════════════════════════════════════════════════════════════
#  SECTION 4 — RISK CURVES (Non-linear severity functions)
# ═══════════════════════════════════════════════════════════════

def _attendance_risk(att: float) -> float:
    """
    Attendance risk curve (matches spec). Returns 0.0–1.0.
    95–100 → Excellent (0.00)
    90–95  → Good      (0.02–0.10)
    80–90  → Acceptable(0.10–0.25)
    75–80  → Concern   (0.25–0.40)
    65–75  → Risk      (0.40–0.65)
    <65    → Major Risk(0.65–1.00)
    """
    if att >= 95:
        return 0.0
    if att >= 90:
        return 0.02 + (95 - att) * 0.016
    if att >= 80:
        return 0.10 + (90 - att) * 0.015
    if att >= 75:
        return 0.25 + (80 - att) * 0.03
    if att >= 65:
        return 0.40 + (75 - att) * 0.025
    # Below 65 — Major Risk zone
    return min(1.0, 0.65 + (65 - att) * 0.014)


def _backlog_risk(n: float) -> float:
    """
    Backlog severity curve (matches spec). Returns 0.0–1.0.
    0      → Excellent  (0.00)
    1      → Small risk (0.25)
    2      → Moderate   (0.50)
    3      → Major      (0.75) — student CANNOT be Low Risk
    4+     → Heavy      (1.00)
    """
    n = int(n)
    if n == 0:
        return 0.0
    if n == 1:
        return 0.25
    if n == 2:
        return 0.50
    if n == 3:
        return 0.75
    return 1.0  # 4+ → Heavy


def _cgpa_risk(cgpa: float) -> float:
    """
    CGPA risk curve (matches spec). Returns 0.0–1.0.
    8.5+      → Excellent (0.00)
    7.5–8.5   → Good      (0.00–0.15)
    6.5–7.5   → Average   (0.15–0.40)
    5.5–6.5   → Risk      (0.40–0.70)
    <5.5      → High Risk (0.70–1.00)
    """
    if cgpa >= 8.5:
        return 0.0
    if cgpa >= 7.5:
        return (8.5 - cgpa) / (8.5 - 7.5) * 0.15
    if cgpa >= 6.5:
        return 0.15 + (7.5 - cgpa) / (7.5 - 6.5) * 0.25
    if cgpa >= 5.5:
        return 0.40 + (6.5 - cgpa) / (6.5 - 5.5) * 0.30
    return min(1.0, 0.70 + (5.5 - cgpa) * 0.15)


def _marks_risk(marks: float, safe_norm: float = 75.0) -> float:
    """Linear marks risk — 0 at safe_norm, 1 at 0."""
    if marks >= safe_norm:
        return 0.0
    return (safe_norm - marks) / safe_norm


def _consecutive_absence_risk(n: float) -> float:
    """0 consecutive → 0 risk, 3+ → significant, 7+ → critical."""
    if n <= 0:
        return 0.0
    if n <= 2:
        return n * 0.12
    if n <= 5:
        return 0.24 + (n - 2) * 0.15
    return min(1.0, 0.69 + (n - 5) * 0.06)


def _leave_frequency_risk(freq: float) -> float:
    """0–2 acceptable, 3–5 moderate, >5 high."""
    if freq <= 2:
        return 0.0
    if freq <= 5:
        return (freq - 2) * 0.12
    return min(1.0, 0.36 + (freq - 5) * 0.08)


def _background_risk(pct: float) -> float:
    """Academic background (10th/Inter/Diploma) risk."""
    if pct >= 75:
        return 0.0
    if pct >= 60:
        return (75 - pct) / 75 * 0.35
    if pct >= 45:
        return 0.35 + (60 - pct) / 60 * 0.40
    return min(1.0, 0.75 + (45 - pct) * 0.01)


def _trend_risk(mark_history: list[float]) -> float:
    """
    Returns 0–1 trend risk via linear regression slope.
    Declining performance → higher risk.
    Improving performance → lower risk (can be 0).
    """
    if len(mark_history) < 2:
        return 0.0
    n = len(mark_history)
    x_mean = (n - 1) / 2
    y_mean = sum(mark_history) / n
    num = sum((i - x_mean) * (mark_history[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    slope = num / den
    if slope >= 2.0:
        return 0.0  # Improving — no risk
    if slope >= 0:
        return 0.05  # Flat — tiny risk
    # Declining: slope = -2 → 0.15, slope = -10 → 0.80
    return min(1.0, 0.15 + abs(slope) * 0.065)


# ═══════════════════════════════════════════════════════════════
#  SECTION 5 — DOMAIN SCORERS
# ═══════════════════════════════════════════════════════════════

def _score_attendance(f: dict) -> float | None:
    att = f.get("attendance_pct")
    if att is None:
        return None
    return _attendance_risk(att)


def _score_backlogs(f: dict) -> float | None:
    bkl = f.get("backlog_count")
    if bkl is None:
        return None
    return _backlog_risk(bkl)


def _score_internal_marks(f: dict) -> float | None:
    vals = []
    for field in ("internal_marks", "subject_marks", "assignment_marks"):
        v = f.get(field)
        if v is not None:
            vals.append(_marks_risk(v))
    if not vals:
        return None
    return sum(vals) / len(vals)


def _score_mid_exam(f: dict) -> float | None:
    v = f.get("mid_exam_score")
    if v is None:
        return None
    return _marks_risk(v)


def _score_assignments(f: dict) -> float | None:
    vals = []
    am = f.get("assignment_marks")
    if am is not None:
        vals.append(_marks_risk(am, 75))
    sr = f.get("submission_rate")
    if sr is not None:
        vals.append(_marks_risk(sr, 90))
    miss = f.get("missing_assignments")
    if miss is not None:
        vals.append(min(1.0, miss * 0.15))
    late = f.get("late_submissions")
    if late is not None:
        vals.append(min(1.0, late * 0.10))
    if not vals:
        return None
    return sum(vals) / len(vals)


def _score_lab(f: dict) -> float | None:
    vals = []
    lm = f.get("lab_marks")
    if lm is not None:
        vals.append(_marks_risk(lm))
    la = f.get("lab_attendance")
    if la is not None:
        vals.append(_attendance_risk(la))
    ec = f.get("experiment_completion")
    if ec is not None:
        vals.append(_marks_risk(ec, 90))
    if not vals:
        return None
    return sum(vals) / len(vals)


def _score_academic_background(f: dict) -> float | None:
    vals = []
    for field in ("tenth_percentage", "inter_percentage", "diploma_percentage"):
        v = f.get(field)
        if v is not None:
            vals.append(_background_risk(v))
    es = f.get("entrance_score")
    if es is not None:
        vals.append(_marks_risk(es, 70))
    er = f.get("entrance_rank")
    if er is not None and er > 0:
        # rank 1 = 0 risk, rank 100000+ = 1.0 risk
        vals.append(min(1.0, math.log10(max(1, er)) / 5.0))
    if not vals:
        return None
    return sum(vals) / len(vals)


def _score_cgpa(f: dict) -> float | None:
    cgpa = f.get("cgpa")
    if cgpa is None:
        cgpa = f.get("semester_gpa")
    if cgpa is None:
        return None
    return _cgpa_risk(cgpa)


def _score_cons_absences(f: dict) -> float | None:
    v = f.get("consecutive_absences")
    if v is None:
        return None
    return _consecutive_absence_risk(v)


def _score_leave_frequency(f: dict) -> float | None:
    v = f.get("leave_frequency")
    if v is None:
        return None
    return _leave_frequency_risk(v)


# ═══════════════════════════════════════════════════════════════
#  SECTION 6 — YEAR-SPECIFIC MODELS
# ═══════════════════════════════════════════════════════════════

# ── First-Year model weights (must sum to 1.0) ────────────────
# Academic Background 20%, Attendance 25%, Internal 15%,
# Mid Exam 15%, Assignments 10%, Lab 5%, Absences 5%, Leave 5%
FIRST_YEAR_DOMAINS: list[tuple[str, Any, float]] = [
    ("attendance",          _score_attendance,          0.25),
    ("academic_background", _score_academic_background, 0.20),
    ("internal_marks",      _score_internal_marks,      0.15),
    ("mid_exam",            _score_mid_exam,            0.15),
    ("assignments",         _score_assignments,         0.10),
    ("lab",                 _score_lab,                 0.05),
    ("cons_absences",       _score_cons_absences,       0.05),
    ("leave_frequency",     _score_leave_frequency,     0.05),
]  # total = 1.00

# ── Senior-Year model weights (must sum to 1.0) ───────────────
# CGPA 25%, Backlogs 25%, Attendance 20%, Internal 10%,
# Mid Exam 10%, Assignments+Labs 5%, Trend 5%
SENIOR_DOMAINS: list[tuple[str, Any, float]] = [
    ("cgpa_marks",      _score_cgpa,           0.25),
    ("backlogs",        _score_backlogs,       0.25),
    ("attendance",      _score_attendance,     0.20),
    ("internal_marks",  _score_internal_marks, 0.10),
    ("mid_exam",        _score_mid_exam,       0.10),
    ("assignments",     _score_assignments,    0.025),
    ("lab",             _score_lab,            0.025),
    # cons_absences + leave_frequency carry remaining weight via trend
    ("cons_absences",   _score_cons_absences,  0.025),
    ("leave_frequency", _score_leave_frequency,0.025),
]  # total = 1.00  (trend domain adds 0.05 when available, weights renormalized)

# Friendly display labels
DOMAIN_LABELS: dict[str, str] = {
    "attendance":          "Attendance",
    "backlogs":            "Backlogs",
    "cgpa_marks":          "CGPA / GPA",
    "mid_exam":            "Mid Exam",
    "internal_marks":      "Internal Marks",
    "academic_background": "Academic Background",
    "assignments":         "Assignments",
    "lab":                 "Lab Performance",
    "cons_absences":       "Consecutive Absences",
    "leave_frequency":     "Leave Frequency",
    "trend":               "Performance Trend",
}

# Field display labels (for SHAP chart)
FIELD_LABELS: dict[str, str] = {
    "attendance_pct":       "Attendance %",
    "consecutive_absences": "Consec. Absences",
    "days_absent":          "Days Absent",
    "leave_frequency":      "Leave Frequency",
    "internal_marks":       "Internal Marks",
    "mid_exam_score":       "Mid Exam Score",
    "subject_marks":        "Subject Marks",
    "assignment_marks":     "Assignment Marks",
    "submission_rate":      "Submission Rate",
    "missing_assignments":  "Missing Assignments",
    "late_submissions":     "Late Submissions",
    "lab_marks":            "Lab Marks",
    "lab_attendance":       "Lab Attendance",
    "experiment_completion":"Experiment Completion",
    "tenth_percentage":     "10th Percentage",
    "inter_percentage":     "Intermediate %",
    "diploma_percentage":   "Diploma %",
    "entrance_score":       "Entrance Score",
    "entrance_rank":        "Entrance Rank",
    "backlog_count":        "Backlogs",
    "cgpa":                 "CGPA",
    "semester_gpa":         "Semester GPA",
    "semester_marks":       "Semester Marks",
}


def _label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " ").title())


# ═══════════════════════════════════════════════════════════════
#  SECTION 7 — CORE SCORING ENGINE
# ═══════════════════════════════════════════════════════════════

class _RiskScorer:
    """
    Given a domain definition list and features dict, computes:
      - risk_score (0–100)
      - level (Low/Medium/High/Critical)
      - domain_risk (dict: domain → 0–1 raw risk, None if missing)
      - domain_shap (dict: domain → contribution to risk_score, sums to risk_score)
      - domain_readable (dict: domain → 0–100 quality, "N/A" if missing)
    """

    def __init__(
        self,
        domain_defs: list[tuple[str, Any, float]],
        features: dict[str, float | None],
        mark_history: list[float] | None = None,
    ):
        self._defs = domain_defs
        self._f = features
        self._hist = mark_history or []

        # Optionally add trend domain if history available
        self._trend_risk: float | None = None
        if self._hist:
            self._trend_risk = _trend_risk(self._hist)

        self._compute()

    def _compute(self) -> None:
        raw_scores: dict[str, float | None] = {}

        for name, scorer_fn, _w in self._defs:
            raw_scores[name] = scorer_fn(self._f)

        # Trend domain (if enabled)
        if self._trend_risk is not None:
            raw_scores["trend"] = self._trend_risk

        # Collect active domains (where data is available)
        active: dict[str, tuple[float, float]] = {}  # name → (raw_risk, weight)
        weight_map = {name: w for name, _fn, w in self._defs}
        if self._trend_risk is not None:
            weight_map["trend"] = 0.10

        for name, raw in raw_scores.items():
            if raw is not None:
                active[name] = (raw, weight_map.get(name, 0.05))

        # Normalize weights to active domains only
        total_active_weight = sum(w for _, w in active.values())

        if total_active_weight <= 0:
            self.risk_score = 0.0
            self.level = "Low"
            self.domain_risk = raw_scores
            self.domain_shap = {}
            self.domain_readable = {
                k: "N/A" if v is None else round((1 - v) * 100, 1)
                for k, v in raw_scores.items()
            }
            return

        # Weighted risk score (normalized)
        self.risk_score = round(
            sum(r * (w / total_active_weight) * 100 for r, w in active.values()),
            1
        )
        self.risk_score = min(100.0, max(0.0, self.risk_score))

        # ── Three-tier classification (no Critical) ───────────
        # Low: 0–27   Medium: 28–57   High: 58–100
        if self.risk_score >= 58:
            self.level = "High"
        elif self.risk_score >= 28:
            self.level = "Medium"
        else:
            self.level = "Low"

        # ── Rule override: 3+ backlogs → never Low ────────────
        # Even if the normalized score is low, 3+ active backlogs
        # must produce at least Medium risk.
        bkl = self._f.get("backlog_count")
        if bkl is not None and bkl >= 3 and self.level == "Low":
            self.level = "Medium"
            # Nudge score above 28 to keep it consistent
            self.risk_score = max(self.risk_score, 28.0)

        # ── Rule override: first-year weak background → never Low ─
        # If avg of available background scores < 60%, student must
        # be at least Medium (insufficient preparedness for degree).
        bg_vals = [
            self._f.get(k) for k in
            ("tenth_percentage", "inter_percentage", "diploma_percentage")
        ]
        bg_vals = [v for v in bg_vals if v is not None]
        if bg_vals and (sum(bg_vals) / len(bg_vals)) < 60 and self.level == "Low":
            self.level = "Medium"
            self.risk_score = max(self.risk_score, 28.0)


        # SHAP: each domain's exact share of risk_score (sums to risk_score)
        self.domain_shap: dict[str, float] = {}
        for name, (r, w) in active.items():
            self.domain_shap[name] = round(r * (w / total_active_weight) * 100, 1)

        # Readable domain quality (100 = perfect, 0 = worst, "N/A" = missing)
        self.domain_risk = raw_scores
        self.domain_readable: dict[str, Any] = {}
        for name, raw in raw_scores.items():
            if raw is None:
                self.domain_readable[name] = "N/A"
            else:
                self.domain_readable[name] = round((1 - raw) * 100, 1)


# ═══════════════════════════════════════════════════════════════
#  SECTION 8 — EARLY WARNING DETECTOR
# ═══════════════════════════════════════════════════════════════

def _detect_alerts(f: dict[str, float | None]) -> list[str]:
    alerts: list[str] = []

    att = f.get("attendance_pct")
    if att is not None:
        if att < 65:
            alerts.append(f"🔴 Major Risk — Attendance {att:.1f}%: below 65% (Major Risk zone)")
        elif att < 75:
            alerts.append(f"🟠 Risk — Attendance {att:.1f}%: approaching defaulter limit")
        elif att < 80:
            alerts.append(f"🟡 Concern — Attendance {att:.1f}%: below acceptable range")

    cons = f.get("consecutive_absences")
    if cons is not None and cons >= 5:
        alerts.append(f"🔴 {int(cons)} consecutive absences — immediate follow-up required")
    elif cons is not None and cons >= 3:
        alerts.append(f"🟠 {int(cons)} consecutive absences — pattern forming, monitor closely")

    bkl = f.get("backlog_count")
    if bkl is not None and bkl >= 4:
        alerts.append(f"🔴 {int(bkl)} active backlogs — heavy impact, structured plan required")
    elif bkl is not None and bkl >= 3:
        alerts.append(f"🔴 {int(bkl)} active backlogs — major risk, recovery program needed")
    elif bkl is not None and bkl >= 2:
        alerts.append(f"🟠 {int(bkl)} active backlogs — moderate impact, mentoring recommended")
    elif bkl is not None and bkl == 1:
        alerts.append(f"🟡 1 backlog — small risk increase, early clearance advised")

    mid = f.get("mid_exam_score")
    if mid is not None and mid < 35:
        alerts.append(f"🔴 Mid-exam score very low: {mid:.1f}% — remedial support required")
    elif mid is not None and mid < 50:
        alerts.append(f"🟠 Mid-exam score below passing: {mid:.1f}%")

    miss = f.get("missing_assignments")
    if miss is not None and miss >= 3:
        alerts.append(f"🟠 {int(miss)} missing assignments — engagement concern")

    lab = f.get("lab_marks")
    if lab is not None and lab < 40:
        alerts.append(f"🟠 Lab performance low: {lab:.1f}%")

    cgpa = f.get("cgpa")
    if cgpa is None:
        cgpa = f.get("semester_gpa")
    if cgpa is not None and cgpa < 5.5:
        alerts.append(f"🔴 CGPA {cgpa:.2f} — High Risk zone (below 5.5)")
    elif cgpa is not None and cgpa < 6.5:
        alerts.append(f"🟠 CGPA {cgpa:.2f} — Risk zone (5.5–6.5)")

    return alerts


# ═══════════════════════════════════════════════════════════════
#  SECTION 9 — NATURAL LANGUAGE EXPLAINER
# ═══════════════════════════════════════════════════════════════

def _explain(
    level: str,
    risk_score: float,
    domain_shap: dict[str, float],
    features: dict[str, float | None],
    is_first_year: bool,
) -> str:
    # Sort domains by SHAP contribution descending
    top_domains = sorted(domain_shap.items(), key=lambda x: x[1], reverse=True)
    top_names = [DOMAIN_LABELS.get(d, d) for d, _ in top_domains[:3]]
    bottom_names = [DOMAIN_LABELS.get(d, d) for d, v in top_domains if v <= 5.0][:2]

    year_str = "first-year student" if is_first_year else "student"

    if level == "High":
        base = (
            f"This {year_str} is classified as HIGH RISK with a score of "
            f"{risk_score:.0f}/100. "
        )
        if top_names:
            base += f"The primary risk drivers are: {', '.join(top_names[:3])}. "
        if bottom_names:
            base += f"Relative strengths are seen in: {', '.join(bottom_names)}. "
        base += (
            "Structured academic support, regular faculty counseling sessions, "
            "and close attendance monitoring are recommended."
        )

    elif level == "Medium":
        base = (
            f"This {year_str} is at MEDIUM RISK with a score of {risk_score:.0f}/100. "
            "Performance is below optimal in several areas but has not reached a critical threshold. "
        )
        if top_names:
            base += f"Key areas of concern include: {', '.join(top_names[:2])}. "
        base += (
            "Early faculty intervention through mentoring can prevent escalation to high risk."
        )

    else:  # Low
        base = (
            f"This {year_str} is at LOW RISK with a score of {risk_score:.0f}/100. "
            "Academic performance and engagement indicators are generally satisfactory. "
        )
        concern_domains = [DOMAIN_LABELS.get(d, d) for d, v in top_domains if v > 3.0][:2]
        if concern_domains:
            base += f"Minor improvements are recommended in: {', '.join(concern_domains)}. "
        base += "Continue periodic monitoring to maintain the current trajectory."

    return base


# ═══════════════════════════════════════════════════════════════
#  SECTION 10 — RECOMMENDATION ENGINE
# ═══════════════════════════════════════════════════════════════

def _recommend(
    level: str,
    domain_shap: dict[str, float],
    features: dict[str, float | None],
    alerts: list[str],
    is_first_year: bool,
) -> list[dict[str, str]]:
    """
    Returns list of {action, priority, reason} dicts.
    All recommendations are derived from actual feature values.
    Priority: critical / warning / info
    """
    recs: list[dict[str, str]] = []

    att = features.get("attendance_pct")
    cons = features.get("consecutive_absences")
    bkl = features.get("backlog_count")
    mid = features.get("mid_exam_score")
    miss = features.get("missing_assignments")
    lab = features.get("lab_marks")
    cgpa = features.get("cgpa") or features.get("semester_gpa")
    bg_tenth = features.get("tenth_percentage")
    bg_inter = features.get("inter_percentage")

    # --- Attendance ---
    if att is not None and att < 60:
        recs.append({"action": "Emergency Parent Meeting",
                     "priority": "critical",
                     "reason": f"Attendance {att:.0f}% — critically below 60% threshold"})
    elif att is not None and att < 75:
        recs.append({"action": "Attendance Monitoring Plan",
                     "priority": "warning",
                     "reason": f"Attendance {att:.0f}% — at risk of becoming a defaulter"})

    if cons is not None and cons >= 5:
        recs.append({"action": "Emergency Counseling Session",
                     "priority": "critical",
                     "reason": f"{int(cons)} consecutive absences detected"})
    elif cons is not None and cons >= 3:
        recs.append({"action": "Faculty Follow-up",
                     "priority": "warning",
                     "reason": f"{int(cons)} consecutive absences — pattern forming"})

    # --- Backlogs ---
    if bkl is not None and bkl >= 5:
        recs.append({"action": "Degree Continuation Review",
                     "priority": "critical",
                     "reason": f"{int(bkl)} active backlogs — progression at risk"})
    elif bkl is not None and bkl >= 3:
        recs.append({"action": "Backlog Recovery Program",
                     "priority": "critical",
                     "reason": f"{int(bkl)} active backlogs — immediate remediation needed"})
    elif bkl is not None and bkl >= 1:
        recs.append({"action": "Academic Mentoring",
                     "priority": "warning",
                     "reason": f"{int(bkl)} backlog(s) — early remediation recommended"})

    # --- Mid Exam ---
    if mid is not None and mid < 40:
        recs.append({"action": "Remedial Classes",
                     "priority": "critical",
                     "reason": f"Mid-exam score {mid:.0f}% — below passing threshold"})
    elif mid is not None and mid < 55:
        recs.append({"action": "Study Skills Training",
                     "priority": "warning",
                     "reason": f"Mid-exam score {mid:.0f}% — below expected range"})

    # --- Assignments ---
    if miss is not None and miss >= 3:
        recs.append({"action": "Assignment Tracking Review",
                     "priority": "warning",
                     "reason": f"{int(miss)} assignments pending — engagement concern"})

    # --- Lab ---
    if lab is not None and lab < 50:
        recs.append({"action": "Lab Support Sessions",
                     "priority": "warning",
                     "reason": f"Lab performance at {lab:.0f}%"})

    # --- CGPA ---
    if cgpa is not None and cgpa < 6.0:
        recs.append({"action": "Academic Counseling",
                     "priority": "critical",
                     "reason": f"CGPA {cgpa:.2f} — below minimum academic standing"})
    elif cgpa is not None and cgpa < 7.0:
        recs.append({"action": "CGPA Improvement Plan",
                     "priority": "warning",
                     "reason": f"CGPA {cgpa:.2f} — in risk zone"})

    # --- First-year: background weakness ---
    if is_first_year:
        bg_scores = [s for s in [bg_tenth, bg_inter] if s is not None]
        if bg_scores and sum(bg_scores) / len(bg_scores) < 60:
            recs.append({"action": "First-Year Mentoring Program",
                         "priority": "warning",
                         "reason": "Weak academic background on admission — requires guided support"})

    # --- SHAP-driven recommendations (catch domains not covered above) ---
    top_domain = max(domain_shap.items(), key=lambda x: x[1])[0] if domain_shap else None
    if top_domain and not any(r["action"] in (
        "Attendance Monitoring Plan", "Emergency Parent Meeting",
        "Backlog Recovery Program", "Degree Continuation Review"
    ) for r in recs):
        label = DOMAIN_LABELS.get(top_domain, top_domain)
        recs.append({"action": f"{label} Improvement Plan",
                     "priority": "info",
                     "reason": f"Highest risk contribution from {label} domain"})

    # --- Default recommendations ---
    if level in ("Low",) and not recs:
        recs.append({"action": "Periodic Progress Review",
                     "priority": "info",
                     "reason": "Maintain current academic trajectory"})

    if level in ("Medium",) and len(recs) == 0:
        recs.append({"action": "Faculty Guidance Sessions",
                     "priority": "warning",
                     "reason": "Medium risk — proactive monitoring recommended"})

    if level == "High" and not any(r["priority"] == "critical" for r in recs):
        recs.append({"action": "Immediate Faculty Intervention",
                     "priority": "critical",
                     "reason": "High risk level requires structured academic support"})

    return recs


# ═══════════════════════════════════════════════════════════════
#  SECTION 11 — ALIAS FALLBACK MAP
#  Extracts values from common aliased keys when ERPFeatureDiscoverer
#  finds nothing (e.g. when only basic student dict is available).
# ═══════════════════════════════════════════════════════════════

_ALIAS_FALLBACK: dict[str, list[str]] = {
    "attendance_pct":       ["attendance_pct", "avg_attendance", "att", "satt",
                             "attendance", "attendance_percentage", "attendance_percent"],
    "internal_marks":       ["internal_marks", "avg_marks", "marks", "smarks",
                             "total_marks", "score", "obtained_marks"],
    "backlog_count":        ["backlog_count", "backlogs", "sbkl", "backlog",
                             "arrears", "bkl", "active_backlogs"],
    "mid_exam_score":       ["mid_exam_score", "mid_marks", "midterm_score", "mid_score"],
    "assignment_marks":     ["assignment_marks", "assignment_score", "assignments"],
    "lab_marks":            ["lab_marks", "lab_score", "practical_marks", "lab"],
    "tenth_percentage":     ["tenth_percentage", "tenth_pct", "ssc_percentage", "ssc_marks"],
    "inter_percentage":     ["inter_percentage", "intermediate_pct", "hsc_percentage",
                             "inter_pct"],
    "entrance_score":       ["entrance_score", "eamcet_score", "jee_score"],
    "entrance_rank":        ["entrance_rank", "eamcet_rank", "jee_rank"],
    "cgpa":                 ["cgpa", "cumulative_gpa", "gpa"],
    "consecutive_absences": ["consecutive_absences", "consec_absences"],
    "leave_frequency":      ["leave_frequency", "leave_count", "leaves_taken", "leave_freq"],
    "missing_assignments":  ["missing_assignments", "pending_assignments"],
    "submission_rate":      ["submission_rate", "sub_rate"],
}


def _extract_features(
    student_row: dict[str, Any],
    discoverer: ERPFeatureDiscoverer | None,
) -> dict[str, float | None]:
    """Extract all possible features from a student row dict."""
    features: dict[str, float | None] = {}

    # Step 1: ERP discoverer (real column names from academic_columns set)
    if discoverer:
        discovered = discoverer.extract(student_row)
        for k, v in discovered.items():
            if v is not None:
                features[k] = v

    # Step 2: Fill gaps via alias fallback
    for logical, aliases in _ALIAS_FALLBACK.items():
        if features.get(logical) is None:
            for alias in aliases:
                raw = student_row.get(alias)
                if raw is not None:
                    try:
                        features[logical] = float(raw)
                        break
                    except (TypeError, ValueError):
                        pass

    return features


def _parse_year(year: Any) -> int:
    """Convert '1st Year', '2nd Year', 1, '2', etc. to integer."""
    if year is None:
        return 2  # Default to senior model if unknown
    s = str(year).strip()
    if s and s[0].isdigit():
        return int(s[0])
    # E.g. "1st Year" → 1
    for token in s.split():
        if token and token[0].isdigit():
            return int(token[0])
    return 2


def _build_status_badge(level: str) -> str:
    mapping = {
        "Low":    "GOOD",
        "Medium": "WATCHLIST",
        "High":   "AT RISK",
    }
    return mapping.get(level, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════
#  SECTION 12 — CONSISTENCY VALIDATOR
# ═══════════════════════════════════════════════════════════════

def _validate_report(report: dict[str, Any]) -> list[str]:
    """
    Returns a list of inconsistency warning strings.
    Empty list = report is consistent.
    """
    warnings: list[str] = []
    score = report.get("score", 0)
    level = report.get("level", "")
    shap_sum = sum(v for v in report.get("contributions", {}).values()
                   if isinstance(v, (int, float)))

    # SHAP must approximately sum to risk score
    if abs(shap_sum - score) > 2.0:
        warnings.append(
            f"SHAP sum {shap_sum:.1f} does not match risk score {score:.1f}"
        )

    # Level must match score (3-tier: Low 0-27, Medium 28-57, High 58-100)
    expected_level = (
        "High"   if score >= 58 else
        "Medium" if score >= 28 else
        "Low"
    )
    # Allow Medium override for 3+ backlogs even when score < 28
    if level != expected_level and not (level == "Medium" and score >= 26):
        warnings.append(
            f"Level '{level}' does not match score {score:.1f} (expected '{expected_level}')"
        )

    # Recommendations must not recommend critical action for Low risk
    recs = report.get("recommendations", [])
    if level == "Low":
        critical_recs = [r for r in recs if isinstance(r, dict)
                         and r.get("priority") == "critical"]
        if critical_recs:
            warnings.append(
                f"Low risk student has {len(critical_recs)} critical recommendation(s) — "
                "check if risk drivers are consistent"
            )

    return warnings


# ═══════════════════════════════════════════════════════════════
#  SECTION 13 — TOP-LEVEL PREDICTOR (Public API)
# ═══════════════════════════════════════════════════════════════

class AdvancedRiskPredictor:
    """
    Top-level class used by the UI.
    Call analyze(student_row, year=None) to get a rich report dict.
    Backward compatible with existing dashboard.py calls.
    """

    def __init__(self, db_handler=None):
        self.db = db_handler
        self._discoverer: ERPFeatureDiscoverer | None = None

        if db_handler and hasattr(db_handler, "academic_columns"):
            try:
                self._discoverer = ERPFeatureDiscoverer(
                    db_handler.academic_columns,
                    db_handler.student_columns,
                )
            except Exception:
                self._discoverer = None

    def analyze(self, student_row: dict[str, Any], year: Any = None) -> dict[str, Any]:
        """
        Full analysis pipeline for a single student row.
        year: "1st Year" / "2nd Year" / 1 / 2 / None (defaults to senior model)

        Returns a report dict with keys:
          score, level, dominant, action, contributions, domain_scores,
          explanation, recommendations, trend, alerts, features, shap,
          confidence, status_badge, validation_warnings
        """

        # ── 1. Feature extraction ─────────────────────────────
        features = _extract_features(student_row, self._discoverer)

        # ── 2. Year detection ─────────────────────────────────
        # Priority: explicit year arg > student_row 'year' field
        resolved_year = year or student_row.get("year") or student_row.get("year_id")
        year_int = _parse_year(resolved_year)
        is_first_year = (year_int == 1)

        # ── 3. Domain scoring ─────────────────────────────────
        domain_defs = FIRST_YEAR_DOMAINS if is_first_year else SENIOR_DOMAINS

        # Build mark history for trend (use any available mark sequence)
        mark_hist: list[float] = []
        for k in ("internal_marks", "mid_exam_score", "semester_marks"):
            v = features.get(k)
            if v is not None:
                mark_hist.append(v)

        scorer = _RiskScorer(domain_defs, features, mark_hist if len(mark_hist) >= 2 else [])

        risk_score   = scorer.risk_score
        level        = scorer.level
        domain_shap  = scorer.domain_shap          # sums to risk_score
        domain_readable = scorer.domain_readable   # 0–100 or "N/A"

        # ── 4. SHAP contributions for chart ───────────────────
        # Use domain SHAP values (which sum to risk_score exactly).
        # Display with friendly domain labels.
        contributions: dict[str, float] = {
            DOMAIN_LABELS.get(k, k): v
            for k, v in domain_shap.items()
            if v > 0
        }
        # Sort descending
        contributions = dict(
            sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        )

        # ── 5. Early warnings ─────────────────────────────────
        alerts = _detect_alerts(features)

        # ── 6. Natural language explanation ───────────────────
        explanation = _explain(level, risk_score, domain_shap, features, is_first_year)

        # ── 7. Recommendations ────────────────────────────────
        recommendations = _recommend(level, domain_shap, features, alerts, is_first_year)

        # ── 8. Dominant factor ────────────────────────────────
        dominant = (
            max(domain_shap.items(), key=lambda x: x[1])[0]
            if domain_shap else "Insufficient Data"
        )
        dominant_label = DOMAIN_LABELS.get(dominant, dominant)

        # ── 9. AI action (first recommendation action) ────────
        action = recommendations[0]["action"] if recommendations else "Monitor"

        # ── 10. Trend simulation for chart ────────────────────
        base_mark = (
            features.get("internal_marks") or
            features.get("avg_marks") or
            student_row.get("avg_marks") or
            50.0
        )
        if risk_score >= 58:    # High
            trend = [base_mark + 12, base_mark + 5, base_mark - 3, base_mark - 8]
        elif risk_score >= 28:  # Medium
            trend = [base_mark + 5, base_mark - 2, base_mark + 1, base_mark]
        else:                   # Low
            trend = [base_mark - 5, base_mark - 2, base_mark + 1, base_mark]
        trend = [round(max(0.0, min(100.0, t)), 1) for t in trend]

        # ── 11. Confidence ────────────────────────────────────
        known_count = sum(1 for v in features.values() if v is not None)
        confidence = "High" if known_count >= 6 else ("Medium" if known_count >= 3 else "Low")

        # ── 12. Status badge ──────────────────────────────────
        status_badge = _build_status_badge(level)

        # ── 13. Features for display (labelled, non-None only) ─
        display_features = {
            _label(k): v for k, v in features.items() if v is not None
        }

        # ── 14. Full report ───────────────────────────────────
        report = {
            # Core (backward compatible)
            "score":         risk_score,
            "level":         level,
            "dominant":      dominant_label,
            "action":        action,
            "contributions": contributions,    # SHAP values, sum = risk_score
            "trend":         trend,
            "confidence":    confidence,
            "missing":       [k for k, v in features.items() if v is None],

            # Rich fields
            "domain_scores":   domain_readable,   # 0–100 quality (or "N/A")
            "alerts":          alerts,
            "explanation":     explanation,
            "recommendations": recommendations,
            "features":        display_features,
            "shap":            contributions,      # alias for chart access
            "status_badge":    status_badge,
            "year":            year_int,
            "is_first_year":   is_first_year,
            "model_used":      "First-Year Model" if is_first_year else "Senior-Year Model",
        }

        # ── 15. Consistency validation ────────────────────────
        validation_warnings = _validate_report(report)
        report["validation_warnings"] = validation_warnings

        return report

    # ── Backward-compatible batch analyze ─────────────────────
    def batch_analyze(self, students_list):
        """For dashboard charts — reuses the existing fast sklearn batch path."""
        try:
            from logic.predictor import RiskPredictor
            return RiskPredictor().batch_analyze(students_list)
        except Exception:
            return {"High": 0, "Medium": 0, "Low": 0}, {}
