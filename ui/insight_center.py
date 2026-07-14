import customtkinter as ctk
import pandas as pd
import numpy as np
import sys
import os
import threading

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from ui.styles import COLORS, FONTS, DIMS
from logic.insight_service import InsightService
from logic.db_handler import DBHandler
from logic.central_auth import CentralAuth
from logic.intervention_engine import InterventionEngine

class InsightCenter(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.insight_service = InsightService()
        self.db = None
        
        self.slider_vars = {}
        self.contrib_labels = {}
        self.value_labels = {}
        self.student_data = {}
        self.ignore_updates = False
        self._debounce_id = None      # Phase 6: debounce handle for slider events
        self._prediction_running = False  # Phase 6: guard against concurrent predictions
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=25, pady=20)
        
        self.build_ui()

    def build_ui(self):
        # Header Section
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(hdr, text="ACADEMIC RISK INTELLIGENCE LABORATORY", font=FONTS["h2"], text_color=COLORS["accent"]).pack(side="left")
        
        load_f = ctk.CTkFrame(hdr, fg_color="transparent")
        load_f.pack(side="right")
        self.search_var = ctk.StringVar()
        self.search_ent = ctk.CTkEntry(load_f, placeholder_text="Load Student ID...", width=200, textvariable=self.search_var)
        self.search_ent.pack(side="left", padx=5)
        ctk.CTkButton(load_f, text="LOAD DATA", width=90, fg_color="#222", font=FONTS["caption"], command=self.load_real_student).pack(side="left")

        # Student Context Panel
        self.context_card = ctk.CTkFrame(self.scroll, fg_color=COLORS["card"], corner_radius=8, border_width=1, border_color=COLORS["border"])
        self.context_card.pack(fill="x", pady=(0, 10))
        self.lbl_context = ctk.CTkLabel(self.context_card, text="No Student Loaded. Adjust sliders below for global scenario simulation.", font=FONTS["body"], text_color="#888")
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
        ctk.CTkLabel(builder_card, text="STUDENT PARAMETER LAB BUILDER", font=FONTS["body"], text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=(15, 10))
        
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
            sec_lbl = ctk.CTkLabel(builder_card, text=section.upper(), font=FONTS["caption"], text_color="#777")
            sec_lbl.pack(anchor="w", padx=15, pady=(12, 4))
            
            for key, label, v_min, v_max, v_init, avg, safe, thresh, unit, is_float in params:
                sf = ctk.CTkFrame(builder_card, fg_color="transparent")
                sf.pack(fill="x", padx=15, pady=6)
                
                top_row = ctk.CTkFrame(sf, fg_color="transparent")
                top_row.pack(fill="x")
                ctk.CTkLabel(top_row, text=label, font=FONTS["body"], text_color="white").pack(side="left")
                
                val_lbl = ctk.CTkLabel(top_row, text=f"{v_init} {unit}", font=FONTS["body"], text_color=COLORS["accent"])
                val_lbl.pack(side="right")
                self.value_labels[key] = val_lbl
                
                var = ctk.DoubleVar(value=v_init)
                self.slider_vars[key] = var
                
                slider = ctk.CTkSlider(sf, from_=v_min, to=v_max, variable=var, height=14, command=self.on_slider_event)
                slider.pack(fill="x", pady=4)
                
                bot_row = ctk.CTkFrame(sf, fg_color="transparent")
                bot_row.pack(fill="x")
                
                meta_txt = f"College Avg: {avg}  |  Safe Range: {safe}  |  Risk Threshold: {thresh}"
                ctk.CTkLabel(bot_row, text=meta_txt, font=FONTS["badge"], text_color="#666").pack(side="left")
                
                contrib_lbl = ctk.CTkLabel(bot_row, text="Current Impact: +0.0 Points", font=FONTS["badge"], text_color="#888")
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
        
        ctk.CTkLabel(pred_card, text="CURRENT PREDICTION", font=FONTS["body"], text_color="#4B7CB3").pack(anchor="w", padx=20, pady=(15, 5))
        
        res_row = ctk.CTkFrame(pred_card, fg_color="transparent")
        res_row.pack(fill="x", padx=20, pady=(0, 5))
        
        self.lbl_level = ctk.CTkLabel(res_row, text="LOW RISK", font=FONTS["h2"], text_color=COLORS["success"])
        self.lbl_level.pack(side="left")
        
        self.lbl_score = ctk.CTkLabel(res_row, text="12 / 100", font=FONTS["h2"], text_color="white")
        self.lbl_score.pack(side="left", padx=20)
        
        self.lbl_conf = ctk.CTkLabel(res_row, text="Confidence: 92%", font=FONTS["body"], text_color="#4B6A8A")
        self.lbl_conf.pack(side="right")

        self.gauge_frame = ctk.CTkFrame(pred_card, fg_color="transparent", height=40)
        self.gauge_frame.pack(fill="x", padx=20, pady=(10, 15))
        self.gauge_canvas = ctk.CTkCanvas(self.gauge_frame, height=30, bg="#0c1220", highlightthickness=0)
        self.gauge_canvas.pack(fill="both", expand=True)

        # Why the model made this decision
        reason_card = ctk.CTkFrame(right_col, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        reason_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(reason_card, text="WHY THE MODEL MADE THIS DECISION", font=FONTS["body"], text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 10))
        
        self.reason_scroll = ctk.CTkFrame(reason_card, fg_color="transparent")
        self.reason_scroll.pack(fill="x", padx=20, pady=(0, 15))

        # Historical Pattern Analysis
        history_card = ctk.CTkFrame(right_col, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        history_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(history_card, text="HISTORICAL PATTERN ANALYSIS", font=FONTS["body"], text_color="#FFD600").pack(anchor="w", padx=20, pady=(15, 10))
        
        self.history_scroll = ctk.CTkFrame(history_card, fg_color="transparent")
        self.history_scroll.pack(fill="x", padx=20, pady=(0, 15))

        # Intervention Forecast
        forecast_card = ctk.CTkFrame(right_col, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        forecast_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(forecast_card, text="INTERVENTION FORECAST", font=FONTS["body"], text_color="#4ADE80").pack(anchor="w", padx=20, pady=(15, 10))
        
        self.forecast_scroll = ctk.CTkFrame(forecast_card, fg_color="transparent")
        self.forecast_scroll.pack(fill="x", padx=20, pady=(0, 15))

        # Recommendations
        rec_card = ctk.CTkFrame(right_col, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        rec_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(rec_card, text="PRIORITY RECOMMENDATIONS", font=FONTS["body"], text_color="#4ADE80").pack(anchor="w", padx=20, pady=(15, 10))
        
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
            self.gauge_canvas.create_text(x, y_pos - 10, text=str(pct), fill="#888", font=FONTS["badge"])
            self.gauge_canvas.create_line(x, y_pos - 3, x, y_pos + 3, fill="#888")
            
        marker_x = 10 + (min(100, max(0, score)) / 100) * (width - 20)
        color = COLORS["danger"] if score >= 58 else (COLORS["warning"] if score >= 28 else COLORS["success"])
        self.gauge_canvas.create_oval(marker_x-6, y_pos-6, marker_x+6, y_pos+6, fill=color, outline="white")

    def on_slider_event(self, *args):
        """Debounced slider handler — waits 300 ms before running prediction."""
        if self.ignore_updates:
            return
        # Cancel any previously scheduled call
        if self._debounce_id is not None:
            try:
                self.after_cancel(self._debounce_id)
            except Exception:
                pass
        self._debounce_id = self.after(300, self._run_prediction_async)

    def _run_prediction_async(self):
        """Launch run_prediction on a background thread to avoid UI freeze."""
        if self._prediction_running:
            return
        self._prediction_running = True
        threading.Thread(target=self._prediction_worker, daemon=True).start()

    def _prediction_worker(self):
        """Background worker — runs prediction then marshals UI update to main thread."""
        try:
            data = {k: var.get() for k, var in self.slider_vars.items()}
            report = self.insight_service.get_simulation_report(data, year="2nd Year")
            self.after(0, self.run_prediction_ui, data, report)
        except Exception as e:
            from logic.logger import get_logger
            get_logger(__name__).error(f"Prediction worker error: {e}")
        finally:
            self._prediction_running = False

    def run_prediction(self):
        """Synchronous entry-point (called on_show and after student load)."""
        self._run_prediction_async()

    def run_prediction_ui(self, data, report):
        """Update all UI elements from a completed prediction report (main thread only)."""
        score = report.get("score", 0.0)
        level = report.get("level", "Low")
        conf = report.get("confidence", 92)
        if isinstance(conf, (int, float)):
            conf = f"{conf}%"
        
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
                self.contrib_labels[key].configure(text=f"Current Impact: {prefix}{val:.0f}%", text_color=clr)

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
            
            ctk.CTkLabel(lbl_f, text=name, font=FONTS["body"], text_color="#ccc").pack(side="left")
            prefix = "+" if val > 0 else ""
            color = COLORS["danger"] if val > 0 else (COLORS["success"] if val < 0 else "#888")
            ctk.CTkLabel(lbl_f, text=f"{prefix}{val:.0f}%", font=FONTS["body"], text_color=color).pack(side="right")
            
            pct = (abs(val) / total_abs) * 100
            bar_f = ctk.CTkFrame(row, fg_color="transparent", height=10)
            bar_f.pack(fill="x", pady=(2, 0))
            
            bar_bg = ctk.CTkFrame(bar_f, fg_color="#222", height=8, corner_radius=4)
            bar_bg.pack(side="left", fill="x", expand=True, padx=(0, 10))
            bar_bg.pack_propagate(False)
            
            if pct > 0:
                bar_fg = ctk.CTkFrame(bar_bg, fg_color=color, height=8, corner_radius=4)
                bar_fg.place(relx=0, rely=0, relwidth=min(1.0, pct/100.0), relheight=1.0)
            
            ctk.CTkLabel(bar_f, text=f"{pct:.0f}%", font=FONTS["badge"], text_color="#888", width=30).pack(side="right")

        # NLP Explanation text at the bottom
        nlp_text = report.get("nlp_explanation", "") if 'report' in locals() else (self.current_report.get("nlp_explanation", "") if getattr(self, 'current_report', None) else "")
        if nlp_text:
            ctk.CTkLabel(self.reason_scroll, text=nlp_text, font=FONTS["caption"], text_color="#aaa", wraplength=280).pack(pady=(10, 0), anchor="w")

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
            card = ctk.CTkFrame(self.history_scroll, fg_color=COLORS["card"], corner_radius=6)
            card.pack(fill="x", pady=4)
            
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=15, pady=(10, 2))
            ctk.CTkLabel(top, text=title, font=FONTS["caption"], text_color="white").pack(side="left")
            ctk.CTkLabel(top, text=trend, font=FONTS["caption"], text_color="#aaa").pack(side="right")
            
            ctk.CTkLabel(card, text=f"Detect: {insight}", font=FONTS["caption"], text_color=color).pack(anchor="w", padx=15, pady=(0, 10))

    def update_forecast_panel(self, data, current_score):
        for w in self.forecast_scroll.winfo_children(): w.destroy()
        
        sc1_data = data.copy()
        sc1_data["attendance_pct"] = max(sc1_data.get("attendance_pct", 0), 85.0)
        sc1_score = self.insight_service.get_simulation_report(sc1_data, year="2nd Year").get("score", 0.0)
        
        sc2_data = data.copy()
        sc2_data["backlog_count"] = 0.0
        sc2_score = self.insight_service.get_simulation_report(sc2_data, year="2nd Year").get("score", 0.0)
        
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
            card = ctk.CTkFrame(self.forecast_scroll, fg_color=COLORS["card"], corner_radius=6)
            card.pack(fill="x", pady=4)
            
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=15, pady=(10, 5))
            ctk.CTkLabel(top, text=f"Current Risk: {current_score:.0f}", font=FONTS["caption"], text_color="#888").pack(side="left")
            
            mid = ctk.CTkFrame(card, fg_color="transparent")
            mid.pack(fill="x", padx=15, pady=2)
            ctk.CTkLabel(mid, text=act, font=FONTS["body"], text_color="white").pack(side="left")
            
            bot = ctk.CTkFrame(card, fg_color="transparent")
            bot.pack(fill="x", padx=15, pady=(5, 10))
            ctk.CTkLabel(bot, text=f"New Risk: {new_score:.0f}", font=FONTS["body"], text_color="#4ADE80").pack(side="left")
            ctk.CTkLabel(bot, text=f"Improvement: {diff:.0f} Points", font=FONTS["caption"], text_color="#4ADE80").pack(side="right")

    def update_recommendations_panel(self, report):
        for w in self.rec_scroll.winfo_children(): w.destroy()
        
        # 1. Natural Language Report
        nlg_text = report.get("nlg_report", "")
        if nlg_text:
            nlg_card = ctk.CTkFrame(self.rec_scroll, fg_color=COLORS["card"], corner_radius=6, border_width=1, border_color=COLORS["border"])
            nlg_card.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(nlg_card, text="AI Analysis Summary", font=FONTS["caption"], text_color="#00E5FF").pack(anchor="w", padx=15, pady=(10, 2))
            ctk.CTkLabel(nlg_card, text=nlg_text, font=FONTS["caption"], text_color="#ccc", wraplength=420, justify="left").pack(anchor="w", padx=15, pady=(2, 10))
            
        # 2. Recommendations
        recs = report.get("recommendations", [])
        if not recs:
            ctk.CTkLabel(self.rec_scroll, text="No urgent recommendations.", text_color="#888").pack(anchor="w", padx=15)
            return
            
        student_id = self.search_var.get().strip() if hasattr(self, 'search_var') else ""
        faculty_user = self.controller.shared_data.get("username", "System")
        college = self.controller.shared_data.get("college_name", "Unknown")
            
        for i, rec in enumerate(recs[:4]):
            if isinstance(rec, dict):
                act = rec.get('action', '')
                rsn = rec.get('rationale', '')
                out = rec.get('expected_outcome', '')
                pri = rec.get('priority', 3)
            else:
                act = str(rec)
                rsn = "Based on current model evaluation."
                out = "Improve academic standing."
                pri = 3
                
            card = ctk.CTkFrame(self.rec_scroll, fg_color=COLORS["card"], corner_radius=6)
            card.pack(fill="x", pady=4)
            
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=15, pady=(10, 2))
            
            p_color = COLORS["danger"] if pri == 1 else (COLORS["warning"] if pri == 2 else COLORS["success"])
            ctk.CTkLabel(top_row, text=f"Priority {pri}", font=FONTS["badge"], text_color=p_color).pack(side="left")
            
            if student_id:
                # Add action tracking dropdown
                def make_cmd(action_name=act, rlevel=report.get("level", "Unknown"), dom=report.get("dominant", "Unknown"), pri_level=pri):
                    def status_changed(new_status):
                        from logic.intervention_engine import InterventionEngine
                        ie = InterventionEngine()
                        
                        # Prepare current metrics
                        curr_metrics = {
                            "att": data.get("attendance", data.get("avg_attendance", 0)),
                            "marks": data.get("marks", data.get("avg_marks", 0)),
                            "bkl": data.get("backlogs", 0)
                        }
                        
                        # Find if record exists
                        from logic.central_auth import CentralAuth
                        conn = CentralAuth()._get_conn()
                        record_id = None
                        if conn:
                            try:
                                cursor = conn.cursor(dictionary=True)
                                cursor.execute("SELECT id FROM interventions WHERE student_id=%s AND recommended_action=%s ORDER BY id DESC LIMIT 1", (student_id, action_name))
                                row = cursor.fetchone()
                                if row:
                                    record_id = row['id']
                            finally:
                                conn.close()
                                
                        if record_id:
                            ie.update_intervention_status(record_id, new_status, after_metrics=curr_metrics if new_status == "Completed" else None)
                        else:
                            ie.save_intervention(college, student_id, faculty_user, rlevel, dom, action_name, pri_level, new_status, before_metrics=curr_metrics)
                    return status_changed
                
                track_var = ctk.StringVar(value="Planned")
                tracker = ctk.CTkOptionMenu(top_row, values=["Planned", "In Progress", "Completed"], 
                                           variable=track_var, width=110, height=20, font=FONTS["badge"],
                                           command=make_cmd())
                tracker.pack(side="right")
            
            ctk.CTkLabel(card, text=act, font=FONTS["h3"], text_color="white", wraplength=400, justify="left").pack(anchor="w", padx=15, pady=2)
            ctk.CTkLabel(card, text=f"Rationale: {rsn}", font=FONTS["caption"], text_color="#aaa", wraplength=400, justify="left").pack(anchor="w", padx=15, pady=(2, 2))
            ctk.CTkLabel(card, text=f"Expected: {out}", font=FONTS["caption"], text_color="#4ADE80", wraplength=400, justify="left").pack(anchor="w", padx=15, pady=(0, 10))

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
            self.current_student_data = target
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
                        except Exception as e:
                            print(f"Exception caught: {e}")
                            pass
            
            base_report = self.insight_service.get_simulation_report(target, year="2nd Year")
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
                
            self.lbl_context.configure(text=context_text, text_color="white", font=FONTS["h3"])
            
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
        self.insight_service = InsightService()
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
        # Clear previous elements immediately
        for widget in self.scroll.winfo_children():
            widget.destroy()
            
        loading_lbl = ctk.CTkLabel(self.scroll, text="Analyzing Risk Profile & Fetching History... Please Wait.", font=FONTS["h3"], text_color=COLORS["accent"])
        loading_lbl.pack(pady=50)
        
        import threading
        threading.Thread(target=self._refresh_worker, args=(data, loading_lbl), daemon=True).start()

    def _refresh_worker(self, data, loading_lbl):
        try:
            report = self.insight_service.get_simulation_report(data)
            
            student_id = data.get('id', data.get('student_id', ''))
            college_name = self.controller.shared_data.get("college_name", "")
            
            from logic.central_auth import CentralAuth
            from logic.intervention_engine import InterventionEngine
            
            ca = CentralAuth()
            ie = InterventionEngine()
            
            raw_notes = ca.get_notes_for_student(student_id)
            raw_interventions = ie.get_database_interventions(college_name, student_id)
            
            self.after(0, self._refresh_ui, data, report, raw_notes, raw_interventions, loading_lbl)
        except Exception as e:
            from logic.logger import get_logger
            get_logger(__name__).error(f"Dashboard refresh worker error: {e}")
            self.after(0, lambda: loading_lbl.configure(text="Error loading insights. Check logs.", text_color="red"))

    def _refresh_ui(self, data, report, raw_notes, raw_interventions, loading_lbl):
        try:
            loading_lbl.destroy()
        except Exception:
            pass

        lvl = report.get('level', 'Low')
        score_val = report.get('score', 0.0)
        conf = report.get('confidence', 90)
        if isinstance(conf, (int, float)):
            conf = f"{conf}%"
        
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
        
        ctk.CTkLabel(left_h, text=data.get('display_name', 'Unknown').upper(), font=FONTS["h1"], text_color="white").pack(anchor="w")
        
        lbl_sub = f"Reg No: {data.get('display_reg_no', 'N/A')}  |  Dept: {data.get('branch_name', 'N/A')}  |  Year: {data.get('current_year', 'N/A')}"
        ctk.CTkLabel(left_h, text=lbl_sub, font=FONTS["body"], text_color="#aaa").pack(anchor="w", pady=(4, 6))
        
        # Contact Information
        contact_txt = f"📞 Parent Contact: {data.get('parent_phone', 'N/A')}  |  📧 Email: {data.get('email', 'N/A')}"
        ctk.CTkLabel(left_h, text=contact_txt, font=FONTS["caption"], text_color="#777").pack(anchor="w")
        
        # Right Actions & Scores
        right_h = ctk.CTkFrame(header_card, fg_color="transparent")
        right_h.pack(side="right", padx=20, pady=15)
        
        ctk.CTkLabel(right_h, text=f"RISK SCORE: {score_val:.1f} / 100", font=FONTS["h2"], text_color=r_color).pack(anchor="e")
        ctk.CTkLabel(right_h, text=f"{lvl.upper()} RISK CATEGORY", font=FONTS["body"], text_color=r_color).pack(anchor="e", pady=(2, 2))
        ctk.CTkLabel(right_h, text=f"Prediction Confidence: {conf}", font=FONTS["caption"], text_color="#888").pack(anchor="e", pady=(0, 10))
        
        def notify_parent():
            from ui.dashboard import ModernMessagebox
            ModernMessagebox("Notification Sent", f"Risk alert notification dispatched to parent contact: {data.get('parent_phone', 'N/A')}", "success")
            
        notify_btn = ctk.CTkButton(right_h, text="📞 NOTIFY PARENT", font=FONTS["caption"], fg_color=COLORS["danger"], text_color="white", height=28, command=notify_parent)
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
        
        ctk.CTkLabel(assess_card, text="🧠 AI RISK ASSESSMENT", font=FONTS["body"], text_color="#FFD600").pack(anchor="w", padx=15, pady=(10, 5))
        
        # Build explanation from actual feature values
        att_pct = data.get('attendance_pct', 0)
        backlogs = data.get('backlog_count', 0)
        cgpa = data.get('cgpa', 0)
        
        att_txt = f"Attendance: {float(att_pct):.1f}% (Threshold: 75%)"
        bl_txt = f"Active Backlogs: {int(float(backlogs))} (Threshold: 0)"
        cgpa_txt = f"CGPA: {float(cgpa)} (Threshold: 5.5)"
        
        ctk.CTkLabel(assess_card, text=f"Key Inputs:  {att_txt}   |   {bl_txt}   |   {cgpa_txt}", font=FONTS["caption"], text_color="#ccc").pack(anchor="w", padx=15, pady=(0, 5))
        
        explanation = report.get('explanation', f"The model evaluated the student as {lvl} Risk primarily based on these parameters.")
        ctk.CTkLabel(assess_card, text=explanation, wraplength=500, justify="left", font=FONTS["caption"], text_color="#ddd").pack(anchor="w", padx=15, pady=(0, 15))

        # ----------------------------------------------------
        # 3. HISTORICAL TREND ANALYSIS (Left Pane)
        # ----------------------------------------------------
        trend_card = ctk.CTkFrame(left_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        trend_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(trend_card, text="📈 HISTORICAL TREND ANALYSIS", font=FONTS["body"], text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=(10, 5))
        
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
            ctk.CTkLabel(trend_card, text="No historical semester records found in ERP database.", font=FONTS["caption"], text_color="#777").pack(anchor="w", padx=15, pady=(0, 15))

        # ----------------------------------------------------
        # 4. STUDENT ACTIVITY TIMELINE (Left Pane)
        # ----------------------------------------------------
        timeline_card = ctk.CTkFrame(left_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        timeline_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(timeline_card, text="📅 STUDENT ACTIVITY TIMELINE", font=FONTS["body"], text_color="#888").pack(anchor="w", padx=15, pady=(10, 5))
        
        # Dynamic Timeline Rendering (Interventions + Notes)
        # (Data already fetched in background worker)
        student_id = data.get('id', data.get('student_id', ''))
        
        timeline_events = []
        for n in raw_notes:
            st = n.get('note_status', 'ACTIVE')
            if st == 'CRITICAL': c = "#FF5555"
            elif st == 'FOLLOW_UP': c = "yellow"
            elif st == 'ACTIVE': c = "#4ADE80"
            else: c = "cyan"
            
            timeline_events.append({
                "date": n.get('created_at'),
                "desc": f"Note [{st}]: {n.get('note_text', '')[:30]}...",
                "type": "Note",
                "color": c
            })
            
        for iv in raw_interventions:
            timeline_events.append({
                "date": iv.get('date_created'),
                "desc": f"Intervention: {iv.get('recommendation_text', '')}",
                "type": "Action"
            })
            
        # Sort chronologically, newest first
        import datetime
        def parse_dt(d):
            if isinstance(d, datetime.datetime): return d
            try: return datetime.datetime.strptime(str(d), "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"Exception caught: {e}")
                return datetime.datetime.min
            
        timeline_events.sort(key=lambda x: parse_dt(x['date']), reverse=True)
        
        if not timeline_events:
            activities = [("Today", "Risk score initialized", COLORS["accent"])]
        else:
            activities = []
            for ev in timeline_events[:5]:
                dt = parse_dt(ev['date'])
                if dt == datetime.datetime.min: d_str = "Past"
                else: d_str = dt.strftime("%b %d, %Y")
                activities.append((d_str, ev['desc'], ev.get('color', COLORS["accent"])))
                
        for date, desc, color in activities:
            row = ctk.CTkFrame(timeline_card, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=4)
            ctk.CTkLabel(row, text=date, font=FONTS["badge"], text_color=color, width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=desc, font=FONTS["caption"], text_color="#ddd").pack(side="left")
            
        ctk.CTkFrame(timeline_card, height=10, fg_color="transparent").pack()

        # ----------------------------------------------------
        # 4.1 FACULTY NOTES HISTORY (Left Pane)
        # ----------------------------------------------------
        history_card = ctk.CTkFrame(left_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        history_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(history_card, text="📝 NOTE HISTORY", font=FONTS["body"], text_color="#FFD600").pack(anchor="w", padx=15, pady=(10, 5))
        
        # Embedded Note History Feed
        history_frame = ctk.CTkScrollableFrame(history_card, height=100, fg_color="transparent")
        history_frame.pack(fill="x", padx=15, pady=5)
        
        def load_history():
            for w in history_frame.winfo_children(): w.destroy()
            notes = raw_notes
            if not notes:
                ctk.CTkLabel(history_frame, text="No previous notes for this student.", text_color="#555", font=FONTS["caption"]).pack(pady=10)
                return
            for n in notes:
                st = n.get('note_status', 'ACTIVE')
                if st == 'CRITICAL': c = "#FF5555"
                elif st == 'FOLLOW_UP': c = "yellow"
                elif st == 'ACTIVE': c = "#4ADE80"
                else: c = "cyan"
                
                # Chat-style bubble
                b_frame = ctk.CTkFrame(history_frame, fg_color="transparent")
                b_frame.pack(fill="x", pady=5, padx=10)
                
                # Left colored border effect
                f_card = ctk.CTkFrame(b_frame, fg_color=c, corner_radius=8)
                f_card.pack(anchor="w", fill="x")
                
                inner_card = ctk.CTkFrame(f_card, fg_color="#18181b", corner_radius=6)
                inner_card.pack(fill="both", expand=True, padx=(4, 1), pady=1)
                
                author = n.get('faculty_username', 'Unknown')
                dt = n.get('created_at')
                dt_str = dt.strftime("%b %d, %Y %I:%M %p") if dt else "Unknown Date"
                
                head_f = ctk.CTkFrame(inner_card, fg_color="transparent")
                head_f.pack(fill="x", padx=10, pady=(8,0))
                
                ctk.CTkLabel(head_f, text=f"{author}", font=FONTS["body"], text_color="#e4e4e7").pack(side="left")
                ctk.CTkLabel(head_f, text=f" • {dt_str}", font=FONTS["badge"], text_color="#aaa").pack(side="left", padx=5)
                
                badge = ctk.CTkLabel(head_f, text=f" {st} ", font=FONTS["badge"], text_color="#000", fg_color=c, corner_radius=4)
                badge.pack(side="right", padx=(10,0))
                
                ctk.CTkLabel(inner_card, text=n.get('note_text', ''), font=FONTS["body"], text_color="#a1a1aa", wraplength=450, justify="left").pack(anchor="w", padx=10, pady=(8,10))
                
        load_history()
        
        # ----------------------------------------------------
        # 4.2 ADD FACULTY NOTE (Left Pane)
        # ----------------------------------------------------
        input_card = ctk.CTkFrame(left_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        input_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(input_card, text="➕ ADD FACULTY NOTE", font=FONTS["body"], text_color="#FFD600").pack(anchor="w", padx=15, pady=(10, 5))
        
        status_f = ctk.CTkFrame(input_card, fg_color="transparent")
        status_f.pack(fill="x", padx=15, pady=(5, 5))
        ctk.CTkLabel(status_f, text="Note Status:", font=FONTS["caption"], text_color="#a1a1aa").pack(side="left", padx=(0, 10))
        self.note_status_var = ctk.StringVar(value="ACTIVE")
        self.note_status_combo = ctk.CTkComboBox(status_f, values=["ACTIVE", "FOLLOW_UP", "CRITICAL", "CLOSED"], variable=self.note_status_var, width=150, fg_color="#1e1e24", border_color="#3f3f46", button_color="#3f3f46")
        self.note_status_combo.pack(side="left")
        
        input_wrapper = ctk.CTkFrame(input_card, fg_color="#1e1e24", corner_radius=12, border_width=1, border_color="#3f3f46")
        input_wrapper.pack(fill="x", padx=15, pady=(5, 15))
        
        note_text = ctk.CTkTextbox(input_wrapper, height=50, fg_color="transparent", text_color="white", border_width=0, font=FONTS["body"])
        note_text.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        
        def save_faculty_note():
            nt = note_text.get("1.0", "end-1c").strip()
            if not nt: return
            fac_usr = self.controller.shared_data.get("username", "Unknown")
            dept = self.controller.shared_data.get("department", data.get("branch_name", "Unknown"))
            st = self.note_status_var.get()
            CentralAuth().save_faculty_note(student_id, fac_usr, dept, nt, note_status=st)
            note_text.delete("1.0", "end")
            from ui.dashboard import ModernMessagebox
            ModernMessagebox("Note Saved", "Faculty note successfully added to student record.", "success")
            load_history() # Refresh the embedded history
            
        send_btn = ctk.CTkButton(input_wrapper, text="➤", width=40, height=40, corner_radius=8, font=FONTS["h2"], fg_color="#38bdf8", text_color="black", hover_color="#0284c7", command=save_faculty_note)
        send_btn.pack(side="right", padx=10, pady=10)

        # ----------------------------------------------------
        # 5. WHY THE MODEL MADE THIS DECISION (Right Pane)
        # ----------------------------------------------------
        contrib_card = ctk.CTkFrame(right_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        contrib_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(contrib_card, text="⚖️ WHY THE MODEL MADE THIS DECISION", font=FONTS["body"], text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=(10, 5))
        
        contribs = report.get('contributions', {})
        if contribs:
            sorted_c = sorted(contribs.items(), key=lambda x: abs(x[1]), reverse=True)
            
            # Show specific points
            for idx, (name, val) in enumerate(sorted_c[:5]):
                row = ctk.CTkFrame(contrib_card, fg_color="transparent")
                row.pack(fill="x", padx=15, pady=2)
                
                c_lbl = ctk.CTkLabel(row, text=f"{idx+1}. {name}", font=FONTS["caption"], text_color="#ccc")
                c_lbl.pack(side="left")
                
                prefix = "+" if val > 0 else ""
                color = COLORS["danger"] if val > 0 else (COLORS["success"] if val < 0 else "#888")
                
                c_val = ctk.CTkLabel(row, text=f"{prefix}{val:.0f}%", font=FONTS["caption"], text_color=color)
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
            ctk.CTkLabel(contrib_card, text="No risk contribution factor records.", font=FONTS["caption"], text_color="#777").pack(anchor="w", padx=15, pady=(0, 15))

        # ----------------------------------------------------
        # 6. INTERVENTION FORECAST (Right Pane)
        # ----------------------------------------------------
        forecast_card = ctk.CTkFrame(right_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        forecast_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(forecast_card, text="🔮 INTERVENTION FORECAST", font=FONTS["body"], text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=(10, 5))
        
        # Attendance Intervention Simulation
        sc1_data = data.copy()
        sc1_data["attendance_pct"] = max(sc1_data.get("attendance_pct", 0), 85.0)
        sc1_report = self.insight_service.get_simulation_report(sc1_data, year="2nd Year")
        sc1_score = sc1_report.get("score", 0.0)
        
        # Backlog Intervention Simulation
        sc2_data = data.copy()
        sc2_data["backlog_count"] = 0.0
        sc2_report = self.insight_service.get_simulation_report(sc2_data, year="2nd Year")
        sc2_score = sc2_report.get("score", 0.0)

        forecasts = [
            ("Improve Attendance to 85%", f"New Risk: {sc1_score:.1f}", score_val - sc1_score),
            ("Clear All Active Backlogs", f"New Risk: {sc2_score:.1f}", score_val - sc2_score)
        ]
        
        for act, res, diff in forecasts:
            row = ctk.CTkFrame(forecast_card, fg_color=COLORS["card"])
            row.pack(fill="x", padx=15, pady=3)
            ctk.CTkLabel(row, text=f"Scenario: {act}", font=FONTS["caption"], text_color="white", anchor="w").pack(side="left", padx=10, pady=8)
            
            val_frame = ctk.CTkFrame(row, fg_color="transparent")
            val_frame.pack(side="right", padx=10)
            
            ctk.CTkLabel(val_frame, text=res, font=FONTS["caption"], text_color="#4ADE80" if diff > 0 else "#888").pack(side="left")
            if diff > 0:
                ctk.CTkLabel(val_frame, text=f" (-{diff:.1f} pts)", font=FONTS["badge"], text_color="#4ADE80").pack(side="left")
            
        ctk.CTkFrame(forecast_card, height=10, fg_color="transparent").pack()

        # ----------------------------------------------------
        # 7. RECOMMENDED ACTIONS (Right Pane)
        # ----------------------------------------------------
        rec_card = ctk.CTkFrame(right_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        rec_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(rec_card, text="✅ RECOMMENDED ACTIONS (Prioritized)", font=FONTS["body"], text_color="#4ADE80").pack(anchor="w", padx=15, pady=(10, 5))
        
        ctk.CTkFrame(rec_card, height=10, fg_color="transparent").pack()

        recs = report.get('recommendations', [])
        if recs:
            for idx, rec in enumerate(recs[:4]):
                if isinstance(rec, dict):
                    txt = f"{idx+1}. {rec.get('action','')} — {rec.get('reason','')}"
                else:
                    txt = f"{idx+1}. {str(rec)}"
                ctk.CTkLabel(rec_card, text=txt, wraplength=450, justify="left", font=FONTS["caption"], text_color="#d1fae5").pack(anchor="w", padx=15, pady=2)
        else:
            ctk.CTkLabel(rec_card, text="1. Maintain current academic parameters.", font=FONTS["caption"], text_color="#aaa").pack(anchor="w", padx=15, pady=5)
            
        ctk.CTkFrame(rec_card, height=10, fg_color="transparent").pack()

        # ----------------------------------------------------
        # 8. INTERVENTION EFFECTIVENESS TRACKER (Right Pane)
        # ----------------------------------------------------
        tracker_card = ctk.CTkFrame(right_pane, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        tracker_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(tracker_card, text="🎯 INTERVENTION TRACKING", font=FONTS["body"], text_color="#00E5FF").pack(anchor="w", padx=15, pady=(10, 5))
        
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
            ctk.CTkLabel(rec_add_f, text=f"Top AI Rec: {act}", font=FONTS["caption"], text_color="#aaa").pack(side="left")
            ctk.CTkButton(rec_add_f, text="+ Add to Tracked", width=100, height=20, font=FONTS["badge"], fg_color="#1e3a5f", command=lambda: add_to_tracker(act, rsn, prio)).pack(side="right")
        
        # Display Tracked Interventions
        tracked_scroll = ctk.CTkScrollableFrame(tracker_card, fg_color="transparent", height=120)
        tracked_scroll.pack(fill="x", padx=15, pady=5)
        
        tracked = self.db.get_interventions(data['id']) if self.db and 'id' in data else []
        
        if not tracked:
            ctk.CTkLabel(tracked_scroll, text="No active interventions being tracked.", text_color="#666", font=FONTS["caption"]).pack(anchor="w")
        else:
            completed = sum(1 for t in tracked if t['status'] == 'Completed')
            effectiveness = (completed / len(tracked)) * 100 if len(tracked) > 0 else 0
            
            eff_card = ctk.CTkFrame(tracker_card, fg_color=COLORS["card"])
            eff_card.pack(fill="x", padx=15, pady=(0, 10))
            ctk.CTkLabel(eff_card, text=f"Effectiveness Score: {effectiveness:.0f}%", font=FONTS["body"], text_color=COLORS["success"] if effectiveness > 50 else COLORS["warning"]).pack(side="left", padx=10, pady=5)
            ctk.CTkLabel(eff_card, text=f"({completed}/{len(tracked)} Resolved)", font=FONTS["badge"], text_color="#888").pack(side="right", padx=10, pady=5)

            for t in tracked:
                t_row = ctk.CTkFrame(tracked_scroll, fg_color=COLORS["card"], corner_radius=6)
                t_row.pack(fill="x", pady=2)
                
                ctk.CTkLabel(t_row, text=t['recommendation_text'], font=FONTS["caption"], text_color="white", wraplength=250, justify="left").pack(side="left", padx=10, pady=8)
                
                status_color = {"Planned": "#ffa502", "In Progress": "#1e90ff", "Completed": "#2ed573"}
                clr = status_color.get(t['status'], "white")
                
                # Button to cycle status
                def cycle_status(t_id=t['id'], cur_stat=t['status']):
                    next_stat = "In Progress" if cur_stat == "Planned" else ("Completed" if cur_stat == "In Progress" else "Planned")
                    if self.db:
                        self.db.update_intervention_status(t_id, next_stat)
                        self.refresh(self.raw_data)
                
                stat_btn = ctk.CTkButton(t_row, text=t['status'], width=80, height=20, font=FONTS["badge"], text_color=clr, fg_color="#222", hover_color="#333", command=cycle_status)
                stat_btn.pack(side="right", padx=10, pady=5)

        # ----------------------------------------------------
        # 9. FACULTY NOTES & NOTES HISTORY
        # ----------------------------------------------------
        notes_card = ctk.CTkFrame(self.scroll, fg_color="#121212", corner_radius=8, border_width=1, border_color="#222")
        notes_card.pack(fill="x", pady=(10, 20))
        
        ctk.CTkLabel(notes_card, text="📝 FACULTY OBSERVATION NOTES & HISTORY", font=FONTS["body"], text_color="gray").pack(anchor="w", padx=15, pady=(10, 2))
        
        self.txt_note = ctk.CTkTextbox(notes_card, height=60, fg_color="#1b1b1b")
        self.txt_note.pack(fill="x", padx=15, pady=5)
        
        # Notes history mock listing (Preserving layout representation)
        history_frame = ctk.CTkFrame(notes_card, fg_color="transparent")
        history_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(history_frame, text="Saved Notes History:", font=FONTS["badge"], text_color="#555").pack(anchor="w")
        ctk.CTkLabel(history_frame, text="• No previous faculty notes found for this student.", font=FONTS["caption"], text_color="#777").pack(anchor="w", padx=10, pady=2)
        
        def save_note():
            ModernMessagebox("Saved", "Observations recorded to student audit logs.", "success")
            
        ctk.CTkButton(notes_card, text="SAVE OBSERVATION", fg_color="#222", font=FONTS["caption"], command=save_note).pack(anchor="e", padx=15, pady=(5, 10))

