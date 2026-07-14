import atexit
import customtkinter as ctk
from tkinter import messagebox
import os
import sys
import warnings

warnings.simplefilter("ignore", ResourceWarning)

# Ensure we can find the ui folder
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# IMPORT DASHBOARD
from ui.dashboard import DashboardScreen, ModernMessagebox
from ui.login import LoginScreen, RegisterScreen
from ui.erp_wizard import ERPWizard
from ui.loading import LoadingScreen
from logic import session_cache

# --- CONFIG & STYLES ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Colors for Popups
COLORS = {
    "danger": "#FF5555",
    "success": "#00C853",
    "warning": "#FF9100",
    "accent": "#00E5FF",
    "text_gray": "#AAAAAA",
    "card": "#151A22"
}

# ====================================================
#  MODERN POPUP CLASSES
# ====================================================


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
        self.configure(fg_color=COLORS["card"])
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
        try:
            session_cache.destroy()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        import os
        os._exit(0)

    def __init__(self):
        super().__init__()
        self.title("AcaDesk - Student Risk Analysis System")
        self.geometry("1100x700")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        import atexit
        atexit.register(session_cache.destroy)

        try:
            import os
            import ctypes
            # Set AppUserModelID to force Windows taskbar to use our icon instead of Python's default
            myappid = 'acadesk.studentriskanalysissystem.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            
            icon_path = resource_path("icon.ico")
            self.iconbitmap(icon_path)
        except Exception as e:
            print("Failed to set app icon:", e)
            
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
            
            AnalyticsDBHandler().initialize_tables()
            CentralAuth().initialize_tables()
            
        except Exception as e:
            print("Background DB Initialization Failed:", e)

        self.container = ctk.CTkFrame(self)
        self.container.pack(side="top", fill="both", expand=True)

        self.frames = {}
        for F in (WelcomeScreen, RegisterScreen, DashboardScreen, LoginScreen, LoadingScreen):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            # Instead of grid, we'll use place() dynamically, but initially we hide them
            # frame.grid(row=0, column=0, sticky="nsew")

        erp = ERPWizard(self.container, self, self.frames["DashboardScreen"])
        self.frames["ERPWizard"] = erp

        self.current_page = None
        self.is_animating = False

        self.show_frame("WelcomeScreen")
        self.after(100, lambda: self.state("zoomed"))

    def show_frame(self, page_name, **kwargs):
        if self.is_animating or self.current_page == page_name:
            return

        if kwargs:
            for k, v in kwargs.items():
                self.shared_data[k] = v
                
        new_frame = self.frames[page_name]

        if self.current_page is None:
            # First load, no animation
            new_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.current_page = page_name
            if hasattr(new_frame, "on_show"):
                new_frame.on_show()
            return

        old_frame = self.frames[self.current_page]
        self.is_animating = True

        # Position new frame off-screen to the right
        new_frame.place(relx=1, rely=0, relwidth=1, relheight=1)
        new_frame.tkraise()

        self.animate_transition(old_frame, new_frame, 0, page_name)

    def animate_transition(self, old_frame, new_frame, step, page_name):
        speed = 0.08  # Adjust for faster/slower animation
        step += speed
        if step >= 1.0:
            step = 1.0

        # Ease-out cubic for a smooth snap effect
        ease = 1 - pow(1 - step, 3)

        # Slide old frame to left, new frame from right
        old_frame.place(relx=-ease, rely=0, relwidth=1, relheight=1)
        new_frame.place(relx=1 - ease, rely=0, relwidth=1, relheight=1)

        if step < 1.0:
            self.after(16, lambda: self.animate_transition(old_frame, new_frame, step, page_name))
        else:
            old_frame.place_forget()
            self.current_page = page_name
            self.is_animating = False
            if hasattr(new_frame, "on_show"):
                new_frame.on_show()

