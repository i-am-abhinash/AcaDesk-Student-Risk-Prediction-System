import customtkinter as ctk
from tkinter import messagebox
import os
import sys

# Ensure we can find the ui folder
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# IMPORT DASHBOARD
from ui.dashboard import DashboardScreen
from ui.login import LoginScreen, RegisterScreen
from ui.startup import ERPSetupScreen, ConnectionDiagnosticsScreen

# --- CONFIG & STYLES ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Colors for Popups
COLORS = {
    "danger": "#FF5555",
    "success": "#00C853",
    "warning": "#FF9100",
    "accent": "#00E5FF",
    "text_gray": "#AAAAAA"
}

# ====================================================
#  MODERN POPUP CLASSES
# ====================================================
class ModernMessagebox(ctk.CTkToplevel):
    def __init__(self, title, message, icon="info"):
        super().__init__()
        self.title(title)
        width = 420
        height = 220
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a")
        self.protocol("WM_DELETE_WINDOW", self.close)

        if icon == "error":
            color = COLORS["danger"]
            symbol = "❌"
        elif icon == "success":
            color = COLORS["success"]
            symbol = "✅"
        elif icon == "warning":
            color = COLORS["warning"]
            symbol = "⚠️"
        else:
            color = COLORS["accent"]
            symbol = "ℹ️"

        ctk.CTkFrame(self, fg_color=color, height=8).pack(fill="x", side="top")
        ctk.CTkLabel(self, text=f"{symbol}  {title.upper()}", font=("Arial", 16, "bold"), text_color=color).pack(pady=(25, 10))
        ctk.CTkLabel(self, text=message, font=("Arial", 13), text_color="#E0E0E0", wraplength=380).pack(pady=10, padx=20)
        ctk.CTkButton(self, text="OK", width=100, height=35, fg_color=color, text_color="black", 
                      font=("Arial", 12, "bold"), hover_color="white", command=self.close).pack(pady=20, side="bottom")
        self.grab_set()

    def close(self):
        self.grab_release()
        self.destroy()

class ModernAskYesNo(ctk.CTkToplevel):
    def __init__(self, title, message, on_yes):
        super().__init__()
        self.title(title)
        self.on_yes = on_yes
        width = 400
        height = 200
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a")
        self.protocol("WM_DELETE_WINDOW", self.close)

        ctk.CTkFrame(self, fg_color=COLORS["warning"], height=5).pack(fill="x", side="top")
        ctk.CTkLabel(self, text=f"⚠️ {title.upper()}", font=("Arial", 16, "bold"), text_color=COLORS["warning"]).pack(pady=(20, 10))
        ctk.CTkLabel(self, text=message, font=("Arial", 13), text_color="white", wraplength=350).pack(pady=10)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20, side="bottom")
        ctk.CTkButton(btn_frame, text="CANCEL", width=100, fg_color="#333", command=self.close).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="CONFIRM", width=100, fg_color=COLORS["danger"], text_color="white", command=self.confirm).pack(side="left", padx=10)
        self.grab_set()

    def confirm(self):
        self.close()
        self.on_yes()

    def close(self):
        self.grab_release()
        self.destroy()      

# ==========================================
# MAIN APP CONTROLLER
# ==========================================
class RiskAnalysisApp(ctk.CTk):
    def report_callback_exception(self, exc, val, tb):
        if "invalid command name" in str(val):
            return
        # Since ctk.CTk doesn't always have super().report_callback_exception, 
        # we can just use the base tk method or ignore.
        import tkinter as tk
        tk.Tk.report_callback_exception(self, exc, val, tb)

    def on_closing(self):
        import os
        os._exit(0)

    def __init__(self):
        super().__init__()
        self.title("AcaDesk - Student Risk Analysis System")
        self.geometry("1100x700")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # PURE MEMORY STATE (No SQLite)
        self.shared_data = {
            "username": None,
            "user_type": None,
            "college_name": "Setup Required",
            "erp_setup_needed": False,
            "erp_config": None,
            "assigned_branch": None,
            "assigned_department": None,
            "is_hod": 0
        }

        # Silently initialize the central and analytics databases
        try:
            from logic.central_db_handler import CentralDBHandler
            from logic.analytics_db_handler import AnalyticsDBHandler
            from logic.central_auth import CentralAuth
            
            CentralDBHandler().initialize_tables()
            AnalyticsDBHandler().initialize_tables()
            CentralAuth().initialize_tables()
        except Exception as e:
            print("Background DB Initialization Failed:", e)

        self.container = ctk.CTkFrame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (WelcomeScreen, RegisterScreen, ERPSetupScreen, ConnectionDiagnosticsScreen, DashboardScreen, LoginScreen):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("WelcomeScreen")

    def show_frame(self, page_name, **kwargs):
        if kwargs:
            for k, v in kwargs.items():
                self.shared_data[k] = v
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

