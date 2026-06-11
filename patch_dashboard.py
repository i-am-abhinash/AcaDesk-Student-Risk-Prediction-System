import re
import os

dashboard_path = r"d:\AcaDesk1\ui\dashboard.py"

with open(dashboard_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add HODManagerPanel Class right after FacultyManagerPanel
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
        
        self.n_entry = ctk.CTkEntry(row_frame, placeholder_text="HOD Name", width=140)
        self.n_entry.pack(side="left", padx=5)

        self.u_entry = ctk.CTkEntry(row_frame, placeholder_text="Username", width=120)
        self.u_entry.pack(side="left", padx=5)
        
        self.p_entry = ctk.CTkEntry(row_frame, placeholder_text="Password", width=120, show="*")
        self.p_entry.pack(side="left", padx=5)
        
        self.br_combo = ctk.CTkComboBox(row_frame, width=140)
        self.br_combo.set("Select Department")
        self.br_combo.pack(side="left", padx=5)
        
        add_btn = ctk.CTkButton(
            row_frame, 
            text="+ ADD HOD", 
            fg_color=COLORS["accent"], 
            text_color="black", 
            width=100, 
            command=self.add_hod
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
            self.br_combo.configure(values=list(self.branch_map.keys()))
            
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        try:
            college = self.controller.shared_data.get("college_name")
            hods = CentralAuth().get_hod_list(college)
            
            for h in hods:
                dept_id = str(h['assigned_department'])
                dept_name = "Unknown"
                if self.db:
                    dept_name = self.db.get_branch_map().get(dept_id, dept_id)
                
                row = ctk.CTkFrame(self.list_frame, fg_color=COLORS["card"], height=50)
                row.pack(fill="x", pady=5)
                
                lbl = ctk.CTkLabel(
                    row, 
                    text=f"👔  {h['username']}  [{dept_name}]", 
                    font=FONTS["h3"],
                    text_color="#00C853"
                )
                lbl.pack(side="left", padx=15)
                
                rev_btn = ctk.CTkButton(
                    row, 
                    text="REMOVE", 
                    fg_color="#330000", 
                    text_color=COLORS["danger"], 
                    width=80, 
                    command=lambda u=h['username']: self.revoke(u)
                )
                rev_btn.pack(side="right", padx=15)
        except Exception as e:
            print(f"Error refreshing HODs: {e}")

    def add_hod(self):
        name = self.n_entry.get()
        username = self.u_entry.get()
        password = self.p_entry.get()
        selection = self.br_combo.get()
        
        if name and username and password and selection != "Select Department":
            dept_id = self.branch_map.get(selection)
            admin_user = self.controller.shared_data["username"]
            success, msg = CentralAuth().add_hod(admin_user, name, username, password, dept_id)
            if success:
                self.n_entry.delete(0, 'end')
                self.u_entry.delete(0, 'end')
                self.p_entry.delete(0, 'end')
                self.refresh()
            else:
                ModernMessagebox("Error", msg, "error")

    def revoke(self, username):
        college = self.controller.shared_data["college_name"]
        if CentralAuth().revoke_hod(username, college):
            self.refresh()

# ====================================================
#  ANALYTICS PANEL
"""

content = content.replace("# ====================================================\n#  ANALYTICS PANEL", hod_manager_code)


# 2. Update Sidebar
sidebar_old = """        # Sidebar Menu Buttons
        self.btn_dash = self.add_btn("📊  Dashboard", lambda: self.dash.show_view("Analytics"))
        self.btn_fac = self.add_btn("👥  Faculty Manager", lambda: self.dash.show_view("Faculty"))
        self.btn_sim = self.add_btn("🧠  AI Simulator", self.dash.open_ai_simulator)
        self.btn_pass = self.add_btn("🔒  Change Password", self.dash.open_change_pass) 
        
        # Logout Button"""

sidebar_new = """        # Sidebar Menu Buttons
        self.btn_dash = self.add_btn("📊  Dashboard", lambda: self.dash.show_view("Analytics"))
        self.btn_hod = self.add_btn("👔  HOD Manager", lambda: self.dash.show_view("HOD"))
        self.btn_fac = self.add_btn("👥  Faculty Manager", lambda: self.dash.show_view("Faculty"))
        self.btn_sim = self.add_btn("🧠  AI Simulator", self.dash.open_ai_simulator)
        self.btn_pass = self.add_btn("🔒  Change Password", self.dash.open_change_pass) 
        
        # Logout Button"""
content = content.replace(sidebar_old, sidebar_new)

sidebar_refresh_old = """    def refresh(self):
        username = self.controller.shared_data.get('username', 'User')
        self.lbl_user.configure(text=f"User: {username}")
        
        user_type = self.controller.shared_data.get("user_type")
        if user_type == "Admin": 
            self.btn_fac.pack(fill="x", padx=10, pady=2)
        else: 
            self.btn_fac.pack_forget()"""

sidebar_refresh_new = """    def refresh(self):
        username = self.controller.shared_data.get('username', 'User')
        self.lbl_user.configure(text=f"User: {username}")
        
        user_type = self.controller.shared_data.get("user_type")
        
        self.btn_hod.pack_forget()
        self.btn_fac.pack_forget()
        
        if user_type == "Admin": 
            self.btn_hod.pack(fill="x", padx=10, pady=2)
            self.btn_fac.pack(fill="x", padx=10, pady=2)
        elif user_type == "HOD":
            self.btn_fac.pack(fill="x", padx=10, pady=2)"""
content = content.replace(sidebar_refresh_old, sidebar_refresh_new)


# 3. Update DashboardScreen
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


# 4. Update FacultyManagerPanel.refresh to restrict branch if HOD
fac_ref_old = """        erp_conf = self.controller.shared_data.get("erp_config")
        if erp_conf:
            self.db = DBHandler(erp_conf)
            b_map = self.db.get_branch_map()
            self.branch_map = {name: str(id) for id, name in b_map.items()}
            self.br_combo.configure(values=list(self.branch_map.keys()))"""

fac_ref_new = """        erp_conf = self.controller.shared_data.get("erp_config")
        if erp_conf:
            self.db = DBHandler(erp_conf)
            b_map = self.db.get_branch_map()
            self.branch_map = {name: str(id) for id, name in b_map.items()}
            
            user_type = self.controller.shared_data.get("user_type")
            if user_type == "HOD":
                assigned_dept = self.controller.shared_data.get("assigned_department")
                assigned_name = b_map.get(assigned_dept, assigned_dept)
                self.br_combo.configure(values=[assigned_name])
                self.br_combo.set(assigned_name)
                self.br_combo.configure(state="disabled")
            else:
                self.br_combo.configure(values=list(self.branch_map.keys()))
                self.br_combo.configure(state="normal")"""
content = content.replace(fac_ref_old, fac_ref_new)

# 5. Update AnalyticsPanel.refresh
ana_ref_old = """        user_type = self.controller.shared_data.get("user_type")
        if user_type == "Faculty":
            assigned = self.controller.shared_data.get("assigned_branch")
            if assigned:
                self.current_branch = assigned
                self.show_year_selection()
                return
                
        self.show_branch_selection()"""

ana_ref_new = """        user_type = self.controller.shared_data.get("user_type")
        if user_type == "Faculty":
            assigned = self.controller.shared_data.get("assigned_branch")
            if assigned:
                self.current_branch = assigned
                self.show_year_selection()
                return
        elif user_type == "HOD":
            assigned = self.controller.shared_data.get("assigned_department")
            if assigned:
                self.current_branch = assigned
                self.show_year_selection()
                return
                
        self.show_branch_selection()"""
content = content.replace(ana_ref_old, ana_ref_new)

with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied to dashboard.py")
