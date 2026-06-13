import customtkinter as ctk

COLORS = {
    "bg": "#0B0E14",
    "card": "#151A22",
    "accent": "#00E5FF",
    "success": "#00E676",
    "warning": "#FFEA00",
    "danger": "#FF1744",
}

class DepartmentDrillDown(ctk.CTkToplevel):
    def __init__(self, parent, branch_name, stats_data):
        super().__init__(parent)
        self.title(f"{branch_name} - Detailed Analytics")
        self.geometry("700x500")
        self.configure(fg_color=COLORS["bg"])
        self.attributes("-topmost", True)
        
        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=10)
        header.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(header, text=f"📊 {branch_name} Department Analytics", font=("Arial", 22, "bold"), text_color="white").pack(pady=15)
        
        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Risk Distribution
        risk_frame = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        risk_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(risk_frame, text="Risk Distribution", font=("Arial", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=10)
        
        row1 = ctk.CTkFrame(risk_frame, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(row1, text=f"High Risk: {stats_data.get('High', 0)}", text_color=COLORS["danger"], font=("Arial", 14, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(row1, text=f"Medium Risk: {stats_data.get('Medium', 0)}", text_color=COLORS["warning"], font=("Arial", 14, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(row1, text=f"Low Risk: {stats_data.get('Low', 0)}", text_color=COLORS["success"], font=("Arial", 14, "bold")).pack(side="left", padx=10)

        # Averages (mocked or retrieved if available)
        avg_frame = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        avg_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(avg_frame, text="Performance Averages", font=("Arial", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=10)
        row2 = ctk.CTkFrame(avg_frame, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=10)
        
        # We assume the caller passed these or we use placeholders if absent
        att = stats_data.get('avg_attendance', 0.0)
        if isinstance(att, float): att = round(att, 1)
        cgpa = stats_data.get('avg_cgpa', 0.0)
        if isinstance(cgpa, float): cgpa = round(cgpa, 2)
        
        ctk.CTkLabel(row2, text=f"Average Attendance: {att}%", text_color="white", font=("Arial", 14)).pack(side="left", padx=10)
        ctk.CTkLabel(row2, text=f"Average CGPA: {cgpa}", text_color="white", font=("Arial", 14)).pack(side="left", padx=10)
        
        # Top SHAP Drivers
        shap_frame = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        shap_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(shap_frame, text="Top Risk Drivers", font=("Arial", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=10)
        
        drivers = stats_data.get('top_drivers', [])
        for driver in drivers:
            # Handle both string (heuristic fallback) and tuple (shap driver) formats
            if isinstance(driver, tuple):
                driver_name, impact = driver
            else:
                driver_name = str(driver)
                impact = "High Impact"
                
            d_row = ctk.CTkFrame(shap_frame, fg_color="#1a1a1a")
            d_row.pack(fill="x", padx=15, pady=5)
            ctk.CTkLabel(d_row, text=f"• {driver_name}", text_color="white", font=("Arial", 14)).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(d_row, text=impact, text_color=COLORS["danger"], font=("Arial", 14, "bold")).pack(side="right", padx=10, pady=8)
            
        close_btn = ctk.CTkButton(self, text="Close", fg_color="#333", command=self.destroy)
        close_btn.pack(pady=20)
