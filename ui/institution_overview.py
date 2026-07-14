import customtkinter as ctk
import threading
from ui.styles import COLORS, FONTS
from logic.db_handler import DBHandler
from logic.risk_engine import AdvancedRiskPredictor

PREMIUM_BG = "#090A0F"
PREMIUM_CARD = "#12141E"
PREMIUM_HOVER = "#1A1D2D"

class InstitutionOverviewPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=PREMIUM_BG)
        self.controller = controller
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        hdr_frame = ctk.CTkFrame(self.scroll, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        hdr_frame.pack(fill="x", pady=(0, 20))
        
        self.lbl_title = ctk.CTkLabel(hdr_frame, text="🏦  Institutional Risk Intelligence", font=("Outfit", 24, "bold"), text_color="#00E5FF")
        self.lbl_title.pack(side="left", padx=20, pady=15)
        
        self.btn_refresh = ctk.CTkButton(hdr_frame, text="📸 Snapshot Data", width=130, fg_color="#1A1D2D", border_width=1, border_color="#2A2E3F", text_color="white", hover_color="#2A2E3F", corner_radius=6, font=("Inter", 13, "bold"), command=self.refresh)
        self.btn_refresh.pack(side="right", padx=20, pady=15)
        
        self.main_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)
        
        self._is_loading = False

    def on_show(self):
        self.refresh()

    def refresh(self):
        if self._is_loading: return
        self._is_loading = True
        self.btn_refresh.configure(state="disabled", text="↻ LOADING...")
        
        user_type = self.controller.shared_data.get("user_type")
        if user_type == "HOD":
            self.lbl_title.configure(text="🏦  Department Risk Intelligence")
        else:
            self.lbl_title.configure(text="🏦  Institutional Risk Intelligence")
            
        for w in self.main_frame.winfo_children(): w.destroy()
        
        loading_lbl = ctk.CTkLabel(self.main_frame, text="Analyzing institution data... Please wait.", font=("Arial", 16, "bold"), text_color="#555")
        loading_lbl.pack(pady=50)
        
        threading.Thread(target=self._fetch_data_thread, daemon=True).start()

    def _fetch_data_thread(self):
        try:
            from logic.session_cache import get_dashboard_summary
            summary_data = get_dashboard_summary()
            
            user_type = self.controller.shared_data.get("user_type")
            assigned_dept = self.controller.shared_data.get("assigned_department")
            target_branch = str(assigned_dept) if user_type == "HOD" else None
            
            total_students = 0
            overall_risk_counts = {"High": 0, "Medium": 0, "Low": 0, "Pending": 0}
            dept_stats = {}
            
            for row in summary_data:
                bid = str(row["branch_id"])
                if target_branch and bid != target_branch:
                    continue
                    
                bname = row["branch_name"]
                if bname not in dept_stats:
                    dept_stats[bname] = {
                        "Total": 0, "High": 0, "Medium": 0, "Low": 0, "Pending": 0,
                        "health_score": 0, "avg_attendance": 0, "avg_cgpa": 0,
                        "_att_sum": 0, "_cgpa_sum": 0
                    }
                
                lvl = row["risk_level"]
                cnt = row["count"]
                
                total_students += cnt
                if lvl in overall_risk_counts: overall_risk_counts[lvl] += cnt
                if lvl in dept_stats[bname]: dept_stats[bname][lvl] += cnt
                dept_stats[bname]["Total"] += cnt
                
                dept_stats[bname]["_att_sum"] += (row["avg_att"] or 0) * cnt
                dept_stats[bname]["_cgpa_sum"] += (row["avg_cgpa"] or 0) * cnt

            if total_students == 0:
                self.after(0, self._render_error, "No student records found in the session cache.", COLORS.get("warning", "#FF9100"))
                return
                
            for bname, stats in dept_stats.items():
                t = stats["Total"]
                if t > 0:
                    stats["avg_attendance"] = stats["_att_sum"] / t
                    stats["avg_cgpa"] = stats["_cgpa_sum"] / t
                    h = stats["High"]
                    m = stats["Medium"]
                    stats["health_score"] = max(0, min(100, 100 - ((h * 1.0) + (m * 0.5)) / t * 100))
                    
            ranked = sorted(dept_stats.keys(), key=lambda k: dept_stats[k]["health_score"], reverse=True)
            best_branch = ranked[0] if ranked else "N/A"
            worst_branch = ranked[-1] if ranked else "N/A"

            data = {
                "total_students": total_students,
                "risk_counts": overall_risk_counts,
                "dept_stats": dept_stats,
                "worst_branch": worst_branch,
                "best_branch": best_branch
            }
                    
            self.after(0, self._render_ui, data)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.after(0, self._render_error, f"Error loading institution data: {e}")

    def _render_error(self, msg, color=COLORS.get("danger", "#FF5555")):
        self._is_loading = False
        self.btn_refresh.configure(state="normal", text="📸 Snapshot Data")
        for w in self.main_frame.winfo_children(): w.destroy()
        ctk.CTkLabel(self.main_frame, text=msg, font=("Arial", 14), text_color=color).pack(pady=20)

    def _render_ui(self, data):
        self._is_loading = False
        self.btn_refresh.configure(state="normal", text="📸 Snapshot Data")
        for w in self.main_frame.winfo_children(): w.destroy()
        
        # 1. Summary Cards
        summary_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        summary_frame.pack(fill="x", pady=(0, 15))
        self.build_summary_cards(summary_frame, data["total_students"], data["risk_counts"])
        
        # 2. Highlights
        user_type = self.controller.shared_data.get("user_type")
        if user_type != "HOD":
            highlights_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            highlights_frame.pack(fill="x", pady=(0, 20))
            self.build_highlights_bar(highlights_frame, data["best_branch"], data["worst_branch"], data["dept_stats"])
        
        # 3. Two Panel Layout (Leaderboard + Risk Chart)
        panels_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        panels_frame.pack(fill="both", expand=True)
        panels_frame.grid_columnconfigure((0, 1), weight=1, uniform="cols")
        
        self.build_leaderboard(panels_frame, data["dept_stats"])
        self.build_risk_chart(panels_frame, data["dept_stats"])

    def _apply_hover_fx(self, widget, normal_color, hover_color):
        def on_enter(e): widget.configure(fg_color=hover_color)
        def on_leave(e): widget.configure(fg_color=normal_color)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        for child in widget.winfo_children():
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)

    def build_summary_cards(self, parent, total, counts):
        parent.grid_columnconfigure((0,1,2,3), weight=1)
        
        cards = [
            ("TOTAL STUDENTS", total, "white"),
            ("LOW RISK", counts["Low"], COLORS.get("success", "#00C853")),
            ("MEDIUM RISK", counts["Medium"], COLORS.get("warning", "#FF9100")),
            ("HIGH RISK", counts["High"], COLORS.get("danger", "#FF5555"))
        ]
        
        for i, (title, val, color) in enumerate(cards):
            # Outer frame acts as a subtle shadow/border
            outer = ctk.CTkFrame(parent, fg_color="#181a26", corner_radius=14)
            outer.grid(row=0, column=i, padx=8, sticky="nsew")
            
            card = ctk.CTkFrame(outer, fg_color=PREMIUM_CARD, corner_radius=12)
            card.pack(fill="both", expand=True, padx=1, pady=1)
            
            self._apply_hover_fx(card, PREMIUM_CARD, PREMIUM_HOVER)
            
            strip = ctk.CTkFrame(card, width=4, fg_color=color, corner_radius=0)
            strip.pack(side="left", fill="y", pady=10)
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(side="left", fill="both", expand=True, padx=20, pady=10)
            
            ctk.CTkLabel(content, text=title, font=("Inter", 11, "bold"), text_color="#7A849C").pack(anchor="w")
            ctk.CTkLabel(content, text=str(val), font=("Outfit", 26, "bold"), text_color=color).pack(anchor="w", pady=(2, 0))

    def build_highlights_bar(self, parent, best, worst, dept_stats):
        parent.grid_columnconfigure((0,1), weight=1)
        
        best_score = dept_stats[best]["health_score"] if best in dept_stats else 0
        worst_stats = dept_stats.get(worst)
        worst_pct = (worst_stats["High"] / worst_stats["Total"] * 100) if worst_stats and worst_stats["Total"] > 0 else 0
        
        hls = [
            ("🏆 HEALTHIEST DEPARTMENT", f"{best}  (Score: {best_score:.1f})", COLORS.get("success", "#00C853"), 0),
            ("⚠️ MOST AT-RISK DEPARTMENT", f"{worst}  ({worst_pct:.1f}% High Risk)", COLORS.get("danger", "#FF5555"), 1)
        ]
        
        for title, val, color, col in hls:
            outer = ctk.CTkFrame(parent, fg_color="#181a26", corner_radius=14)
            outer.grid(row=0, column=col, padx=8, sticky="nsew")
            
            card = ctk.CTkFrame(outer, fg_color=PREMIUM_CARD, corner_radius=12)
            card.pack(fill="both", expand=True, padx=1, pady=1)
            self._apply_hover_fx(card, PREMIUM_CARD, PREMIUM_HOVER)
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=25, pady=12)
            
            ctk.CTkLabel(content, text=title, font=("Inter", 11, "bold"), text_color=color).pack(anchor="w")
            ctk.CTkLabel(content, text=val, font=("Outfit", 18, "bold"), text_color="white").pack(anchor="w", pady=(2, 0))

    def build_leaderboard(self, parent, dept_stats):
        outer = ctk.CTkFrame(parent, fg_color="#181a26", corner_radius=14)
        outer.grid(row=0, column=0, sticky="nsew", padx=(8, 10))
        
        left_panel = ctk.CTkFrame(outer, fg_color=PREMIUM_CARD, corner_radius=12)
        left_panel.pack(fill="both", expand=True, padx=1, pady=1)
        
        ctk.CTkLabel(left_panel, text="Department Health Leaderboard", font=("Outfit", 18, "bold"), text_color="white").pack(anchor="w", padx=25, pady=(25, 15))
        
        dept_list = [(d, s) for d, s in dept_stats.items()]
        dept_list.sort(key=lambda x: x[1]["health_score"], reverse=True)
        
        lb_scroll = ctk.CTkFrame(left_panel, fg_color="transparent")
        lb_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))
        
        for i, (d, s) in enumerate(dept_list):
            row = ctk.CTkFrame(lb_scroll, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=12)
            self._apply_hover_fx(row, "transparent", "#1A1D2D")
            
            h_score = s['health_score']
            prog_color = COLORS.get("success", "#00C853") if h_score > 70 else (COLORS.get("warning", "#FF9100") if h_score > 40 else COLORS.get("danger", "#FF5555"))
            
            rank_text = f"#{i+1}  {d}"
            ctk.CTkLabel(row, text=rank_text, font=("Inter", 15, "bold"), text_color="#00E5FF", width=100, anchor="w").pack(side="left")
            
            # Dynamic Health Bar
            prog = ctk.CTkProgressBar(row, width=150, height=8, corner_radius=4, progress_color=prog_color, fg_color="#2A2E3F")
            prog.pack(side="left", padx=(15, 20))
            prog.set(h_score / 100.0)
            
            score_text = f"{int(h_score)}/100"
            ctk.CTkLabel(row, text=score_text, font=("Inter", 15, "bold"), text_color=prog_color).pack(side="right")

    def build_risk_chart(self, parent, dept_stats):
        outer = ctk.CTkFrame(parent, fg_color="#181a26", corner_radius=14)
        outer.grid(row=0, column=1, sticky="nsew", padx=(10, 8))
        
        right_panel = ctk.CTkFrame(outer, fg_color=PREMIUM_CARD, corner_radius=12)
        right_panel.pack(fill="both", expand=True, padx=1, pady=1)
        
        ctk.CTkLabel(right_panel, text="Department Risk Distribution", font=("Outfit", 18, "bold"), text_color="white").pack(anchor="w", padx=25, pady=(25, 15))
        
        # Legend
        leg_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        leg_frame.pack(fill="x", padx=25, pady=(0, 20))
        for text, col in [("Low", COLORS.get("success", "#00C853")), ("Medium", COLORS.get("warning", "#FF9100")), ("High", COLORS.get("danger", "#FF5555"))]:
            f = ctk.CTkFrame(leg_frame, fg_color="transparent")
            f.pack(side="left", padx=(0, 20))
            ctk.CTkFrame(f, width=12, height=12, corner_radius=6, fg_color=col).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(f, text=text, font=("Inter", 12), text_color="#aaa").pack(side="left")
        
        dept_list = [(d, s) for d, s in dept_stats.items()]
        # Sort by total students for visual appeal
        dept_list.sort(key=lambda x: x[1]["Total"], reverse=True)
        max_students = max([s["Total"] for _, s in dept_list]) if dept_list else 1
        
        chart_scroll = ctk.CTkFrame(right_panel, fg_color="transparent")
        chart_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))
        
        # Native CTk Stacked Bar Generation
        BAR_CONTAINER_WIDTH = 380
        for d, s in dept_list:
            row = ctk.CTkFrame(chart_scroll, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=12)
            self._apply_hover_fx(row, "transparent", "#1A1D2D")
            
            ctk.CTkLabel(row, text=d, font=("Inter", 14, "bold"), text_color="#00E5FF", width=70, anchor="e").pack(side="left", padx=(0, 15))
            
            bar_container = ctk.CTkFrame(row, fg_color="transparent", width=BAR_CONTAINER_WIDTH, height=18)
            bar_container.pack(side="left", fill="x", expand=True)
            bar_container.pack_propagate(False)
            
            # Ensure bar scales gracefully with a little padding room
            scale = (BAR_CONTAINER_WIDTH - 10) / max_students if max_students > 0 else 0
            
            w_green = int(s["Low"] * scale)
            w_orange = int(s["Medium"] * scale)
            w_red = int(s["High"] * scale)
            
            # To simulate rounded inner corners beautifully, we just pack frames side by side.
            if w_green > 0:
                ctk.CTkFrame(bar_container, fg_color=COLORS.get("success", "#00C853"), width=w_green, height=18, corner_radius=4).pack(side="left", padx=(0, 2))
            if w_orange > 0:
                ctk.CTkFrame(bar_container, fg_color=COLORS.get("warning", "#FF9100"), width=w_orange, height=18, corner_radius=4).pack(side="left", padx=(0, 2))
            if w_red > 0:
                ctk.CTkFrame(bar_container, fg_color=COLORS.get("danger", "#FF5555"), width=w_red, height=18, corner_radius=4).pack(side="left")
            
            # Subtle total label
            ctk.CTkLabel(row, text=str(s["Total"]), font=("Inter", 12, "bold"), text_color="#7A849C").pack(side="right", padx=(10, 0))
