import customtkinter as ctk
import threading
from ui.dashboard import ModernMessagebox, COLORS
from logic.schema_detector import SchemaDetector
from logic.central_auth import CentralAuth

class ERPWizard(ctk.CTkFrame):
    def __init__(self, parent, controller, dash):
        super().__init__(parent, fg_color="#111")
        self.controller = controller
        self.dash = dash
        self.current_step = 1
        self.schema_results = None
        
        self.container = ctk.CTkFrame(self, corner_radius=20, fg_color="#1a1a1a")
        self.container.pack(fill="both", expand=True, padx=120, pady=40)
        
        self.header = ctk.CTkFrame(self.container, fg_color="transparent")
        self.header.pack(fill="x", pady=(30, 10), padx=30)
        
        head_lbl = ctk.CTkLabel(self.header, text="AUTO-DETECT ERP SETUP", font=("Arial Black", 24))
        head_lbl.pack(anchor="w")
        
        self.step_lbl = ctk.CTkLabel(self.header, text="Step 1 of 2", text_color="gray")
        self.step_lbl.pack(anchor="w")
        
        self.main_body = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_body.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.footer = ctk.CTkFrame(self.container, fg_color="transparent")
        self.footer.pack(fill="x", padx=40, pady=20, side="bottom")
        
        self.btn_back = ctk.CTkButton(self.footer, text="← BACK", height=45, fg_color="#333", command=self.prev_step)
        self.btn_action = ctk.CTkButton(self.footer, text="SCAN & DETECT SCHEMA →", height=45, fg_color="#00E5FF", text_color="black", command=self.do_scan)
        
        self.init_steps()
        self.show_step(1)

    def init_steps(self):
        # Step 1: Credentials
        self.s1 = ctk.CTkFrame(self.main_body, fg_color="transparent")
        
        form_scroll = ctk.CTkScrollableFrame(self.s1, fg_color="transparent")
        form_scroll.pack(side="left", fill="both", expand=True, padx=10)
        
        info_panel = ctk.CTkFrame(self.s1, fg_color=COLORS["card"], corner_radius=15, width=300)
        info_panel.pack(side="right", fill="y", padx=10)
        info_panel.pack_propagate(False)
        ctk.CTkLabel(info_panel, text="1. Connection", font=("Arial", 18, "bold"), text_color="#00E5FF").pack(pady=20)
        ctk.CTkLabel(info_panel, text="Provide Database Server Credentials. We will connect and automatically scan for student tables.", text_color="#ccc", wraplength=250, justify="left").pack(padx=20)
        
        def add_field(parent, label_text, default_value, secret=False):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=12)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=label_text, font=("Arial", 12, "bold"), anchor="w", width=180).grid(row=0, column=0, sticky="w")
            entry = ctk.CTkEntry(row, height=45)
            entry.insert(0, default_value)
            if secret: entry.configure(show="*")
            entry.grid(row=0, column=1, sticky="ew", padx=(20, 50))
            return entry

        self.db_tech = ctk.CTkComboBox(form_scroll, values=["MySQL / MariaDB"], height=45)
        self.db_tech.pack(pady=10)
        self.db_tech.set("MySQL / MariaDB")
        
        self.host = add_field(form_scroll, "Host IP:", "localhost")
        self.port = add_field(form_scroll, "Port:", "3306")
        self.db_name = add_field(form_scroll, "DB Name:", "engineering_college")
        self.user = add_field(form_scroll, "User:", "root")
        self.pwd = add_field(form_scroll, "Password:", "", True)
        
        # Step 2: Mapping Suggestions
        self.s2 = ctk.CTkScrollableFrame(self.main_body, fg_color="transparent")
        
        self.lbl_scan_status = ctk.CTkLabel(self.s2, text="", font=("Arial", 14), text_color=COLORS["warning"])
        self.lbl_scan_status.pack(pady=10)
        
        self.mapping_frame = ctk.CTkFrame(self.s2, fg_color="transparent")
        self.mapping_frame.pack(fill="both", expand=True)

    def show_step(self, s):
        self.current_step = s
        self.s1.pack_forget()
        self.s2.pack_forget()
        self.btn_back.pack_forget()
        self.btn_action.pack_forget()
        
        self.step_lbl.configure(text=f"Step {s} of 2")
        
        if s == 1:
            self.s1.pack(fill="both", expand=True)
            self.btn_action.configure(text="SCAN & DETECT SCHEMA →", fg_color="#00E5FF", command=self.do_scan)
            self.btn_action.pack(side="right")
        elif s == 2:
            self.s2.pack(fill="both", expand=True)
            self.btn_back.pack(side="left")
            self.btn_action.configure(text="VALIDATE & SAVE CONFIG", fg_color="#00C853", command=self.validate_and_save)
            self.btn_action.pack(side="right")

    def prev_step(self):
        self.show_step(self.current_step - 1)

    def do_scan(self):
        host = self.host.get().strip()
        port = self.port.get().strip()
        db = self.db_name.get().strip()
        user = self.user.get().strip()
        pwd = self.pwd.get().strip()
        
        if not all([host, port, db, user]):
            ModernMessagebox("Missing Info", "Please fill all connection fields.", "warning")
            return
            
        self.btn_action.configure(state="disabled", text="SCANNING...")
        
        def scan_thread():
            detector = SchemaDetector(host, port, db, user, pwd)
            success, msg = detector.connect()
            if not success:
                self.after(0, lambda: self.scan_failed(msg))
                return
                
            self.after(0, lambda: self.lbl_scan_status.configure(text="Connected. Scanning metadata..."))
            
            if not detector.scan_schema():
                self.after(0, lambda: self.scan_failed("Failed to read INFORMATION_SCHEMA"))
                return
                
            self.after(0, lambda: self.lbl_scan_status.configure(text="Analyzing structure..."))
            
            results = detector.detect_schema()
            self.after(0, lambda: self.scan_success(results, detector.tables, detector.columns))
            
        threading.Thread(target=scan_thread, daemon=True).start()
        
    def scan_failed(self, msg):
        self.btn_action.configure(state="normal", text="SCAN & DETECT SCHEMA →")
        ModernMessagebox("Scan Failed", f"Could not connect or scan database:\n{msg}", "error")

    def scan_success(self, results, all_tables, all_columns):
        self.btn_action.configure(state="normal")
        self.schema_results = results
        self.all_tables = all_tables
        self.all_columns = all_columns
        self.build_mapping_ui()
        self.show_step(2)
        self.lbl_scan_status.configure(text="Review Detected Schema", text_color=COLORS["success"])

    def build_mapping_ui(self):
        for w in self.mapping_frame.winfo_children():
            w.destroy()
            
        self.field_vars = {} # group -> {key: ctk.StringVar}

        def create_group(title, data, keys_to_show, color):
            group = ctk.CTkFrame(self.mapping_frame, fg_color=COLORS["card"], corner_radius=10)
            group.pack(fill="x", pady=10, padx=5)
            
            header = ctk.CTkFrame(group, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=10)
            
            ctk.CTkLabel(header, text=title, font=("Arial", 16, "bold"), text_color=color).pack(side="left")
            
            conf = data["confidence"]
            conf_color = COLORS["success"] if conf >= 80 else (COLORS["warning"] if conf >= 50 else COLORS["danger"])
            ctk.CTkLabel(header, text=f"{conf}% Match", font=("Arial", 12, "bold"), fg_color=conf_color, text_color="black", corner_radius=5).pack(side="right", ipadx=5)
            
            # Table selection
            tbl_row = ctk.CTkFrame(group, fg_color="transparent")
            tbl_row.pack(fill="x", padx=15, pady=5)
            ctk.CTkLabel(tbl_row, text="Table:", font=("Arial", 12, "bold"), width=120, anchor="w").pack(side="left")
            tbl_var = ctk.StringVar(value=data["name"] or "")
            self.field_vars[title] = {"_table": tbl_var}
            tbl_cb = ctk.CTkComboBox(tbl_row, values=[""] + self.all_tables, variable=tbl_var, width=250)
            tbl_cb.pack(side="left", padx=10)
            
            # Columns
            cols_frame = ctk.CTkFrame(group, fg_color="#222", corner_radius=5)
            cols_frame.pack(fill="x", padx=15, pady=10)
            
            for key in keys_to_show:
                col_data = data["columns"].get(key, {"name": "", "confidence": 0})
                
                row = ctk.CTkFrame(cols_frame, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=5)
                
                ctk.CTkLabel(row, text=key + ":", width=150, anchor="w").pack(side="left")
                
                c_conf = col_data["confidence"]
                c_color = COLORS["success"] if c_conf >= 80 else (COLORS["warning"] if c_conf >= 50 else COLORS["danger"])
                ctk.CTkLabel(row, text="●", text_color=c_color, width=20).pack(side="left")
                
                var = ctk.StringVar(value=col_data["name"] or "")
                self.field_vars[title][key] = var
                
                # Dynamic column choices based on currently selected table would be ideal, 
                # but we'll use a simple Entry for overrides to keep it straightforward.
                ent = ctk.CTkEntry(row, textvariable=var, width=200)
                ent.pack(side="left", padx=10)

        create_group("Student Data", self.schema_results["tbl_student"], 
                     ["col_student_id", "col_name", "join_branch", "col_year", "col_email", "col_p_phone", "col_p_email"], 
                     COLORS["accent"])
                     
        create_group("Academic Data", self.schema_results["tbl_academic"], 
                     ["join_student", "col_attendance", "col_marks", "col_backlogs", "col_tenth", "col_inter", "col_diploma", "col_lab", "col_mid", "col_cons_abs", "col_leave"], 
                     "#FF9100")
                     
        create_group("Branch Data", self.schema_results["tbl_branch"], 
                     ["join_branch", "col_branch_name"], 
                     "#E040FB")

    def validate_and_save(self):
        self.btn_action.configure(state="disabled", text="VALIDATING...")
        
        # 1. Gather configured values
        s_tbl = self.field_vars["Student Data"]["_table"].get()
        a_tbl = self.field_vars["Academic Data"]["_table"].get()
        b_tbl = self.field_vars["Branch Data"]["_table"].get()
        
        s_id = self.field_vars["Student Data"]["col_student_id"].get()
        s_name = self.field_vars["Student Data"]["col_name"].get()
        s_join = self.field_vars["Academic Data"]["join_student"].get()
        
        att = self.field_vars["Academic Data"]["col_attendance"].get()
        
        # We need to construct the mapping dictionary compatible with the system
        mapping = {
            "tbl_student": s_tbl, 
            "tbl_academic": a_tbl, 
            "tbl_branch": b_tbl, 
            "col_student_join": s_join, 
            "col_branch_join": self.field_vars["Student Data"]["join_branch"].get(), 
            "col_id": s_id, 
            "col_name": s_name, 
            "col_branch_name": self.field_vars["Branch Data"]["col_branch_name"].get(), 
            "col_att": att, 
            "col_marks": self.field_vars["Academic Data"]["col_marks"].get(), 
            "col_backlogs": self.field_vars["Academic Data"]["col_backlogs"].get(), 
            "col_tenth": self.field_vars["Academic Data"]["col_tenth"].get(),
            "col_inter": self.field_vars["Academic Data"]["col_inter"].get(),
            "col_diploma": self.field_vars["Academic Data"]["col_diploma"].get(),
            "col_lab_perf": self.field_vars["Academic Data"]["col_lab"].get(),
            "col_mid_exam": self.field_vars["Academic Data"]["col_mid"].get(),
            "col_cons_abs": self.field_vars["Academic Data"]["col_cons_abs"].get(),
            "col_leave_freq": self.field_vars["Academic Data"]["col_leave"].get(),
            "col_parent_phone": self.field_vars["Student Data"]["col_p_phone"].get(),
            "col_parent_email": self.field_vars["Student Data"]["col_p_email"].get(),
            "col_year": self.field_vars["Student Data"]["col_year"].get(), 
            "col_email": self.field_vars["Student Data"]["col_email"].get()
        }
        
        def run_test():
            try:
                sql = f"SELECT s.{s_id}, s.{s_name}, a.{att} FROM {s_tbl} s JOIN {a_tbl} a ON s.{s_id} = a.{s_join} LIMIT 3"
                import mysql.connector
                conn = mysql.connector.connect(
                    host=self.host.get(), user=self.user.get(), password=self.pwd.get(), 
                    database=self.db_name.get(), port=int(self.port.get()), connect_timeout=3
                )
                cursor = conn.cursor(dictionary=True)
                cursor.execute(sql)
                samples = cursor.fetchall()
                conn.close()
                
                if samples:
                    self.after(0, lambda: self.on_validation_success(mapping, samples))
                else:
                    self.after(0, lambda: self.on_validation_fail("Tables joined successfully but returned 0 records."))
            except Exception as e:
                self.after(0, lambda: self.on_validation_fail(str(e)))
                
        threading.Thread(target=run_test, daemon=True).start()

    def on_validation_fail(self, msg):
        self.btn_action.configure(state="normal", text="VALIDATE & SAVE CONFIG")
        ModernMessagebox("Validation Failed", f"Schema validation failed:\n{msg}", "error")

    def on_validation_success(self, mapping, samples):
        # Save logic
        college = self.controller.shared_data.get("college_name", "Default College")
        tech = self.db_tech.get()
        host = self.host.get()
        port = self.port.get()
        db = self.db_name.get()
        user = self.user.get()
        pwd = self.pwd.get()
        
        if CentralAuth().save_erp_config(college, tech, host, port, db, user, pwd, mapping):
            config_data = mapping.copy()
            config_data["host"] = host
            config_data["user"] = user
            config_data["password"] = pwd
            config_data["database"] = db
            config_data["port"] = port
            
            self.controller.shared_data.update({
                "erp_config": config_data, 
                "erp_setup_needed": False
            })
            
            ModernMessagebox("Success", "ERP Schema Detected & Saved Successfully!", "success")
            self.dash.on_show()
        else:
            self.btn_action.configure(state="normal", text="VALIDATE & SAVE CONFIG")
            ModernMessagebox("Save Failed", "Could not save configuration to CentralAuth.", "error")
