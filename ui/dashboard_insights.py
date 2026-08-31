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

class InsightsMixin:
    def _draw_admin_charts(self, global_stats, branch_stats, loading_lbl):
        loading_lbl.destroy()
        
        self.charts_frame.grid_columnconfigure(0, weight=1)
        self.charts_frame.grid_columnconfigure(1, weight=2)
        
        # Left: Overall Risk (Matplotlib Pie Chart)
        l_outer = ctk.CTkFrame(self.charts_frame, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        l_outer.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        
        ctk.CTkLabel(l_outer, text="OVERALL INSTITUTION RISK", font=("Inter", 12, "bold"), text_color="#7A849C").pack(pady=(10, 0))
        
        total = global_stats["High"] + global_stats["Medium"] + global_stats["Low"]
        if total > 0:
            pie_container = ctk.CTkFrame(l_outer, fg_color="transparent")
            pie_container.pack(fill="both", expand=True, padx=5, pady=5)
            
            import matplotlib.pyplot as plt
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            fig1 = Figure(figsize=(2.2, 2.2), dpi=100)
            fig1.patch.set_facecolor("#12141E")
            ax1 = fig1.add_subplot(111)
            
            labels = ["High Risk", "Medium", "Safe"]
            counts = [global_stats["High"], global_stats["Medium"], global_stats["Low"]]
            colors = ["#FF3D00", "#FF9100", "#00E676"]
            
            filtered_labels = []
            filtered_counts = []
            filtered_colors = []
            for lbl, count, color in zip(labels, counts, colors):
                if count > 0:
                    filtered_labels.append(lbl)
                    filtered_counts.append(count)
                    filtered_colors.append(color)
            
            wedges, texts, autotexts = ax1.pie(filtered_counts, labels=filtered_labels, colors=filtered_colors, autopct='%1.1f%%', 
                                               textprops={'color':"white", 'fontsize': 8, 'weight': 'bold'}, 
                                               pctdistance=0.75, 
                                               wedgeprops=dict(width=0.3, edgecolor="#12141E", linewidth=2))
            
            centre_circle = plt.Circle((0,0),0.70,fc="#12141E")
            fig1.gca().add_artist(centre_circle)
            
            fig1.tight_layout(pad=0)
            canvas1 = FigureCanvasTkAgg(fig1, master=pie_container)
            canvas1.draw()
            canvas1.get_tk_widget().pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(l_outer, text="No Data Available", text_color="gray").pack(expand=True)

        # Right: Risk by Department (Native Stacked Bar)
        r_outer = ctk.CTkFrame(self.charts_frame, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        r_outer.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        
        ctk.CTkLabel(r_outer, text="RISK BY DEPARTMENT", font=("Inter", 12, "bold"), text_color="#7A849C").pack(pady=(10, 0))
        
        dept_names = list(branch_stats.keys())
        if dept_names:
            bars_frame = ctk.CTkFrame(r_outer, fg_color="transparent")
            bars_frame.pack(fill="both", expand=True, padx=20, pady=(2, 5))
            
            for d in dept_names:
                row = ctk.CTkFrame(bars_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                
                ctk.CTkLabel(row, text=d, font=("Inter", 10, "bold"), text_color="white", width=50, anchor="e").pack(side="left", padx=(0, 8))
                
                h = branch_stats[d].get("High", 0)
                m = branch_stats[d].get("Medium", 0)
                l = branch_stats[d].get("Low", 0)
                tot = h + m + l
                
                track = ctk.CTkFrame(row, fg_color="#1A1D2D", height=6, corner_radius=3)
                track.pack(side="left", fill="x", expand=True)
                track.pack_propagate(False)
                
                if tot > 0:
                    pw_l = l/tot
                    pw_m = m/tot
                    pw_h = h/tot
                    
                    if pw_l > 0:
                        ctk.CTkFrame(track, fg_color="#00E676", width=1, corner_radius=3).place(relx=0, rely=0, relwidth=pw_l, relheight=1)
                    if pw_m > 0:
                        ctk.CTkFrame(track, fg_color="#FF9100", width=1, corner_radius=3 if pw_h==0 else 0).place(relx=pw_l, rely=0, relwidth=pw_m, relheight=1)
                    if pw_h > 0:
                        ctk.CTkFrame(track, fg_color="#FF3D00", width=1, corner_radius=3).place(relx=pw_l+pw_m, rely=0, relwidth=pw_h, relheight=1)
        else:
            ctk.CTkLabel(r_outer, text="No Data Available", text_color="gray").pack(expand=True)

    def _render_dept_analytics(self, frame, data):
        for w in frame.winfo_children(): w.destroy()
        if not data or not data["ranked_departments"]:
            ctk.CTkLabel(frame, text="No data available for this department.", text_color="gray").pack()
            return
            
        stats = data["ranked_departments"][0][1]
        
        # 1. The Big 3 Core Health Pulse Cards
        pulse_frame = ctk.CTkFrame(frame, fg_color="transparent")
        pulse_frame.pack(fill="x", pady=(0, 20))
        pulse_frame.grid_columnconfigure((0,1,2), weight=1)
        
        pulses = [
            ("Avg Attendance", f"{stats.get('avg_attendance', 0):.1f}%", "#00E676" if stats.get('avg_attendance', 0) > 75 else "#FF3D00"),
            ("Avg CGPA/Marks", f"{stats.get('avg_cgpa', 0):.1f}%", "#00E5FF"),
            ("Dept Health Score", f"{int(stats.get('health_score', 0))}/100", "#00E676" if stats.get('health_score', 0) > 75 else "#FF3D00")
        ]
        
        for i, (title, val, color) in enumerate(pulses):
            card = ctk.CTkFrame(pulse_frame, fg_color="#12141E", corner_radius=12)
            card.grid(row=0, column=i, padx=8, sticky="nsew")
            
            top_glow = ctk.CTkFrame(card, height=4, fg_color=color, corner_radius=0)
            top_glow.pack(fill="x")
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=25, pady=25)
            ctk.CTkLabel(content, text=title, font=("Inter", 12, "bold"), text_color="#7A849C").pack(anchor="w")
            ctk.CTkLabel(content, text=val, font=("Outfit", 36, "bold"), text_color=color).pack(anchor="w", pady=(5, 0))
            
        # 2. Risk Density Pill & Alert Tags
        bottom_metrics = ctk.CTkFrame(frame, fg_color="transparent")
        bottom_metrics.pack(fill="x", pady=(0, 10))
        
        # Left side: Risk Pill
        risk_frame = ctk.CTkFrame(bottom_metrics, fg_color="#12141E", corner_radius=20, border_width=1, border_color="#2A2E3F")
        risk_frame.pack(side="left", padx=(8, 0), ipady=5)
        
        ctk.CTkLabel(risk_frame, text="RISK DENSITY:", font=("Inter", 11, "bold"), text_color="#7A849C").pack(side="left", padx=(20, 10))
        
        high = stats.get("High", 0)
        med = stats.get("Medium", 0)
        low = stats.get("Low", 0)
        pending = stats.get("Pending", 0)
        
        def make_risk_badge(parent, count, label, color):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(side="left", padx=10)
            ctk.CTkLabel(f, text=str(count), font=("Outfit", 18, "bold"), text_color=color).pack(side="left", padx=(0, 5))
            ctk.CTkLabel(f, text=label, font=("Inter", 11, "bold"), text_color="#aaa").pack(side="left")
            
        if high > 0: make_risk_badge(risk_frame, high, "HIGH", "#FF3D00")
        if med > 0: make_risk_badge(risk_frame, med, "MED", "#FF9100")
        if low > 0: make_risk_badge(risk_frame, low, "LOW", "#00E676")
        if pending > 0: make_risk_badge(risk_frame, pending, "PENDING", "#00E5FF")
        if high == 0 and med == 0 and low == 0 and pending == 0: make_risk_badge(risk_frame, 0, "STUDENTS", "#aaa")
        
        # Right side: Alert Tags
        alerts = ctk.CTkFrame(bottom_metrics, fg_color="transparent")
        alerts.pack(side="right", padx=(0, 8))
        
        bkl = stats.get('avg_backlogs', 0)
        bkl_color = "#FF3D00" if bkl > 1 else "#00E676"
        ctk.CTkLabel(alerts, text=f"⚠️ Avg Backlogs: {bkl:.1f}", font=("Inter", 12, "bold"), fg_color="#1A1D2D", text_color=bkl_color, corner_radius=8).pack(side="right", padx=5, ipadx=10, ipady=8)
        
        drivers = stats.get('top_drivers', ["N/A"])[0] if stats.get('top_drivers') else "N/A"
        ctk.CTkLabel(alerts, text=f"🔍 Driver: {drivers}", font=("Inter", 12, "bold"), fg_color="#1A1D2D", text_color="#FF9100", corner_radius=8).pack(side="right", padx=5, ipadx=10, ipady=8)

