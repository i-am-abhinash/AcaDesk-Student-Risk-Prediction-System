import os
import joblib
import pandas as pd
import numpy as np

class RiskPredictor:
    def __init__(self):
        self.model = None
        self.model_path = "synapse_model.pkl"
        self._load_model()

    def _load_model(self):
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            elif os.path.exists(os.path.join("..", self.model_path)):
                self.model = joblib.load(os.path.join("..", self.model_path))
            else:
                print("⚠️ AI Model not found. Using fallback.")
        except Exception as e:
            print(f"⚠️ Error loading AI: {e}")

    def get_global_importance(self):
        if self.model:
            imp = self.model.feature_importances_
            return {"Attendance": imp[0], "Internal Marks": imp[1], "Backlogs": imp[2]}
        return {"Attendance": 0.35, "Internal Marks": 0.25, "Backlogs": 0.40}

    def batch_analyze(self, students_list):
        """Vectorized Batch Processing for Dashboard Speed"""
        if not students_list: return {"High": 0, "Medium": 0, "Low": 0}, {}
        
        df = pd.DataFrame(students_list)
        X = pd.DataFrame()
        X['attendance'] = pd.to_numeric(df.get('avg_attendance', 0), errors='coerce').fillna(0)
        X['marks'] = pd.to_numeric(df.get('avg_marks', 0), errors='coerce').fillna(0)
        X['backlogs'] = pd.to_numeric(df.get('backlogs', 0), errors='coerce').fillna(0)

        if self.model:
            predictions = self.model.predict(X)
        else:
            # Heuristic Fallback
            conditions = [(X['backlogs'] > 2) | (X['attendance'] < 60), (X['backlogs'] > 0)]
            predictions = np.select(conditions, ['High', 'Medium'], default='Low')

        df['risk'] = predictions
        g_counts = df['risk'].value_counts().to_dict()
        global_stats = {k: g_counts.get(k, 0) for k in ["High", "Medium", "Low"]}

        branch_stats = {}
        if 'branch' in df.columns:
            try:
                groups = df.groupby(['branch', 'risk']).size().unstack(fill_value=0)
                for branch_id, row in groups.iterrows():
                    stats = {"High": 0, "Medium": 0, "Low": 0}
                    for r in ["High", "Medium", "Low"]:
                        if r in row: stats[r] = int(row[r])
                    branch_stats[branch_id] = stats
            except: pass
        return global_stats, branch_stats

    def analyze_student(self, attendance, marks, backlogs, current_sem):
        """
        Refined Analysis with Data Integrity and Tie-Breaking Logic.
        """
        # 1. Sanitize Inputs
        try:
            att = float(attendance) if attendance is not None else 0.0
            mrk = float(marks) if marks is not None else 0.0
            bkl = int(backlogs) if backlogs is not None else 0
        except: return self._get_error_report()

        # 2. Check for Missing Data (Data Integrity)
        missing_data = []
        if att == 0: missing_data.append("Attendance")
        if mrk == 0: missing_data.append("Marks")
        
        # Determine Confidence
        confidence = "High"
        if missing_data: confidence = "Low (Missing Data)"

        # 3. AI Prediction
        if not self.model: return self._get_fallback_report(att, mrk, bkl)

        input_data = pd.DataFrame([[att, mrk, bkl]], columns=['attendance', 'marks', 'backlogs'])
        try:
            pred = self.model.predict(input_data)[0]
            probs = self.model.predict_proba(input_data)[0]
            classes = self.model.classes_ 
            
            h_idx = np.where(classes == 'High')[0]
            m_idx = np.where(classes == 'Medium')[0]
            p_high = probs[h_idx][0] if len(h_idx)>0 else 0
            p_med = probs[m_idx][0] if len(m_idx)>0 else 0
            
            # Base Score
            risk_score = (p_high * 100) + (p_med * 50)
            
            # --- FIX: CAP SCORE IF DATA MISSING ---
            # We cannot be 100% sure if data is missing. Cap at 75 (Warning Zone).
            if missing_data and risk_score > 75:
                risk_score = 75
            
            risk_score = round(min(100, risk_score), 1)

        except: return self._get_fallback_report(att, mrk, bkl)

        # 4. Explainability (The "Why")
        # Logic: We calculate deviation from "Safe Norms" (75% Att, 50% Marks, 0 Backlogs)
        
        # If data is missing (0), contribution is 0 (Don't blame missing data)
        dev_att = max(0, 75 - att) / 75 if att > 0 else 0
        dev_mrk = max(0, 50 - mrk) / 50 if mrk > 0 else 0
        dev_bkl = min(5, bkl) / 5
        
        total_dev = dev_att + dev_mrk + dev_bkl
        if total_dev == 0: total_dev = 1

        contribs = {
            "Attendance": (dev_att / total_dev) * 100, 
            "Academics": (dev_mrk / total_dev) * 100, 
            "Backlogs": (dev_bkl / total_dev) * 100
        }
        
        # 5. Dominant Factor Logic (With Tie-Breaking)
        if risk_score < 20:
            dom = "None (Safe)"
        elif missing_data and risk_score > 50:
            dom = "Inconclusive (Data Missing)"
        else:
            # Sort factors by contribution
            sorted_factors = sorted(contribs.items(), key=lambda x: x[1], reverse=True)
            top_1_name, top_1_val = sorted_factors[0]
            top_2_name, top_2_val = sorted_factors[1]

            # If the top two are close (within 10%), call it Joint
            if (top_1_val - top_2_val) < 10 and top_1_val > 0:
                dom = f"Joint {top_1_name} & {top_2_name}"
            else:
                dom = top_1_name

        # 6. Trend Simulation
        trend_data = []
        if pred == "High": trend_data = [mrk + 15, mrk + 10, mrk + 5, mrk] 
        elif pred == "Medium": trend_data = [mrk + 5, mrk - 5, mrk + 2, mrk]
        else: trend_data = [mrk - 10, mrk - 5, mrk - 2, mrk]
        trend_data = [max(0, min(100, x)) for x in trend_data]

        # 7. Action Engine
        act = "Monitor"
        if pred == "High":
            if "Backlogs" in dom: act = "Degree Counseling"
            elif "Attendance" in dom: act = "Parents Meeting"
            elif "Academics" in dom: act = "Remedial Classes"
            elif "Inconclusive" in dom: act = "Verify Database Records"
            else: act = "General Intervention"
        elif pred == "Medium": act = "Issue Warning"

        return {
            "score": risk_score, "level": pred, "dominant": dom, 
            "action": act, "contributions": contribs, "tags": "ML-RF",
            "confidence": confidence, "missing": missing_data,
            "trend": trend_data
        }

    def _get_fallback_report(self, a, m, b):
        return {"score": 0, "level": "Low", "dominant": "-", "action": "-", 
                "contributions": {}, "tags": "ERR", "confidence": "Low", "trend": []}
    
    def _get_error_report(self):
        return {"score": 0, "level": "Error", "dominant": "-", "action": "-", 
                "contributions": {}, "tags": "ERR", "confidence": "Low", "trend": []}