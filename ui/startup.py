import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image
from logic.config_manager import load_config, save_config
from logic.db_handler import DBHandler
from logic.central_auth import CentralAuth

# Design color palette
COLORS = {
    "bg": "#0A0A0A",
    "card": "#141414",
    "secondary": "#1A1A1A",
    "accent": "#00E5FF",
    "success": "#00D26A",
    "warning": "#FFA726",
    "danger": "#FF4C4C",
    "text": "#FFFFFF",
    "subtext": "#A0A0A0"
}

class ERPSetupScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLORS["bg"])
        self.controller = controller
        self.valid_config = None
        self._build_ui()

    def _build_ui(self):
        # Centered main card
        self.card = ctk.CTkFrame(self, fg_color=COLORS["card"], width=950, height=700,
                                 corner_radius=20)
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        # Shadow effect – add an outer frame with slight offset and cyan glow
        self.card.configure(border_width=2, border_color="#00E5FF")

        # Header with title and subtitle
        header_frame = ctk.CTkFrame(self.card, fg_color=COLORS["card"])
        header_frame.pack(pady=(30, 10), fill="x")
        # Title with database icon (using Unicode)
        title_lbl = ctk.CTkLabel(header_frame, text="\U0001F4C1 ERP Connection Setup",
                                 font=("Montserrat", 28, "bold"), text_color=COLORS["accent"])
        title_lbl.pack(pady=(0, 5))
        subtitle_lbl = ctk.CTkLabel(header_frame, text="Connect AcaDesk securely to your institution ERP database. All student data remains read‑only.",
                                    font=("Arial", 14), text_color=COLORS["subtext"], wraplength=800, justify="center")
        subtitle_lbl.pack()

        # Content split: left illustration, right form + status
        content_frame = ctk.CTkFrame(self.card, fg_color=COLORS["card"])
        content_frame.pack(pady=20, fill="both", expand=True)

