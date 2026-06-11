import re

dashboard_path = r"d:\AcaDesk1\ui\dashboard.py"
with open(dashboard_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Sidebar
sidebar_old = """        self.btn_hod.pack_forget()
        self.btn_fac.pack_forget()
        
        if user_type == "Admin": 
            self.btn_hod.pack(fill="x", padx=10, pady=2)
            self.btn_fac.pack(fill="x", padx=10, pady=2)
        elif user_type == "Faculty" and is_hod:
            self.btn_fac.pack(fill="x", padx=10, pady=2)"""

sidebar_new = """        self.btn_hod.pack_forget()
        self.btn_fac.pack_forget()
        
        if user_type == "Admin": 
            self.btn_hod.pack(fill="x", padx=10, pady=2)
            self.btn_fac.pack(fill="x", padx=10, pady=2)
        elif user_type == "HOD":
            self.btn_fac.pack(fill="x", padx=10, pady=2)"""
content = content.replace(sidebar_old, sidebar_new)

# 2. Fix FacultyManagerPanel refresh (remove is_hod logic)
fac_ref_old = """            user_type = self.controller.shared_data.get("user_type")
            is_hod = self.controller.shared_data.get("is_hod")
            if user_type == "Faculty" and is_hod:
                assigned_dept = self.controller.shared_data.get("assigned_department")
                if not assigned_dept:
                    assigned_dept = self.controller.shared_data.get("assigned_branch")
                assigned_name = b_map.get(assigned_dept, assigned_dept)
                self.br_combo.configure(values=[assigned_name])
                self.br_combo.set(assigned_name)
                self.br_combo.configure(state="disabled")
            else:
                self.br_combo.configure(values=list(self.branch_map.keys()))
                self.br_combo.configure(state="normal")"""

fac_ref_new = """            user_type = self.controller.shared_data.get("user_type")
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

# 3. Wipe out all HODManagerPanel definitions
content = re.sub(r'# ====================================================\n#  HOD MANAGER.*?# ====================================================\n#  ANALYTICS PANEL', '# ====================================================\n#  ANALYTICS PANEL', content, flags=re.DOTALL)

# 4. Insert new HODManagerPanel
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
        
        self.u_entry = ctk.CTkEntry(row_frame, placeholder_text="Username", width=160)
        self.u_entry.pack(side="left", padx=5)
        
        self.p_entry = ctk.CTkEntry(row_frame, placeholder_text="Password", width=160, show="*")
        self.p_entry.pack(side="left", padx=5)
        
        self.br_combo = ctk.CTkComboBox(row_frame, width=160)
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
            from logic.central_auth import CentralAuth
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
                    text=f"👔  {h['username']}   |   Department: {dept_name}", 
                    font=FONTS["h3"],
                    text_color="#00E5FF"
                )
                lbl.pack(side="left", padx=15)
                
                rev_btn = ctk.CTkButton(
                    row, 
                    text="REMOVE", 
                    fg_color="#330000", 
                    text_color=COLORS["danger"], 
                    width=100, 
                    command=lambda u=h['username']: self.revoke_hod(u)
                )
                rev_btn.pack(side="right", padx=15)
        except Exception as e:
            print(f"Error refreshing HODs: {e}")

    def add_hod(self):
        username = self.u_entry.get()
        password = self.p_entry.get()
        selection = self.br_combo.get()
        
        if username and password and selection != "Select Department":
            dept_id = self.branch_map.get(selection)
            admin_user = self.controller.shared_data["username"]
            from logic.central_auth import CentralAuth
            from ui.components import ModernMessagebox
            success, msg = CentralAuth().add_hod(admin_user, username, password, dept_id)
            if success:
                self.u_entry.delete(0, 'end')
                self.p_entry.delete(0, 'end')
                self.br_combo.set("Select Department")
                self.refresh()
            else:
                ModernMessagebox("Error", msg, "error")

    def revoke_hod(self, username):
        college = self.controller.shared_data["college_name"]
        from logic.central_auth import CentralAuth
        if CentralAuth().revoke_hod(username, college):
            self.refresh()

# ====================================================
#  ANALYTICS PANEL
"""

content = content.replace("# ====================================================\n#  ANALYTICS PANEL", hod_manager_code)

# 5. Fix AnalyticsPanel checking is_hod
ana_old = """        user_type = self.controller.shared_data.get("user_type")
        is_hod = self.controller.shared_data.get("is_hod")
        if user_type == "Faculty":
            if is_hod:
                assigned = self.controller.shared_data.get("assigned_department", self.controller.shared_data.get("assigned_branch"))
                if assigned:
                    self.current_branch = assigned
                    self.show_year_selection()
                    return
            else:
                assigned = self.controller.shared_data.get("assigned_branch")
                if assigned:
                    self.current_branch = assigned
                    self.show_year_selection()
                    return
        elif user_type == "HOD":
            assigned = self.controller.shared_data.get("assigned_department")"""

ana_new = """        user_type = self.controller.shared_data.get("user_type")
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
                return"""

content = content.replace(ana_old, ana_new)

with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(content)

print("UI Strict Separation Applied.")