# ==========================================
# SCREEN 1: LOGIN (Welcome Screen built-in)
# ==========================================
class WelcomeScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#0B0E14")
        self.controller = controller

        self.btn_config = ctk.CTkButton(self, text="ℹ System Info", width=100, height=30, 
                                        fg_color="#1A1D2D", hover_color="#2A2E3F", 
                                        border_width=1, border_color="#2A2E3F",
                                        command=self.configure_server_ip)
        self.btn_config.place(relx=0.95, rely=0.05, anchor="ne")

        left_frame = ctk.CTkFrame(self, fg_color="#080A0F", width=400, corner_radius=0)
        left_frame.place(relx=0, rely=0, relwidth=0.4, relheight=1)
        
        try:
            from PIL import Image
            import os
            logo_path = resource_path("AcaDesk (2).png")
            img = Image.open(logo_path)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(280, 280))
            self.logo_lbl = ctk.CTkLabel(left_frame, text="", image=ctk_img)
            self.logo_lbl.place(relx=0.5, rely=0.30, anchor="center")
        except Exception as e:
            pass
        
        ctk.CTkLabel(left_frame, text="AcaDesk", font=("Outfit", 55, "bold"), text_color="#00E5FF").place(relx=0.5, rely=0.62, anchor="center")
        ctk.CTkLabel(left_frame, text="Student Risk Intelligence", font=("Inter", 20), text_color="#7A849C").place(relx=0.5, rely=0.68, anchor="center")
        
        self.lbl_college = ctk.CTkLabel(left_frame, text=self.controller.shared_data["college_name"], font=("Inter", 12), text_color="#2A2E3F")
        self.lbl_college.place(relx=0.5, rely=0.9, anchor="center")

        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.place(relx=0.4, rely=0, relwidth=0.6, relheight=1)

        self.login_box = ctk.CTkFrame(right_frame, fg_color="#12141E", width=360, height=480, corner_radius=16, border_width=1, border_color="#2A2E3F")
        self.login_box.place(relx=0.5, rely=0.6, anchor="center") # Start lower for animation
        self.login_box.pack_propagate(False)

        ctk.CTkLabel(self.login_box, text="SECURE LOGIN", font=("Outfit", 24, "bold"), text_color="#00E5FF").pack(pady=(40, 30))

        self.entry_user = ctk.CTkEntry(self.login_box, placeholder_text="Username", width=300, height=45, fg_color="#1A1D2D", border_width=1, border_color="#2A2E3F", corner_radius=8, font=("Inter", 14), text_color="white")
        self.entry_user.pack(pady=10, padx=30)

        self.entry_pass = ctk.CTkEntry(self.login_box, placeholder_text="Password", show="*", width=300, height=45, fg_color="#1A1D2D", border_width=1, border_color="#2A2E3F", corner_radius=8, font=("Inter", 14), text_color="white")
        self.entry_pass.pack(pady=10, padx=30)
        self.entry_pass.bind("<Return>", lambda event: self.login_logic())

        self.role_var = ctk.StringVar(value="Faculty")
        role_frame = ctk.CTkFrame(self.login_box, fg_color="transparent")
        role_frame.pack(pady=20)
        
        r1 = ctk.CTkRadioButton(role_frame, text="Admin", variable=self.role_var, value="Admin", 
                                fg_color="#00E5FF", hover_color="#00B3CC", border_color="#2A2E3F", text_color="#7A849C", font=("Inter", 13))
        r1.pack(side="left", padx=20)
        
        r2 = ctk.CTkRadioButton(role_frame, text="Faculty", variable=self.role_var, value="Faculty", 
                                fg_color="#00E5FF", hover_color="#00B3CC", border_color="#2A2E3F", text_color="#7A849C", font=("Inter", 13))
        r2.pack(side="left", padx=20)

        self.btn_login = ctk.CTkButton(self.login_box, text="ACCESS DASHBOARD", width=300, height=45, fg_color="#00E5FF", text_color="black", hover_color="#00B3CC", corner_radius=8, font=("Outfit", 14, "bold"),
                      command=self.login_logic)
        self.btn_login.pack(pady=10)

        self.btn_reg = ctk.CTkButton(self.login_box, text="Register / Add Admin", fg_color="transparent", text_color="#7A849C", hover_color="#1A1D2D", font=("Inter", 12),
                      command=self.handle_register)
        self.btn_reg.pack(pady=10)

        self.target_rely = 0.5
        self.current_rely = 0.6
        self.after(100, self.animate_login_box)

    def animate_login_box(self):
        if self.current_rely > self.target_rely:
            self.current_rely -= 0.006
            if self.current_rely < self.target_rely:
                self.current_rely = self.target_rely
            self.login_box.place(relx=0.5, rely=self.current_rely, anchor="center")
            self.after(16, self.animate_login_box)

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

        self.btn_login.configure(state="disabled", text="Authenticating...")
        self.update()

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
                        ModernMessagebox("Connection Failed", "Database server unreachable. Please configure your ERP connection.", "error")
                        self.controller.shared_data["erp_setup_needed"] = True
                        self.controller.show_frame("ERPWizard")
                        return
                    success, msg = db.validate_tables()
                    if not success:
                        ModernMessagebox("Schema Validation Failed", f"Tables not mapped correctly:\n{msg}\n\nPlease run the Auto-Detect Wizard.", "error")
                        self.controller.shared_data["erp_setup_needed"] = True
                        self.controller.show_frame("ERPWizard")
                        return
                    
                    # All checks passed — go to Loading Screen which will sync cache
                    self.controller.show_frame("LoadingScreen")
                else:
                    if user['role'] == "Faculty" or user['role'] == "HOD":
                        ModernMessagebox("System Locked", "System setup has not yet been completed by the Administrator.", "error")
                        return
                    self.controller.shared_data["erp_setup_needed"] = True
                    self.controller.show_frame("ERPWizard")

                self.entry_pass.delete(0, 'end')
            else:
                ModernMessagebox("Login Failed", msg, "error")

        except Exception as e:
            ModernMessagebox("Error", str(e), "error")
        finally:
            self.btn_login.configure(state="normal", text="ACCESS DASHBOARD")

if __name__ == "__main__":
    app = RiskAnalysisApp()
    app.mainloop()