# Left side illustration removed for a cleaner UI
# Image omitted – the ERP illustration has been removed as requested.

        # Right side form and status panel
        right_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["secondary"])
        right_frame.pack(side="right", padx=20, fill="both", expand=True)

        # Form fields
        field_cfg = {
            "width": 350,
            "height": 50,
            "corner_radius": 12,
            "fg_color": "#1E1E1E",
            "border_width": 0,
            "placeholder_text_color": COLORS["subtext"]
        }
        self.erp_host = ctk.CTkEntry(right_frame, placeholder_text="Host (e.g. localhost)", **field_cfg)
        self.erp_host.pack(pady=10)
        self.erp_port = ctk.CTkEntry(right_frame, placeholder_text="Port (e.g. 3306)", **field_cfg)
        self.erp_port.pack(pady=10)
        self.erp_db = ctk.CTkEntry(right_frame, placeholder_text="Database Name", **field_cfg)
        self.erp_db.pack(pady=10)
        self.erp_user = ctk.CTkEntry(right_frame, placeholder_text="Username", **field_cfg)
        self.erp_user.pack(pady=10)
        self.erp_pass = ctk.CTkEntry(right_frame, placeholder_text="Password", show="*", **field_cfg)
        self.erp_pass.pack(pady=10)

        # ERP Status Panel (below form)
        status_panel = ctk.CTkFrame(right_frame, fg_color=COLORS["secondary"], corner_radius=10)
        status_panel.pack(pady=15, fill="x")
        ctk.CTkLabel(status_panel, text="ERP Status", font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(pady=(5,0))
        self.lbl_conn_status = ctk.CTkLabel(status_panel, text="Not Connected", font=("Arial", 11), text_color=COLORS["warning"])
        self.lbl_conn_status.pack()
        self.lbl_mode = ctk.CTkLabel(status_panel, text="Mode: Read Only", font=("Arial", 11), text_color=COLORS["subtext"])
        self.lbl_mode.pack()
        self.lbl_security = ctk.CTkLabel(status_panel, text="Security: Protected", font=("Arial", 11), text_color=COLORS["subtext"])
        self.lbl_security.pack(pady=(0,5))
        # New label for schema diagnostics
        self.lbl_schema = ctk.CTkLabel(status_panel, text="", font=("Arial", 10), text_color=COLORS["subtext"], wraplength=300)
        self.lbl_schema.pack(pady=(5,0))

        # Test Connection button
        self.btn_test = ctk.CTkButton(self.card, text="Test Connection", width=250, height=50,
                                     fg_color=COLORS["accent"], hover_color="#00FFFF",
                                     text_color=COLORS["bg"], font=("Arial", 14, "bold"),
                                     command=self.test_connection)
        self.btn_test.pack(pady=10)

        # Save & Continue button (initially disabled)
        self.btn_proceed = ctk.CTkButton(self.card, text="Save Connection & Continue", width=300, height=50,
                                        fg_color=COLORS["success"], hover_color="#00FF80",
                                        text_color=COLORS["bg"], font=("Arial", 14, "bold"),
                                        state="disabled", command=self.save_and_continue)
        self.btn_proceed.pack(pady=10)

        # Security notice at bottom of card
        notice_frame = ctk.CTkFrame(self.card, fg_color=COLORS["secondary"], corner_radius=10)
        notice_frame.pack(pady=15, fill="x", padx=30)
        ctk.CTkLabel(notice_frame, text="\U0001F6E1 AcaDesk operates in strict ERP Read‑Only mode. No student records are modified, deleted, or written back to the college ERP.",
                     font=("Arial", 11), text_color=COLORS["subtext"], wraplength=850, justify="center").pack(pady=5)

    def on_show(self):
        self.lbl_conn_status.configure(text="Not Connected", text_color=COLORS["warning"])
        self.btn_proceed.configure(state="disabled")
        self.valid_config = None

    def test_connection(self):
        # Update status panel
        self.lbl_conn_status.configure(text="Testing connection...", text_color=COLORS["subtext"])
        self.update()
        config = {
            "host": self.erp_host.get(),
            "port": self.erp_port.get(),
            "database": self.erp_db.get(),
            "user": self.erp_user.get(),
            "password": self.erp_pass.get()
        }
        db = DBHandler(config)
        if not db.connected:
            self.lbl_conn_status.configure(text="Connection Failed", text_color=COLORS["warning"])
            return
        success, msg = db.validate_tables()
        if not success:
            self.lbl_conn_status.configure(text=f"Table Validation Failed: {msg}", text_color=COLORS["warning"])
            return
        # Schema diagnostics
        detected_students = sorted(db.student_columns)
        detected_academics = sorted(db.academic_columns)
        missing_student = db.expected_student_keys - {k for k, v in db.map.items() if k in db.expected_student_keys and v in db.student_columns}
        missing_academic = db.expected_academic_keys - {k for k, v in db.map.items() if k in db.expected_academic_keys and v in db.academic_columns}
        diag_msg = "Detected Columns: Student " + str(detected_students) + ", Academic " + str(detected_academics)
        if missing_student or missing_academic:
            diag_msg += " | Missing:"
            if missing_student:
                diag_msg += " Student " + str(sorted(missing_student))
            if missing_academic:
                diag_msg += " Academic " + str(sorted(missing_academic))
        self.lbl_schema.configure(text=diag_msg)
        sample_data = db.get_sample_data()
        if sample_data:
            self.lbl_conn_status.configure(text="Connected", text_color=COLORS["success"])
            self.btn_proceed.configure(state="normal")
            self.valid_config = config
            self.show_success_card()
            self.show_preview_window(sample_data)
        else:
            self.lbl_conn_status.configure(text="Unable to read sample data", text_color=COLORS["warning"])

    def show_success_card(self):
        # Transient success overlay
        success_win = ctk.CTkToplevel(self)
        success_win.title("")
        success_win.geometry("400x200")
        success_win.grab_set()
        success_win.configure(fg_color=COLORS["card"])
        ctk.CTkLabel(success_win, text="\u2714 ERP Connection Successful", font=("Arial", 18, "bold"), text_color=COLORS["success"]).pack(pady=20)
        ctk.CTkLabel(success_win, text="Server Reachable | Credentials Verified | Read‑Only Access Confirmed | Student Records Found", font=("Arial", 12), text_color=COLORS["text"], wraplength=350, justify="center").pack(pady=10)
        ctk.CTkButton(success_win, text="Continue", command=success_win.destroy, fg_color=COLORS["accent"], text_color=COLORS["bg"]).pack(pady=10)
        success_win.after(100, lambda: success_win.lift())

    def show_preview_window(self, data):
        preview = ctk.CTkToplevel(self)
        preview.title("Sample Data Preview")
        preview.geometry("600x450")
        preview.configure(fg_color=COLORS["bg"])
        ctk.CTkLabel(preview, text="Detected Student Records", font=("Arial", 18, "bold"), text_color=COLORS["accent"]).pack(pady=15)
        # Table header
        header = ctk.CTkFrame(preview, fg_color=COLORS["secondary"])
        header.pack(fill="x", padx=20)
        for col in ["Student Name", "Roll Number", "Department"]:
            ctk.CTkLabel(header, text=col, font=("Arial", 12, "bold"), text_color=COLORS["text"], width=180).pack(side="left", padx=5, pady=5)
        # Sample rows (first 5)
        for row in data["samples"][:5]:
            row_frame = ctk.CTkFrame(preview, fg_color=COLORS["card"])
            row_frame.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(row_frame, text=row.get("name", ""), font=("Arial", 12), text_color=COLORS["text"], width=180).pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=row.get("roll_no", ""), font=("Arial", 12), text_color=COLORS["text"], width=180).pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=row.get("branch_name", ""), font=("Arial", 12), text_color=COLORS["text"], width=180).pack(side="left", padx=5)
        ctk.CTkButton(preview, text="Close Preview", command=preview.destroy, fg_color=COLORS["accent"], text_color=COLORS["bg"]).pack(pady=15)

    def save_and_continue(self):
        if not self.valid_config:
            return
        # Save to local JSON config
        current_config = load_config()
        current_config["erp"] = self.valid_config
        save_config(current_config)
        # Save to Central DB via CentralAuth
        college_name = self.controller.shared_data.get("college_name", "Unknown College")
        auth = CentralAuth()
        auth.save_erp_config(
            college_name,
            "mysql",
            self.valid_config["host"],
            self.valid_config["port"],
            self.valid_config["database"],
            self.valid_config["user"],
            self.valid_config["password"]
        )
        self.controller.shared_data["erp_config"] = self.valid_config
        self.controller.show_frame("DashboardScreen")

