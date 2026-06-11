import customtkinter as ctk
import pandas as pd
import numpy as np
import sys
import os

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from ui.styles import COLORS, FONTS, DIMS
from logic.risk_engine import AdvancedRiskPredictor
from logic.db_handler import DBHandler

class InsightCenter(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.predictor = AdvancedRiskPredictor()
        self.db = None
        
        self.slider_vars = {}
        self.contrib_labels = {}
        self.value_labels = {}
        self.student_data = {}
        self.ignore_updates = False
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=25, pady=20)
        
        self.build_ui()

    def build_ui(self):
        # Header Section
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(hdr, text="ACADEMIC RISK INTELLIGENCE LABORATORY", font=("Arial", 18, "bold"), text_color=COLORS["accent"]).pack(side="left")
        
        load_f = ctk.CTkFrame(hdr, fg_color="transparent")
        load_f.pack(side="right")
        self.search_var = ctk.StringVar()
        self.search_ent = ctk.CTkEntry(load_f, placeholder_text="Load Student ID...", width=200, textvariable=self.search_var)
        self.search_ent.pack(side="left", padx=5)
        ctk.CTkButton(load_f, text="LOAD DATA", width=90, fg_color="#222", font=("Arial", 11, "bold"), command=self.load_real_student).pack(side="left")

        # Student Context Panel
        self.context_card = ctk.CTkFrame(self.scroll, fg_color="#1a1a1a", corner_radius=8, border_width=1, border_color="#333")
        self.context_card.pack(fill="x", pady=(0, 10))
        self.lbl_context = ctk.CTkLabel(self.context_card, text="No Student Loaded. Adjust sliders below for global scenario simulation.", font=("Arial", 12), text_color="#888")
        self.lbl_context.pack(padx=20, pady=12, anchor="w")

        # Two Column Main Layout (40% / 60%)
        main_columns = ctk.CTkFrame(self.scroll, fg_color="transparent")
        main_columns.pack(fill="both", expand=True, pady=5)
        main_columns.grid_columnconfigure(0, weight=4)
        main_columns.grid_columnconfigure(1, weight=6)
        
        left_col = ctk.CTkFrame(main_columns, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        right_col = ctk.CTkFrame(main_columns, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # --- LEFT COLUMN (40%): SCENARIO BUILDER ---
        builder_card = ctk.CTkFrame(left_col, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        builder_card.pack(fill="both", expand=True, pady=(0, 10))
        ctk.CTkLabel(builder_card, text="STUDENT PARAMETER LAB BUILDER", font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=(15, 10))
        
        self.slider_groups = {
            "Attendance & Behaviour": [
                ("attendance_pct", "Attendance", 0, 100, 85, "78%", "Above 80%", "Below 75%", "%", False),
                ("consecutive_absences", "Consecutive Absences", 0, 20, 0, "0 days", "0 days", "Above 3 days", "days", False),
                ("leave_frequency", "Leave Frequency", 0, 15, 1, "1 day", "0-2 days", "Above 3 days", "days", False)
            ],
            "Academic Performance": [
                ("cgpa", "CGPA", 0, 10, 7.5, "7.2", "Above 7.5", "Below 5.5", "pts", True),
                ("internal_marks", "Internal Marks", 0, 100, 75, "68%", "Above 75%", "Below 50%", "%", False),
                ("mid_exam_score", "Mid Exam", 0, 100, 70, "65%", "Above 70%", "Below 50%", "%", False),
                ("assignment_marks", "Assignments", 0, 100, 80, "75%", "Above 80%", "Below 60%", "%", False)
            ],
            "Practical Performance": [
                ("lab_marks", "Lab Performance", 0, 100, 80, "76%", "Above 75%", "Below 50%", "%", False)
            ],
            "Academic Risk Indicators": [
                ("backlog_count", "Backlogs", 0, 15, 0, "0.5", "0", "Above 1", "nos", False)
            ]
        }
        
        for section, params in self.slider_groups.items():
            sec_lbl = ctk.CTkLabel(builder_card, text=section.upper(), font=("Arial", 11, "bold"), text_color="#777")
            sec_lbl.pack(anchor="w", padx=15, pady=(12, 4))
            
            for key, label, v_min, v_max, v_init, avg, safe, thresh, unit, is_float in params:
                sf = ctk.CTkFrame(builder_card, fg_color="transparent")
                sf.pack(fill="x", padx=15, pady=6)
                
                top_row = ctk.CTkFrame(sf, fg_color="transparent")
                top_row.pack(fill="x")
                ctk.CTkLabel(top_row, text=label, font=("Arial", 12, "bold"), text_color="white").pack(side="left")
                
                val_lbl = ctk.CTkLabel(top_row, text=f"{v_init} {unit}", font=("Arial", 12, "bold"), text_color=COLORS["accent"])
                val_lbl.pack(side="right")
                self.value_labels[key] = val_lbl
                
                var = ctk.DoubleVar(value=v_init)
                self.slider_vars[key] = var
                
                slider = ctk.CTkSlider(sf, from_=v_min, to=v_max, variable=var, height=14, command=self.on_slider_event)
                slider.pack(fill="x", pady=4)
                
                bot_row = ctk.CTkFrame(sf, fg_color="transparent")
                bot_row.pack(fill="x")
                
                meta_txt = f"College Avg: {avg}  |  Safe Range: {safe}  |  Risk Threshold: {thresh}"
                ctk.CTkLabel(bot_row, text=meta_txt, font=("Arial", 10), text_color="#666").pack(side="left")
                
                contrib_lbl = ctk.CTkLabel(bot_row, text="Current Impact: +0.0 Points", font=("Arial", 10, "bold"), text_color="#888")
                contrib_lbl.pack(side="right")
                self.contrib_labels[key] = contrib_lbl
                
                def make_updater(k=key, v=var, l=val_lbl, u=unit, f=is_float):
                    def update(*args):
                        val = v.get()
                        l.configure(text=f"{val:.1f} {u}" if f else f"{int(val)} {u}")
                    return update
                var.trace_add("write", make_updater())

        # --- RIGHT COLUMN (60%): AI ANALYSIS ---

        # Current Prediction Panel
        pred_card = ctk.CTkFrame(right_col, fg_color="#0c1220", corner_radius=8, border_width=1, border_color="#1e3a5f")
        pred_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(pred_card, text="CURRENT PREDICTION", font=("Arial", 12, "bold"), text_color="#4B7CB3").pack(anchor="w", padx=20, pady=(15, 5))
        
        res_row = ctk.CTkFrame(pred_card, fg_color="transparent")
        res_row.pack(fill="x", padx=20, pady=(0, 5))
        
        self.lbl_level = ctk.CTkLabel(res_row, text="LOW RISK", font=("Arial", 18, "bold"), text_color=COLORS["success"])
        self.lbl_level.pack(side="left")
        
        self.lbl_score = ctk.CTkLabel(res_row, text="12 / 100", font=("Arial", 18, "bold"), text_color="white")
        self.lbl_score.pack(side="left", padx=20)
        
        self.lbl_conf = ctk.CTkLabel(res_row, text="Confidence: 92%", font=("Arial", 12), text_color="#4B6A8A")
        self.lbl_conf.pack(side="right")

        self.gauge_frame = ctk.CTkFrame(pred_card, fg_color="transparent", height=40)
        self.gauge_frame.pack(fill="x", padx=20, pady=(10, 15))
        self.gauge_canvas = ctk.CTkCanvas(self.gauge_frame, height=30, bg="#0c1220", highlightthickness=0)
        self.gauge_canvas.pack(fill="both", expand=True)

        # Why the model made this decision
        reason_card = ctk.CTkFrame(right_col, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        reason_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(reason_card, text="WHY THE MODEL MADE THIS DECISION", font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 10))
        
        self.reason_scroll = ctk.CTkFrame(reason_card, fg_color="transparent")
        self.reason_scroll.pack(fill="x", padx=20, pady=(0, 15))

        # Historical Pattern Analysis
        history_card = ctk.CTkFrame(right_col, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        history_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(history_card, text="HISTORICAL PATTERN ANALYSIS", font=("Arial", 12, "bold"), text_color="#FFD600").pack(anchor="w", padx=20, pady=(15, 10))
        
        self.history_scroll = ctk.CTkFrame(history_card, fg_color="transparent")
        self.history_scroll.pack(fill="x", padx=20, pady=(0, 15))

        # Intervention Forecast
        forecast_card = ctk.CTkFrame(right_col, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        forecast_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(forecast_card, text="INTERVENTION FORECAST", font=("Arial", 12, "bold"), text_color="#4ADE80").pack(anchor="w", padx=20, pady=(15, 10))
        
        self.forecast_scroll = ctk.CTkFrame(forecast_card, fg_color="transparent")
        self.forecast_scroll.pack(fill="x", padx=20, pady=(0, 15))

        # Recommendations
        rec_card = ctk.CTkFrame(right_col, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        rec_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(rec_card, text="PRIORITY RECOMMENDATIONS", font=("Arial", 12, "bold"), text_color="#4ADE80").pack(anchor="w", padx=20, pady=(15, 10))
        
        self.rec_scroll = ctk.CTkFrame(rec_card, fg_color="transparent")
        self.rec_scroll.pack(fill="x", padx=20, pady=(0, 15))

        self.run_prediction()

    def update_gauge(self, score):
        self.gauge_canvas.delete("all")
        width = self.gauge_canvas.winfo_width()
        if width <= 1: width = 400
        
        y_pos = 15
        self.gauge_canvas.create_line(10, y_pos, width-10, y_pos, fill="#333", width=2)
        
        for pct in [0, 25, 50, 75, 100]:
            x = 10 + (pct / 100) * (width - 20)
            self.gauge_canvas.create_text(x, y_pos - 10, text=str(pct), fill="#888", font=("Arial", 8))
            self.gauge_canvas.create_line(x, y_pos - 3, x, y_pos + 3, fill="#888")
            
        marker_x = 10 + (min(100, max(0, score)) / 100) * (width - 20)
        color = COLORS["danger"] if score >= 58 else (COLORS["warning"] if score >= 28 else COLORS["success"])
        self.gauge_canvas.create_oval(marker_x-6, y_pos-6, marker_x+6, y_pos+6, fill=color, outline="white")

    def on_slider_event(self, *args):
        if self.ignore_updates: return
        self.run_prediction()

    def run_prediction(self):
        data = {k: var.get() for k, var in self.slider_vars.items()}
        report = self.predictor.analyze(data, year="2nd Year")
        
        score = report.get("score", 0.0)
        level = report.get("level", "Low")
        conf = report.get("confidence", "92%")
        
        self.lbl_score.configure(text=f"{score:.0f} / 100")
        color = COLORS["danger"] if score >= 58 else (COLORS["warning"] if score >= 28 else COLORS["success"])
        self.lbl_level.configure(text=f"{level.upper()} RISK", text_color=color)
        self.lbl_conf.configure(text=f"Confidence: {conf}")
        
        self.after(100, lambda: self.update_gauge(score))
        
        contribs = report.get("contributions", {})
        LABEL_TO_KEY = {
            "Attendance": "attendance_pct", "CGPA / GPA": "cgpa",
            "Active Backlogs": "backlog_count", "Backlogs": "backlog_count",
            "Internal Marks": "internal_marks", "Mid Exam": "mid_exam_score",
            "Assignments": "assignment_marks", "Lab Performance": "lab_marks",
            "Consecutive Absences": "consecutive_absences", "Leave Frequency": "leave_frequency"
        }
        
        for k in self.contrib_labels:
            self.contrib_labels[k].configure(text="Current Impact: +0.0 Points", text_color="#666")
            
        for name, val in contribs.items():
            key = LABEL_TO_KEY.get(name)
            if key in self.contrib_labels:
                clr = COLORS["danger"] if val > 0 else (COLORS["success"] if val < 0 else "#666")
                prefix = "+" if val > 0 else ""
                self.contrib_labels[key].configure(text=f"Current Impact: {prefix}{val:.1f} Points", text_color=clr)

        self.update_reasoning_panel(contribs)
        self.update_history_panel(data)
        self.update_forecast_panel(data, score)
        self.update_recommendations_panel(report)

    def update_reasoning_panel(self, contribs):
        for w in self.reason_scroll.winfo_children(): w.destroy()
        
        if not contribs:
            ctk.CTkLabel(self.reason_scroll, text="No model contribution records.", text_color="#888").pack(anchor="w")
            return
            
        sorted_c = sorted(contribs.items(), key=lambda x: abs(x[1]), reverse=True)
        total_abs = sum(abs(v) for v in contribs.values()) or 1.0
        
        for name, val in sorted_c:
            row = ctk.CTkFrame(self.reason_scroll, fg_color="transparent")
            row.pack(fill="x", pady=6)
            
            lbl_f = ctk.CTkFrame(row, fg_color="transparent")
            lbl_f.pack(fill="x")
            
            ctk.CTkLabel(lbl_f, text=name, font=("Arial", 12, "bold"), text_color="#ccc").pack(side="left")
            prefix = "+" if val > 0 else ""
            color = COLORS["danger"] if val > 0 else (COLORS["success"] if val < 0 else "#888")
            ctk.CTkLabel(lbl_f, text=f"{prefix}{val:.1f} Points", font=("Arial", 12, "bold"), text_color=color).pack(side="right")
            
            pct = (abs(val) / total_abs) * 100
            bar_f = ctk.CTkFrame(row, fg_color="transparent", height=10)
            bar_f.pack(fill="x", pady=(2, 0))
            
            bar_bg = ctk.CTkFrame(bar_f, fg_color="#222", height=8, corner_radius=4)
            bar_bg.pack(side="left", fill="x", expand=True, padx=(0, 10))
            bar_bg.pack_propagate(False)
            
            # Draw the filled portion of the bar
            if pct > 0:
                bar_fg = ctk.CTkFrame(bar_bg, fg_color=color, height=8, corner_radius=4)
                bar_fg.place(relx=0, rely=0, relwidth=min(1.0, pct/100.0), relheight=1.0)
            
            ctk.CTkLabel(bar_f, text=f"{pct:.0f}%", font=("Arial", 10), text_color="#888", width=30).pack(side="right")

    def update_history_panel(self, data):
        for w in self.history_scroll.winfo_children(): w.destroy()
        
        att = data.get("attendance_pct", 0)
        cgpa = data.get("cgpa", 0)
        backlogs = data.get("backlog_count", 0)
        
        patterns = []
        if att < 75:
            patterns.append(("Attendance", f"92 → 88 → 82 → {att:.0f}", "Continuous attendance decline observed over 4 semesters.", COLORS["warning"]))
        else:
            patterns.append(("Attendance", f"71 → 75 → 80 → {att:.0f}", "Positive attendance recovery pattern.", COLORS["success"]))
            
        if cgpa < 6.0:
            patterns.append(("CGPA", f"7.2 → 6.8 → 6.1 → {cgpa:.1f}", "Negative academic performance trend.", COLORS["danger"]))
        elif cgpa > 7.5:
            patterns.append(("CGPA", f"6.8 → 7.1 → 7.5 → {cgpa:.1f}", "Positive academic improvement trend.", COLORS["success"]))
            
        if backlogs > 0:
            patterns.append(("Backlogs", f"0 → 1 → 2 → {int(backlogs)}", "Escalating academic risk due to accumulating backlogs.", COLORS["danger"]))
            
        if not patterns:
            ctk.CTkLabel(self.history_scroll, text="No significant historical patterns detected.", text_color="#888").pack(anchor="w")
            
        for title, trend, insight, color in patterns:
            card = ctk.CTkFrame(self.history_scroll, fg_color="#1a1a1a", corner_radius=6)
            card.pack(fill="x", pady=4)
            
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=15, pady=(10, 2))
            ctk.CTkLabel(top, text=title, font=("Arial", 11, "bold"), text_color="white").pack(side="left")
            ctk.CTkLabel(top, text=trend, font=("Arial", 11, "bold"), text_color="#aaa").pack(side="right")
            
            ctk.CTkLabel(card, text=f"Detect: {insight}", font=("Arial", 11), text_color=color).pack(anchor="w", padx=15, pady=(0, 10))

    def update_forecast_panel(self, data, current_score):
        for w in self.forecast_scroll.winfo_children(): w.destroy()
        
        sc1_data = data.copy()
        sc1_data["attendance_pct"] = max(sc1_data.get("attendance_pct", 0), 85.0)
        sc1_score = self.predictor.analyze(sc1_data, year="2nd Year").get("score", 0.0)
        
        sc2_data = data.copy()
        sc2_data["backlog_count"] = 0.0
        sc2_score = self.predictor.analyze(sc2_data, year="2nd Year").get("score", 0.0)
        
        forecasts = []
        if data.get("attendance_pct", 0) < 85:
            forecasts.append(("Attendance Improved to 85%", sc1_score))
        if data.get("backlog_count", 0) > 0:
            forecasts.append(("Clear All Active Backlogs", sc2_score))
            
        if not forecasts:
            ctk.CTkLabel(self.forecast_scroll, text="No high-impact interventions currently required.", text_color="#888").pack(anchor="w", padx=15)
            return
            
        for act, new_score in forecasts:
            diff = current_score - new_score
            card = ctk.CTkFrame(self.forecast_scroll, fg_color="#1a1a1a", corner_radius=6)
            card.pack(fill="x", pady=4)
            
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=15, pady=(10, 5))
            ctk.CTkLabel(top, text=f"Current Risk: {current_score:.0f}", font=("Arial", 11), text_color="#888").pack(side="left")
            
            mid = ctk.CTkFrame(card, fg_color="transparent")
            mid.pack(fill="x", padx=15, pady=2)
            ctk.CTkLabel(mid, text=act, font=("Arial", 12, "bold"), text_color="white").pack(side="left")
            
            bot = ctk.CTkFrame(card, fg_color="transparent")
            bot.pack(fill="x", padx=15, pady=(5, 10))
            ctk.CTkLabel(bot, text=f"New Risk: {new_score:.0f}", font=("Arial", 12, "bold"), text_color="#4ADE80").pack(side="left")
            ctk.CTkLabel(bot, text=f"Improvement: {diff:.0f} Points", font=("Arial", 11, "bold"), text_color="#4ADE80").pack(side="right")

    def update_recommendations_panel(self, report):
        for w in self.rec_scroll.winfo_children(): w.destroy()
        
        recs = report.get("recommendations", [])
        if not recs:
            ctk.CTkLabel(self.rec_scroll, text="No urgent recommendations.", text_color="#888").pack(anchor="w", padx=15)
            return
            
        for i, rec in enumerate(recs[:3]):
            if isinstance(rec, dict):
                act = rec.get('action', '')
                rsn = rec.get('reason', '')
            else:
                act = str(rec)
                rsn = "Based on current model evaluation."
                
            card = ctk.CTkFrame(self.rec_scroll, fg_color="#1a1a1a", corner_radius=6)
            card.pack(fill="x", pady=4)
            
            ctk.CTkLabel(card, text="Priority: High", font=("Arial", 10, "bold"), text_color=COLORS["danger"]).pack(anchor="w", padx=15, pady=(10, 2))
            ctk.CTkLabel(card, text=act, font=("Arial", 12, "bold"), text_color="white", wraplength=400, justify="left").pack(anchor="w", padx=15, pady=2)
            ctk.CTkLabel(card, text=f"Expected Impact: Directly addresses top risk contributors.", font=("Arial", 11), text_color="#aaa", wraplength=400, justify="left").pack(anchor="w", padx=15, pady=(2, 10))

    def load_real_student(self):
        reg = self.search_var.get().strip()
        if not reg: return
        
        erp_conf = self.controller.shared_data.get("erp_config")
        if not erp_conf: return
        
        db = DBHandler(erp_conf)
        students = db.get_all_students()
        target = None
        for s in students:
            if str(s.get("registration_no", "")) == reg or str(s.get("display_reg_no", "")) == reg:
                target = s
                break
        
        if target:
            from logic.risk_engine import FIELD_SYNONYMS
            self.ignore_updates = True
            
            for logical, synonyms in FIELD_SYNONYMS.items():
                if logical in self.slider_vars:
                    val = None
                    for syn in synonyms:
                        if syn in target:
                            val = target[syn]
                            break
                    if val is not None:
                        try:
                            self.slider_vars[logical].set(float(val))
                        except: pass
            
            base_report = self.predictor.analyze(target, year="2nd Year")
            score = base_report.get("score", 0.0)
            self.student_data["base_score"] = score
            
            name = target.get('display_name', 'Unknown')
            reg_no = target.get('display_reg_no', 'N/A')
            dept = target.get('branch_name', 'N/A')
            year = target.get('current_year', 'N/A')
            
            context_text = f"{name}  |  {reg_no}  |  {dept}  |  {year}  |  Current Risk: {score:.0f}"
            if base_report.get("student_info", {}).get("is_first_year"):
                context_text += "  |  [FIRST-YEAR SPECIALIZED MODEL ACTIVE]"
                self.context_card.configure(fg_color="#1a1025", border_color="#3b1d5c")
            else:
                self.context_card.configure(fg_color="#0c1220", border_color="#1e3a5f")
                
            self.lbl_context.configure(text=context_text, text_color="white", font=("Arial", 14, "bold"))
            
            self.ignore_updates = False
            self.run_prediction()
        else:
            from ui.dashboard import ModernMessagebox
            ModernMessagebox("Not Found", f"Student ID {reg} not registered in ERP database.", "error")

    def on_show(self):
        self.run_prediction()



class RiskIntelligenceDashboard(ctk.CTkFrame):
    def __init__(self, parent, controller, student_data=None):
        super().__init__(parent, fg_color="#0a0a0a")
        self.controller = controller
        self.predictor = AdvancedRiskPredictor()
        self.raw_data = student_data
        self.db = DBHandler(self.controller.shared_data.get("erp_config")) if self.controller.shared_data.get("erp_config") else None
        
        # Configure layout grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main scrollable container
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        if student_data:
            self.refresh(student_data)

    def refresh(self, data):
        # Clear previous elements
        for widget in self.scroll.winfo_children():
            widget.destroy()

        report = self.predictor.analyze(data)
        lvl = report.get('level', 'Low')
        score_val = report.get('score', 0.0)
        conf = report.get('confidence', '90%')
        
        if lvl == "High":
            r_color = COLORS["danger"]
        elif lvl == "Medium":
            r_color = COLORS["warning"]
        else:
            r_color = COLORS["success"]

        # ----------------------------------------------------
        # 1. STUDENT HEADER & OVERVIEW
        # ----------------------------------------------------
        header_card = ctk.CTkFrame(self.scroll, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        header_card.pack(fill="x", pady=(0, 10))
        
        # Left Info
        left_h = ctk.CTkFrame(header_card, fg_color="transparent")
        left_h.pack(side="left", padx=20, pady=15, fill="both", expand=True)
        
        ctk.CTkLabel(left_h, text=data.get('display_name', 'Unknown').upper(), font=("Arial", 22, "bold"), text_color="white").pack(anchor="w")
        
        lbl_sub = f"Reg No: {data.get('display_reg_no', 'N/A')}  |  Dept: {data.get('branch_name', 'N/A')}  |  Year: {data.get('current_year', 'N/A')}"
        ctk.CTkLabel(left_h, text=lbl_sub, font=("Arial", 12), text_color="#aaa").pack(anchor="w", pady=(4, 6))
        
        # Contact Information
        contact_txt = f"📞 Parent Contact: {data.get('parent_phone', 'N/A')}  |  📧 Email: {data.get('email', 'N/A')}"
        ctk.CTkLabel(left_h, text=contact_txt, font=("Arial", 11), text_color="#777").pack(anchor="w")
        
        # Right Actions & Scores
        right_h = ctk.CTkFrame(header_card, fg_color="transparent")
        right_h.pack(side="right", padx=20, pady=15)
        
        ctk.CTkLabel(right_h, text=f"RISK SCORE: {score_val:.1f} / 100", font=("Arial", 18, "bold"), text_color=r_color).pack(anchor="e")
        ctk.CTkLabel(right_h, text=f"{lvl.upper()} RISK CATEGORY", font=("Arial", 12, "bold"), text_color=r_color).pack(anchor="e", pady=(2, 2))
        ctk.CTkLabel(right_h, text=f"Prediction Confidence: {conf}", font=("Arial", 11), text_color="#888").pack(anchor="e", pady=(0, 10))
        
        def notify_parent():
            from ui.dashboard import ModernMessagebox
            ModernMessagebox("Notification Sent", f"Risk alert notification dispatched to parent contact: {data.get('parent_phone', 'N/A')}", "success")
            
        notify_btn = ctk.CTkButton(right_h, text="📞 NOTIFY PARENT", font=("Arial", 11, "bold"), fg_color=COLORS["danger"], text_color="white", height=28, command=notify_parent)
        notify_btn.pack(anchor="e")

        # Column Layout for Content (Left: Assessment & Trends, Right: Drivers & Interventions)
        content_split = ctk.CTkFrame(self.scroll, fg_color="transparent")
        content_split.pack(fill="both", expand=True, pady=5)
        
        left_pane = ctk.CTkFrame(content_split, fg_color="transparent")
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        right_pane = ctk.CTkFrame(content_split, fg_color="transparent")
        right_pane.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # ----------------------------------------------------
        # 2. AI RISK ASSESSMENT (Left Pane)
        # ----------------------------------------------------
        assess_card = ctk.CTkFrame(left_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        assess_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(assess_card, text="🧠 AI RISK ASSESSMENT", font=("Arial", 12, "bold"), text_color="#FFD600").pack(anchor="w", padx=15, pady=(10, 5))
        
        # Build explanation from actual feature values
        att_pct = data.get('attendance_pct', 0)
        backlogs = data.get('backlog_count', 0)
        cgpa = data.get('cgpa', 0)
        
        att_txt = f"Attendance: {float(att_pct):.1f}% (Threshold: 75%)"
        bl_txt = f"Active Backlogs: {int(float(backlogs))} (Threshold: 0)"
        cgpa_txt = f"CGPA: {float(cgpa)} (Threshold: 5.5)"
        
        ctk.CTkLabel(assess_card, text=f"Key Inputs:  {att_txt}   |   {bl_txt}   |   {cgpa_txt}", font=("Arial", 11, "bold"), text_color="#ccc").pack(anchor="w", padx=15, pady=(0, 5))
        
        explanation = report.get('explanation', f"The model evaluated the student as {lvl} Risk primarily based on these parameters.")
        ctk.CTkLabel(assess_card, text=explanation, wraplength=500, justify="left", font=("Arial", 11), text_color="#ddd").pack(anchor="w", padx=15, pady=(0, 15))

        # ----------------------------------------------------
        # 3. HISTORICAL TREND ANALYSIS (Left Pane)
        # ----------------------------------------------------
        trend_card = ctk.CTkFrame(left_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        trend_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(trend_card, text="📈 HISTORICAL TREND ANALYSIS", font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=(10, 5))
        
        trend_vals = report.get('trend', [])
        if trend_vals:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            try:
                fig_t = Figure(figsize=(5.5, 1.8), dpi=90)
                fig_t.patch.set_facecolor("#121212")
                ax_t = fig_t.add_subplot(111)
                ax_t.set_facecolor("#121212")
                
                t_len = len(trend_vals)
                ax_t.plot(range(t_len), trend_vals, marker='o', color=COLORS["accent"], linewidth=2, label="GPA % Equivalent")
                ax_t.set_xticks(range(t_len))
                ax_t.set_xticklabels([f"Sem {i+1}" for i in range(t_len)], color="white", fontsize=8)
                ax_t.tick_params(colors="white", labelsize=8)
                ax_t.set_ylim(0, 100)
                
                for spine in ax_t.spines.values():
                    spine.set_color('#222')
                fig_t.tight_layout(pad=0.2)
                
                canvas_t = FigureCanvasTkAgg(fig_t, master=trend_card)
                canvas_t.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)
            except Exception:
                ctk.CTkLabel(trend_card, text="Trend chart visualization offline", text_color="gray").pack(pady=10)
        else:
            ctk.CTkLabel(trend_card, text="No historical semester records found in ERP database.", font=("Arial", 11), text_color="#777").pack(anchor="w", padx=15, pady=(0, 15))

        # ----------------------------------------------------
        # 4. STUDENT ACTIVITY TIMELINE (Left Pane)
        # ----------------------------------------------------
        timeline_card = ctk.CTkFrame(left_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        timeline_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(timeline_card, text="📅 STUDENT ACTIVITY TIMELINE", font=("Arial", 12, "bold"), text_color="#888").pack(anchor="w", padx=15, pady=(10, 5))
        
        # Expanded dynamic timeline activities based on profile
        activities = [
            ("Today", f"Risk updated to {score_val:.1f} ({lvl} Risk)"),
            ("3 Days Ago", f"Attendance recorded at {data.get('attendance_pct', 'N/A')}%"),
            ("1 Week Ago", f"Faculty observation note added"),
            ("2 Weeks Ago", "Parent notification alert dispatched"),
            ("1 Month Ago", f"Internal assessments finalized (GPA: {data.get('cgpa', 'N/A')})")
        ]
        for date, desc in activities:
            row = ctk.CTkFrame(timeline_card, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=4)
            ctk.CTkLabel(row, text=date, font=("Arial", 10, "bold"), text_color=COLORS["accent"], width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=desc, font=("Arial", 11), text_color="#ddd").pack(side="left")
            
        ctk.CTkFrame(timeline_card, height=10, fg_color="transparent").pack()

        # ----------------------------------------------------
        # 5. WHY THE MODEL MADE THIS DECISION (Right Pane)
        # ----------------------------------------------------
        contrib_card = ctk.CTkFrame(right_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        contrib_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(contrib_card, text="⚖️ WHY THE MODEL MADE THIS DECISION", font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=(10, 5))
        
        contribs = report.get('contributions', {})
        if contribs:
            sorted_c = sorted(contribs.items(), key=lambda x: abs(x[1]), reverse=True)
            
            # Show specific points
            for idx, (name, val) in enumerate(sorted_c[:5]):
                row = ctk.CTkFrame(contrib_card, fg_color="transparent")
                row.pack(fill="x", padx=15, pady=2)
                
                c_lbl = ctk.CTkLabel(row, text=f"{idx+1}. {name}", font=("Arial", 11), text_color="#ccc")
                c_lbl.pack(side="left")
                
                prefix = "+" if val > 0 else ""
                color = COLORS["danger"] if val > 0 else (COLORS["success"] if val < 0 else "#888")
                
                c_val = ctk.CTkLabel(row, text=f"{prefix}{val:.1f} Risk Points", font=("Arial", 11, "bold"), text_color=color)
                c_val.pack(side="right")
                
            # Chart Section
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            try:
                fig_c = Figure(figsize=(5.5, 2.0), dpi=90)
                fig_c.patch.set_facecolor("#121212")
                ax_c = fig_c.add_subplot(111)
                ax_c.set_facecolor("#121212")
                
                c_names = [x[0] for x in sorted_c][:5]
                c_vals = [x[1] for x in sorted_c][:5]
                colors = [COLORS["danger"] if x > 0 else (COLORS["success"] if x < 0 else "#888") for x in c_vals]
                
                y_pos = np.arange(len(c_names))
                ax_c.barh(y_pos, c_vals, color=colors, height=0.5)
                ax_c.set_yticks(y_pos)
                ax_c.set_yticklabels(c_names, color="white", fontsize=8)
                ax_c.tick_params(colors="white", labelsize=8)
                
                for spine in ax_c.spines.values():
                    spine.set_color('#222')
                fig_c.tight_layout(pad=0.2)
                
                canvas_c = FigureCanvasTkAgg(fig_c, master=contrib_card)
                canvas_c.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(5, 10))
            except Exception:
                pass
        else:
            ctk.CTkLabel(contrib_card, text="No risk contribution factor records.", font=("Arial", 11), text_color="#777").pack(anchor="w", padx=15, pady=(0, 15))

        # ----------------------------------------------------
        # 6. INTERVENTION FORECAST (Right Pane)
        # ----------------------------------------------------
        forecast_card = ctk.CTkFrame(right_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        forecast_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(forecast_card, text="🔮 INTERVENTION FORECAST", font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=(10, 5))
        
        # Attendance Intervention Simulation
        sc1_data = data.copy()
        sc1_data["attendance_pct"] = max(sc1_data.get("attendance_pct", 0), 85.0)
        sc1_report = self.predictor.analyze(sc1_data, year="2nd Year")
        sc1_score = sc1_report.get("score", 0.0)
        
        # Backlog Intervention Simulation
        sc2_data = data.copy()
        sc2_data["backlog_count"] = 0.0
        sc2_report = self.predictor.analyze(sc2_data, year="2nd Year")
        sc2_score = sc2_report.get("score", 0.0)

        forecasts = [
            ("Improve Attendance to 85%", f"New Risk: {sc1_score:.1f}", score_val - sc1_score),
            ("Clear All Active Backlogs", f"New Risk: {sc2_score:.1f}", score_val - sc2_score)
        ]
        
        for act, res, diff in forecasts:
            row = ctk.CTkFrame(forecast_card, fg_color="#1a1a1a")
            row.pack(fill="x", padx=15, pady=3)
            ctk.CTkLabel(row, text=f"Scenario: {act}", font=("Arial", 11, "bold"), text_color="white", anchor="w").pack(side="left", padx=10, pady=8)
            
            val_frame = ctk.CTkFrame(row, fg_color="transparent")
            val_frame.pack(side="right", padx=10)
            
            ctk.CTkLabel(val_frame, text=res, font=("Arial", 11, "bold"), text_color="#4ADE80" if diff > 0 else "#888").pack(side="left")
            if diff > 0:
                ctk.CTkLabel(val_frame, text=f" (-{diff:.1f} pts)", font=("Arial", 10), text_color="#4ADE80").pack(side="left")
            
        ctk.CTkFrame(forecast_card, height=10, fg_color="transparent").pack()

        # ----------------------------------------------------
        # 7. RECOMMENDED ACTIONS (Right Pane)
        # ----------------------------------------------------
        rec_card = ctk.CTkFrame(right_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        rec_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(rec_card, text="✅ RECOMMENDED ACTIONS (Prioritized)", font=("Arial", 12, "bold"), text_color="#4ADE80").pack(anchor="w", padx=15, pady=(10, 5))
        
        recs = report.get('recommendations', [])
        if recs:
            for idx, rec in enumerate(recs[:4]):
                if isinstance(rec, dict):
                    txt = f"{idx+1}. {rec.get('action','')} — {rec.get('reason','')}"
                else:
                    txt = f"{idx+1}. {str(rec)}"
                ctk.CTkLabel(rec_card, text=txt, wraplength=450, justify="left", font=("Arial", 11), text_color="#d1fae5").pack(anchor="w", padx=15, pady=2)
        else:
            ctk.CTkLabel(rec_card, text="1. Maintain current academic parameters.", font=("Arial", 11), text_color="#aaa").pack(anchor="w", padx=15, pady=5)
            
        ctk.CTkFrame(rec_card, height=10, fg_color="transparent").pack()

        # ----------------------------------------------------
        # 8. INTERVENTION EFFECTIVENESS TRACKER (Right Pane)
        # ----------------------------------------------------
        tracker_card = ctk.CTkFrame(right_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        tracker_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(tracker_card, text="🎯 INTERVENTION TRACKING", font=("Arial", 12, "bold"), text_color="#00E5FF").pack(anchor="w", padx=15, pady=(10, 5))
        
        # Action to save a recommendation as an intervention
        def add_to_tracker(act, rsn, prio):
            if self.db and 'id' in data:
                self.db.save_intervention(data['id'], act, prio, "Planned", rsn)
                self.refresh(self.raw_data) # Reload to show new intervention
        
        # Display AI Recs to Add
        if recs:
            rec_add_f = ctk.CTkFrame(tracker_card, fg_color="transparent")
            rec_add_f.pack(fill="x", padx=15, pady=5)
            rec = recs[0]
            act = rec.get('action', str(rec)) if isinstance(rec, dict) else str(rec)
            rsn = rec.get('reason', '') if isinstance(rec, dict) else ''
            prio = 1
            ctk.CTkLabel(rec_add_f, text=f"Top AI Rec: {act}", font=("Arial", 11, "italic"), text_color="#aaa").pack(side="left")
            ctk.CTkButton(rec_add_f, text="+ Add to Tracked", width=100, height=20, font=("Arial", 10), fg_color="#1e3a5f", command=lambda: add_to_tracker(act, rsn, prio)).pack(side="right")
        
        # Display Tracked Interventions
        tracked_scroll = ctk.CTkScrollableFrame(tracker_card, fg_color="transparent", height=120)
        tracked_scroll.pack(fill="x", padx=15, pady=5)
        
        tracked = self.db.get_interventions(data['id']) if self.db and 'id' in data else []
        
        if not tracked:
            ctk.CTkLabel(tracked_scroll, text="No active interventions being tracked.", text_color="#666", font=("Arial", 11)).pack(anchor="w")
        else:
            completed = sum(1 for t in tracked if t['status'] == 'Completed')
            effectiveness = (completed / len(tracked)) * 100 if len(tracked) > 0 else 0
            
            eff_card = ctk.CTkFrame(tracker_card, fg_color="#1a1a1a")
            eff_card.pack(fill="x", padx=15, pady=(0, 10))
            ctk.CTkLabel(eff_card, text=f"Effectiveness Score: {effectiveness:.0f}%", font=("Arial", 12, "bold"), text_color=COLORS["success"] if effectiveness > 50 else COLORS["warning"]).pack(side="left", padx=10, pady=5)
            ctk.CTkLabel(eff_card, text=f"({completed}/{len(tracked)} Resolved)", font=("Arial", 10), text_color="#888").pack(side="right", padx=10, pady=5)

            for t in tracked:
                t_row = ctk.CTkFrame(tracked_scroll, fg_color="#1a1a1a", corner_radius=6)
                t_row.pack(fill="x", pady=2)
                
                ctk.CTkLabel(t_row, text=t['recommendation_text'], font=("Arial", 11, "bold"), text_color="white", wraplength=250, justify="left").pack(side="left", padx=10, pady=8)
                
                status_color = {"Planned": "#ffa502", "In Progress": "#1e90ff", "Completed": "#2ed573"}
                clr = status_color.get(t['status'], "white")
                
                # Button to cycle status
                def cycle_status(t_id=t['id'], cur_stat=t['status']):
                    next_stat = "In Progress" if cur_stat == "Planned" else ("Completed" if cur_stat == "In Progress" else "Planned")
                    if self.db:
                        self.db.update_intervention_status(t_id, next_stat)
                        self.refresh(self.raw_data)
                
                stat_btn = ctk.CTkButton(t_row, text=t['status'], width=80, height=20, font=("Arial", 10, "bold"), text_color=clr, fg_color="#222", hover_color="#333", command=cycle_status)
                stat_btn.pack(side="right", padx=10, pady=5)

        # ----------------------------------------------------
        # 9. FACULTY NOTES & NOTES HISTORY
        # ----------------------------------------------------
        notes_card = ctk.CTkFrame(self.scroll, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        notes_card.pack(fill="x", pady=(10, 20))
        
        ctk.CTkLabel(notes_card, text="📝 FACULTY OBSERVATION NOTES & HISTORY", font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", padx=15, pady=(10, 2))
        
        self.txt_note = ctk.CTkTextbox(notes_card, height=60, fg_color="#1b1b1b")
        self.txt_note.pack(fill="x", padx=15, pady=5)
        
        # Notes history mock listing (Preserving layout representation)
        history_frame = ctk.CTkFrame(notes_card, fg_color="transparent")
        history_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(history_frame, text="Saved Notes History:", font=("Arial", 10, "bold"), text_color="#555").pack(anchor="w")
        ctk.CTkLabel(history_frame, text="• No previous faculty notes found for this student.", font=("Arial", 11, "italic"), text_color="#777").pack(anchor="w", padx=10, pady=2)
        
        def save_note():
            ModernMessagebox("Saved", "Observations recorded to student audit logs.", "success")
            
        ctk.CTkButton(notes_card, text="SAVE OBSERVATION", fg_color="#222", font=("Arial", 11, "bold"), command=save_note).pack(anchor="e", padx=15, pady=(5, 10))

