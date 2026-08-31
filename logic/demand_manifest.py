"""
AcaDesk Data Demand Manifest
==============================
Defines every piece of data AcaDesk needs from a college ERP, along with
every known synonym for that field across real-world Indian college ERP systems
(Jspider, Quartz, Keka, Fedena, Campus, OpenEduCat, custom in-house systems).

This module is pure data — no logic, no I/O, no imports beyond typing.
The SchemaDetector's demand_driven_discover() method consumes this manifest
to perform a highly targeted INFORMATION_SCHEMA scan instead of a full scan.

Architecture: Layer 2 (Schema Intelligence) — static configuration only.
"""

from __future__ import annotations
from typing import Dict, List, NamedTuple, Optional


class FieldSpec(NamedTuple):
    """Specification for a single data field AcaDesk needs."""
    purpose: str           # Human-readable description of what this field is
    synonyms: List[str]    # All known column name variants (lowercase)
    requirement_level: str # "CRITICAL", "IMPORTANT", or "SUPPLEMENTARY"
    score_weight: int      # Points added when this field is found in a table
    field_type: str = "DIRECT" # Primary strategy: DIRECT or FK_LOOKUP
    lookup_hint: Optional[List[str]] = None
    lookup_value_column_hints: Optional[List[str]] = None
    fallback_recipes: Optional[List[Dict]] = None


# ---------------------------------------------------------------------------
# ROLE: STUDENT_MASTER
# One row per student — identity, enrolment, and contact data
# ---------------------------------------------------------------------------

