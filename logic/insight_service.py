"""
Insight Service
===============
Pure service layer for aggregating Risk Intelligence.
Decouples UI (insight_center.py) from the AI models and Database layers.
"""

from logic.prediction_service import PredictionService
from logic.central_auth import CentralAuth
from logic.intervention_engine import InterventionEngine

class InsightService:
    def __init__(self):
        self.predictor = PredictionService()

    def get_simulation_report(self, student_data: dict, year: str = "2nd Year") -> dict:
        """Runs the AI predictor on provided data for simulation."""
        return self.predictor.analyze(student_data, year=year)

    def get_full_student_insight(self, student_data: dict, college_name: str) -> tuple:
        """
        Fetches the complete intelligence profile for a student:
        Returns: (report, raw_notes, raw_interventions)
        """
        report = self.predictor.analyze(student_data)
        
        student_id = student_data.get('id', student_data.get('student_id', ''))
        
        ca = CentralAuth()
        ie = InterventionEngine()
        
        raw_notes = ca.get_notes_for_student(student_id)
        raw_interventions = ie.get_database_interventions(college_name, student_id)
        
        return report, raw_notes, raw_interventions