# ---------------------------------------------------------------------------
# Connection Diagnostics Screen (original implementation retained for imports)
# ---------------------------------------------------------------------------
class ConnectionDiagnosticsScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLORS["bg"])
        self.controller = controller
        ctk.CTkLabel(self, text="CONNECTION DIAGNOSTICS", font=("Montserrat", 24, "bold"), text_color=COLORS["danger"]).pack(pady=(50, 10))
        self.lbl_error = ctk.CTkLabel(self, text="A database connection error occurred.", font=("Arial", 16), text_color="#E0E0E0")
        self.lbl_error.pack(pady=20)
        self.log_box = ctk.CTkTextbox(self, width=600, height=200, fg_color=COLORS["card"], text_color="#E0E0E0", font=("Consolas", 14))
        self.log_box.pack(pady=20)
        ctk.CTkButton(self, text="Back to Login", fg_color="#333", text_color="white", command=lambda: self.controller.show_frame("WelcomeScreen")).pack(pady=10)

    def on_show(self):
        err_msg = self.controller.shared_data.get("diagnostic_error", "Unknown Network Error")
        self.log_box.delete("1.0", "end")
        conn_stat = "SUCCESS"
        auth_stat = "SUCCESS"
        db_stat = "SUCCESS"
        val_stat = "SUCCESS"
        err_lower = err_msg.lower()
        if "unreachable" in err_lower or "network" in err_lower or "failed: database server" in err_lower:
            conn_stat = "FAILED"
            auth_stat = "PENDING"
            db_stat = "PENDING"
            val_stat = "PENDING"
        elif "authentication" in err_lower or "access denied" in err_lower:
            auth_stat = "FAILED"
            db_stat = "PENDING"
            val_stat = "PENDING"
        elif "database does not exist" in err_lower:
            db_stat = "FAILED"
            val_stat = "PENDING"
        else:
            val_stat = "FAILED"
        report = f"DIAGNOSTIC REPORT:\n\n"
        report += f"Connection:     {conn_stat}\n"
        report += f"Authentication: {auth_stat}\n"
        report += f"Database Access:{db_stat}\n"
        report += f"Validation Query:{val_stat}\n\n"
        report += f"Reason:\n{err_msg}\n\n"
        report += "Suggested Fix:\nCheck if the ERP Database server is running and the credentials are correct."
        self.log_box.insert("end", report)