# ==========================================
# SCREEN 1: LOGIN (Welcome Screen built-in)
# ==========================================
class WelcomeScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#000000")
        self.controller = controller

        self.btn_config = ctk.CTkButton(self, text="⚙️ Server IP", width=100, height=30, 
                                        fg_color="#333", hover_color="#444", 
                                        command=self.configure_server_ip)
        self.btn_config.place(relx=0.95, rely=0.05, anchor="ne")

        left_frame = ctk.CTkFrame(self, fg_color="#111111", width=400, corner_radius=0)
        left_frame.place(relx=0, rely=0, relwidth=0.4, relheight=1)
        
        ctk.CTkLabel(left_frame, text="AcaDesk", font=("Montserrat", 40, "bold"), text_color="#00E5FF").place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(left_frame, text="Student Risk Intelligence", font=("Roboto", 16), text_color="gray").place(relx=0.5, rely=0.48, anchor="center")
        
        self.lbl_college = ctk.CTkLabel(left_frame, text=self.controller.shared_data["college_name"], font=("Consolas", 12), text_color="#333")
        self.lbl_college.place(relx=0.5, rely=0.9, anchor="center")

        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.place(relx=0.4, rely=0, relwidth=0.6, relheight=1)

        self.login_box = ctk.CTkFrame(right_frame, fg_color="#1a1a1a", width=400, height=500, corner_radius=20)
        self.login_box.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(self.login_box, text="SECURE LOGIN", font=("Arial", 24, "bold"), text_color="#00E5FF").pack(pady=(40, 30))

        self.entry_user = ctk.CTkEntry(self.login_box, placeholder_text="Username", width=300, height=50, font=("Roboto", 14))
        self.entry_user.pack(pady=10)

        self.entry_pass = ctk.CTkEntry(self.login_box, placeholder_text="Password", show="*", width=300, height=50, font=("Roboto", 14))
        self.entry_pass.pack(pady=10)

        self.role_var = ctk.StringVar(value="Faculty")
        role_frame = ctk.CTkFrame(self.login_box, fg_color="transparent")
        role_frame.pack(pady=20)
        
        r1 = ctk.CTkRadioButton(role_frame, text="Admin", variable=self.role_var, value="Admin", 
                                fg_color="#00E5FF", text_color="white")
        r1.pack(side="left", padx=20)
        
        r2 = ctk.CTkRadioButton(role_frame, text="Faculty", variable=self.role_var, value="Faculty", 
                                fg_color="#00E5FF", text_color="white")
        r2.pack(side="left", padx=20)

        ctk.CTkButton(self.login_box, text="ACCESS DASHBOARD", width=300, height=50, fg_color="#00E5FF", text_color="black", font=("Arial", 14, "bold"),
                      command=self.login_logic).pack(pady=10)

        self.btn_reg = ctk.CTkButton(self.login_box, text="Register / Add Admin", fg_color="transparent", text_color="gray", hover_color="#222",
                      command=self.handle_register)
        self.btn_reg.pack(pady=10)

    def handle_register(self):
        if self.role_var.get() == "Admin":
            self.controller.show_frame("RegisterScreen")

    def on_show(self):
        self.lbl_college.configure(text=self.controller.shared_data["college_name"])

    def configure_server_ip(self):
        ModernMessagebox("System Managed", "Server connection is managed centrally via the Cloud.", "info")

    def login_logic(self):
        u = self.entry_user.get()
        p = self.entry_pass.get()
        role = self.role_var.get()

        if not u or not p:
            ModernMessagebox("Error", "Fields cannot be empty", "error")
            return

        try:
            # Replaced SQLite with Central Cloud Auth
            from logic.central_auth import CentralAuth
            auth = CentralAuth()
            data, msg = auth.login(u, p)
            
            if data:
                user = data['user']
                
                # Role Check
                if user['role'] != role:
                    # Allow HODs to login using the Faculty option
                    if not (user['role'] == "HOD" and role == "Faculty"):
                        ModernMessagebox("Role Error", f"You are registered as a {user['role']}, not {role}.", "error")
                        return

                # Load memory variables
                self.controller.shared_data["username"] = user['username']
                self.controller.shared_data["user_type"] = user['role']
                self.controller.shared_data["college_name"] = user['college_name']
                self.controller.shared_data["assigned_branch"] = user.get('assigned_branch')
                self.controller.shared_data["assigned_department"] = user.get('assigned_department')
                self.controller.shared_data["is_hod"] = user.get('is_hod', 0)
                
                erp_config = data.get('erp_config')
                if erp_config:
                    self.controller.shared_data["erp_config"] = erp_config
                    self.controller.shared_data["erp_setup_needed"] = False
                    
                    # Validate ERP Connection
                    from logic.db_handler import DBHandler
                    db = DBHandler(erp_config)
                    if not db.connected:
                        self.controller.shared_data["diagnostic_error"] = "Database server unreachable."
                        self.controller.show_frame("ConnectionDiagnosticsScreen")
                        return
                    success, msg = db.validate_tables()
                    if not success:
                        self.controller.shared_data["diagnostic_error"] = f"Validation Failed:\\n{msg}"
                        self.controller.show_frame("ConnectionDiagnosticsScreen")
                        return
                    
                    self.controller.show_frame("DashboardScreen")
                else:
                    if user['role'] == "Faculty" or user['role'] == "HOD":
                        ModernMessagebox("System Locked", "System setup has not yet been completed by the Administrator.", "error")
                        return
                    self.controller.shared_data["erp_setup_needed"] = True
                    self.controller.show_frame("ERPSetupScreen")

                self.entry_pass.delete(0, 'end')
            else:
                ModernMessagebox("Login Failed", msg, "error")

        except Exception as e:
            ModernMessagebox("Error", str(e), "error")

if __name__ == "__main__":
    app = RiskAnalysisApp()
    app.mainloop()