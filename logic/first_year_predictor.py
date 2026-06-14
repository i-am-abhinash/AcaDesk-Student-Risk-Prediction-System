import os
import joblib
import pandas as pd
import numpy as np

class FirstYearPredictor:
    def __init__(self):
        self.model = None
        self.model_path = "first_year_model.pkl"
        self._load_model()

    def _load_model(self):
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            elif os.path.exists(os.path.join("..", self.model_path)):
                self.model = joblib.load(os.path.join("..", self.model_path))
            else:
                print("⚠️ First-Year AI Model not found. Using fallback.")
        except Exception as e:
            print(f"⚠️ Error loading First-Year AI: {e}")

    def _process_inputs(self, student_features):
        tenth = float(student_features.get('tenth_percentage', 0) or 0)
        inter = float(student_features.get('intermediate_percentage', 0) or 0)
        diploma = float(student_features.get('diploma_percentage', 0) or 0)
        
        # Missing data handling: Use Inter if available, otherwise Diploma
        higher_edu = inter if inter > 0 else diploma
        
        att = float(student_features.get('attendance', student_features.get('avg_attendance', 0)) or 0)
        mrk = float(student_features.get('marks', student_features.get('internal_marks', 0)) or 0)
        absences = int(student_features.get('consecutive_absences', 0) or 0)
        
        cols = ['tenth_percentage', 'prior_higher_edu_percentage', 'attendance', 'internal_marks', 'consecutive_absences']
        input_data = pd.DataFrame([[tenth, higher_edu, att, mrk, absences]], columns=cols)
        
        return input_data, tenth, higher_edu, att

    def batch_analyze(self, students_list):
        if not students_list: return {"High": 0, "Medium": 0, "Low": 0}, {}
        
        df = pd.DataFrame(students_list)
        X = pd.DataFrame()
        
        def get_col(col_name):
            if col_name in df.columns: return pd.to_numeric(df[col_name], errors='coerce').fillna(0)
            return pd.Series([0.0]*len(df))

        X['tenth_percentage'] = get_col('tenth')
        inter = get_col('inter')
        diploma = get_col('diploma')
        X['prior_higher_edu_percentage'] = np.where(inter > 0, inter, diploma)
        X['attendance'] = get_col('avg_attendance')
        X['internal_marks'] = get_col('avg_marks')
        X['consecutive_absences'] = get_col('consecutive_absences')

        cols = ['tenth_percentage', 'prior_higher_edu_percentage', 'attendance', 'internal_marks', 'consecutive_absences']
        X = X[cols]

        if self.model:
            predictions = self.model.predict(X)
        else:
            # Fallback
            conditions = [(X['attendance'] < 65) | ((X['tenth_percentage'] < 55) & (X['prior_higher_edu_percentage'] < 55)),
                          (X['attendance'] < 75) | (X['internal_marks'] < 50) | (X['consecutive_absences'] > 5)]
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

    def analyze_student(self, student_features):
        input_data, tenth, higher_edu, att = self._process_inputs(student_features)

        if not self.model:
            return self._fallback_analyze(tenth, higher_edu, att)

        try:
            pred = self.model.predict(input_data)[0]
            probs = self.model.predict_proba(input_data)[0]
            
            classes = self.model.classes_ 
            p_high = probs[np.where(classes == 'High')[0][0]] if 'High' in classes else 0
            p_med = probs[np.where(classes == 'Medium')[0][0]] if 'Medium' in classes else 0
            p_low = probs[np.where(classes == 'Low')[0][0]] if 'Low' in classes else 0

            confidence = int(max(p_high, p_med, p_low) * 100)
            
            if pred == 'High': risk_score = 71 + (p_high * 29)
            elif pred == 'Medium': risk_score = 41 + (p_med * 29)
            else: risk_score = 5 + (p_low * 35)
                
            risk_score = min(max(int(risk_score), 1), 100)

            # Explainable AI Contributions
            # For First-Year, we can use model.feature_importances_ multiplied by the deviation from safe baselines
            # Or simplified SHAP approximation
            contributions = {}
            if hasattr(self.model, 'feature_importances_'):
                imp = self.model.feature_importances_
                contributions['10th Percentage'] = round(imp[0] * 100)
                contributions['Higher Ed (Inter/Diploma)'] = round(imp[1] * 100)
                contributions['Attendance'] = round(imp[2] * 100)
                contributions['Internal Marks'] = round(imp[3] * 100)
                contributions['Absences'] = round(imp[4] * 100)
            else:
                contributions = {'Attendance': 40, 'Higher Ed (Inter/Diploma)': 35, '10th Percentage': 15, 'Internal Marks': 10}

            # Normalize to 100%
            total = sum(contributions.values())
            if total > 0:
                for k in contributions:
                    contributions[k] = int((contributions[k] / total) * 100)

            # Recommendations
            recommendations = []
            if higher_edu < 60 or tenth < 60:
                recommendations.append("Academic Mentoring (Low Previous Academic Performance)")
            if att < 75:
                recommendations.append("Attendance Counseling")
            if input_data['internal_marks'][0] < 50:
                recommendations.append("Remedial Classes")
            
            if not recommendations:
                recommendations.append("Continue current monitoring. No immediate intervention needed.")

            return {
                "risk_category": pred,
                "risk_score": risk_score,
                "confidence": confidence,
                "shap_values": contributions,
                "is_first_year": True,
                "recommendations": recommendations
            }

        except Exception as e:
            print(f"FirstYearPredictor Error: {e}")
            return self._fallback_analyze(tenth, higher_edu, att)

    def _fallback_analyze(self, tenth, higher_edu, att):
        risk = "Low"
        score = 20
        if att < 65 or (tenth < 55 and higher_edu < 55):
            risk = "High"
            score = 85
        elif att < 75 or higher_edu < 65:
            risk = "Medium"
            score = 60

        return {
            "risk_category": risk,
            "risk_score": score,
            "confidence": 80,
            "shap_values": {'Attendance': 50, 'Higher Ed': 30, '10th Percentage': 20},
            "is_first_year": True,
            "recommendations": ["Academic Mentoring"] if risk != "Low" else ["Monitor"]
        }
