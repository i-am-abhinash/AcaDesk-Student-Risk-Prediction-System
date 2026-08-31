import os
import json
import joblib
import pandas as pd
import numpy as np
from logic.logger import get_logger
from logic.marking_scheme import MarkingSchemeDetector

logger = get_logger(__name__)

class RiskPredictor:
    def __init__(self, college_name: str = None):
        self.college_name = college_name
        self.model = None
        self.model_type = None
        self.model_features = None
        self.marking_scheme = None
        self.label_encoder = None
        self._load_model()
    
    def _safe_name(self, name: str) -> str:
        import re
        return re.sub(r'[^a-zA-Z0-9_]', '_', name).lower()
        
    def _load_model(self):
        """
        Load model in priority order:
        1. College-specific model
        2. Global fallback
        3. Heuristic mode
        """
        if self.college_name:
            college_path = os.path.join(
                "models",
                f"{self._safe_name(self.college_name)}_model.pkl"
            )
            if os.path.exists(college_path):
                try:
                    bundle = joblib.load(college_path)
                    self.model = bundle["model"]
                    self.model_type = bundle["model_type"]
                    self.model_features = bundle["features"]
                    self.marking_scheme = bundle["marking_scheme"]
                    self.label_encoder = bundle.get("label_encoder")
                    logger.info("Loaded college-specific %s model for %s", self.model_type, self.college_name)
                    return
                except Exception as e:
                    logger.error(f"Error loading college model {college_path}: {e}")
        
        # Fallback to global model
        if os.path.exists("synapse_model.pkl"):
            try:
                self.model = joblib.load("synapse_model.pkl")
                self.model_type = "random_forest"
                self.model_features = None
                self.marking_scheme = None
                logger.info("Loaded global fallback model synapse_model.pkl")
                return
            except Exception as e:
                logger.error(f"Error loading synapse_model.pkl: {e}")
        
        logger.warning("No model found. Running in heuristic mode.")
    
    def analyze_student(self, student_features: dict, current_sem: int = None, history_data: list = None) -> dict:
        """
        Normalize features using the college's marking scheme before prediction.
        """
        if self.model and self.model_features and self.marking_scheme:
            # We are using a college-specific model
            detector = MarkingSchemeDetector()
            
            # Check how many of the expected features are actually provided
            provided_count = sum(1 for f in self.model_features if f in student_features and student_features[f] is not None)
            
            if provided_count < 2 and len(self.model_features) >= 2:
                # Too few features provided, fall through to heuristic
                pass
            else:
                try:
                    X_dict = {}
                    for feat in self.model_features:
                        val = student_features.get(feat)
                        if val is not None:
                            try:
                                val = float(val)
                                if feat in self.marking_scheme:
                                    X_dict[feat] = detector.normalize_to_percentage(val, self.marking_scheme[feat])
                                else:
                                    X_dict[feat] = val
                            except (ValueError, TypeError):
                                X_dict[feat] = 0.0 # Use 0.0 or median
                        else:
                            X_dict[feat] = 0.0
                            
                    X_df = pd.DataFrame([X_dict])[self.model_features]
                    
                    if hasattr(self.model, 'predict_proba'):
                        probs = self.model.predict_proba(X_df)[0]
                        pred = self.model.predict(X_df)[0]
                        if self.label_encoder:
                            pred = self.label_encoder.inverse_transform([pred])[0]
                            # XGBoost probabilities align with classes_
                            classes = self.label_encoder.classes_
                        else:
                            classes = self.model.classes_
                            
                        risk_prob = {}
                        for i, c in enumerate(classes):
                            risk_prob[c] = probs[i]
                            
                        # Extract High risk probability
                        high_risk_prob = risk_prob.get('High', 0.0)
                    else:
                        pred = self.model.predict(X_df)[0]
                        if self.label_encoder:
                            pred = self.label_encoder.inverse_transform([pred])[0]
                        high_risk_prob = 1.0 if pred == 'High' else 0.0
                        
                    return {
                        "risk_level": pred,
                        "risk_score": round(high_risk_prob * 100, 2),
                        "model_used": self.model_type
                    }
                except Exception as e:
                    logger.error(f"Prediction error using college model: {e}")
                    # Fall through to global/heuristic
        
        # Fallback to Global Model (which expects hardcoded columns without dynamic normalization)
        if self.model and not self.model_features:
            try:
                def _get_val(keys, default=0.0):
                    for k in keys:
                        if k in student_features and student_features[k] is not None:
                            try:
                                return float(student_features[k])
                            except: pass
                    return default
                    
                att = _get_val(['attendance', 'avg_attendance', 'attendance_pct'])
                cgpa = _get_val(['cgpa'])
                bkl = _get_val(['backlogs'])
                marks = _get_val(['avg_marks', 'internal_marks'])
                mid = _get_val(['mid_exam_score'])
                lab = _get_val(['lab_performance'])
                assign = _get_val(['assignment_marks'])
                t = _get_val(['tenth', 'tenth_percentage'])
                inter = _get_val(['inter', 'inter_percentage'])
                dip = _get_val(['diploma', 'diploma_percentage'])
                cons = _get_val(['consecutive_absences'])
                lv = _get_val(['leave_frequency'])
                
                # If CGPA is missing but marks exist, simulate CGPA on 10pt
                if cgpa == 0.0 and marks > 0.0:
                    cgpa = marks / 10.0
                    
                cols = ['avg_attendance', 'cgpa', 'backlogs', 'avg_marks', 
                        'mid_exam_score', 'lab_performance', 'assignment_marks',
                        'tenth', 'inter', 'diploma', 
                        'consecutive_absences', 'leave_frequency']
                        
                X_df = pd.DataFrame([{
                    'avg_attendance': att, 'cgpa': cgpa, 'backlogs': bkl, 'avg_marks': marks,
                    'mid_exam_score': mid, 'lab_performance': lab, 'assignment_marks': assign,
                    'tenth': t, 'inter': inter, 'diploma': dip,
                    'consecutive_absences': cons, 'leave_frequency': lv
                }])[cols]
                
                if hasattr(self.model, 'feature_names_in_'):
                    expected_cols = list(self.model.feature_names_in_)
                    for c in expected_cols:
                        if c not in X_df.columns:
                            X_df[c] = 0.0
                    X_df = X_df[expected_cols]
                    
                if hasattr(self.model, 'predict_proba'):
                    probs = self.model.predict_proba(X_df)[0]
                    pred = self.model.predict(X_df)[0]
                    classes = self.model.classes_
                    risk_prob = {c: probs[i] for i, c in enumerate(classes)}
                    high_risk_prob = risk_prob.get('High', 0.0)
                else:
                    pred = self.model.predict(X_df)[0]
                    high_risk_prob = 1.0 if pred == 'High' else 0.0
                    
                return {
                    "risk_level": pred,
                    "risk_score": round(high_risk_prob * 100, 2),
                    "model_used": "global_fallback"
                }
            except Exception as e:
                logger.error(f"Prediction error using global model: {e}")
                # Fall through
                
        # Heuristic Mode
        def _get_val(keys, default=0.0):
            for k in keys:
                if k in student_features and student_features[k] is not None:
                    try: return float(student_features[k])
                    except: pass
            return default
            
        bkl = _get_val(['backlogs'])
        att = _get_val(['attendance', 'avg_attendance', 'attendance_pct'])
        
        if bkl > 2 or att < 60:
            pred = 'High'
            score = 85.0
        elif bkl > 0:
            pred = 'Medium'
            score = 65.0
        else:
            pred = 'Low'
            score = 15.0
            
        return {
            "risk_level": pred,
            "risk_score": score,
            "model_used": "heuristic"
        }

    def batch_analyze(self, students_list: list[dict]):
        """Vectorized/Batch Processing for Dashboard Speed"""
        if not students_list: return {"High": 0, "Medium": 0, "Low": 0}, {}
        
        global_stats = {"High": 0, "Medium": 0, "Low": 0}
        branch_stats = {}
        
        for student in students_list:
            res = self.analyze_student(student)
            risk = res["risk_level"]
            global_stats[risk] += 1
            
            branch = student.get("branch")
            if branch:
                if branch not in branch_stats:
                    branch_stats[branch] = {"High": 0, "Medium": 0, "Low": 0}
                branch_stats[branch][risk] += 1
                
        return global_stats, branch_stats