STUDENT_MASTER_FIELDS: List[FieldSpec] = [
    # ── REQUIRED ──────────────────────────────────────────────────────────
    FieldSpec(
        purpose="student_id",
        synonyms=[
            "student_id", "roll_no", "roll_number", "reg_no",
            "registration_no", "regd_no", "admission_no",
            "hallticket_no", "stud_id", "usn", "htno",
            "enroll_no", "enrollment_no", "roll", "regno",
            "htno", "hallticket", "student_code", "stud_code",
            "scholar_no", "application_no",
        ],
        requirement_level="CRITICAL",
        score_weight=10,
    ),
    FieldSpec(
        purpose="full_name",
        synonyms=[
            "name", "student_name", "full_name", "stud_name",
            "sname", "student_fullname", "candidate_name",
            "applicant_name", "firstname", "first_name",
            "student_full_name", "stud_fullname",
        ],
        requirement_level="CRITICAL",
        score_weight=10,
    ),
    FieldSpec(
        purpose="branch_foreign_key",
        synonyms=[
            "branch_id", "dept_id", "department_id", "program_id",
            "course_id", "branch_code", "dept_code", "program_code",
            "stream_id", "specialization_id", "section_id",
            "course_code", "department_code", "branchid",
            "deptid", "dept", "branch",
        ],
        requirement_level="IMPORTANT",
        score_weight=10,
        field_type="FK_LOOKUP",
    ),
    FieldSpec(
        purpose="current_year",
        synonyms=[
            "year", "academic_year", "current_year", "study_year",
            "yr", "class_year", "year_of_study", "year_id",
            "academic_year_id", "year_level", "study_level",
            "year_of_programme", "year_of_program", 
            "semester_year", "class_id", "class_level",
            "level_id", "programme_year", "course_year",
            "enrollment_year_id", "batch_year_id", "admission_year",
            "current_semester", "batch", "batch_year"
        ],
        requirement_level="IMPORTANT",
        score_weight=10,
        field_type="FK_LOOKUP",
        lookup_hint=[
            "years", "year_levels", "academic_years", 
            "class_levels", "study_levels", "year_master",
            "academic_level", "programme_years"
        ],
        lookup_value_column_hints=[
            "name", "year_name", "level_name", "description",
            "title", "display_name", "year_label"
        ],
        fallback_recipes=[
            {
                "resolution_type": "STUDENT_LINKED_TABLE",
                "computation": "years_elapsed",
                "source_table_hints": ["admission", "admissions", "enrollment_record", "student_admission"],
                "value_column_hints": ["admission_date", "joined_date", "enrollment_date", "date_of_admission"],
                "cardinality": "ONE_TO_ONE"
            },
            {
                "resolution_type": "DERIVED_AGGREGATE",
                "source_table_hints": ["enrollment", "enrollments"],
                "join_via_hints": ["course", "courses"],
                "value_column_hints": ["semester", "sem", "term"],
                "filter_condition_hints": {
                    "column_hints": ["status", "state", "enrollment_status"],
                    "match_values": ["Active", "Enrolled", "In Progress", "Current", "Ongoing"]
                },
                "aggregation_function": "MAX"
            }
        ]
    ),
    # ── OPTIONAL ──────────────────────────────────────────────────────────
    FieldSpec(
        purpose="email",
        synonyms=[
            "email", "student_email", "mail", "email_id",
            "stud_email", "personal_email", "stud_mail",
            "emailid", "email_address", "student_mail",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
    ),
    FieldSpec(
        purpose="parent_phone",
        synonyms=[
            "parent_phone", "father_phone", "mother_phone",
            "guardian_phone", "parent_mobile", "emergency_contact",
            "parent_contact", "father_mobile", "mother_mobile",
            "guardian_mobile", "p_phone", "parent_no",
            "father_contact", "guardian_contact",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
        fallback_recipes=[
            {
                "resolution_type": "STUDENT_LINKED_TABLE",
                "source_table_hints": ["parent", "parents", "guardian", "guardians", "contact", "contacts"],
                "value_column_hints": ["phone", "mobile", "contact_no", "contact_number", "phone_number"],
                "cardinality": "ONE_TO_ONE"
            }
        ]
    ),
    FieldSpec(
        purpose="parent_email",
        synonyms=[
            "parent_email", "father_email", "guardian_email",
            "parent_mail", "family_email", "p_email",
            "parent_emailid", "guardian_mail",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
        fallback_recipes=[
            {
                "resolution_type": "STUDENT_LINKED_TABLE",
                "source_table_hints": ["parent", "parents", "guardian", "guardians", "contact", "contacts"],
                "value_column_hints": ["email", "mail", "email_id", "email_address"],
                "cardinality": "ONE_TO_ONE"
            }
        ]
    ),
    FieldSpec(
        purpose="admission_type",
        synonyms=[
            "admission_type", "admission_category", "quota",
            "admission_quota", "category", "admission_mode",
            "type", "adm_type", "cat", "stud_category",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
        field_type="FK_LOOKUP",
        lookup_hint=["admission_categories", "categories", "quota_master", "admission_types"],
        fallback_recipes=[
            {
                "resolution_type": "STUDENT_LINKED_TABLE",
                "source_table_hints": ["admission", "admissions"],
                "value_column_hints": ["category", "admission_type", "quota"],
                "cardinality": "ONE_TO_ONE"
            }
        ]
    ),
    FieldSpec(
        purpose="entrance_rank",
        synonyms=[
            "entrance_rank", "eamcet_rank", "jee_rank", "rank",
            "entrance_score", "eamcet_score", "jee_score",
            "merit_rank", "entrance_percentile", "jee_percentile",
            "eapcet_rank", "kcet_rank", "ts_eamcet_rank",
            "ap_eamcet_rank",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
        fallback_recipes=[
            {
                "resolution_type": "STUDENT_LINKED_TABLE",
                "source_table_hints": ["admission", "admissions"],
                "value_column_hints": ["entrance_rank", "eamcet_rank", "jee_rank", "rank", "entrance_score", "score", "merit_rank"],
                "cardinality": "ONE_TO_ONE"
            }
        ]
    ),
]


# ---------------------------------------------------------------------------
# ROLE: ACADEMIC_RECORDS
# Academic performance per student — typically multi-row (one per semester)
# ---------------------------------------------------------------------------

ACADEMIC_RECORDS_FIELDS: List[FieldSpec] = [
    # ── REQUIRED ──────────────────────────────────────────────────────────
    FieldSpec(
        purpose="student_foreign_key",
        synonyms=[
            "student_id", "roll_no", "roll_number", "reg_no",
            "registration_no", "regd_no", "stud_id", "usn",
            "htno", "enroll_no", "enrollment_no", "roll",
            "regno", "student_code",
        ],
        requirement_level="CRITICAL",
        score_weight=10,
    ),
    FieldSpec(
        purpose="attendance_pct",
        synonyms=[
            "attendance", "attendance_pct", "attendance_percentage",
            "att_pct", "avg_attendance", "att_percent",
            "perc_attendance", "attendance_avg", "att_percentage",
            "overall_attendance", "total_attendance", "att",
            "pct_attendance", "present_percentage",
            "attendance_percent", "avg_att",
        ],
        requirement_level="IMPORTANT",
        score_weight=10,
        fallback_recipes=[
            {
                "resolution_type": "DERIVED_AGGREGATE",
                "source_table_hints": ["attendance", "attendance_log", "attendance_record", "class_attendance"],
                "value_column_hints": ["status", "attendance_status", "present_flag"],
                "group_by": "student_foreign_key",
                "aggregation_function": "RATIO",
                "ratio_numerator_match_values": ["P", "Present", "1", "Y", "Yes"]
            }
        ]
    ),
    FieldSpec(
        purpose="internal_marks",
        synonyms=[
            "marks", "internal_marks", "avg_marks", "internal_score",
            "ia_marks", "cia_marks", "theory_marks", "internal",
            "int_marks", "sessional_marks", "internal_assessment",
            "assessment_marks", "unit_test_marks", "cie_marks",
            "continuous_assessment", "avg_internal",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=10,
    ),
    FieldSpec(
        purpose="backlog_count",
        synonyms=[
            "backlogs", "backlog_count", "arrears", "no_of_arrears",
            "pending_subjects", "failed_subjects", "supply_count",
            "no_of_backlogs", "arrear_count", "detained_subjects",
            "back_papers", "failed_papers", "arrear_subjects",
            "total_backlogs", "backlog", "arrear",
        ],
        requirement_level="IMPORTANT",
        score_weight=10,
        fallback_recipes=[
            {
                "resolution_type": "DERIVED_AGGREGATE",
                "source_table_hints": ["grade", "grades", "results"],
                "join_via_hints": ["enrollment", "enrollments"],
                "value_column_hints": ["letter_grade", "grade", "result"],
                "filter_condition_hints": {
                    "column_hints": ["letter_grade", "grade", "status", "result"],
                    "match_values": ["F", "FAIL", "Fail", "Failed", "Backlog", "Arrear", "Detained", "RA", "U"]
                },
                "aggregation_function": "COUNT"
            },
            {
                "resolution_type": "DERIVED_AGGREGATE",
                "source_table_hints": ["enrollment", "enrollments", "registration"],
                "value_column_hints": ["status"],
                "filter_condition_hints": {
                    "column_hints": ["status"],
                    "match_values": ["F", "FAIL", "Fail", "Failed", "Backlog", "Arrear", "Detained", "RA", "U"]
                },
                "aggregation_function": "COUNT"
            }
        ]
    ),
    # ── OPTIONAL ──────────────────────────────────────────────────────────
    FieldSpec(
        purpose="semester",
        synonyms=[
            "semester", "sem", "sem_no", "semester_no",
            "current_semester", "academic_semester", "term",
            "sem_number", "semno",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
    ),
    FieldSpec(
        purpose="cgpa",
        synonyms=[
            "cgpa", "gpa", "cumulative_gpa", "cgpa_value",
            "grade_points", "cgpa_score", "cum_gpa",
            "cumulative_grade_points", "overall_gpa",
            "sgpa", "current_gpa",
        ],
        requirement_level="IMPORTANT",
        score_weight=10,
        fallback_recipes=[
            {
                "resolution_type": "DERIVED_AGGREGATE",
                "source_table_hints": ["grade", "grades", "results", "academic_results", "marks_record"],
                "join_via_hints": ["enrollment", "enrollments", "registration", "course_registration"],
                "value_column_hints": ["gpa_points", "grade_points", "points", "grade_value"],
                "group_by": "student_foreign_key",
                "aggregation_function": "AVG",
                "weight_column_hints": ["credits", "credit_hours", "weight", "units"]
            }
        ]
    ),
    FieldSpec(
        purpose="mid_exam_score",
        synonyms=[
            "mid_exam_score", "mid_marks", "midterm_score",
            "mid_score", "mid_term", "mid_exam", "midterm_marks",
            "mid_test", "midterm", "mid",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
    ),
    FieldSpec(
        purpose="lab_performance",
        synonyms=[
            "lab_performance", "lab_marks", "lab_score",
            "practical_marks", "lab_grade", "lab_internal",
            "practical_score", "lab", "practical",
            "lab_assessment",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
    ),
    FieldSpec(
        purpose="assignment_marks",
        synonyms=[
            "assignment_marks", "assignment_score", "assignments",
            "assignment", "hw_marks", "homework_marks",
            "homework_score", "assign_marks",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
    ),
    FieldSpec(
        purpose="consecutive_absences",
        synonyms=[],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
        field_type="COMPUTED_BEHAVIORAL",
    ),
    FieldSpec(
        purpose="leave_frequency",
        synonyms=[],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
        field_type="COMPUTED_BEHAVIORAL",
    ),
    FieldSpec(
        purpose="tenth_percentage",
        synonyms=[
            "tenth", "tenth_percentage", "tenth_pct",
            "ssc_percentage", "ssc_marks", "x_percentage",
            "class_10_percentage", "ten_percentage",
            "matriculation_percentage", "ssc", "class10",
            "tenth_marks", "tenth_percent",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
    ),
    FieldSpec(
        purpose="inter_percentage",
        synonyms=[
            "inter", "intermediate_percentage", "inter_pct",
            "hsc_percentage", "plus2_percentage",
            "xii_percentage", "class_12_percentage",
            "twelve_percentage", "inter_marks", "hsc",
            "class12", "plus_two", "twelve_marks",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
    ),
    FieldSpec(
        purpose="diploma_percentage",
        synonyms=[
            "diploma", "diploma_percentage", "diploma_pct",
            "polytechnic_percentage", "poly_percentage",
            "diploma_marks", "poly_marks",
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
    ),
]


# ---------------------------------------------------------------------------
# ROLE: BRANCH_MASTER
# One row per branch/department — the lookup table for department names
# ---------------------------------------------------------------------------

BRANCH_MASTER_FIELDS: List[FieldSpec] = [
    # ── REQUIRED ──────────────────────────────────────────────────────────
    FieldSpec(
        purpose="branch_id",
        synonyms=[
            "id", "branch_id", "dept_id", "department_id",
            "program_id", "course_id", "branch_code", "dept_code",
            "stream_id", "specialization_id", "course_code",
            "department_code", "branchid", "deptid",
        ],
        requirement_level="CRITICAL",
        score_weight=10,
    ),
    FieldSpec(
        purpose="branch_name",
        synonyms=[
            "branch_name", "dept_name", "department_name",
            "program_name", "course_name", "branch", "department",
            "stream_name", "specialization", "course",
            "branch_title", "dept_title", "program_title",
            "department_title", "stream", "discipline", "name", "title"
        ],
        requirement_level="CRITICAL",
        score_weight=10,
    ),
]


# ---------------------------------------------------------------------------
# ROLE: PARENT_CONTACTS
# Optional table for parent/guardian contact info
# ---------------------------------------------------------------------------

PARENT_CONTACTS_FIELDS: List[FieldSpec] = [
    FieldSpec(
        purpose="student_foreign_key",
        synonyms=[
            "student_id", "stud_id", "reg_no", "registration_no",
            "roll_no", "roll_number", "admission_no", "usn"
        ],
        requirement_level="CRITICAL",
        score_weight=10,
    ),
    FieldSpec(
        purpose="parent_email",
        synonyms=[
            "email", "parent_email", "guardian_email", 
            "father_email", "mother_email", "parent_mail",
            "family_email", "contact_email"
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
    ),
    FieldSpec(
        purpose="parent_phone",
        synonyms=[
            "phone", "parent_phone", "mobile", "guardian_phone",
            "contact_no", "parent_mobile", "father_phone",
            "mother_phone", "parent_contact", "emergency_contact",
            "guardian_mobile", "father_mobile", "mother_mobile"
        ],
        requirement_level="SUPPLEMENTARY",
        score_weight=2,
    ),
]


# ---------------------------------------------------------------------------
# Aggregated lookup helpers consumed by SchemaDetector
# ---------------------------------------------------------------------------

# All roles as a registry: role_name → list of FieldSpec
ALL_ROLES: Dict[str, List[FieldSpec]] = {
    "STUDENT_MASTER": STUDENT_MASTER_FIELDS,
    "ACADEMIC_RECORDS": ACADEMIC_RECORDS_FIELDS,
    "BRANCH_MASTER": BRANCH_MASTER_FIELDS,
    "PARENT_CONTACTS": PARENT_CONTACTS_FIELDS,
}

# Flat set of all synonyms across all roles — used for the single
# INFORMATION_SCHEMA IN-clause query
ALL_SYNONYMS: List[str] = sorted({
    synonym
    for fields in ALL_ROLES.values()
    for field_spec in fields
    for synonym in field_spec.synonyms
})

# Synonym → (role, purpose) reverse lookup — used during scoring
SYNONYM_TO_FIELD: Dict[str, Dict[str, object]] = {}
for _role_name, _fields in ALL_ROLES.items():
    for _fspec in _fields:
        for _syn in _fspec.synonyms:
            if _syn not in SYNONYM_TO_FIELD:
                SYNONYM_TO_FIELD[_syn] = {
                    "role": _role_name,
                    "purpose": _fspec.purpose,
                    "requirement_level": _fspec.requirement_level,
                    "score_weight": _fspec.score_weight,
                }
