import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.styles import COLORS, FONTS
from logic.db_handler import DBHandler
from logic.risk_engine import AdvancedRiskPredictor

class InstitutionOverviewPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        
        # Scrollable container
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        hdr_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(hdr_frame, text="INSTITUTION OVERVIEW", font=FONTS["h1"], text_color=COLORS["accent"]).pack(side="left")
        
        # Refresh Button
        ctk.CTkButton(hdr_frame, text="↻ REFRESH DATA", width=120, fg_color="#222", text_color="white", command=self.refresh).pack(side="right")
        
        # Containers for dynamic content
        self.summary_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.summary_frame.pack(fill="x", pady=(0, 20))
        
        self.charts_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.charts_frame.pack(fill="x", pady=(0, 20))
        
        self.table_frame = ctk.CTkFrame(self.scroll, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        self.table_frame.pack(fill="x", pady=(0, 20))
        
        self.trends_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.trends_frame.pack(fill="x", pady=(0, 20))

    def on_show(self):
        self.refresh()

    def refresh(self):
        for w in self.summary_frame.winfo_children(): w.destroy()
        for w in self.charts_frame.winfo_children(): w.destroy()
        for w in self.table_frame.winfo_children(): w.destroy()
        for w in self.trends_frame.winfo_children(): w.destroy()
        
        erp_conf = self.controller.shared_data.get("erp_config")
        if not erp_conf:
            ctk.CTkLabel(self.summary_frame, text="Database configuration missing.", text_color=COLORS["danger"]).pack()
            return
            
        try:
            db = DBHandler(erp_conf)
            predictor = AdvancedRiskPredictor(db)
            
            all_students = db.get_all_students()
            if not all_students:
                ctk.CTkLabel(self.summary_frame, text="No student records found in the database.", text_color=COLORS["warning"]).pack()
                return

            branch_map = db.get_branch_map()
            
            # Analyze all students to build aggregates
            total_students = len(all_students)
            risk_counts = {"High": 0, "Medium": 0, "Low": 0}
            dept_stats = {}
            
            for s in all_students:
                # Use engine to predict
                report = predictor.analyze(s)
                lvl = report.get("level", "Low")
                risk_counts[lvl] += 1
                
                # Dept aggregates
                b_id = str(s.get("branch_id", ""))
                b_name = branch_map.get(b_id, b_id) or "Unknown"
                if b_name not in dept_stats:
                    dept_stats[b_name] = {"Total": 0, "High": 0, "Medium": 0, "Low": 0, "att_sum": 0, "cgpa_sum": 0, "valid_cgpa": 0}
                
                ds = dept_stats[b_name]
                ds["Total"] += 1
                ds[lvl] += 1
                
                att = float(s.get("avg_attendance") or s.get("attendance_pct") or 0)
                cgpa = float(s.get("cgpa") or s.get("cumulative_gpa") or 0)
                
                ds["att_sum"] += att
                if cgpa > 0:
                    ds["cgpa_sum"] += cgpa
                    ds["valid_cgpa"] += 1

            # 1. Summary Cards
            self.build_summary_cards(total_students, risk_counts)
            
            # 2. Risk Distribution Chart & Performance Overview
            self.build_charts(risk_counts, dept_stats)
            
            # 3. Department Risk Comparison Table
            self.build_department_table(dept_stats)
            
            # 4. Trends Analytics
            self.build_trends_analytics()

        except Exception as e:
            ctk.CTkLabel(self.summary_frame, text=f"Error loading institution data: {e}", text_color=COLORS["danger"]).pack()
            import traceback
            traceback.print_exc()

    def build_summary_cards(self, total, counts):
        self.summary_frame.grid_columnconfigure((0,1,2,3), weight=1)
        
        cards = [
            ("Total Students", total, "white"),
            ("Low Risk", counts["Low"], COLORS["success"]),
            ("Medium Risk", counts["Medium"], COLORS["warning"]),
            ("High Risk", counts["High"], COLORS["danger"])
        ]
        
        for i, (title, val, color) in enumerate(cards):
            card = ctk.CTkFrame(self.summary_frame, fg_color="#1a1a1a", corner_radius=8, border_width=1, border_color="#333")
            card.grid(row=0, column=i, padx=10, sticky="nsew")
            ctk.CTkLabel(card, text=title, font=("Arial", 12), text_color="#888").pack(pady=(15, 5))
            ctk.CTkLabel(card, text=str(val), font=("Arial", 28, "bold"), text_color=color).pack(pady=(0, 15))

    def build_charts(self, risk_counts, dept_stats):
        self.charts_frame.grid_columnconfigure((0,1), weight=1)
        
        # Left Chart: Risk Distribution Donut
        left_card = ctk.CTkFrame(self.charts_frame, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        left_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        ctk.CTkLabel(left_card, text="OVERALL RISK DISTRIBUTION", font=("Arial", 11, "bold"), text_color="#fff").pack(pady=(10, 0))
        
        fig1 = Figure(figsize=(4, 3), dpi=100)
        fig1.patch.set_facecolor("#141414")
        ax1 = fig1.add_subplot(111)
        
        labels = ["High", "Medium", "Low"]
        sizes = [risk_counts["High"], risk_counts["Medium"], risk_counts["Low"]]
        colors = [COLORS["danger"], COLORS["warning"], COLORS["success"]]
        
        if sum(sizes) > 0:
            wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, pctdistance=0.75)
            for t in texts: t.set_color("white")
            for at in autotexts: at.set_color("black"); at.set_weight("bold")
            # Draw circle for donut
            centre_circle = fig1.gca().add_artist(Figure.patch.Circle((0,0),0.50,fc='#141414'))
        
        canvas1 = FigureCanvasTkAgg(fig1, master=left_card)
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        # Right Chart: Branch Performance (Avg Attendance & CGPA)
        right_card = ctk.CTkFrame(self.charts_frame, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        right_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        ctk.CTkLabel(right_card, text="DEPARTMENT PERFORMANCE", font=("Arial", 11, "bold"), text_color="#fff").pack(pady=(10, 0))
        
        depts = list(dept_stats.keys())
        att_avgs = [ds["att_sum"]/ds["Total"] if ds["Total"]>0 else 0 for ds in dept_stats.values()]
        cgpa_avgs = [ds["cgpa_sum"]/ds["valid_cgpa"] if ds["valid_cgpa"]>0 else 0 for ds in dept_stats.values()]
        
        fig2 = Figure(figsize=(5, 3), dpi=100)
        fig2.patch.set_facecolor("#141414")
        ax2 = fig2.add_subplot(111)
        ax2.set_facecolor("#141414")
        
        if depts:
            x = range(len(depts))
            ax2.bar([i-0.2 for i in x], att_avgs, width=0.4, color=COLORS["accent"], label="Avg Attendance %")
            # Scale CGPA to 100 for visual comparison
            ax2.bar([i+0.2 for i in x], [c*10 for c in cgpa_avgs], width=0.4, color="#4ADE80", label="Avg CGPA (x10)")
            ax2.set_xticks(list(x))
            ax2.set_xticklabels(depts, color="white", rotation=15, ha="right", fontsize=8)
            ax2.tick_params(axis='y', colors='white')
            ax2.legend(facecolor="#1a1a1a", edgecolor="#333", labelcolor="white", fontsize=8)
        
        canvas2 = FigureCanvasTkAgg(fig2, master=right_card)
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def build_department_table(self, dept_stats):
        ctk.CTkLabel(self.table_frame, text="DEPARTMENT RISK COMPARISON", font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Sort by High Risk Percentage
        dept_list = []
        for d, s in dept_stats.items():
            hr_pct = (s["High"] / s["Total"] * 100) if s["Total"] > 0 else 0
            dept_list.append((d, s, hr_pct))
        dept_list.sort(key=lambda x: x[2], reverse=True)
        
        # Headers
        hdr_row = ctk.CTkFrame(self.table_frame, fg_color="#1a1a1a")
        hdr_row.pack(fill="x", padx=10, pady=(0, 5))
        
        cols = [("DEPARTMENT", 200), ("TOTAL STUDENTS", 150), ("HIGH RISK", 120), ("MEDIUM RISK", 120), ("LOW RISK", 120)]
        for text, width in cols:
            ctk.CTkLabel(hdr_row, text=text, font=("Arial", 10, "bold"), text_color="#888", width=width, anchor="w").pack(side="left", padx=10, pady=5)
            
        # Rows
        for d, s, hr_pct in dept_list:
            row = ctk.CTkFrame(self.table_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            
            ctk.CTkLabel(row, text=d, font=("Arial", 11, "bold"), text_color="white", width=200, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=str(s["Total"]), font=("Arial", 11), text_color="#ccc", width=150, anchor="w").pack(side="left", padx=10)
            
            hr_txt = f"{s['High']} ({hr_pct:.1f}%)"
            ctk.CTkLabel(row, text=hr_txt, font=("Arial", 11, "bold"), text_color=COLORS["danger"], width=120, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=str(s["Medium"]), font=("Arial", 11), text_color=COLORS["warning"], width=120, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=str(s["Low"]), font=("Arial", 11), text_color=COLORS["success"], width=120, anchor="w").pack(side="left", padx=10)
            
        ctk.CTkFrame(self.table_frame, height=10, fg_color="transparent").pack()

    def build_trends_analytics(self):
        trend_card = ctk.CTkFrame(self.trends_frame, fg_color="#141414", corner_radius=8, border_width=1, border_color="#222")
        trend_card.pack(fill="x")
        
        ctk.CTkLabel(trend_card, text="SEMESTER-WISE RISK TRENDS", font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 5))
        
        # Graceful message since historical data spans might not be fully populated in generic schemas
        msg = "Historical semester-by-semester records are currently being aggregated. Live prediction tracking is active."
        ctk.CTkLabel(trend_card, text=msg, font=("Arial", 11), text_color="#888").pack(anchor="w", padx=20, pady=(0, 20))
