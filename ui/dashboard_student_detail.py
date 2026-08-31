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

class StudentDetailMixin:
    def open_deep_analysis(self, data, report):
        top = ctk.CTkToplevel(self)
        top.geometry("1100x850")
        top.title("AcaDesk - Student Diagnosis")
        top.attributes("-topmost", True)
        top.configure(fg_color=COLORS["bg"])

        # Color configurations
        r_color = COLORS["success"]
        if report['level'] == "High": r_color = COLORS["danger"]
        elif report['level'] == "Medium": r_color = COLORS["warning"]

        p_email = data.get('parent_email', 'Not Provided')
        is_email_missing = p_email == 'Not Provided' or not p_email
        branch_name = self.translator.get_name(self.current_branch)

        has_email = bool(
            (data.get("email") or "").strip() or
            (data.get("parent_email") or "").strip()
        )
        btn_notify_state = "normal" if has_email else "disabled"
        btn_notify_text = "🔔 Notify" if has_email else "🔔 No Email on Record"

        def send_email_alert():
            emails_to_send = []
            student_email = (data.get("email") or "").strip()
            parent_email = (data.get("parent_email") or "").strip()
            if student_email:
                emails_to_send.append(student_email)
            if parent_email:
                emails_to_send.append(parent_email)
            
            if not emails_to_send:
                ModernMessagebox(
                    "No Contact Information",
                    "No email address is recorded for this student or their parent in the ERP database. The alert cannot be sent.",
                    "error"
                )
                return
            
            from logic.email_service import EmailService
            es = EmailService()
            success = es.send_early_warning_alert(
                to_emails=emails_to_send,
                student_name=data.get("display_name", data.get("name", "Student")),
                student_id=data.get("registration_no", data.get("id", "Unknown")),
                college_name=self.controller.shared_data.get("college_name", "Your College"),
                risk_level=report.get("level", "Unknown"),
                dominant_factor=list(report.get("drivers", {}).keys())[0] if report.get("drivers") else "Multiple Factors"
            )
            
            if success:
                ModernMessagebox("Alert Sent", f"Early warning alert sent to: {', '.join(emails_to_send)}", "success")
            else:
                ModernMessagebox("Send Failed", "The alert could not be sent. Please check the email configuration.", "error")

        # --- LEFT PANEL (320px, Fixed Summary) ---
        left_panel = ctk.CTkFrame(top, width=320, fg_color=COLORS["sidebar"], corner_radius=0, border_width=0, border_color=COLORS["border"])
        left_panel.pack(side="left", fill="y")
        left_panel.pack_propagate(False)

        # Avatar Circle: 64px circle
        avatar_frame = ctk.CTkFrame(left_panel, width=64, height=64, corner_radius=32, fg_color=r_color)
        avatar_frame.pack(pady=(40, 10))
        avatar_frame.pack_propagate(False)
        
        name_str = data.get("name", "Student")
        name_parts = name_str.split()
        initials = "".join([p[0] for p in name_parts[:2]]).upper() if name_parts else "S"
        
        avatar_lbl = ctk.CTkLabel(avatar_frame, text=initials, font=("Roboto", 24, "bold"), text_color="black" if r_color in [COLORS["success"], COLORS["warning"]] else "white")
        avatar_lbl.pack(expand=True)

        ctk.CTkLabel(left_panel, text=data.get("name", "Student"), font=("Roboto", 16, "bold"), text_color="white", wraplength=280).pack(pady=(5, 2))
        ctk.CTkLabel(left_panel, text=f"ID: {data.get('id', 'N/A')}", font=FONTS["body"], text_color="gray").pack(pady=(0, 20))

        ctk.CTkFrame(left_panel, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(left_panel, text=f"{report['score']}", font=("Roboto", 48, "bold"), text_color=r_color).pack(pady=(10, 2))
        ctk.CTkLabel(left_panel, text=f"{report['level'].upper()} RISK", font=FONTS["h3"], text_color=r_color).pack(pady=(0, 2))
        ctk.CTkLabel(left_panel, text=f"Confidence: {report.get('confidence', 0)}%", font=FONTS["body"], text_color="gray").pack(pady=(0, 20))

        ctk.CTkFrame(left_panel, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=20, pady=10)

        info_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=10)
        
        def add_info_row(parent, label, value):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, font=FONTS["body"], text_color="gray", width=90, anchor="w").pack(side="left")
            val_lbl = ctk.CTkLabel(row, text=value, font=FONTS["body"], text_color="white", anchor="w", wraplength=170, justify="left")
            val_lbl.pack(side="left", fill="x", expand=True)
            return val_lbl
            
        add_info_row(info_frame, "Department:", branch_name)
        add_info_row(info_frame, "Year:", str(data.get("year", "N/A")))
        
        contact_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        contact_row.pack(fill="x", pady=5)
        ctk.CTkLabel(contact_row, text="Contact:", font=FONTS["body"], text_color="gray", width=90, anchor="w").pack(side="left")
        
        contact_txt = p_email if p_email != 'Not Provided' else str(data.get('phone', data.get('email', 'Not Provided')))
        ctk.CTkLabel(contact_row, text=contact_txt, font=FONTS["body"], text_color="white", anchor="w", wraplength=170, justify="left").pack(side="left", fill="x", expand=True)
        
        if is_email_missing:
            btn_add_contact = ctk.CTkButton(
                left_panel, 
                text="✎ Add Contact", 
                width=180,
                height=30,
                fg_color="transparent",
                border_width=1,
                border_color=COLORS["accent"],
                text_color=COLORS["accent"],
                font=FONTS["caption"],
                command=lambda: self._open_edit_contact_dialog(data)
            )
            btn_add_contact.pack(pady=10)

        btn_notify = ctk.CTkButton(
            left_panel,
            text=btn_notify_text,
            fg_color="#00E5FF" if has_email else "#2A2E3F",
            hover_color="#00B8D4" if has_email else "#2A2E3F",
            text_color="black" if has_email else "#7A849C",
            font=FONTS["h3"],
            height=40,
            state=btn_notify_state,
            command=send_email_alert
        )
        btn_notify.pack(side="bottom", fill="x", padx=20, pady=20)

        # --- RIGHT PANEL (Scrollable Content) ---
        scroll = ctk.CTkScrollableFrame(top, fg_color="transparent")
        scroll.pack(side="left", fill="both", expand=True, padx=20, pady=10)

        def make_section_title(parent, text):
            title_frame = ctk.CTkFrame(parent, fg_color="transparent")
            title_frame.pack(anchor="w", fill="x", pady=(20, 10))
            accent = ctk.CTkFrame(title_frame, width=4, height=18, fg_color="#00E5FF")
            accent.pack(side="left", padx=(5, 10))
            lbl = ctk.CTkLabel(title_frame, text=text, font=("Roboto", 12, "bold"), text_color="#00E5FF", anchor="w")
            lbl.pack(side="left")

        # 1. AI ASSESSMENT
        nlg_report = report.get('explanation', report.get('nlg_report', ''))
        if nlg_report:
            make_section_title(scroll, "AI ASSESSMENT")
            nlg_card = ctk.CTkFrame(scroll, fg_color="#1A1D2D", border_width=0, corner_radius=8)
            nlg_card.pack(fill="x", pady=5)
            ctk.CTkLabel(nlg_card, text=nlg_report, text_color="white", font=FONTS["body"], wraplength=700, justify="left").pack(anchor="w", padx=20, pady=15)

        # 2. ACADEMIC SNAPSHOT
        make_section_title(scroll, "ACADEMIC SNAPSHOT")
        pill_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        pill_frame.pack(fill="x", pady=5)

        def get_pill_color(key, value):
            try:
                val = float(value)
            except (ValueError, TypeError):
                return "gray"
            if key == "attendance":
                return COLORS["success"] if val >= 80 else (COLORS["warning"] if val >= 65 else COLORS["danger"])
            elif key == "cgpa":
                return COLORS["success"] if val >= 7.0 else (COLORS["warning"] if val >= 5.5 else COLORS["danger"])
            elif key == "backlogs":
                return COLORS["success"] if val == 0 else (COLORS["warning"] if val <= 2 else COLORS["danger"])
            elif key == "internal":
                return COLORS["success"] if val >= 70 else (COLORS["warning"] if val >= 50 else COLORS["danger"])
            elif key == "mid":
                return COLORS["success"] if val >= 65 else (COLORS["warning"] if val >= 50 else COLORS["danger"])
            elif key == "lab":
                return COLORS["success"] if val >= 75 else (COLORS["warning"] if val >= 55 else COLORS["danger"])
            elif key == "assignments":
                return COLORS["success"] if val >= 75 else (COLORS["warning"] if val >= 60 else COLORS["danger"])
            return "gray"

        attendance_val = data.get('avg_attendance', data.get('attendance_pct', 0))
        cgpa_val = data.get('cgpa', round(data.get('avg_marks', 0)/10.0, 2) if data.get('avg_marks') else 0)
        backlogs_val = data.get('backlogs', 0)
        internal_val = data.get('internal_marks', data.get('internal_percentage', data.get('internals', 72)))
        mid_val = data.get('mid_exam_score', data.get('mid_sem', 68))
        lab_val = data.get('lab_performance', data.get('lab_marks', 80))
        assignments_val = data.get('assignments_percentage', data.get('assignments', 85))

        metrics = [
            ("Attendance", "attendance", attendance_val, "%"),
            ("CGPA", "cgpa", cgpa_val, ""),
            ("Backlogs", "backlogs", backlogs_val, ""),
            ("Internal", "internal", internal_val, "%"),
            ("Mid Exam", "mid", mid_val, "%"),
            ("Lab", "lab", lab_val, "%"),
            ("Assignments", "assignments", assignments_val, "%")
        ]
        
        for label, key, val, unit in metrics:
            p_color = get_pill_color(key, val)
            val_str = f"{val}{unit}" if val is not None else "N/A"
            pill = ctk.CTkFrame(pill_frame, fg_color="#1A1D2D", corner_radius=8, border_width=0, height=60, width=95)
            pill.pack(side="left", padx=5, fill="both", expand=True)
            pill.pack_propagate(False)
            
            top_glow = ctk.CTkFrame(pill, height=3, fg_color=p_color, corner_radius=0)
            top_glow.pack(fill="x")
            
            inner = ctk.CTkFrame(pill, fg_color="transparent")
            inner.pack(fill="both", expand=True)
            ctk.CTkLabel(inner, text=label, font=FONTS["caption"], text_color="gray").pack(pady=(6, 0))
            ctk.CTkLabel(inner, text=val_str, font=FONTS["body"], text_color=p_color).pack(pady=(0, 6))

        # 3. FACTOR CONTRIBUTIONS
        make_section_title(scroll, "FACTOR CONTRIBUTIONS")
        contrib_card = ctk.CTkFrame(scroll, fg_color="#12141E", border_width=0, corner_radius=8)
        contrib_card.pack(fill="x", pady=5)
        
        c_data = report.get('contributions', {"Att": 30, "Marks": 50, "Bkl": 20})
        sorted_contribs = sorted(c_data.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        
        if sorted_contribs:
            max_val = max(abs(v) for k, v in sorted_contribs)
            max_val = max(max_val, 1)  # avoid division by zero
            
            for k, v in sorted_contribs:
                row = ctk.CTkFrame(contrib_card, fg_color="transparent")
                row.pack(fill="x", padx=20, pady=8)
                
                lbl = ctk.CTkLabel(row, text=k[:15], font=FONTS["body"], text_color="#a1a1aa", width=120, anchor="w")
                lbl.pack(side="left")
                
                val_abs = abs(v)
                pct = val_abs / max_val
                bar_color = COLORS["danger"] if val_abs > 15 else COLORS["accent"]
                
                track = ctk.CTkFrame(row, fg_color="#1A1D2D", height=8, corner_radius=4)
                track.pack(side="left", fill="x", expand=True, padx=10)
                track.pack_propagate(False)
                
                if pct > 0:
                    fill_bar = ctk.CTkFrame(track, fg_color=bar_color, height=8, corner_radius=4)
                    fill_bar.place(relx=0, rely=0, relwidth=pct, relheight=1)
                
                val_lbl = ctk.CTkLabel(row, text=f"{val_abs}%", font=FONTS["badge"], text_color="white", width=40, anchor="e")
                val_lbl.pack(side="left")
        else:
            ctk.CTkLabel(contrib_card, text="No contribution data available.", text_color="#555", font=FONTS["caption"]).pack(pady=20)

        # 4. TREND ANALYSIS
        make_section_title(scroll, "TREND ANALYSIS")
        trend_card = ctk.CTkFrame(scroll, fg_color="#12141E", border_width=0, corner_radius=8)
        trend_card.pack(fill="x", pady=5)
        
        # Gather semester history — use session cache directly by student_id
        sid_for_history = str(data.get('student_id', data.get('id', '')))
        from logic.session_cache import get_session_cache
        _cache = get_session_cache()
        semester_history = _cache.get_semester_history(sid_for_history) if _cache else []
        
        # Normalize history keys to standard format
        normalized_history = []
        for h in semester_history:
            normalized_history.append({
                'semester_number': h.get('semester_number', h.get('semester', 0)),
                'cgpa': float(h.get('cgpa_that_semester', h.get('cgpa', 0.0)) or 0.0),
                'attendance': float(h.get('attendance_that_semester', h.get('attendance', 0.0)) or 0.0),
                'backlogs': int(h.get('backlogs_that_semester', h.get('backlogs', 0)) or 0),
            })
        num_sems = len(normalized_history)
        
        if num_sems == 0:
            # No history recorded yet
            no_hist_frame = ctk.CTkFrame(trend_card, fg_color="#1A1D2D", corner_radius=8)
            no_hist_frame.pack(fill="x", padx=20, pady=20)
            ctk.CTkLabel(no_hist_frame, text="⚠️", font=("Arial", 24)).pack(pady=(15, 5))
            ctk.CTkLabel(no_hist_frame,
                text="No semester history is available for this student. Trend analysis will become available after the completion of their first semester.",
                text_color="#a1a1aa", font=FONTS["caption"], wraplength=500, justify="center"
            ).pack(padx=20, pady=(0, 15))
        elif num_sems == 1:
            # Semester 1 snapshot only
            sem = normalized_history[0]
            snap_frame = ctk.CTkFrame(trend_card, fg_color="#1A1D2D", corner_radius=8)
            snap_frame.pack(fill="x", padx=20, pady=20)
            ctk.CTkLabel(snap_frame, text="📊 Semester 1 Snapshot", font=("Arial", 14, "bold"), text_color="#00E5FF").pack(pady=(15, 5))
            ctk.CTkLabel(snap_frame,
                text=f"CGPA: {sem.get('cgpa', 0):.2f}   |   Attendance: {sem.get('attendance', 0):.1f}%   |   Backlogs: {sem.get('backlogs', 0)}\n"
                     "A minimum of two completed semesters is required for trend analysis.",
                text_color="#a1a1aa", font=FONTS["caption"], wraplength=500, justify="center"
            ).pack(padx=20, pady=(0, 15))
        else:
            # 2+ semesters — show real trend chart
            try:
                from logic.trend_engine import TrendAnalyzer
                t_info = TrendAnalyzer().analyze_history(normalized_history)
                t_info["history"] = normalized_history
                
                t_head = ctk.CTkFrame(trend_card, fg_color="transparent")
                t_head.pack(fill="x", padx=20, pady=(15, 5))
                t_status = t_info.get("trend_status", "Stable")
                t_color = COLORS["success"] if "Improv" in t_status else (COLORS["danger"] if "Declin" in t_status or "Critical" in t_status else "gray")
                ctk.CTkLabel(t_head, text=f"Trend: {t_status}", font=FONTS["body"], text_color=t_color).pack(side="left")
                ctk.CTkLabel(t_head, text=f"Score: {t_info.get('trend_score', 50)}/100", font=FONTS["body"], text_color="white").pack(side="right")
                
                from ui.trend_visuals import TrendVisuals
                TrendVisuals.create_trend_charts(trend_card, t_info)
            except Exception as _te:
                import logging as _tlog
                _tlog.getLogger(__name__).error(f"Trend chart render error: {_te}")
                ctk.CTkLabel(trend_card, text="Error rendering trend chart.", text_color="red").pack(pady=20)


        # 5. RECOMMENDED ACTIONS
        recs = report.get('recommendations', [])
        if recs:
            make_section_title(scroll, "RECOMMENDED ACTIONS")
            
            for i, r in enumerate(recs):
                p_color = COLORS['danger'] if r.get('priority', 1) == 1 else COLORS['warning'] if r.get('priority', 2) == 2 else COLORS['success']
                
                r_card = ctk.CTkFrame(scroll, fg_color="#1A1D2D", border_width=0, corner_radius=8, height=65)
                r_card.pack(fill="x", pady=4)
                r_card.pack_propagate(False)
                
                left_glow = ctk.CTkFrame(r_card, width=4, fg_color=p_color, corner_radius=0)
                left_glow.pack(side="left", fill="y")
                
                text_frame = ctk.CTkFrame(r_card, fg_color="transparent")
                text_frame.pack(side="left", fill="both", expand=True, pady=10, padx=16)
                
                header_f = ctk.CTkFrame(text_frame, fg_color="transparent")
                header_f.pack(fill="x")
                
                ctk.CTkLabel(header_f, text=r['action'], font=FONTS["body"], text_color="#e4e4e7", anchor="w").pack(side="left")
                
                badge_lbl = ctk.CTkLabel(header_f, text=f" Priority {r.get('priority', 1)} ", fg_color=p_color, text_color="white", corner_radius=4, font=("Inter", 9, "bold"), height=18)
                badge_lbl.pack(side="right")
                
                ctk.CTkLabel(text_frame, text=r.get('rationale', r.get('reason', '')), text_color="#a1a1aa", font=FONTS["caption"], wraplength=500, anchor="w", justify="left").pack(anchor="w", pady=(2, 0))

        # Embedded functions for Faculty Notes
        def load_history():
            for w in history_frame.winfo_children(): w.destroy()
            st_id = data.get("student_id", data.get("id", data.get("registration_no", "")))
            try:
                from logic.central_auth import CentralAuth
                notes = CentralAuth().get_notes_for_student(st_id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to load notes: {e}")
                notes = []
            if not notes:
                ctk.CTkLabel(history_frame, text="No previous notes for this student.", text_color="#555", font=FONTS["caption"]).pack(pady=10)
                return
            for n in notes:
                st = n.get('note_status', 'ACTIVE')
                if st == 'CRITICAL': c = "#FF5555"
                elif st == 'FOLLOW_UP': c = "yellow"
                elif st == 'ACTIVE': c = "#4ADE80"
                else: c = "cyan"
                
                # Chat-bubble style note
                inner_card = ctk.CTkFrame(history_frame, fg_color="#1A1D2D", border_width=0, corner_radius=16)
                inner_card.pack(fill="x", pady=6, padx=10)
                
                author = n.get('faculty_username', 'Unknown')
                dt = n.get('created_at')
                if isinstance(dt, str):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                    except:
                        pass
                dt_str = dt.strftime("%b %d, %Y %I:%M %p") if hasattr(dt, 'strftime') else "Unknown Date"
                
                head_f = ctk.CTkFrame(inner_card, fg_color="transparent")
                head_f.pack(fill="x", padx=16, pady=(12, 4))
                
                # Tiny dot indicator for status instead of huge border
                status_dot = ctk.CTkFrame(head_f, width=8, height=8, corner_radius=4, fg_color=c)
                status_dot.pack(side="left", pady=(0, 2), padx=(0, 8))
                
                ctk.CTkLabel(head_f, text=f"{author}", font=FONTS["h3"], text_color="#e4e4e7").pack(side="left")
                ctk.CTkLabel(head_f, text=f" • {dt_str}", font=FONTS["caption"], text_color="#aaa").pack(side="left", padx=5)
                
                badge = ctk.CTkLabel(head_f, text=f" {st} ", font=("Inter", 9, "bold"), text_color="#000", fg_color=c, corner_radius=6)
                badge.pack(side="right")
                
                ctk.CTkLabel(inner_card, text=n.get('note_text', ''), font=FONTS["body"], text_color="#d4d4d8", wraplength=480, justify="left").pack(anchor="w", padx=32, pady=(0, 16))

        def save_note():
            nt = self.txt_note.get("1.0", "end-1c").strip()
            if not nt: return
            fac_usr = self.controller.shared_data.get("username", "Unknown")
            st_id = data.get("student_id", data.get("id", data.get("registration_no", "")))
            dept = branch_name
            st = self.note_status_var.get()
            try:
                from logic.central_auth import CentralAuth
                CentralAuth().save_faculty_note(st_id, fac_usr, dept, nt, note_status=st)
                self.txt_note.delete("1.0", "end")
                ModernMessagebox("Saved", "Faculty note successfully added.", "success")
                load_history()
                
                self.note_stats = CentralAuth().get_student_note_stats(department=None)
                # Intentionally omitting self.filter_list() to prevent massive UI freezing. 
                # The note history in the drilldown already reloads via load_history().
            except Exception as e:
                import traceback
                traceback.print_exc()
                ModernMessagebox("Error", f"Failed to save note: {str(e)}", "error")

        # 6. NOTES HISTORY
        make_section_title(scroll, "NOTES HISTORY")
        history_card = ctk.CTkFrame(scroll, fg_color="#12141E", border_width=0, corner_radius=8)
        history_card.pack(fill="x", pady=5)
        
        history_frame = ctk.CTkScrollableFrame(history_card, height=180, fg_color="transparent")
        history_frame.pack(fill="x", padx=15, pady=15)
        load_history()
        
        # 7. ADD NEW NOTE
        make_section_title(scroll, "ADD NEW NOTE")
        new_note_card = ctk.CTkFrame(scroll, fg_color="#12141E", border_width=0, corner_radius=8)
        new_note_card.pack(fill="x", pady=5)
        
        controls_f = ctk.CTkFrame(new_note_card, fg_color="transparent")
        controls_f.pack(fill="x", padx=15, pady=(15, 10))
        ctk.CTkLabel(controls_f, text="Note Status:", font=FONTS["caption"], text_color="#a1a1aa").pack(side="left", padx=(0, 10))
        self.note_status_var = ctk.StringVar(value="ACTIVE")
        self.note_status_combo = ctk.CTkComboBox(controls_f, values=["ACTIVE", "FOLLOW_UP", "CRITICAL", "CLOSED"], variable=self.note_status_var, width=130, fg_color="#1e1e24", border_color="#3f3f46", button_color="#3f3f46", dropdown_fg_color="#12141E", dropdown_text_color="white", dropdown_hover_color="#1A1D2D", text_color="white")
        self.note_status_combo.pack(side="left")
        
        input_wrapper = ctk.CTkFrame(new_note_card, fg_color="#1A1D2D", corner_radius=16, border_width=0)
        input_wrapper.pack(fill="x", padx=15, pady=(0, 15))
        
        self.txt_note = ctk.CTkTextbox(input_wrapper, height=50, fg_color="transparent", text_color="white", border_width=0, font=FONTS["body"])
        self.txt_note.pack(side="left", fill="both", expand=True, padx=(15, 5), pady=10)
        
        send_btn = ctk.CTkButton(input_wrapper, text="➤", width=40, height=40, corner_radius=20, font=FONTS["h2"], fg_color=COLORS["accent"], text_color="black", hover_color="#00E5FF", command=save_note)
        send_btn.pack(side="right", padx=10, pady=10)

        # 8. CLOSE DIAGNOSIS
        close_btn = ctk.CTkButton(scroll, text="CLOSE DIAGNOSIS", fg_color="#3f3f46", hover_color="#52525b", text_color="white", corner_radius=8, font=FONTS["body"], command=top.destroy, height=40)
        close_btn.pack(fill="x", pady=(20, 20))

    def _open_edit_contact_dialog(self, data):
        diag = ctk.CTkToplevel(self)
        diag.geometry("400x300")
        diag.title("Update Parent Contact")
        diag.attributes("-topmost", True)
        diag.configure(fg_color="#111")
        
        ctk.CTkLabel(diag, text="Update Contact Info", font=FONTS["h2"]).pack(pady=20)
        
        ctk.CTkLabel(diag, text="Parent Email:").pack()
        email_ent = ctk.CTkEntry(diag, width=250)
        email_ent.pack(pady=5)
        
        ctk.CTkLabel(diag, text="Parent Phone:").pack()
        phone_ent = ctk.CTkEntry(diag, width=250)
        phone_ent.pack(pady=5)
        
        def save():
            new_email = email_ent.get().strip()
            new_phone = phone_ent.get().strip()
            import tkinter.messagebox as mb
            mb.showinfo("Success", "Contact info updated in local view. (Requires ERP write access to persist)")
            data['parent_email'] = new_email
            data['parent_phone'] = new_phone
            diag.destroy()
            
        ctk.CTkButton(diag, text="Save", fg_color=COLORS["success"], command=save).pack(pady=20)

    def _open_notify_parent_dialog(self, data, report):
        diag = ctk.CTkToplevel(self)
        diag.geometry("500x600")
        diag.title("AcaDesk - Parent Notification (Email)")
        diag.attributes("-topmost", True)
        diag.configure(fg_color="#111")
        
        ctk.CTkLabel(diag, text="DISPATCH ALERT", font=FONTS["h2"], text_color=COLORS["accent"]).pack(pady=(20, 5))
        
        p_email = data.get('parent_email', 'Not Provided')
        p_phone = data.get('parent_phone', 'Not Provided')
        
        info_frame = ctk.CTkFrame(diag, fg_color=COLORS["card"])
        info_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(info_frame, text=f"Student: {data['name']}", font=FONTS["h3"]).pack(anchor="w", padx=15, pady=(15, 2))
        ctk.CTkLabel(info_frame, text=f"Parent Email: {p_email}", text_color="gray").pack(anchor="w", padx=15, pady=2)
        ctk.CTkLabel(info_frame, text=f"Parent Phone: {p_phone}", text_color="gray").pack(anchor="w", padx=15, pady=(2, 15))
        
        ctk.CTkLabel(diag, text="Message Body:", anchor="w").pack(fill="x", padx=20, pady=(10, 0))
        msg_box = ctk.CTkTextbox(diag, height=150, fg_color=COLORS["input_bg"])
        msg_box.pack(fill="x", padx=20, pady=5)
        
        default_msg = (
            f"Dear Parent,\n\n"
            f"This is an automated alert from AcaDesk regarding your ward, {data['name']}. "
            f"Our AI system has flagged a {report['level']} risk in their academic progress.\n\n"
            f"Attendance: {data.get('avg_attendance', 'N/A')}%\n"
            f"Please contact the HOD/Faculty immediately."
        )
        msg_box.insert("0.0", default_msg)
        
        cred_frame = ctk.CTkFrame(diag, fg_color="transparent")
        cred_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(cred_frame, text="Gmail App Password:", font=FONTS["body"]).pack(side="left", padx=5)
        pass_entry = ctk.CTkEntry(cred_frame, show="*", width=200, placeholder_text="16-letter App Password")
        pass_entry.pack(side="left", padx=5)
        
        def send_email_action():
            import tkinter.messagebox as mb
            from logic.email_sender import send_email_notification
            
            pwd = pass_entry.get().strip()
            if not pwd:
                mb.showerror("Error", "Please enter your Gmail App Password to send real emails.")
                return
                
            if p_email == 'Not Provided':
                mb.showerror("Error", "No parent email found on record!")
                return
                
            body = msg_box.get("0.0", "end").strip()
            success, msg = send_email_notification(p_email, f"AcaDesk Alert for {data['name']}", body, pwd)
            
            if success:
                mb.showinfo("Success", msg)
                diag.destroy()
            else:
                mb.showerror("Failed", msg)
                
        btn_send = ctk.CTkButton(diag, text="Send Email", fg_color=COLORS["success"], font=FONTS["h3"], height=40, command=send_email_action)
        btn_send.pack(pady=20)
        
        close_btn = ctk.CTkButton(scroll, text="CLOSE DIAGNOSIS", command=top.destroy)
        close_btn.pack(pady=10)

    def export_report(self):
        try:
            students = self.db.get_students(self.current_branch, self.current_year)
            fname = f"Risk_Report_{int(time.time())}.csv"
            pd.DataFrame(students).to_csv(fname, index=False)
            ModernMessagebox("Success", f"Saved: {fname}", "success")
        except Exception as e:
            ModernMessagebox("Error", str(e), "error")

    def add_line(self, p, l, v, color="white"):
        line_f = ctk.CTkFrame(p, fg_color="transparent")
        line_f.pack(fill="x", padx=10)
        
        lbl = ctk.CTkLabel(line_f, text=l, text_color="gray", width=120, anchor="w")
        lbl.pack(side="left")
        
        val = ctk.CTkLabel(line_f, text=v, text_color=color, font=FONTS["caption"])
        val.pack(side="left")
        
    def _profile_badge(self, parent, label_text, value_text):
        badge_frame = ctk.CTkFrame(parent, fg_color="transparent")
        badge_frame.pack(side="left", fill="x", expand=True, padx=10, pady=15)
        
        lbl = ctk.CTkLabel(badge_frame, text=label_text, text_color="gray", font=FONTS["caption"])
        lbl.pack(anchor="center")
        
        val = ctk.CTkLabel(badge_frame, text=value_text, text_color="white", font=FONTS["h3"])
        val.pack(anchor="center")

