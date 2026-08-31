import customtkinter as ctk
import threading
import json
import logging
import mysql.connector
from ui.dashboard import ModernMessagebox, COLORS
from logic.central_auth import CentralAuth

logger = logging.getLogger(__name__)

class ERPWizard(ctk.CTkFrame):
    def __init__(self, parent, controller, dash):
        super().__init__(parent, fg_color="#0B0E14")
        self.controller = controller
        self.dash = dash
        self.current_step = 1
        self.schema_graph = {}
        self.all_tables = []
        self.suggestions = {}
        self.mapping = {}
        self.preview_records = []
        self.validation_msg = ""
        self.validation_passed = False
        
        self.container = ctk.CTkFrame(self, corner_radius=16, fg_color="#12141E", border_width=1, border_color="#2A2E3F")
        self.container.pack(fill="both", expand=True, padx=120, pady=40)
        
        self.header = ctk.CTkFrame(self.container, fg_color="transparent")
        self.header.pack(fill="x", pady=(30, 10), padx=30)
        
        head_lbl = ctk.CTkLabel(self.header, text="INTELLIGENT ERP INTEGRATION", font=("Outfit", 26, "bold"), text_color="#00E5FF")
        head_lbl.pack(anchor="w")
        
        self.step_lbl = ctk.CTkLabel(self.header, text="Step 1 of 3", font=("Inter", 14), text_color="#7A849C")
        self.step_lbl.pack(anchor="w")
        
        self.footer = ctk.CTkFrame(self.container, fg_color="transparent")
        self.footer.pack(fill="x", padx=40, pady=20, side="bottom")
        
        self.main_body = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_body.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.btn_back = ctk.CTkButton(self.footer, text="← BACK", height=45, fg_color="transparent", text_color="#7A849C", hover_color="#1A1D2D", font=("Inter", 13), command=self.prev_step)
        self.btn_action = ctk.CTkButton(self.footer, text="CONNECT & SCAN →", height=45, fg_color="#00E5FF", hover_color="#00B3CC", font=("Outfit", 15, "bold"), text_color="black", command=self.do_scan)
        
        self.init_steps()
        self.show_step(1)

    def on_show(self):
        erp_config = self.controller.shared_data.get("erp_config")
        if erp_config:
            if erp_config.get("mapping_confirmed_by_human"):
                # Setup complete, skip wizard
                self.controller.show_frame("LoadingScreen")
                return
            else:
                ModernMessagebox("Verification Required", "Your ERP schema mapping needs manual verification.", "info")
                if "host" in erp_config:
                    self.host.delete(0, "end")
                    self.host.insert(0, erp_config["host"])
                if "port" in erp_config:
                    self.port.delete(0, "end")
                    self.port.insert(0, str(erp_config["port"]))
                if "database" in erp_config:
                    self.db_name.delete(0, "end")
                    self.db_name.insert(0, erp_config["database"])
                if "user" in erp_config:
                    self.user.delete(0, "end")
                    self.user.insert(0, erp_config["user"])
                if "password" in erp_config:
                    self.pwd.delete(0, "end")
                    self.pwd.insert(0, erp_config["password"])
                self.after(500, self.do_scan)

    def _get_connection(self):
        return mysql.connector.connect(
            host=self.host.get().strip(),
            port=self.port.get().strip(),
            database=self.db_name.get().strip(),
            user=self.user.get().strip(),
            password=self.pwd.get().strip()
        )

    def init_steps(self):
        # Step 1: Credentials
        self.s1 = ctk.CTkFrame(self.main_body, fg_color="transparent")
        form_scroll = ctk.CTkScrollableFrame(self.s1, fg_color="transparent")
        form_scroll.pack(side="left", fill="both", expand=True, padx=10)
        
        info_panel = ctk.CTkFrame(self.s1, fg_color="#151923", corner_radius=15, width=300, border_color="#2A2F45", border_width=1)
        info_panel.pack(side="right", fill="y", padx=10)
        info_panel.pack_propagate(False)
        ctk.CTkLabel(info_panel, text="1. Connect to ERP", font=("Outfit", 20, "bold"), text_color="#00E5FF").pack(pady=(30, 15))
        ctk.CTkLabel(info_panel, text="Provide Database Server Credentials.\n\nWe will perform a lightweight metadata scan to automatically find the major business entities.", text_color="#8B949E", font=("Inter", 14), wraplength=250, justify="left").pack(padx=25)
        
        def add_field(parent, label_text, default_value, secret=False):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=10)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=label_text, font=("Outfit", 14), text_color="#A1A9B8", anchor="w", width=140).grid(row=0, column=0, sticky="w", padx=(10,0))
            entry = ctk.CTkEntry(row, height=45, fg_color="#1A1D2D", border_color="#2A2F45", text_color="white", font=("Inter", 14), corner_radius=8)
            entry.insert(0, default_value)
            if secret: entry.configure(show="•")
            entry.grid(row=0, column=1, sticky="ew", padx=(10, 40))
            return entry

        self.db_tech = add_field(form_scroll, "Database Type:", "MySQL / MariaDB")
        self.db_tech.configure(state="readonly")
        
        self.host = add_field(form_scroll, "Host IP:", "localhost")
        self.port = add_field(form_scroll, "Port:", "3306")
        self.db_name = add_field(form_scroll, "DB Name:", "engineering_college")
        self.user = add_field(form_scroll, "User:", "root")
        self.pwd = add_field(form_scroll, "Password:", "", True)
        
        # Step 2: Table Confirmation
        self.s2 = ctk.CTkScrollableFrame(self.main_body, fg_color="transparent")
        self.lbl_scan_status = ctk.CTkLabel(self.s2, text="", font=("Arial", 14), text_color=COLORS["warning"])
        self.lbl_scan_status.pack(pady=(0,10))
        
        self.table_frame = ctk.CTkFrame(self.s2, fg_color="#1A1D2D", corner_radius=10)
        self.table_frame.pack(fill="both", expand=True, padx=40, pady=10)
        
        ctk.CTkLabel(self.table_frame, text="Confirm Major Entities", font=("Outfit", 20, "bold"), text_color="#00E5FF").pack(pady=(20,5))
        ctk.CTkLabel(self.table_frame, text="We've discovered the structure. Please confirm the main tables. AcaDesk will automatically map all columns, relationships, and derived features for you.", text_color="#A1A9B8", font=("Inter", 13), wraplength=500).pack(pady=(0,20))

        self.table_selectors_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.table_selectors_frame.pack(fill="x", padx=40, pady=10)
        
        self.optional_frame = ctk.CTkFrame(self.table_frame, fg_color="#151923", corner_radius=8)
        self.optional_frame.pack(fill="x", padx=40, pady=10)
        
        btn_rescan = ctk.CTkButton(self.table_frame, text="↻ Re-scan selected tables", fg_color="transparent", border_width=1, border_color="#3A3F55", hover_color="#2A2F45", command=self.do_deep_discover_and_preview)
        btn_rescan.pack(pady=20)

        # Step 3: Preview Data
        self.s3 = ctk.CTkScrollableFrame(self.main_body, fg_color="transparent")
        
        self.lbl_s3_status = ctk.CTkLabel(self.s3, text="", font=("Arial", 14))
        self.lbl_s3_status.pack(pady=(0,10))
        
        self.preview_cards_frame = ctk.CTkFrame(self.s3, fg_color="transparent")
        self.preview_cards_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.mapping_summary_frame = ctk.CTkFrame(self.s3, fg_color="#1A1D2D", corner_radius=10)
        self.mapping_summary_frame.pack(fill="x", padx=20, pady=20)

    def show_step(self, s):
        self.current_step = s
        self.s1.pack_forget()
        self.s2.pack_forget()
        self.s3.pack_forget()
        self.btn_back.pack_forget()
        self.btn_action.pack_forget()
        
        self.step_lbl.configure(text=f"Step {s} of 3")
        
        if s == 1:
            self.s1.pack(fill="both", expand=True)
            self.btn_action.configure(text="CONNECT & SCAN →", fg_color="#00E5FF", command=self.do_scan)
            self.btn_action.pack(side="right")
        elif s == 2:
            self.s2.pack(fill="both", expand=True)
            self.btn_back.pack(side="left")
            self.btn_action.configure(text="PREVIEW DATA →", fg_color="#FF9100", command=self.do_deep_discover_and_preview)
            self.btn_action.pack(side="right")
        elif s == 3:
            self.s3.pack(fill="both", expand=True)
            self.btn_back.pack(side="left")
            self.btn_action.configure(text="CONFIRM & SAVE", fg_color="#00C853", command=self.validate_and_save)
            if not self.validation_passed:
                self.btn_action.configure(state="disabled", fg_color="#3A3F55")
            self.btn_action.pack(side="right")

    def prev_step(self):
        if self.current_step == 3:
            self.show_step(2)
        elif self.current_step == 2:
            self.show_step(1)

    def do_scan(self):
        host = self.host.get().strip()
        db = self.db_name.get().strip()
        if not all([host, self.port.get(), db, self.user.get()]):
            ModernMessagebox("Missing Info", "Please fill all connection fields.", "warning")
            return
            
        self.btn_action.configure(state="disabled", text="SCANNING METADATA...")
        
        def scan_thread():
            try:
                conn = self._get_connection()
                from logic.table_discoverer import LightweightMetadataScan
                scan = LightweightMetadataScan(conn, db)
                all_tables, schema_graph = scan.run_scan()
                suggestions = scan.score_tables()
                conn.close()
                self.after(0, lambda: self.scan_success(suggestions, all_tables, schema_graph))
            except Exception as e:
                self.after(0, lambda: self.scan_failed(f"Scan error: {str(e)}"))

        threading.Thread(target=scan_thread, daemon=True).start()

    def scan_failed(self, msg):
        self.btn_action.configure(state="normal", text="CONNECT & SCAN →")
        ModernMessagebox("Scan Failed", f"Could not connect or scan database:\n{msg}", "error")

    def scan_success(self, suggestions, all_tables, schema_graph):
        self.btn_action.configure(state="normal")
        self.all_tables = all_tables
        self.schema_graph = schema_graph
        self.suggestions = suggestions
        self.table_vars = {}
        
        self.lbl_scan_status.configure(text="Metadata scanned successfully.", text_color=COLORS["success"])
        
        for w in self.table_selectors_frame.winfo_children(): w.destroy()
        for w in self.optional_frame.winfo_children(): w.destroy()
            
        entities = [
            ("STUDENT", "Student information table", "The main table with one row per enrolled student."),
            ("ACADEMIC", "Academic results table", "Marks, grades, and semester results."),
            ("ATTENDANCE", "Attendance records table", "Daily or aggregated attendance records."),
            ("DEPARTMENT", "Department / branch table", "Branch/department details.")
        ]
        
        all_opts = [""] + self.all_tables
        
        def build_row(parent, role, label, desc):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=15, padx=10)
            row.grid_columnconfigure(1, weight=1)
            
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.grid(row=0, column=0, sticky="w", padx=(0, 20))
            
            ctk.CTkLabel(info_frame, text=label, font=("Outfit", 16, "bold"), text_color="#E2E8F0").pack(anchor="w")
            ctk.CTkLabel(info_frame, text=desc, font=("Inter", 12), text_color="#7A849C").pack(anchor="w")
            
            cb = ctk.CTkComboBox(row, values=all_opts, width=250, height=40, font=("Inter", 14))
            cb.grid(row=0, column=1, sticky="e", padx=10)
            
            # Find best suggestion
            suggs = self.suggestions.get(role, [])
            best = suggs[0] if suggs else None
            
            if best and best["confidence"] >= 40:
                cb.set(best["table"])
                conf = best["confidence"]
                color = "#00C853" if conf >= 80 else "#FF9100" if conf >= 60 else "#FF3D00"
                badge = ctk.CTkLabel(row, text=f"{conf}% match", text_color=color, font=("Outfit", 12, "bold"))
                badge.grid(row=0, column=2, sticky="w")
            else:
                cb.set("")
                ctk.CTkLabel(row, text="Manual selection required", text_color="#FF3D00", font=("Outfit", 12)).grid(row=0, column=2, sticky="w")
                
            self.table_vars[role] = cb
            
            cols_lbl = ctk.CTkLabel(row, text="", font=("Inter", 11), text_color="#5A647C")
            cols_lbl.grid(row=1, column=1, sticky="e", padx=10)
            
            def update_cols(*args):
                tbl = cb.get()
                if tbl in self.schema_graph["tables"]:
                    c_count = len(self.schema_graph["tables"][tbl]["columns"])
                    top_cols = list(self.schema_graph["tables"][tbl]["columns"].keys())[:3]
                    cols_lbl.configure(text=f"{c_count} cols. Top: {', '.join(top_cols)}")
                else:
                    cols_lbl.configure(text="")
            update_cols()
            # In a real app we'd bind command, but ComboBox doesn't always support easy binding without trace, we'll just update on rescan.

        for role, lbl, desc in entities:
            build_row(self.table_selectors_frame, role, lbl, desc)
            
        ctk.CTkLabel(self.optional_frame, text="Optional tables (expand to configure)", text_color="#A1A9B8", font=("Inter", 13, "bold")).pack(pady=10)
        build_row(self.optional_frame, "ADMISSION", "Admission details table", "Optional.")
        build_row(self.optional_frame, "PARENT", "Parent contacts table", "Optional.")
            
        self.show_step(2)

    def do_deep_discover_and_preview(self):
        confirmed = {k: v.get() for k, v in self.table_vars.items() if v.get()}
        if not confirmed.get("STUDENT") or not confirmed.get("ACADEMIC") or not confirmed.get("ATTENDANCE") or not confirmed.get("DEPARTMENT"):
            ModernMessagebox("Missing Required Tables", "Please select all four required entities.", "warning")
            return
            
        self.btn_action.configure(state="disabled", text="ANALYZING...")
        
        def discover_thread():
            try:
                # Phase 3
                from logic.relationship_discoverer import BoundedRelationshipDiscovery
                rel_disc = BoundedRelationshipDiscovery(self.schema_graph, confirmed)
                join_paths, scope = rel_disc.run_discovery()
                
                # Phase 4 & 5
                from logic.column_resolver import ColumnResolver
                conn = self._get_connection()
                col_res = ColumnResolver(conn, self.schema_graph, scope, confirmed, join_paths)
                try:
                    mapping = col_res.run_resolution()
                except Exception as e:
                    logger.error("Column resolution failed unexpectedly: %s", e, exc_info=True)
                    mapping = {"is_partial": True, "error": str(e)}
                
                # Build final flat mapping
                flat_mapping = {
                    "tbl_student": confirmed.get("STUDENT"),
                    "tbl_academic": confirmed.get("ACADEMIC"),
                    "tbl_attendance": confirmed.get("ATTENDANCE"),
                    "tbl_branch": confirmed.get("DEPARTMENT"),
                    "tbl_parent": confirmed.get("PARENT"),
                    "tbl_admission": confirmed.get("ADMISSION"),
                    "join_path_academic": json.dumps(join_paths.get("student_to_academic", {})),
                    "join_path_attendance": json.dumps(join_paths.get("student_to_attendance", {})),
                    "extended_features_json": mapping.get("extended_features_json", "[]"),
                    "strategy": "INTELLIGENT_ADAPTER"
                }
                
                # Flatten resolved fields
                for field, res in mapping.items():
                    if field == "extended_features_json": continue
                    
                    method = res.get("method")
                    if field == "student_id":
                        flat_mapping["col_student_pk"] = res.get("column")
                    elif field == "full_name":
                        flat_mapping["col_student_name"] = res.get("column")
                    elif field == "department_fk":
                        flat_mapping["col_branch_type"] = method
                        if method == "FK_LOOKUP":
                            flat_mapping["col_branch_fk"] = res.get("column")
                            flat_mapping["col_branch_pk"] = res.get("ref_pk")
                            flat_mapping["col_branch_name"] = res.get("ref_display")
                        elif method == "DIRECT":
                            flat_mapping["col_branch_name"] = res.get("column")
                    elif field == "current_year":
                        flat_mapping["col_year_type"] = method
                        if method == "FK_LOOKUP":
                            flat_mapping["col_student_year"] = res.get("column")
                            flat_mapping["col_year_lookup_table"] = res.get("ref_table")
                            flat_mapping["col_year_lookup_pk"] = res.get("ref_pk")
                            flat_mapping["col_year_lookup_val"] = res.get("ref_display")
                        elif method == "DIRECT":
                            flat_mapping["col_student_year"] = res.get("column")
                        # DERIVED handling handled by preview logic internally via joins/formulas
                    elif field == "attendance_pct":
                        flat_mapping["col_att_type"] = method
                        if method == "DERIVED_AGGREGATE":
                            flat_mapping["col_attendance_join"] = res.get("student_fk")
                            flat_mapping["col_attendance_status"] = res.get("status_col")
                            flat_mapping["col_attendance_present_vals"] = ",".join([f"'{v}'" if isinstance(v, str) else str(v) for v in res.get("present_values", [])])
                        elif method == "DIRECT":
                            flat_mapping["col_att_pct"] = res.get("column")
                    elif field == "cgpa":
                        flat_mapping["col_cgpa_type"] = method
                        if method == "DIRECT": flat_mapping["col_cgpa"] = res.get("column")
                    elif field == "backlogs":
                        flat_mapping["col_backlogs_type"] = method
                        if method == "DIRECT": flat_mapping["col_backlogs"] = res.get("column")
                    elif field == "internal_marks":
                        if method == "DIRECT": flat_mapping["col_internal_marks"] = res.get("column")
                    else:
                        if method == "DIRECT":
                            flat_mapping[f"col_{field}"] = res.get("column")
                            
                self.mapping = flat_mapping
                self.mapping_full = mapping # Keep rich mapping for preview cards
                
                # Phase 6
                from logic.preview_builder import PreviewQueryBuilder
                pb = PreviewQueryBuilder(conn, mapping)
                success = pb.run_preview()
                valid, msg = pb.validate_gate()
                
                conn.close()
                
                self.validation_passed = valid
                self.validation_msg = msg
                self.preview_records = pb.records
                self.sql_error = pb.sql_error
                
                self.after(0, self.show_preview)
            except Exception as e:
                logger.error(f"Discovery error: {e}")
                self.after(0, lambda: self.scan_failed(f"Discovery error: {str(e)}"))
                
        threading.Thread(target=discover_thread, daemon=True).start()

    def show_preview(self):
        self.btn_action.configure(state="normal")
        self.show_step(3)
        
        for w in self.preview_cards_frame.winfo_children(): w.destroy()
        for w in self.mapping_summary_frame.winfo_children(): w.destroy()
        
        if not self.validation_passed:
            self.lbl_s3_status.configure(text=self.validation_msg, text_color=COLORS["danger"])
            if self.sql_error:
                ctk.CTkLabel(self.preview_cards_frame, text=f"SQL Error: {self.sql_error}", text_color=COLORS["danger"]).pack(pady=10)
        else:
            self.lbl_s3_status.configure(text="Validation Passed. Please review data below.", text_color=COLORS["success"])
            
        for rec in self.preview_records:
            card = ctk.CTkFrame(self.preview_cards_frame, fg_color="#151923", corner_radius=8, border_width=1, border_color="#2A2F45")
            card.pack(fill="x", pady=10)
            
            header = ctk.CTkLabel(card, text=f"{rec.get('full_name', 'Unknown')} • {rec.get('student_id', 'No ID')}", font=("Outfit", 16, "bold"), text_color="#00E5FF")
            header.pack(anchor="w", padx=15, pady=(10,5))
            
            def add_row(lbl, key, map_key):
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=15, pady=2)
                row.grid_columnconfigure(1, weight=1)
                
                ctk.CTkLabel(row, text=f"{lbl}:", text_color="#A1A9B8", font=("Inter", 13), width=100, anchor="w").grid(row=0, column=0, sticky="w")
                val = rec.get(key)
                if val is None: val = "—"
                ctk.CTkLabel(row, text=str(val), text_color="white", font=("Inter", 13, "bold")).grid(row=0, column=1, sticky="w")
                
                method = self.mapping_full.get(map_key, {}).get("method", "ABSENT")
                badge_text = ""
                badge_color = "#5A647C"
                if method == "DIRECT":
                    badge_text = "[✓ direct column]"
                    badge_color = "#00C853"
                elif method == "DERIVED_AGGREGATE":
                    badge_text = "[✓ auto-computed]"
                    badge_color = "#00E5FF"
                elif method == "FK_LOOKUP":
                    badge_text = "[✓ via lookup]"
                    badge_color = "#FF9100"
                elif method == "ABSENT":
                    badge_text = "[⚠ not found]"
                    badge_color = "#FF3D00"
                    
                ctk.CTkLabel(row, text=badge_text, text_color=badge_color, font=("Inter", 11)).grid(row=0, column=2, sticky="e")
                
            add_row("Department", "department", "department_fk")
            add_row("Year", "year", "current_year")
            add_row("Attendance", "attendance_pct", "attendance_pct")
            add_row("Int. Marks", "internal_marks", "internal_marks")
            add_row("CGPA", "cgpa", "cgpa")
            add_row("Backlogs", "backlogs", "backlogs")
            
        # Summary mapping table
        if self.mapping_full.get("is_partial"):
            ctk.CTkLabel(self.mapping_summary_frame, text="Automatic detection found limited matches. Review the suggestions and use the table selectors to help the system find your data.", text_color=COLORS["warning"], wraplength=500).pack(pady=10)
            
        ctk.CTkLabel(self.mapping_summary_frame, text="Mapping Summary", font=("Outfit", 16, "bold"), text_color="white").pack(pady=10)

        
        for k, v in self.mapping_full.items():
            if k == "extended_features_json": continue
            row = ctk.CTkFrame(self.mapping_summary_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            row.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(row, text=k, font=("Inter", 12), text_color="#00E5FF", width=150, anchor="w").grid(row=0, column=0, sticky="w")
            
            method = v.get("method", "ABSENT")
            desc = method
            if method == "DIRECT": desc = f"{v.get('table', '')}.{v.get('column', '')}"
            elif method == "FK_LOOKUP": desc = f"{v.get('table', '')}.{v.get('column', '')} -> {v.get('ref_table', '')}"
            
            ctk.CTkLabel(row, text=desc, font=("Inter", 12), text_color="#A1A9B8").grid(row=0, column=1, sticky="w")

    def validate_and_save(self):
        host = self.host.get().strip()
        port = self.port.get().strip()
        db = self.db_name.get().strip()
        user = self.user.get().strip()
        pwd = self.pwd.get().strip()
        
        from datetime import datetime
        self.mapping["discovery_timestamp"] = datetime.now().isoformat()
        self.mapping["mapping_confirmed_by_human"] = 1
        
        auth = CentralAuth()
        college = self.controller.shared_data['college_name']
        ok = auth.save_erp_config(college, "MySQL", host, port, db, user, pwd, self.mapping)
        if ok:
            # Sync
            self.controller.shared_data["erp_config"] = self.mapping
            self.controller.show_frame("LoadingScreen")
        else:
            ModernMessagebox("Save Failed", "Could not save mapping to DB.", "error")
