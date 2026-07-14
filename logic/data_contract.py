"""
AcaDesk Internal Data Contract
================================
Defines the canonical NormalizedStudent record and SemesterRecord.
These are the ONLY data structures that pass from Layer 3 (Data Retrieval)
upward into the AI engine, analytics, UI, and session cache.

No upstream component may ever receive raw ERP data directly.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List


@dataclass
class NormalizedStudent:
    """
    Canonical normalized student record — AcaDesk's Internal Data Contract.
    Layer 3 (Data Retrieval) is responsible for mapping all ERP schemas into this format.
    All fields that are missing from the ERP are None or 0.0, never raised as errors.
    """
    # --- Identity ---
    student_id: str = ""
    full_name: str = ""
    branch_id: str = ""
    branch_name: str = ""
    current_year: int = 1           # 1, 2, 3, or 4
    current_semester: int = 1
    total_semesters_completed: int = 0
    admission_type: Optional[str] = None        # e.g. "Regular", "Management", "Lateral"
    entrance_rank: Optional[int] = None

    # --- Current Academic Indicators ---
    attendance_pct: float = 0.0
    internal_marks: float = 0.0
    mid_exam_score: float = 0.0
    assignment_marks: float = 0.0
    lab_performance: float = 0.0
    cgpa: float = 0.0
    backlog_count: int = 0
    consecutive_absences: int = 0
    leave_frequency: int = 0

    # --- Prior Academic Background ---
    tenth_percentage: Optional[float] = None
    inter_percentage: Optional[float] = None
    diploma_percentage: Optional[float] = None

    # --- Contact ---
    email: Optional[str] = None
    parent_email: Optional[str] = None
    parent_phone: Optional[str] = None

    # --- Display Helpers (populated by retrieval layer) ---
    display_name: str = ""
    display_reg_no: str = ""
    registration_no: str = ""

    def to_dict(self) -> dict:
        """Converts to a flat dict for SQLite insertion and legacy code compatibility."""
        d = asdict(self)
        # Ensure display_name is set
        if not d["display_name"]:
            d["display_name"] = d["full_name"]
        if not d["display_reg_no"]:
            d["display_reg_no"] = d["student_id"]
        if not d["registration_no"]:
            d["registration_no"] = d["student_id"]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "NormalizedStudent":
        """Reconstructs from a flat dict (e.g. from SQLite row)."""
        # Only include fields that are in the dataclass to avoid TypeError
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)

    def get_year_str(self) -> str:
        """Returns a human readable year string."""
        mapping = {1: "1st Year", 2: "2nd Year", 3: "3rd Year", 4: "4th Year"}
        return mapping.get(self.current_year, f"Year {self.current_year}")

    def is_first_year(self) -> bool:
        return self.current_year == 1

    def has_sufficient_primary_features(self) -> bool:
        """Returns True if at least 4 primary features are non-zero."""
        primary = [
            self.attendance_pct,
            self.internal_marks,
            self.assignment_marks,
            self.lab_performance,
            self.mid_exam_score,
            self.consecutive_absences,
        ]
        non_zero = sum(1 for v in primary if v is not None and v != 0.0)
        return non_zero >= 4


@dataclass
class SemesterRecord:
    """
    One row of a student's semester-by-semester academic history.
    Linked to NormalizedStudent by student_id.
    """
    student_id: str = ""
    semester_number: int = 0
    cgpa_that_semester: float = 0.0
    attendance_that_semester: float = 0.0
    backlogs_that_semester: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SemesterRecord":
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)


# --------------------------------------------------------------------------
# Sentinel return for prediction systems
# --------------------------------------------------------------------------

PENDING_PREDICTION = {
    "status": "PENDING",
    "level": "Pending",
    "score": 0,
    "risk_score": 0,
    "risk_category": "Pending",
    "confidence": 0,
    "message": (
        "Insufficient academic data to generate a risk prediction. "
        "This student requires manual academic review."
    ),
    "drivers": {},
    "protective": {},
    "shap_values": {},
    "recommendations": ["Schedule a manual academic review with the student's mentor."],
    "explanation": (
        "No risk prediction was generated because fewer than 4 primary academic "
        "indicators are available for this student. This commonly occurs at the "
        "start of a semester before attendance and assessment data has been recorded."
    ),
    "trends": {},
    "contributions": {},
    "is_first_year": True,
    "status_badge": "PENDING",
}
