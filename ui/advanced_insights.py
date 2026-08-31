import customtkinter as ctk
import pandas as pd
import numpy as np
import joblib
import os
import threading
from tkinter import Canvas
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve, auc
from sklearn.preprocessing import label_binarize
from ui.styles import COLORS, FONTS

class AdvancedInsightsPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color="#121212")
        self.controller = controller
        
        # Header
        self.header = ctk.CTkFrame(self, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(self.header, text="✨ AI Insights & What-If Analysis", font=("Outfit", 24, "bold"), text_color="#00E5FF").pack(side="left", padx=20, pady=15)
        
        # Main content area
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.model = None
        self.model_features = []
        self.metrics_data = {}
        
        self.loading_lbl = ctk.CTkLabel(self.scroll, text="Loading AI Model and Evaluating Performance...", font=FONTS["h3"])
        self.loading_lbl.pack(pady=50)

    def refresh(self):
        # Trigger evaluation in a thread to keep UI responsive
        for widget in self.scroll.winfo_children():
            widget.destroy()
        
        self.loading_lbl = ctk.CTkLabel(self.scroll, text="Evaluating SYNAPSE AI Model Performance...", font=FONTS["h3"], text_color="#aaaaaa")
        self.loading_lbl.pack(pady=50)
        
        t = threading.Thread(target=self._run_evaluation)
        t.start()

    def _run_evaluation(self):
        try:
            model_path = "synapse_model.pkl"
            if not os.path.exists(model_path):
                model_path = os.path.join("..", "synapse_model.pkl")
            
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
            else:
                self.after(0, self._show_error, "Model file not found. Please train the model first.")
                return

            if hasattr(self.model, 'feature_names_in_'):
                self.model_features = list(self.model.feature_names_in_)
            else:
                self.model_features = ['attendance', 'marks', 'backlogs'] # Fallback
                
            # Fetch real evaluation data from DB
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from logic.db_handler import DBHandler
            
            erp_conf = self.controller.shared_data.get("erp_config")
            db = DBHandler(erp_conf) if erp_conf else None
            
            if db and db.connected:
                raw_data = db.get_training_data()
                db.close()
                df = pd.DataFrame(raw_data)
                
                # Ground truth generation (following train_model logic exactly)
                df['y_true'] = np.where(
                    (df['avg_attendance'] < 65) | (df['backlogs'] >= 3) | (df['cgpa'] < 5.0) | (df['consecutive_absences'] >= 5),
                    'High',
                    np.where(
                        (df['avg_attendance'] < 75) | (df['backlogs'] >= 1) | (df['cgpa'] < 6.5) | (df['consecutive_absences'] >= 3) | (df['avg_marks'] < 50),
                        'Medium',
                        'Low'
                    )
                )
                
                y_true = df['y_true'].values
                X_test = df[self.model_features]
            else:
                self.after(0, self._show_error, "Database connection required for evaluation.")
                return
            
            # Predictions
            y_pred = self.model.predict(X_test)
            y_probs = self.model.predict_proba(X_test)
            
            # Compute Metrics
            acc = accuracy_score(y_true, y_pred)
            prec = precision_score(y_true, y_pred, average='weighted', zero_division=0)
            rec = recall_score(y_true, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
            cm = confusion_matrix(y_true, y_pred, labels=["High", "Medium", "Low"])
            
            # Feature Importances
            importances = []
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            
            self.metrics_data = {
                "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
                "confusion_matrix": cm, "y_true": y_true, "y_probs": y_probs,
                "importances": importances
            }
            
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.after(0, self._render_dashboard)
            
        except Exception as e:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.after(0, self._show_error, str(e))

    def _show_error(self, msg):
        if hasattr(self, 'loading_lbl') and self.loading_lbl.winfo_exists():
            self.loading_lbl.destroy()
        if self.winfo_exists():
            ctk.CTkLabel(self.scroll, text=f"⚠️ Evaluation Error: {msg}", text_color="red", font=FONTS["h3"]).pack(pady=20)

    def _render_dashboard(self):
        if hasattr(self, 'loading_lbl') and self.loading_lbl.winfo_exists():
            self.loading_lbl.destroy()
            
        if not self.winfo_exists(): return
        
        # 1. Feature Importance Bar Chart (Native Midnight Glass)
        if len(self.metrics_data["importances"]) > 0:
            feat_card = ctk.CTkFrame(self.scroll, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
            feat_card.pack(fill="x", padx=10, pady=(10, 20))
            
            ctk.CTkLabel(feat_card, text="GLOBAL FEATURE IMPORTANCE", font=("Inter", 12, "bold"), text_color="#7A849C").pack(pady=(15, 5))
            
            bars_frame = ctk.CTkFrame(feat_card, fg_color="transparent")
            bars_frame.pack(fill="x", expand=True, padx=20, pady=(5, 20))
            
            # Sort importances descending
            feats_and_imps = list(zip(self.model_features, self.metrics_data["importances"]))
            feats_and_imps.sort(key=lambda x: x[1], reverse=True)
            max_imp = feats_and_imps[0][1] if feats_and_imps else 1
            
            for f, imp in feats_and_imps:
                row = ctk.CTkFrame(bars_frame, fg_color="transparent")
                row.pack(fill="x", pady=4)
                
                f_name = f.replace("_", " ").title()
                ctk.CTkLabel(row, text=f_name, font=("Inter", 12, "bold"), text_color="white", width=160, anchor="e").pack(side="left", padx=(0, 15))
                
                track = ctk.CTkFrame(row, fg_color="#1A1D2D", height=10, corner_radius=5)
                track.pack(side="left", fill="x", expand=True)
                track.pack_propagate(False)
                
                pw = imp / max_imp if max_imp > 0 else 0
                if pw > 0:
                    ctk.CTkFrame(track, fg_color="#00E5FF", width=1, corner_radius=5).place(relx=0, rely=0, relwidth=pw, relheight=1)
                
                ctk.CTkLabel(row, text=f"{imp:.3f}", font=("Outfit", 12, "bold"), text_color="#00E5FF", width=50, anchor="w").pack(side="left", padx=(15, 0))
            
        # 2. Risk Adjuster (What-If Sandbox)
        sim_card = ctk.CTkFrame(self.scroll, fg_color="transparent")
        sim_card.pack(fill="x", padx=10, pady=(10, 20))
        
        ctk.CTkLabel(sim_card, text="🎛️ RISK ADJUSTER (WHAT-IF ANALYSIS)", font=("Inter", 12, "bold"), text_color="#7A849C").pack(pady=(10, 20))
        
        content_frame = ctk.CTkFrame(sim_card, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)
        content_frame.grid_columnconfigure(0, weight=2)
        content_frame.grid_columnconfigure(1, weight=1)
        
        sliders_f = ctk.CTkFrame(content_frame, fg_color="transparent")
        sliders_f.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        sliders_f.grid_columnconfigure((0,1,2), weight=1)
        
        results_f = ctk.CTkFrame(content_frame, fg_color="#12141E", corner_radius=16, border_width=2, border_color="#2A2E3F")
        results_f.grid(row=0, column=1, sticky="nsew")
        
        # Variables
        vars_dict = {
            "attendance": ctk.IntVar(value=75),
            "cgpa": ctk.IntVar(value=60),
            "backlogs": ctk.IntVar(value=0),
            "tenth_percentage": ctk.IntVar(value=80),
            "intermediate_percentage": ctk.IntVar(value=80),
            "diploma_percentage": ctk.IntVar(value=0),
            "lab_performance": ctk.IntVar(value=75),
            "mid_exam_score": ctk.IntVar(value=70),
            "consecutive_absences": ctk.IntVar(value=0),
            "leave_frequency": ctk.IntVar(value=2)
        }
        
        def trigger_calc(*args):
            from logic.prediction_service import PredictionService
            features = {
                "attendance": vars_dict["attendance"].get(),
                "cgpa": vars_dict["cgpa"].get() / 10.0,
                "backlogs": vars_dict["backlogs"].get(),
                "tenth_percentage": vars_dict["tenth_percentage"].get(),
                "intermediate_percentage": vars_dict["intermediate_percentage"].get(),
                "diploma_percentage": vars_dict["diploma_percentage"].get(),
                "lab_performance": vars_dict["lab_performance"].get(),
                "mid_exam_score": vars_dict["mid_exam_score"].get(),
                "consecutive_absences": vars_dict["consecutive_absences"].get(),
                "leave_frequency": vars_dict["leave_frequency"].get(),
                "year": "2"
            }
            res = PredictionService().analyze(features)
            
            level = res['level']
            if level == "High":
                l_col = "#FF3D00"
                bg_glow = "#2A0D10"
            elif level == "Medium":
                l_col = "#FF9100"
                bg_glow = "#2A1800"
            else:
                l_col = "#00E676"
                bg_glow = "#002411"
                
            risk_disp.configure(text=f"{level}\nRISK", text_color=l_col)
            results_f.configure(border_color=l_col, fg_color=bg_glow)
            
        # UI Sliders mapping
        slider_configs = [
            ("Attendance %", "attendance", 0, 100, 100),
            ("Average Marks %", "cgpa", 0, 100, 100),
            ("Backlogs", "backlogs", 0, 10, 10),
            ("10th Grade %", "tenth_percentage", 0, 100, 100),
            ("Intermediate %", "intermediate_percentage", 0, 100, 100),
            ("Diploma %", "diploma_percentage", 0, 100, 100),
            ("Lab Performance %", "lab_performance", 0, 100, 100),
            ("Mid Exam %", "mid_exam_score", 0, 100, 100),
            ("Cons. Absences", "consecutive_absences", 0, 30, 30),
            ("Leave Freq", "leave_frequency", 0, 50, 50)
        ]
        
        for idx, (label_text, var_key, min_val, max_val, steps) in enumerate(slider_configs):
            row_idx = idx // 3
            col_idx = idx % 3
            
            card = ctk.CTkFrame(sliders_f, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
            card.grid(row=row_idx, column=col_idx, sticky="nsew", padx=6, pady=6)
            
            # Hover Glow Effect
            def on_enter(e, c=card): c.configure(border_color="#00E5FF")
            def on_leave(e, c=card): c.configure(border_color="#2A2E3F")
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            
            header_f = ctk.CTkFrame(card, fg_color="transparent")
            header_f.pack(fill="x", padx=15, pady=(15, 0))
            
            ctk.CTkLabel(header_f, text=label_text, font=("Inter", 12), text_color="#7A849C").pack(side="left")
            
            val_lbl = ctk.CTkLabel(header_f, text="", font=("Outfit", 18, "bold"), text_color="#00E5FF")
            val_lbl.pack(side="right")
            
            def make_cmd(v_key, v_lbl, v_var):
                def cmd(*a):
                    v_lbl.configure(text=str(v_var.get()))
                    trigger_calc()
                return cmd
                
            s = ctk.CTkSlider(card, from_=min_val, to=max_val, variable=vars_dict[var_key], number_of_steps=steps, button_color="#00E5FF", button_hover_color="#FFFFFF", progress_color="#00E5FF", fg_color="#1A1D2D", height=10, button_length=12)
            s.configure(command=make_cmd(var_key, val_lbl, vars_dict[var_key]))
            s.pack(fill="x", padx=15, pady=(15, 20))
            
            val_lbl.configure(text=str(vars_dict[var_key].get()))
        
        ctk.CTkLabel(results_f, text="Simulation Result", font=("Inter", 16), text_color="#7A849C").pack(pady=(40, 10))
        risk_disp = ctk.CTkLabel(results_f, text="Predicted Risk: ...", font=("Outfit", 28, "bold"))
        risk_disp.pack(pady=10)
        
        ctk.CTkLabel(results_f, text="Adjust sliders to see how changes dynamically update the AI's risk prediction.", text_color="#5C667B", font=("Inter", 12), wraplength=180, justify="center").pack(pady=30)
        
        trigger_calc()
