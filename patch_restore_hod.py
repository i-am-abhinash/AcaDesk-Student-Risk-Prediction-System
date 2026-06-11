import re

dashboard_path = r"d:\AcaDesk1\ui\dashboard.py"

with open(dashboard_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Sidebar
sidebar_old = """        self.btn_dash = self.add_btn("📊  Dashboard", lambda: self.dash.show_view("Analytics"))
        self.btn_fac = self.add_btn("👥  Faculty Manager", lambda: self.dash.show_view("Faculty"))
        self.btn_sim = self.add_btn("🧠  AI Simulator", self.dash.open_ai_simulator)"""

sidebar_new = """        self.btn_dash = self.add_btn("📊  Dashboard", lambda: self.dash.show_view("Analytics"))
        self.btn_hod = self.add_btn("👔  HOD Manager", lambda: self.dash.show_view("HOD"))
        self.btn_fac = self.add_btn("👥  Faculty Manager", lambda: self.dash.show_view("Faculty"))
        self.btn_sim = self.add_btn("🧠  AI Simulator", self.dash.open_ai_simulator)"""
content = content.replace(sidebar_old, sidebar_new)

sidebar_refresh_old = """        self.btn_fac.pack_forget()
        
        if user_type == "Admin": 
            self.btn_fac.pack(fill="x", padx=10, pady=2)
        elif user_type == "Faculty" and is_hod:
            self.btn_fac.pack(fill="x", padx=10, pady=2)"""

sidebar_refresh_new = """        self.btn_hod.pack_forget()
        self.btn_fac.pack_forget()
        
        if user_type == "Admin": 
            self.btn_hod.pack(fill="x", padx=10, pady=2)
            self.btn_fac.pack(fill="x", padx=10, pady=2)
        elif user_type == "Faculty" and is_hod:
            self.btn_fac.pack(fill="x", padx=10, pady=2)"""
content = content.replace(sidebar_refresh_old, sidebar_refresh_new)

# 2. Re-add hod_manager to DashboardScreen
ds_old = """        self.sidebar = Sidebar(self, controller, self)
        self.analytics = AnalyticsPanel(self, controller)
        self.faculty = FacultyManagerPanel(self, controller)
        self.erp = ERPWizard(self, controller, self)"""

ds_new = """        self.sidebar = Sidebar(self, controller, self)
        self.analytics = AnalyticsPanel(self, controller)
        self.faculty = FacultyManagerPanel(self, controller)
        self.hod_manager = HODManagerPanel(self, controller)
        self.erp = ERPWizard(self, controller, self)"""
content = content.replace(ds_old, ds_new)

view_old = """        self.analytics.grid_forget()
        self.faculty.grid_forget()
        self.erp.grid_forget()
        
        if name == "Analytics":
            self.analytics.grid(row=0, column=1, sticky="nsew")
            self.analytics.refresh()
        elif name == "Faculty":
            self.faculty.grid(row=0, column=1, sticky="nsew")
            self.faculty.refresh()"""

view_new = """        self.analytics.grid_forget()
        self.faculty.grid_forget()
        self.hod_manager.grid_forget()
        self.erp.grid_forget()
        
        if name == "Analytics":
            self.analytics.grid(row=0, column=1, sticky="nsew")
            self.analytics.refresh()
        elif name == "Faculty":
            self.faculty.grid(row=0, column=1, sticky="nsew")
            self.faculty.refresh()
        elif name == "HOD":
            self.hod_manager.grid(row=0, column=1, sticky="nsew")
            self.hod_manager.refresh()"""
content = content.replace(view_old, view_new)

# 3. Clean up FacultyManagerPanel (remove promote/demote and HOD tags)
fac_refresh_old = """            for f in faculties:
                branch_id = str(f['assigned_branch'])
                branch_name = "Unknown"
                if self.db:
                    branch_name = self.db.get_branch_map().get(branch_id, branch_id)
                
                row = ctk.CTkFrame(self.list_frame, fg_color=COLORS["card"], height=50)
                row.pack(fill="x", pady=5)
                
                badge = "[HOD] " if f.get("is_hod") else ""
                
                lbl = ctk.CTkLabel(
                    row, 
                    text=f"👤  {badge}{f['username']}  [{branch_name}]", 
                    font=FONTS["h3"],
                    text_color="#00E5FF"
                )
                lbl.pack(side="left", padx=15)
                
                rev_btn = ctk.CTkButton(
                    row, 
                    text="REVOKE", 
                    fg_color="#330000", 
                    text_color=COLORS["danger"], 
                    width=80, 
                    command=lambda u=f['username']: self.revoke(u)
                )
                rev_btn.pack(side="right", padx=15)
                
                user_type = self.controller.shared_data.get("user_type")
                if user_type == "Admin":
                    if f.get("is_hod"):
                        demote_btn = ctk.CTkButton(
                            row, text="Remove HOD", fg_color="#FF9100", text_color="black", width=80,
                            command=lambda u=f['username']: self.demote_hod(u)
                        )
                        demote_btn.pack(side="right", padx=15)
                    else:
                        prom_btn = ctk.CTkButton(
                            row, text="Promote to HOD", fg_color="#00C853", text_color="black", width=80,
                            command=lambda u=f['username']: self.promote_hod(u)
                        )
                        prom_btn.pack(side="right", padx=15)"""

fac_refresh_new = """            for f in faculties:
                branch_id = str(f['assigned_branch'])
                branch_name = "Unknown"
                if self.db:
                    branch_name = self.db.get_branch_map().get(branch_id, branch_id)
                
                row = ctk.CTkFrame(self.list_frame, fg_color=COLORS["card"], height=50)
                row.pack(fill="x", pady=5)
                
                lbl = ctk.CTkLabel(
                    row, 
                    text=f"👤  {f['username']}  [{branch_name}]", 
                    font=FONTS["h3"],
                    text_color="#00E5FF"
                )
                lbl.pack(side="left", padx=15)
                
                rev_btn = ctk.CTkButton(
                    row, 
                    text="REVOKE", 
                    fg_color="#330000", 
                    text_color=COLORS["danger"], 
                    width=80, 
                    command=lambda u=f['username']: self.revoke(u)
                )
                rev_btn.pack(side="right", padx=15)"""
content = content.replace(fac_refresh_old, fac_refresh_new)

fac_methods_old = """    def promote_hod(self, username):
        college = self.controller.shared_data["college_name"]
        admin_user = self.controller.shared_data["username"]
        if CentralAuth().promote_to_hod(username, college, admin_user):
            self.refresh()

    def demote_hod(self, username):
        college = self.controller.shared_data["college_name"]
        admin_user = self.controller.shared_data["username"]
        if CentralAuth().revoke_hod_status(username, college, admin_user):
            self.refresh()"""
content = content.replace(fac_methods_old, "")

# 4. Re-inject HODManagerPanel
hod_manager_code = """
# ====================================================
#  HOD MANAGER
# ====================================================

class HODManagerPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.db = None
        self.branch_map = {}
        self.faculty_list = []
        
        title = ctk.CTkLabel(
            self, 
            text="HOD MANAGEMENT", 
            text_color="#00E5FF",
            font=FONTS["h1"]
        )
        title.pack(anchor="w", padx=40, pady=(40, 20))
        
        # Entry Form
        form_card = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=10)
        form_card.pack(fill="x", padx=40, pady=10)
        
        row_frame = ctk.CTkFrame(form_card, fg_color="transparent")
        row_frame.pack(fill="x", padx=20, pady=20)
        
        self.fac_combo = ctk.CTkComboBox(row_frame, width=180)
        self.fac_combo.set("Select Existing Faculty")
        self.fac_combo.pack(side="left", padx=5)
        
        self.dept_combo = ctk.CTkComboBox(row_frame, width=160)
        self.dept_combo.set("Select Department")
        self.dept_combo.pack(side="left", padx=5)
        
        add_btn = ctk.CTkButton(
            row_frame, 
            text="Assign HOD", 
            fg_color=COLORS["accent"], 
            text_color="black", 
            width=100, 
            command=self.assign_hod
        )
        add_btn.pack(side="left", padx=5)
        
        # HOD List Scroll Area
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20)

    def refresh(self):
        erp_conf = self.controller.shared_data.get("erp_config")
        if erp_conf:
            self.db = DBHandler(erp_conf)
            b_map = self.db.get_branch_map()
            self.branch_map = {name: str(id) for id, name in b_map.items()}
            self.dept_combo.configure(values=list(self.branch_map.keys()))
            
        college = self.controller.shared_data.get("college_name")
        self.faculty_list = [f['username'] for f in CentralAuth().get_non_hod_faculty_list(college)]
        if self.faculty_list:
            self.fac_combo.configure(values=self.faculty_list)
        else:
            self.fac_combo.configure(values=["No Faculty Available"])
            
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        try:
            hods = CentralAuth().get_hod_list(college)
            
            for h in hods:
                dept_id = str(h.get('assigned_department'))
                dept_name = "Unknown"
                if self.db:
                    dept_name = self.db.get_branch_map().get(dept_id, dept_id)
                
                row = ctk.CTkFrame(self.list_frame, fg_color=COLORS["card"], height=50)
                row.pack(fill="x", pady=5)
                
                lbl = ctk.CTkLabel(
                    row, 
                    text=f"👔  {h['username']}   |   Department: {dept_name}   |   HOD Status: Active", 
                    font=FONTS["h3"],
                    text_color="#00E5FF"
                )
                lbl.pack(side="left", padx=15)
                
                rev_btn = ctk.CTkButton(
                    row, 
                    text="REMOVE", 
                    fg_color="#FF9100", 
                    text_color="black", 
                    width=100, 
                    command=lambda u=h['username']: self.revoke_hod(u)
                )
                rev_btn.pack(side="right", padx=15)
        except Exception as e:
            print(f"Error refreshing HODs: {e}")

    def assign_hod(self):
        username = self.fac_combo.get()
        selection = self.dept_combo.get()
        
        if username and username != "Select Existing Faculty" and username != "No Faculty Available" and selection != "Select Department":
            dept_id = self.branch_map.get(selection)
            admin_user = self.controller.shared_data["username"]
            college = self.controller.shared_data["college_name"]
            success, msg = CentralAuth().promote_to_hod(username, dept_id, college, admin_user)
            if success:
                self.fac_combo.set("Select Existing Faculty")
                self.dept_combo.set("Select Department")
                self.refresh()
            else:
                ModernMessagebox("Error", msg, "error")

    def revoke_hod(self, username):
        college = self.controller.shared_data["college_name"]
        admin_user = self.controller.shared_data["username"]
        if CentralAuth().revoke_hod_status(username, college, admin_user):
            self.refresh()

# ====================================================
#  ANALYTICS PANEL
"""

content = content.replace("# ====================================================\n#  ANALYTICS PANEL", hod_manager_code)

with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied.")
