import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from ui.styles import COLORS, FONTS
from logic.institutional_analytics import InstitutionalAnalytics
from logic.predictor import RiskPredictor

class OverviewPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=10)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        self.lbl_title = ctk.CTkLabel(
            header, 
            text="🏛️ Institutional Risk Intelligence", 
            font=FONTS["h2"], 
            text_color="white"
        )
        self.lbl_title.pack(side="left", padx=20, pady=15)
        
        self.btn_snapshot = ctk.CTkButton(header, text="📸 Snapshot Data", font=("Arial", 12, "bold"), fg_color="#1e3a5f", width=120, command=self.take_snapshot)
        self.btn_snapshot.pack(side="right", padx=20, pady=15)
        
        # Content Scroll
        self.content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Containers that will be built on refresh
        self.kpi_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.kpi_frame.pack(fill="x", padx=10, pady=10)
        
        self.insight_frame = ctk.CTkFrame(self.content, fg_color=COLORS["card"], corner_radius=10)
        self.insight_frame.pack(fill="x", padx=10, pady=10)
        
        self.visual_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.visual_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.lbl_insight = ctk.CTkLabel(self.insight_frame, text="Loading insights...", wraplength=800, justify="left", font=("Arial", 14), text_color="#E0E0E0")
        self.lbl_insight.pack(padx=20, pady=20, anchor="w")

    def refresh(self):
        # Clean up old KPIs and charts
        for w in self.kpi_frame.winfo_children(): w.destroy()
        for w in self.visual_frame.winfo_children(): w.destroy()
        self.lbl_insight.configure(text="Crunching data across all departments... Please wait.")
        self.update_idletasks()
        
        try:
            # We access the DB from the AnalyticsPanel which initializes it
            dash = self.master
            analytics_panel = dash.analytics
            
            # Ensure analytics panel has initialized the DB
            if not getattr(analytics_panel, 'db', None):
                conf = self.controller.shared_data.get("erp_config")
                if conf:
                    from logic.db_handler import DBHandler
                    analytics_panel.db = DBHandler(conf)
                    analytics_panel.translator = analytics_panel.db
                else:
                    self.lbl_insight.configure(text="No Database Connection Available. Please configure ERP first.")
                    return
                
            if not getattr(analytics_panel, 'db', None):
                self.lbl_insight.configure(text="No Database Connection Available. Please configure ERP first.")
                return
                
            # translator.map is {id: name}, but compute_dashboard_data expects {name: id}
            flipped_map = {name: str(bid) for bid, name in analytics_panel.translator.map.items()}
            
            user_type = self.controller.shared_data.get("user_type")
            target_branch = None
            if user_type == "HOD":
                target_branch = self.controller.shared_data.get("assigned_branch")
                self.lbl_insight.configure(text="Crunching department data... Please wait.")
            
            # Run the heavy analytics computation in a background thread
            import threading
            
            def run_analysis():
                print("run_analysis: started")
                try:
                    from logic.db_handler import DBHandler
                    local_db = DBHandler(self.controller.shared_data.get("erp_config"))
                    
                    predictor = RiskPredictor()
                    print("run_analysis: predictor initialized")
                    data = InstitutionalAnalytics.compute_dashboard_data(local_db, predictor, flipped_map, target_branch)
                    local_db.close()
                    print("run_analysis: data computed")
                    
                    self.after(0, lambda: self._on_analysis_complete(data, user_type))
                except Exception as e:
                    print(f"run_analysis error: {e}")
                    self.after(0, lambda err=e: self.lbl_insight.configure(text=f"Error analyzing data: {err}"))
                    
            threading.Thread(target=run_analysis, daemon=True).start()
            
        except Exception as e:
            print(f"Error starting overview background task: {e}")
            self.lbl_insight.configure(text=f"Error starting background analysis: {e}")

    def _on_analysis_complete(self, data, user_type):
        print("_on_analysis_complete: started")
        if not data:
            self.lbl_insight.configure(text="No student data available to analyze.")
            return
            
        self.current_data = data # Store for snapshot
        self.lbl_insight.configure(text=data["nlg_insight"])
        
        # 1. Build KPI Cards
        self.kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        health_label = "Department Health" if user_type == "HOD" else "Institution Health"
        
        worst_dept_name = data["ranked_departments"][-1][0] if data["ranked_departments"] else "N/A"
        best_dept_name = data["ranked_departments"][0][0] if data["ranked_departments"] else "N/A"
        
        # Calculate Monthly Change
        monthly_change_str = "N/A"
        mc_color = "gray"
        try:
            print("_on_analysis_complete: getting monthly trends")
            dash = self.master
            analytics_panel = dash.analytics
            target_branch = self.controller.shared_data.get("assigned_branch") if user_type == "HOD" else None
            bid = target_branch if target_branch else "ALL"
            
            trends = analytics_panel.db.get_monthly_trends(bid)
            print("_on_analysis_complete: fetched trends")
            if len(trends) > 0:
                last_score = trends[0]["health_score"]
                diff = data['institutional_health'] - last_score
                prefix = "+" if diff > 0 else ""
                monthly_change_str = f"{prefix}{diff:.1f} pts"
                mc_color = COLORS["success"] if diff > 0 else (COLORS["danger"] if diff < 0 else "gray")
        except Exception as e:
            print(f"_on_analysis_complete error fetching trends: {e}")
            pass

        kpis = [
            ("Total Students", str(data["total_students"]), "#00E5FF"),
            (health_label, f"{data['institutional_health']}/100", COLORS["success"] if data['institutional_health'] > 75 else COLORS["warning"]),
            ("High Risk", str(data["overall_risk_counts"]["High"]), COLORS["danger"]),
            ("Medium Risk", str(data["overall_risk_counts"]["Medium"]), COLORS["warning"]),
            ("Low Risk", str(data["overall_risk_counts"]["Low"]), COLORS["success"]),
            ("Most At-Risk", worst_dept_name, COLORS["danger"]),
            ("Best Performing", best_dept_name, COLORS["success"]),
            ("Monthly Change", monthly_change_str, mc_color)
        ]
        
        for i, (title, val, color) in enumerate(kpis):
            c = ctk.CTkFrame(self.kpi_frame, fg_color=COLORS["card"], corner_radius=10)
            c.grid(row=i//4, column=i%4, padx=5, pady=5, sticky="nsew")
            ctk.CTkLabel(c, text=title, text_color="gray", font=("Arial", 12)).pack(pady=(15, 5))
            ctk.CTkLabel(c, text=val, text_color=color, font=("Arial", 22, "bold")).pack(pady=(0, 15))
            
        # 2. Build Charts Layout
        self.visual_frame.grid_columnconfigure((0, 1), weight=1)
        self.visual_frame.grid_rowconfigure(0, weight=1)
        
        # Left: Department Health Leaderboard
        lead_card = ctk.CTkFrame(self.visual_frame, fg_color=COLORS["card"], corner_radius=10)
        lead_card.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(lead_card, text="Department Health Leaderboard", font=("Arial", 16, "bold"), text_color="white").pack(anchor="w", padx=20, pady=15)
        
        for i, (branch_name, stats) in enumerate(data["ranked_departments"]):
            row = ctk.CTkFrame(lead_card, fg_color="#1a1a1a")
            row.pack(fill="x", padx=15, pady=5)
            color = COLORS["success"] if stats["health_score"] >= 80 else COLORS["warning"] if stats["health_score"] >= 60 else COLORS["danger"]
            ctk.CTkLabel(row, text=f"#{i+1} {branch_name}", font=("Arial", 14, "bold")).pack(side="left", padx=10, pady=10)
            ctk.CTkLabel(row, text=f"Health: {stats['health_score']}/100", font=("Arial", 14, "bold"), text_color=color).pack(side="right", padx=10)
        
        # Right: Risk Distribution Stacked Bar Chart
        dist_card = ctk.CTkFrame(self.visual_frame, fg_color=COLORS["card"], corner_radius=10)
        dist_card.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(dist_card, text="Department Risk Distribution", font=("Arial", 16, "bold"), text_color="white").pack(anchor="w", padx=20, pady=15)
        
        print("_on_analysis_complete: generating matplotlib figure")
        fig = plt.Figure(figsize=(6, 4), dpi=100)
        fig.patch.set_facecolor(COLORS["card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLORS["card"])
        
        branches = []
        h_vals = []
        m_vals = []
        l_vals = []
        
        for b, s in data["ranked_departments"]:
            branches.append(b)
            h_vals.append(s["High"])
            m_vals.append(s["Medium"])
            l_vals.append(s["Low"])
            
        y_pos = np.arange(len(branches))
        ax.barh(y_pos, l_vals, color=COLORS["success"], label="Low")
        ax.barh(y_pos, m_vals, left=l_vals, color=COLORS["warning"], label="Medium")
        ax.barh(y_pos, h_vals, left=np.array(l_vals)+np.array(m_vals), color=COLORS["danger"], label="High")
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(branches, color="white")
        ax.tick_params(colors="white")
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=False, labelcolor='white')
        
        fig.tight_layout()
        print("_on_analysis_complete: drawing canvas")
        canvas = FigureCanvasTkAgg(fig, master=dist_card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        print("_on_analysis_complete: done")

    def take_snapshot(self):
        try:
            if not hasattr(self, 'current_data'):
                return
            dash = self.master
            analytics_panel = dash.analytics
            user_type = self.controller.shared_data.get("user_type")
            target_branch = self.controller.shared_data.get("assigned_branch") if user_type == "HOD" else None
            bid = target_branch if target_branch else "ALL"
            
            import datetime
            month_str = datetime.datetime.now().strftime("%Y-%m")
            score = self.current_data['institutional_health']
            
            # Use safe get to avoid KeyError if specific keys are missing
            avg_att = self.current_data.get('avg_attendance', 0.0)
            avg_cgpa = self.current_data.get('avg_cgpa', 0.0)
            risk_dist = str(self.current_data.get("overall_risk_counts", {}))
            
            analytics_panel.db.save_monthly_snapshot(bid, month_str, score, avg_att, avg_cgpa, risk_dist)
            
            from ui.dashboard import ModernMessagebox
            ModernMessagebox("Snapshot Saved", f"Successfully recorded {month_str} snapshot for trend tracking.", "success")
            self.refresh()
        except Exception as e:
            from ui.dashboard import ModernMessagebox
            ModernMessagebox("Snapshot Error", f"Failed to save snapshot: {e}", "error")
