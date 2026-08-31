import customtkinter as ctk
from tkinter import messagebox, Toplevel, scrolledtext
import pandas as pd
import time
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.styles import COLORS, FONTS, DIMS
try:
    from ui.trend_visuals import TrendVisuals
except ImportError:
    pass

class StudentListMixin:
    def show_student_list(self):
        self.header.pack_forget()
        self._clear()
        name = self.translator.get_name(self.current_branch)
        
        # TOOLBAR (top bar)
        toolbar = ctk.CTkFrame(self.content_area, fg_color="#0d0d0d", height=56, corner_radius=0)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        left_tool = ctk.CTkFrame(toolbar, fg_color="transparent")
        left_tool.pack(side="left", fill="y", padx=20)
        
        btn_back = ctk.CTkButton(left_tool, text="←", width=36, height=36, corner_radius=8, 
                                 fg_color="#222", hover_color="#333", text_color="white", font=FONTS["h3"],
                                 command=self.go_back)
        btn_back.pack(side="left", pady=10)
        
        lbl_title = ctk.CTkLabel(left_tool, text=f"{name} > {self.current_year}", font=("Outfit", 22, "bold"), text_color="#00E5FF")
        lbl_title.pack(side="left", padx=15, pady=10)

        right_tool = ctk.CTkFrame(toolbar, fg_color="transparent")
        right_tool.pack(side="right", fill="y", padx=20)

        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.filter_list)
        search_ent = ctk.CTkEntry(right_tool, textvariable=self.search_var, placeholder_text="Search student name or ID...",
                                  width=250, height=34, corner_radius=17, fg_color=COLORS["card"], border_color=COLORS["border"], border_width=1)
        search_ent.pack(side="left", padx=(0, 15), pady=11)
        search_ent.bind("<FocusIn>", lambda e: search_ent.configure(border_color=COLORS["accent"]))
        search_ent.bind("<FocusOut>", lambda e: search_ent.configure(border_color=COLORS["border"]))

        exp_btn = ctk.CTkButton(right_tool, text="Export CSV", width=100, height=34, corner_radius=17,
                                fg_color=COLORS["card"], border_width=1, border_color=COLORS["accent"], text_color="white",
                                hover_color="#222", command=self.export_report)
        exp_btn.pack(side="left", pady=11)

        # FILTER BAR
        filter_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(20, 0), padx=20)
        
        self.filter_vars = {}
        self.current_filter = "All"
        self.btn_all = self._create_pill_btn(filter_frame, "ALL", "All", "#888888")
        self.btn_high = self._create_pill_btn(filter_frame, "HIGH RISK", "High", "#FF5555")
        self.btn_med = self._create_pill_btn(filter_frame, "MEDIUM RISK", "Medium", "#FF9100")
        self.btn_low = self._create_pill_btn(filter_frame, "LOW RISK", "Low", "#00C853")        
        self.note_filter_var = ctk.StringVar(value="All Students")
        self.note_filter = ctk.CTkComboBox(filter_frame, values=["All Students", "No Notes", "Active Notes", "Follow-Up Required", "Critical Cases", "Closed Cases"], 
                                           variable=self.note_filter_var, command=self.filter_list, width=170, height=32, corner_radius=16, 
                                           fg_color=COLORS["card"], border_color=COLORS["border"], button_color=COLORS["card"], button_hover_color="#1A1D2D",
                                           text_color="white", dropdown_fg_color="#12141E", dropdown_hover_color="#1A1D2D", dropdown_text_color="white")
        self.note_filter.pack(side="right")
        ctk.CTkLabel(filter_frame, text="Note Filter:", text_color="gray").pack(side="right", padx=(0, 10))

        # SUMMARY BAR
        self.summary_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.summary_frame.pack(fill="x", padx=20, pady=(10, 15))

        self.list_frame = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=10)
        
        from logic.central_auth import CentralAuth
        self.note_stats = CentralAuth().get_student_note_stats(department=None)
        
        self._update_filter_visuals()
        self.filter_list()

    def _create_pill_btn(self, p, text, val, color):
        btn = ctk.CTkButton(p, text=text, height=32, corner_radius=16,
                            fg_color="transparent", border_width=1, border_color=color,
                            text_color=color, hover_color=color,
                            command=lambda v=val: self.apply_filter(v))
        btn.pack(side="left", padx=(0, 10))
        btn.base_text = text
        btn.base_color = color
        self.filter_vars[val] = btn
        return btn

    def apply_filter(self, val):
        self.current_filter = val
        self._update_filter_visuals()
        self.filter_list()

    def _update_filter_visuals(self):
        for val, btn in self.filter_vars.items():
            if val == self.current_filter:
                btn.configure(fg_color=btn.base_color, text_color="white", font=FONTS["body"])
            else:
                btn.configure(fg_color="transparent", text_color=btn.base_color, font=FONTS["body"])

    def filter_list(self, *args):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        for widget in self.summary_frame.winfo_children():
            widget.destroy()
            
        loading_lbl = ctk.CTkLabel(self.list_frame, text="Analysing students...", font=FONTS["h2"], text_color="gray")
        loading_lbl.pack(pady=100)
        self.update()
        
        self.after(10, self._process_filter_list)

    def _process_filter_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        import threading
        
        def run_analysis():
            students = self.db.get_students(self.current_branch, self.current_year)
            query = self.search_var.get().lower()
            note_f = self.note_filter_var.get()
            
            filtered_students = []
            for s in students:
                stat = self.note_stats.get(s['id'], {})
                st = stat.get('latest_status', 'NONE') if stat else 'NONE'
                
                keep = True
                if note_f == "No Notes" and st != "NONE": keep = False
                elif note_f == "Active Notes" and st != "ACTIVE": keep = False
                elif note_f == "Follow-Up Required" and st != "FOLLOW_UP": keep = False
                elif note_f == "Critical Cases" and st != "CRITICAL": keep = False
                elif note_f == "Closed Cases" and st != "CLOSED": keep = False
                
                is_match = query in str(s['id']).lower() or query in str(s['name']).lower()
                if is_match and keep:
                    filtered_students.append(s)

            processed_students = []
            counts = {"High": 0, "Medium": 0, "Low": 0, "Pending": 0, "All": 0}
            
            import json
            for s in filtered_students:
                # Use precomputed AI data if available from SQLite join
                score = s.get('risk_score')
                level = s.get('risk_category')
                
                # Fallback if somehow missing
                if score is None or level is None:
                    score = 0.0
                    level = "Low"
                    
                report = {
                    'score': score,
                    'level': level,
                    'risk_score': score,
                    'risk_category': level,
                    'confidence': s.get('confidence', 90)
                }
                
                # Parse full report json if available for deep insights
                try:
                    report_json = s.get('report_json')
                    if report_json:
                        parsed = json.loads(report_json)
                        report.update(parsed)
                except Exception:
                    pass
                    
                counts["All"] += 1
                counts[level] += 1
                processed_students.append((s, report))
                
            self.after(0, lambda: self._render_filtered_list(processed_students, counts))
            
        threading.Thread(target=run_analysis, daemon=True).start()

    def _render_filtered_list(self, processed_students, counts):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        self.btn_all.configure(text=f"{self.btn_all.base_text}  •  {counts['All']}")
        self.btn_high.configure(text=f"{self.btn_high.base_text}  •  {counts['High']}")
        self.btn_med.configure(text=f"{self.btn_med.base_text}  •  {counts['Medium']}")
        self.btn_low.configure(text=f"{self.btn_low.base_text}  •  {counts['Low']}")
        
        sum_txt = ctk.CTkLabel(self.summary_frame, text="Showing ", font=FONTS["caption"], text_color="#888")
        sum_txt.pack(side="left")
        ctk.CTkLabel(self.summary_frame, text=f"{counts['All']} students", font=FONTS["caption"], text_color="white").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text="  |  ", font=FONTS["caption"], text_color="#444").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text=f"{counts['High']} High", font=FONTS["caption"], text_color="#FF5555").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text="  •  ", font=FONTS["caption"], text_color="#444").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text=f"{counts['Medium']} Medium", font=FONTS["caption"], text_color="#FF9100").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text="  •  ", font=FONTS["caption"], text_color="#444").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text=f"{counts['Low']} Low", font=FONTS["caption"], text_color="#00C853").pack(side="left")

        displayed = 0
        for s, report in processed_students:
            if self.current_filter == "All" or report['level'] == self.current_filter:
                self._draw_modern_row(s, report)
                displayed += 1
                
        if displayed == 0:
            empty_f = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            empty_f.pack(pady=50)
            ctk.CTkLabel(empty_f, text="👤\u200d\u2205", font=("Arial", 48), text_color="#444").pack(pady=(0, 10))
            ctk.CTkLabel(empty_f, text="No students found", font=("Arial", 16, "bold"), text_color="#888").pack()
            ctk.CTkLabel(empty_f, text="Try adjusting your search or filter", font=("Arial", 12), text_color="#444").pack()

    def _draw_modern_row(self, s, report):
        import tkinter as tk
        row_wrapper = ctk.CTkFrame(self.list_frame, fg_color=COLORS["card"], corner_radius=8, border_width=1, border_color=COLORS["border"], height=64)
        row_wrapper.pack(fill="x", pady=5, padx=10)
        row_wrapper.pack_propagate(False)
        
        def on_enter(e, rw=row_wrapper): rw.configure(fg_color="#242424")
        def on_leave(e, rw=row_wrapper): rw.configure(fg_color=COLORS["card"])
        row_wrapper.bind("<Enter>", on_enter)
        row_wrapper.bind("<Leave>", on_leave)

        level = report.get('level', 'Low')
        if level == "High": r_col, dim_col = "#FF5555", "#4d0000"
        elif level == "Medium": r_col, dim_col = "#FF9100", "#4d2b00"
        elif level == "Pending": r_col, dim_col = "#7A849C", "#2A2E3F"
        else: r_col, dim_col = "#00C853", "#004d20"
        
        strip = tk.Canvas(row_wrapper, width=4, height=64, bg=r_col, highlightthickness=0)
        strip.pack(side="left", fill="y")
        
        avatar_f = ctk.CTkFrame(row_wrapper, width=40, height=40, corner_radius=20, fg_color=dim_col)
        avatar_f.pack(side="left", padx=(15, 15), pady=12)
        avatar_f.pack_propagate(False)
        
        name_str = str(s.get('name', ''))
            
        initials_lbl = ctk.CTkLabel(avatar_f, text="👤", font=("Arial", 18), text_color="white")
        initials_lbl.place(relx=0.5, rely=0.5, anchor="center")
        
        for child in [strip, avatar_f, initials_lbl]:
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)

        info_f = ctk.CTkFrame(row_wrapper, fg_color="transparent")
        info_f.pack(side="left", fill="both", expand=True, pady=10)
        
        name_f = ctk.CTkFrame(info_f, fg_color="transparent")
        name_f.pack(anchor="w")
        
        lbl_name = ctk.CTkLabel(name_f, text=name_str, font=("Arial", 14, "bold"), text_color="#00E5FF")
        lbl_name.pack(side="left")
        
        if report.get('is_first_year'):
            pill = ctk.CTkFrame(name_f, fg_color="#4a0080", corner_radius=10, height=20)
            pill.pack(side="left", padx=10)
            ctk.CTkLabel(pill, text="1st Year", font=("Arial", 10, "bold"), text_color="white").pack(padx=8, pady=0)
            
        lbl_id = ctk.CTkLabel(info_f, text=str(s.get('id', '')), font=("Arial", 12), text_color="#888888")
        lbl_id.pack(anchor="w", pady=(0, 0))
        
        for child in [info_f, name_f, lbl_name, lbl_id]:
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)

        if level == "Pending":
            btn_diag = ctk.CTkLabel(row_wrapper, text="Data Needed", font=("Arial", 12, "bold"), text_color="gray", width=100)
            btn_diag.pack(side="right", padx=15, pady=15)
        else:
            btn_diag = ctk.CTkButton(row_wrapper, text="DIAGNOSE →", width=100, height=34, corner_radius=17,
                                     fg_color="transparent", border_width=1, border_color="#00E5FF", text_color="#00E5FF",
                                     hover_color="#00E5FF", command=lambda d=s, r=report: self.open_deep_analysis(d, r))
            def diag_enter(e, b=btn_diag, rw=row_wrapper): b.configure(text_color="black"); rw.configure(fg_color="#242424")
            def diag_leave(e, b=btn_diag, rw=row_wrapper): b.configure(text_color="#00E5FF"); rw.configure(fg_color=COLORS["card"])
            btn_diag.bind("<Enter>", diag_enter, add="+")
            btn_diag.bind("<Leave>", diag_leave, add="+")
            btn_diag.pack(side="right", padx=15, pady=15)

        metrics_f = ctk.CTkFrame(row_wrapper, fg_color="transparent")
        metrics_f.pack(side="right", padx=15, pady=15)
        
        score_pill = ctk.CTkFrame(metrics_f, fg_color=dim_col, corner_radius=12, height=24)
        score_pill.pack(side="left", padx=5)
        if level == "Pending":
            ctk.CTkLabel(score_pill, text="Insufficient Data", font=("Arial", 11), text_color=r_col).pack(padx=8, pady=2)
        else:
            ctk.CTkLabel(score_pill, text=f"Score: {report.get('risk_score', 0):.1f}", font=("Arial", 11), text_color=r_col).pack(padx=8, pady=2)
        
        if s.get('avg_attendance') is not None:
            att_pill = ctk.CTkFrame(metrics_f, fg_color="#222222", corner_radius=12, height=24)
            att_pill.pack(side="left", padx=5)
            ctk.CTkLabel(att_pill, text=f"Att: {float(s['avg_attendance']):.1f}%", font=("Arial", 11), text_color="#ccc").pack(padx=8, pady=2)
            
        conf_pill = ctk.CTkFrame(metrics_f, fg_color="#222222", corner_radius=12, height=24)
        conf_pill.pack(side="left", padx=5)
        ctk.CTkLabel(conf_pill, text=f"Conf: {report.get('confidence_score', 0)}%", font=("Arial", 11), text_color="#ccc").pack(padx=8, pady=2)
        
        stat = self.note_stats.get(s['id'], {})
        st = stat.get('latest_status', 'NONE') if stat else 'NONE'
        tot = stat.get('total_notes', 0) if stat else 0
        if st == 'CRITICAL': n_icon, n_color = "🔴", "#FF5555"
        elif st == 'FOLLOW_UP': n_icon, n_color = "🟡", "yellow"
        elif st == 'ACTIVE': n_icon, n_color = "🟢", "#4ADE80"
        elif st == 'CLOSED': n_icon, n_color = "✅", "cyan"
        else: n_icon, n_color = "⚪", "gray"
        
        note_pill = ctk.CTkFrame(metrics_f, fg_color="#222222", corner_radius=12, height=24, cursor="hand2")
        note_pill.pack(side="left", padx=5)
        note_lbl = ctk.CTkLabel(note_pill, text=f"{n_icon} {tot}" if tot > 0 else f"{n_icon}", text_color=n_color, font=("Arial", 11))
        note_lbl.pack(padx=8, pady=2)
        
        def show_quick_view(ev, st_stat=stat):
            if not st_stat: return
            q = ctk.CTkToplevel(self)
            q.title("Note Quick View")
            q.geometry("400x250")
            q.attributes("-topmost", True)
            q.configure(fg_color="#111")
            ctk.CTkLabel(q, text=f"Total Notes: {st_stat.get('total_notes', 0)}", font=FONTS["body"]).pack(pady=(15,5))
            ctk.CTkLabel(q, text=f"Status: {st_stat.get('latest_status', 'NONE')}", text_color=n_color).pack()
            dt = st_stat.get('latest_date')
            dt_str = dt.strftime("%b %d, %Y") if dt else "N/A"
            ctk.CTkLabel(q, text=f"Last Updated: {dt_str} by {st_stat.get('latest_faculty', 'N/A')}", font=FONTS["badge"]).pack()
            ctk.CTkLabel(q, text=st_stat.get('latest_text', ''), wraplength=350, justify="left").pack(pady=10)
            
        note_pill.bind("<Double-1>", show_quick_view)
        note_lbl.bind("<Double-1>", show_quick_view)
        
        def note_enter(ev, st_stat=stat, rw=row_wrapper):
            rw.configure(fg_color="#242424")
            if not st_stat: return
            if not hasattr(self, 'tooltip'):
                self.tooltip = ctk.CTkToplevel(self)
                self.tooltip.overrideredirect(True)
                self.tooltip.configure(fg_color="#222")
                dt = st_stat.get('latest_date')
                dt_str = dt.strftime("%b %d, %Y") if dt else "N/A"
                txt = f"Date: {dt_str}\nFaculty: {st_stat.get('latest_faculty', 'N/A')}\nStatus: {st_stat.get('latest_status')}\nNote: {st_stat.get('latest_text', '')}"
                ctk.CTkLabel(self.tooltip, text=txt, justify="left", font=FONTS["badge"], wraplength=250, text_color="white", corner_radius=5, fg_color="#222").pack(padx=10, pady=5)
                x = ev.widget.winfo_rootx() + 25
                y = ev.widget.winfo_rooty() + 25
                self.tooltip.geometry(f"+{x}+{y}")
                
        def note_leave(ev, rw=row_wrapper):
            rw.configure(fg_color=COLORS["card"])
            if hasattr(self, 'tooltip') and self.tooltip:
                self.tooltip.destroy()
                del self.tooltip
                
        note_pill.bind("<Enter>", note_enter)
        note_pill.bind("<Leave>", note_leave)
        note_lbl.bind("<Enter>", note_enter)
        note_lbl.bind("<Leave>", note_leave)
            
        for p in metrics_f.winfo_children():
            if p.cget("cursor") != "hand2":
                p.bind("<Enter>", on_enter)
                p.bind("<Leave>", on_leave)
                for c in p.winfo_children():
                    c.bind("<Enter>", on_enter)
                    c.bind("<Leave>", on_leave)
