import os
import joblib
import pandas as pd
import numpy as np
from logic.trend_engine import TrendAnalyzer
from logic.intervention_engine import InterventionEngine
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
        def get_col(col_name):
            if col_name in df.columns:
                return pd.to_numeric(df[col_name], errors='coerce').fillna(0)
            return pd.Series([0.0]*len(df))

        X['attendance'] = get_col('avg_attendance')
        X['marks'] = get_col('avg_marks')
        X['backlogs'] = get_col('backlogs')
        X['tenth_percentage'] = get_col('tenth')
        X['intermediate_percentage'] = get_col('inter')
        X['diploma_percentage'] = get_col('diploma')
        X['lab_performance'] = get_col('lab_performance')
        X['mid_exam_score'] = get_col('mid_exam_score')
        X['consecutive_absences'] = get_col('consecutive_absences')
        X['leave_frequency'] = get_col('leave_frequency')

        # Make sure they are in the exact order the model expects if using a 10-feature model
        cols = ['attendance', 'marks', 'backlogs', 'tenth_percentage', 
                'intermediate_percentage', 'diploma_percentage',
                'lab_performance', 'mid_exam_score', 'consecutive_absences', 'leave_frequency']
        X = X[cols]

        if self.model:
            # We predict using wrapper logic safely
            if hasattr(self.model, 'feature_names_in_'):
                expected_cols = list(self.model.feature_names_in_)
                # Add missing expected columns with zeros
                for c in expected_cols:
                    if c not in X.columns:
                        X[c] = 0.0
                X_pred = X[expected_cols]
            else:
                X_pred = X

            if hasattr(self.model, 'predict'):
                predictions = self.model.predict(X_pred)
            else:
                predictions = np.array(['Low'] * len(X))
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

    def analyze_student(self, student_features, current_sem, history_data=None):
        """
        Advanced Analysis with SHAP and 10 features.
        student_features: dict containing attendance, marks, backlogs, tenth_percentage, 
                          intermediate_percentage, diploma_percentage, lab_performance, 
                          mid_exam_score, consecutive_absences, leave_frequency.
        """
        # 1. Sanitize Inputs & Create DataFrame
        try:
            att = float(student_features.get('attendance', student_features.get('avg_attendance', 0)) or 0)
            mrk = float(student_features.get('marks', student_features.get('avg_marks', 0)) or 0)
            bkl = int(student_features.get('backlogs', 0) or 0)
            tenth = float(student_features.get('tenth_percentage', 0) or 0)
            inter = float(student_features.get('intermediate_percentage', 0) or 0)
            diploma = float(student_features.get('diploma_percentage', 0) or 0)
            lab = float(student_features.get('lab_performance', 0) or 0)
            mid = float(student_features.get('mid_exam_score', 0) or 0)
            cons_abs = int(student_features.get('consecutive_absences', 0) or 0)
            leave_freq = int(student_features.get('leave_frequency', 0) or 0)
        except Exception: 
            return self._get_fallback_report(0, 0, 0)

        missing_data = []
        if att == 0: missing_data.append("Attendance")
        if mrk == 0: missing_data.append("Marks")
        
        confidence = "High" if not missing_data else "Low (Missing Data)"

        # Prepare 10 features in exactly the order model expects
        cols = ['attendance', 'marks', 'backlogs', 'tenth_percentage', 
                'intermediate_percentage', 'diploma_percentage',
                'lab_performance', 'mid_exam_score', 'consecutive_absences', 'leave_frequency']
        
        row_data = [[att, mrk, bkl, tenth, inter, diploma, lab, mid, cons_abs, leave_freq]]
        input_data = pd.DataFrame(row_data, columns=cols)

        if not self.model: 
            return self._get_fallback_report(att, mrk, bkl)

        try:
            if hasattr(self.model, 'feature_names_in_'):
                expected_cols = list(self.model.feature_names_in_)
                for c in expected_cols:
                    if c not in input_data.columns:
                        input_data[c] = 0.0
                input_pred = input_data[expected_cols]
            else:
                input_pred = input_data
                
            # For WrapperModel (XGBoost/LGBM wrapper), predict returns strings
            pred = self.model.predict(input_pred)[0]
            probs = self.model.predict_proba(input_pred)[0]
            
            # Identify probabilities safely
            if hasattr(self.model, 'classes_'):
                classes = self.model.classes_ 
                h_idx = np.where(classes == 'High')[0]
                m_idx = np.where(classes == 'Medium')[0]
                l_idx = np.where(classes == 'Low')[0]
                p_high = probs[h_idx][0] if len(h_idx)>0 else 0
                p_med = probs[m_idx][0] if len(m_idx)>0 else 0
                p_low = probs[l_idx][0] if len(l_idx)>0 else 0
            else:
                p_high, p_med, p_low = 0, 0, 0

            confidence = int(max(p_high, p_med, p_low) * 100)
            
            if pred == 'High':
                risk_score = 71 + (p_high * 29) # 71 to 100
            elif pred == 'Medium':
                risk_score = 41 + (p_med * 29)  # 41 to 70
            else:
                risk_score = 5 + (p_low * 35)   # 5 to 40
                
            risk_score = min(max(int(risk_score), 1), 100)
            
            # Calculate SHAP Values
            try:
                import shap
                import warnings
                
                # For tree models wrapped in our custom WrapperModel, extract inner model
                inner_model = getattr(self.model, 'model', self.model)
                
                # Cache the explainer to avoid massive slowdowns in loops
                if not hasattr(self, '_shap_explainer'):
                    self._shap_explainer = shap.TreeExplainer(inner_model)
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    shap_vals = self._shap_explainer.shap_values(input_pred)
                
                # shap_values can be a list (multiclass) or array
                if isinstance(shap_vals, list):
                    if hasattr(self.model, 'classes_') and 'High' in self.model.classes_:
                        h_idx = list(self.model.classes_).index('High')
                        shap_target = shap_vals[h_idx][0]
                    else:
                        shap_target = shap_vals[-1][0] 
                elif len(shap_vals.shape) == 3:
                    if hasattr(self.model, 'classes_') and 'High' in self.model.classes_:
                        h_idx = list(self.model.classes_).index('High')
                        shap_target = shap_vals[0, :, h_idx]
                    else:
                        shap_target = shap_vals[0, :, -1]
                else:
                    shap_target = shap_vals[0]
                    
                actual_cols = expected_cols if hasattr(self.model, 'feature_names_in_') else cols
                shap_dict = {actual_cols[i]: float(shap_target[i]) for i in range(len(actual_cols))}
            except Exception as e:
                print("SHAP calculation failed:", e)
                shap_dict = {}

            # 6. Generate Recommendations
            from logic.intervention_engine import InterventionEngine
            ie = InterventionEngine()
            
            # Use SHAP dict to find top factors
            top_factors = [k for k, v in sorted(shap_dict.items(), key=lambda item: abs(item[1]), reverse=True)[:2]]
            recommendations = ie.generate_recommendations(pred, top_factors, student_features)
            nlg_report = ie.generate_nlp_report(pred, top_factors, student_features, recommendations)
            # Trend Integration
            trend_info = None
            if history_data:
                analyzer = TrendAnalyzer()
                trend_info = analyzer.analyze_history(history_data)
                
                if trend_info["trend_status"] == "Critical Decline": risk_score += 20
                elif trend_info["trend_status"] == "Declining Performance": risk_score += 10
                elif trend_info["trend_status"] == "Improving Performance": risk_score -= 15

            if missing_data and risk_score > 75:
                risk_score = 75
            risk_score = round(max(0, min(100, risk_score)), 1)

        except Exception as e:
            print("Analyze Exception:", e)
            return self._get_fallback_report(att, mrk, bkl)

        # 4. Extract Contributions (Dynamic SHAP or Fallback)
        if 'shap_dict' in locals() and shap_dict:
            # Add Trend Impact to the SHAP values visually if trend exists
            if trend_info and trend_info.get("trend_score", 50) != 50:
                # Calculate an arbitrary SHAP value equivalent for trend based on the score deviation
                trend_impact = (50 - trend_info["trend_score"]) / 100.0  # scaled
                shap_dict["Trend Impact"] = trend_impact
                
            total_shap_abs = sum(abs(v) for v in shap_dict.values())
            if total_shap_abs > 0:
                contribs = {k.replace("_", " ").title(): (abs(v) / total_shap_abs) * 100 for k, v in shap_dict.items() if abs(v) > 0.01}
            else:
                contribs = {"No Major Factors": 100}
        else:
            # Fallback Explainability if SHAP fails
            dev_att = max(0, 75 - att) / 75 if att > 0 else 0
            dev_mrk = max(0, 50 - mrk) / 50 if mrk > 0 else 0
            dev_bkl = min(5, bkl) / 5
            total_dev = max(1, dev_att + dev_mrk + dev_bkl)
            contribs = {
                "Attendance": (dev_att / total_dev) * 100, 
                "Academics": (dev_mrk / total_dev) * 100, 
                "Backlogs": (dev_bkl / total_dev) * 100
            }
        
        # 5. Dominant Factor Logic
        if risk_score < 20:
            dom = "None (Safe)"
        elif missing_data and risk_score > 50:
            dom = "Inconclusive (Data Missing)"
        else:
            sorted_factors = sorted(contribs.items(), key=lambda x: x[1], reverse=True)
            if sorted_factors:
                top_1_name, top_1_val = sorted_factors[0]
                dom = top_1_name
                if len(sorted_factors) > 1:
                    top_2_name, top_2_val = sorted_factors[1]
                    if (top_1_val - top_2_val) < 10 and top_1_val > 0:
                        dom = f"Joint {top_1_name} & {top_2_name}"
            else:
                dom = "Unknown"

        # 6. Trend Simulation / History
        trend_data = []
        if history_data:
            hist = sorted(history_data, key=lambda x: x.get('semester', 0))
            # Multiply CGPA by 10 to scale to 0-100% format expected by the legacy UI
            trend_data = [h.get('cgpa', 0) * 10 for h in hist]
            # Don't pad or slice to strictly 4, let it be dynamic based on the actual number of semesters available
        
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
        
        # Override action if critical decline
        if trend_info and trend_info.get("is_critical_drop"):
            act = "Immediate Intervention (Critical Drop)"
        return {
            "score": risk_score, "level": pred, "dominant": dom, 
            "action": act, "contributions": contribs, "tags": "ML-RF",
            "confidence": confidence, "missing": missing_data,
            "trend": trend_data, "trend_info": trend_info,
            "shap_values": shap_dict if 'shap_dict' in locals() else {},
            "nlg_report": nlg_report if 'nlg_report' in locals() else "",
            "recommendations": recommendations if 'recommendations' in locals() else []
        }

    def analyze_first_year(self, att, tenth, inter, diploma, bkl):
        """Dedicated workflow for 1st-year students using previous academics."""
        # 1. Input normalization
        att = float(att) if att is not None else 0.0
        tenth = float(tenth) if tenth is not None else 0.0
        inter = float(inter) if inter is not None else 0.0
        diploma = float(diploma) if diploma is not None else 0.0
        bkl = int(bkl) if bkl is not None else 0
        
        # 2. Select previous academic indicator (prefer inter/diploma over 10th alone if available)
        prev_acad = 0.0
        acad_label = "Previous Academics"
        
        if inter > 0 and diploma > 0:
            prev_acad = max(inter, diploma)
            acad_label = "Inter/Diploma"
        elif inter > 0:
            prev_acad = inter
            acad_label = "Intermediate"
        elif diploma > 0:
            prev_acad = diploma
            acad_label = "Diploma"
        elif tenth > 0:
            prev_acad = tenth
            acad_label = "10th Grade"
            
        # 3. Base Score Calculation (Heuristic Model)
        # Weights: Prev Academics (40%), Attendance (40%), Current Backlogs (20%)
        # Convert to risk penalties. 
        # Safe norms: Academics > 75%, Att > 75%, Bkl = 0
        
        risk_acad = max(0, 75 - prev_acad) * (40 / 75) if prev_acad > 0 else 20  # Missing data penalty = 20
        risk_att = max(0, 75 - att) * (40 / 75) if att > 0 else 20
        risk_bkl = min(20, bkl * 10)  # 10 points per backlog
        
        risk_score = risk_acad + risk_att + risk_bkl
        
        # Scale risk_score slightly to match 0-100 expected spread
        risk_score = round(min(100.0, risk_score * 1.5), 1)
        
        # 4. Risk Level
        if risk_score > 60: pred = "High"
        elif risk_score > 35: pred = "Medium"
        else: pred = "Low"
        
        # 5. Explainable Contributions
        total_risk = risk_acad + risk_att + risk_bkl
        if total_risk == 0: total_risk = 1
        
        contribs = {
            acad_label: (risk_acad / total_risk) * 100,
            "Attendance": (risk_att / total_risk) * 100,
            "Current Backlogs": (risk_bkl / total_risk) * 100
        }
        
        # 6. Dominant Factor
        sorted_factors = sorted(contribs.items(), key=lambda x: x[1], reverse=True)
        top_1_name, top_1_val = sorted_factors[0]
        
        if risk_score < 20:
            dom = "None (Safe)"
        else:
            dom = top_1_name
            
        # 7. Action Engine
        act = "Monitor"
        if pred == "High":
            if dom == acad_label: act = "Academic Mentoring"
            elif dom == "Attendance": act = "Attendance Counseling"
            elif dom == "Current Backlogs": act = "Remedial Classes"
            else: act = "General Intervention"
        elif pred == "Medium":
            act = "Early Warning Notification"
        
        # Determine dominant factors safely
        dom_factors = []
        if isinstance(dom, str) and dom:
            dom_factors = [dom]
            
        from logic.intervention_engine import InterventionEngine
        ie = InterventionEngine()
        recommendations = ie.generate_recommendations(pred, dom_factors, {'attendance': att, 'backlogs': bkl})
        report_text = ie.generate_nlp_report(pred, dom_factors, {'attendance': att, 'backlogs': bkl}, recommendations)
            
        return {
            "level": pred, "score": risk_score, "dominant": dom,
            "action": act, "contributions": contribs,
            "shap_values": {},
            "nlg_report": report_text,
            "recommendations": recommendations,
            "confidence": "High",
            "trend": [], "is_first_year": True
        }

    def _get_fallback_report(self, a, m, b):
        return {
            "score": 0, "level": "Low", "dominant": "-", "action": "-", 
            "contributions": {}, "tags": "ERR", "confidence": "Low", "trend": [],
            "shap_values": {}, "nlg_report": "Error predicting risk due to model failure or missing data."
        }
    
    def _get_error_report(self):
        return {"score": 0, "level": "Error", "dominant": "-", "action": "-", 
                "contributions": {}, "tags": "ERR", "confidence": "Low", "trend": []}