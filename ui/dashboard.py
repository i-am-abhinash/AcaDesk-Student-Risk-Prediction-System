from ui.dashboard_student_list import StudentListMixin
from ui.dashboard_student_detail import StudentDetailMixin
from ui.dashboard_insights import InsightsMixin
import customtkinter as ctk
from tkinter import messagebox
from tkinter import Toplevel
from tkinter import scrolledtext
from tkinter import ttk
import time
import sys
import os
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from ui.styles import COLORS
from ui.styles import FONTS
from ui.styles import DIMS

# Logic Imports
try:
    from logic.prediction_service import PredictionService
    from ui.trend_visuals import TrendVisuals
    from logic.db_handler import DBHandler
    from logic.central_auth import CentralAuth
except ImportError:
    pass

YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]

# ====================================================
#  UTILITIES & TRANSLATOR
# ====================================================

class ModernMessagebox(ctk.CTkToplevel):
    def __init__(self, title, message, icon="info"):
        super().__init__()
        
        self.title("AcaDesk")
        
        width = 450
        height = 280
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        
        pos_x = (screen_w - width) // 2
        pos_y = (screen_h - height) // 2
        
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color=COLORS["card"])
        
        if icon == "error":
            color = COLORS["danger"]
            symbol = "❌"
        elif icon == "success":
            color = COLORS["success"]
            symbol = "✅"
        else:
            color = COLORS["accent"]
            symbol = "ℹ️"

        # Top accent bar
        header_bar = ctk.CTkFrame(self, fg_color=color, height=8)
        header_bar.pack(fill="x", side="top")
        
        # Title Label
        title_lbl = ctk.CTkLabel(
            self, 
            text=f"{symbol}  {title.upper()}", 
            font=FONTS["h3"], 
            text_color=color
        )
        title_lbl.pack(pady=(25, 10))
        
        # Message Label
        msg_lbl = ctk.CTkLabel(
            self, 
            text=message, 
            font=FONTS["body"], 
            text_color="#E0E0E0", 
            wraplength=400, 
            justify="center"
        )
        msg_lbl.pack(pady=10, padx=20)
        
        # Close Button
        ok_btn = ctk.CTkButton(
            self, 
            text="OK", 
            width=120, 
            height=35, 
            fg_color=color, 
            text_color="black", 
            font=FONTS["body"], 
            command=self.destroy
        )
        ok_btn.pack(pady=20, side="bottom")
        
        self.grab_set()

class BranchTranslator:
    def __init__(self, db_handler):
        self.map = {}
        if db_handler:
            self.map = db_handler.get_branch_map()
            
    def get_name(self, branch_id):
        bid_str = str(branch_id).strip()
        return self.map.get(bid_str, f"Dept {branch_id}")

# ====================================================
#  SIDEBAR
# ====================================================

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, controller, dashboard):
        super().__init__(parent, width=DIMS["sidebar_width"], corner_radius=0, fg_color=COLORS["sidebar"])
        self.controller = controller
        self.dash = dashboard
        
        # App Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(pady=(30, 5))
        
        try:
            from PIL import Image
            import os
            import sys
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = root_dir
            logo_path = os.path.join(base_path, "AcaDesk (2).png")
            img = Image.open(logo_path)
            # Resize image to fit nicely next to text
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(65, 65))
            logo_img = ctk.CTkLabel(header_frame, text="", image=ctk_img)
            logo_img.pack(side="left", padx=(0, 10))
        except Exception as e:
            print("Failed to load sidebar logo:", e)
            
        logo_txt = ctk.CTkLabel(
            header_frame, 
            text="AcaDesk", 
            font=FONTS["h1"], 
            text_color="#00E5FF"
        )
        logo_txt.pack(side="left")
        
        # User display
        self.lbl_user = ctk.CTkLabel(
            self, 
            text="User: ...", 
            text_color=COLORS["text_gray"]
        )
        self.lbl_user.pack(pady=(0, 20))
        
        # Sidebar Menu Buttons
        self.btn_dash = self.add_btn("📊", "Dashboard", lambda: self.dash.show_view("Analytics"))
        self.btn_overview = self.add_btn("🏢", "Institution Overview", lambda: self.dash.show_view("Overview"))
        self.btn_fac = self.add_btn("👥", "Faculty Manager", lambda: self.dash.show_view("Faculty"))
        self.btn_hod = self.add_btn("🎓", "HOD Manager", lambda: self.dash.show_view("HODMgr"))
        self.btn_ai = self.add_btn("✨", "AI Insights", lambda: self.dash.show_view("Insights"))
        self.btn_eval = self.add_btn("🧠", "Model Evaluation", lambda: self.dash.show_view("ModelEval"))
        self.btn_notes = self.add_btn("📝", "Notes Archive", lambda: self.dash.show_view("NotesArchive"))
        self.btn_pass = self.add_btn("🔒", "Change Password", self.dash.open_change_pass)
        
        # Logout Button
        logout_btn = ctk.CTkButton(
            self, 
            text="LOGOUT", 
            fg_color="#330000", 
            text_color=COLORS["danger"], 
            command=lambda: self.controller.show_frame("WelcomeScreen")
        )
        logout_btn.pack(side="bottom", fill="x", padx=20, pady=20)

    def add_btn(self, icon, txt, cmd):
        btn_frame = ctk.CTkFrame(self, fg_color="transparent", height=DIMS["btn_height"], corner_radius=6, cursor="hand2")
        btn_frame.pack_propagate(False) # Keep fixed height
        
        lbl_icon = ctk.CTkLabel(btn_frame, text=icon, font=FONTS["h3"], text_color="#00E5FF", width=30, anchor="center", cursor="hand2")
        lbl_icon.pack(side="left", padx=(10, 5))
        
        lbl_txt = ctk.CTkLabel(btn_frame, text=txt, font=FONTS["h3"], text_color="#00E5FF", anchor="w", cursor="hand2")
        lbl_txt.pack(side="left", fill="x", expand=True)
        
        # Hover and Click bindings
        def on_enter(e): btn_frame.configure(fg_color="#222")
        def on_leave(e): btn_frame.configure(fg_color="transparent")
        def on_click(e): cmd()
            
        for w in [btn_frame, lbl_icon, lbl_txt]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
            
        btn_frame.lbl_icon = lbl_icon
        btn_frame.lbl_txt = lbl_txt
        
        btn_frame.pack(fill="x", padx=10, pady=2)
        return btn_frame

    def refresh(self):
        username = self.controller.shared_data.get('username', 'User')
        self.lbl_user.configure(text=f"User: {username}")
        
        user_type = self.controller.shared_data.get("user_type")
        
        # Hide restricted buttons initially
        for btn in [self.btn_overview, self.btn_fac, self.btn_hod, self.btn_ai, self.btn_eval, self.btn_notes, self.btn_pass]:
            btn.pack_forget()

        if user_type == "Admin": 
            self.btn_overview.lbl_txt.configure(text="Institution Overview")
            self.btn_overview.lbl_icon.configure(text="🏢")
            self.btn_overview.pack(fill="x", padx=10, pady=2)
            self.btn_ai.pack(fill="x", padx=10, pady=2)
            self.btn_fac.pack(fill="x", padx=10, pady=2)
            self.btn_hod.pack(fill="x", padx=10, pady=2)
            self.btn_eval.pack(fill="x", padx=10, pady=2)
        elif user_type == "HOD":
            self.btn_ai.pack(fill="x", padx=10, pady=2)
            self.btn_fac.pack(fill="x", padx=10, pady=2)
        else:
            self.btn_ai.pack(fill="x", padx=10, pady=2)
            
        self.btn_notes.pack(fill="x", padx=10, pady=2)
        self.btn_pass.pack(fill="x", padx=10, pady=2)

# ====================================================
#  FACULTY MANAGER
# ====================================================

class FacultyManagerPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.db = None
        self.branch_map = {}
        
        # Header
        header = ctk.CTkFrame(self, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        header.pack(fill="x", padx=40, pady=(40, 10))
        
        title = ctk.CTkLabel(
            header, 
            text="FACULTY ACCESS MANAGEMENT", 
            text_color="#00E5FF",
            font=("Outfit", 24, "bold")
        )
        title.pack(side="left", padx=20, pady=15)
        
        # Entry Form
        form_card = ctk.CTkFrame(self, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        form_card.pack(fill="x", padx=40, pady=10)
        
        row_frame = ctk.CTkFrame(form_card, fg_color="transparent")
        row_frame.pack(fill="x", padx=20, pady=20)
        
        self.u_entry = ctk.CTkEntry(row_frame, placeholder_text="Username", width=180, fg_color="#1A1D2D", border_width=0, corner_radius=6)
        self.u_entry.pack(side="left", padx=10)
        
        self.p_entry = ctk.CTkEntry(row_frame, placeholder_text="Password", width=180, show="*", fg_color="#1A1D2D", border_width=0, corner_radius=6)
        self.p_entry.pack(side="left", padx=10)
        self.p_entry.bind("<Return>", lambda event: self.add_faculty())
        
        self.br_combo = ctk.CTkComboBox(row_frame, width=160, fg_color="#1A1D2D", border_width=0, button_color="#1A1D2D", dropdown_fg_color="#1A1D2D", corner_radius=6)
        self.br_combo.set("Select Branch")
        self.br_combo.pack(side="left", padx=10)
        
        add_btn = ctk.CTkButton(
            row_frame, 
            text="+ ADD FACULTY", 
            fg_color="#00E5FF", 
            text_color="black", 
            font=("Inter", 12, "bold"),
            width=120, 
            corner_radius=6,
            hover_color="#00B3CC",
            command=self.add_faculty
        )
        add_btn.pack(side="left", padx=10)
        
        # Faculty List Scroll Area
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20)

    def refresh(self):
        erp_conf = self.controller.shared_data.get("erp_config")
        user_type = self.controller.shared_data.get("user_type")
        assigned_dept = self.controller.shared_data.get("assigned_department")
        
        if erp_conf:
            if getattr(self, "db", None):
                try: self.db.close()
                except Exception: pass
            self.db = DBHandler(erp_conf)
            b_map = self.db.get_branch_map()
            self.branch_map = {name: str(id) for id, name in b_map.items()}
            
            if user_type == "HOD" and assigned_dept:
                dept_name = "Assigned Dept"
                for n, id_str in self.branch_map.items():
                    if id_str == str(assigned_dept):
                        dept_name = n
                        break
                self.br_combo.configure(values=[dept_name])
                self.br_combo.set(dept_name)
                self.br_combo.configure(state="disabled")
            else:
                self.br_combo.configure(values=list(self.branch_map.keys()), state="normal")
                self.br_combo.set("Select Branch")
            
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        try:
            college = self.controller.shared_data.get("college_name")
            faculties = CentralAuth().get_faculty_list(college)
            
            for f in faculties:
                branch_id = str(f['assigned_branch'])
                if user_type == "HOD" and assigned_dept and branch_id != str(assigned_dept):
                    continue
                    
                branch_name = "Unknown"
                if self.db:
                    branch_name = self.db.get_branch_map().get(branch_id, branch_id)
                
                row = ctk.CTkFrame(self.list_frame, fg_color="#12141E", corner_radius=10, border_width=1, border_color="#2A2E3F", height=60)
                row.pack(fill="x", pady=6, padx=20)
                row.pack_propagate(False)
                
                def on_enter(e, c=row): c.configure(fg_color="#1A1D2D", border_color="#00E5FF")
                def on_leave(e, c=row): c.configure(fg_color="#12141E", border_color="#2A2E3F")
                row.bind("<Enter>", on_enter)
                row.bind("<Leave>", on_leave)
                
                lbl_frame = ctk.CTkFrame(row, fg_color="transparent")
                lbl_frame.pack(side="left", padx=20, fill="both", expand=True)
                
                icon = ctk.CTkLabel(lbl_frame, text="👤", font=("Outfit", 20))
                icon.pack(side="left")
                
                uname = ctk.CTkLabel(lbl_frame, text=f"{f['username']}", font=("Outfit", 16, "bold"), text_color="white")
                uname.pack(side="left", padx=(15, 5))
                
                bname = ctk.CTkLabel(lbl_frame, text=f"[{branch_name}]", font=("Inter", 12), text_color="#00E5FF")
                bname.pack(side="left")
                
                for child in (lbl_frame, icon, uname, bname):
                    child.bind("<Enter>", on_enter)
                    child.bind("<Leave>", on_leave)
                
                rev_btn = ctk.CTkButton(
                    row, 
                    text="REVOKE", 
                    fg_color="transparent", 
                    border_width=1,
                    border_color="#FF3D00",
                    text_color="#FF3D00", 
                    font=("Inter", 12, "bold"),
                    hover_color="#FF3D00",
                    width=90, 
                    corner_radius=6,
                    command=lambda u=f['username']: self.revoke(u)
                )
                
                def btn_enter(e, b=rev_btn): b.configure(text_color="white")
                def btn_leave(e, b=rev_btn): b.configure(text_color="#FF3D00")
                rev_btn.bind("<Enter>", btn_enter)
                rev_btn.bind("<Leave>", btn_leave)
                rev_btn.pack(side="right", padx=20, pady=10)
        except Exception as e:
            print(f"Error refreshing faculty: {e}")

    def add_faculty(self):
        username = self.u_entry.get()
        password = self.p_entry.get()
        selection = self.br_combo.get()
        
        if username and password and selection != "Select Branch":
            branch_id = self.branch_map.get(selection)
            admin_user = self.controller.shared_data["username"]
            success, msg = CentralAuth().add_faculty(admin_user, username, password, branch_id)
            if success:
                self.refresh()

    def revoke(self, username):
        college = self.controller.shared_data["college_name"]
        if CentralAuth().revoke_faculty(username, college):
            self.refresh()

class HODManagerPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.db = None
        self.branch_map = {}
        
        # Header
        header = ctk.CTkFrame(self, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        header.pack(fill="x", padx=40, pady=(40, 10))
        
        title = ctk.CTkLabel(
            header, 
            text="HEAD OF DEPARTMENT ACCESS MANAGEMENT", 
            text_color="#00E5FF",
            font=("Outfit", 24, "bold")
        )
        title.pack(side="left", padx=20, pady=15)
        
        # Entry Form
        form_card = ctk.CTkFrame(self, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        form_card.pack(fill="x", padx=40, pady=10)
        
        row_frame = ctk.CTkFrame(form_card, fg_color="transparent")
        row_frame.pack(fill="x", padx=20, pady=20)
        
        self.u_entry = ctk.CTkEntry(row_frame, placeholder_text="Username", width=180, fg_color="#1A1D2D", border_width=0, corner_radius=6)
        self.u_entry.pack(side="left", padx=10)
        
        self.p_entry = ctk.CTkEntry(row_frame, placeholder_text="Password", width=180, show="*", fg_color="#1A1D2D", border_width=0, corner_radius=6)
        self.p_entry.pack(side="left", padx=10)
        self.p_entry.bind("<Return>", lambda event: self.add_hod())
        
        self.br_combo = ctk.CTkComboBox(row_frame, width=160, fg_color="#1A1D2D", border_width=0, button_color="#1A1D2D", dropdown_fg_color="#1A1D2D", corner_radius=6)
        self.br_combo.set("Select Branch")
        self.br_combo.pack(side="left", padx=10)
        
        add_btn = ctk.CTkButton(
            row_frame, 
            text="+ ADD HOD", 
            fg_color="#00E5FF", 
            text_color="black", 
            font=("Inter", 12, "bold"),
            width=120, 
            corner_radius=6,
            hover_color="#00B3CC",
            command=self.add_hod
        )
        add_btn.pack(side="left", padx=10)
        
        # List Scroll Area
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20)

    def refresh(self):
        erp_conf = self.controller.shared_data.get("erp_config")
        if erp_conf:
            if getattr(self, "db", None):
                try: self.db.close()
                except Exception: pass
            self.db = DBHandler(erp_conf)
            b_map = self.db.get_branch_map()
            self.branch_map = {name: str(id) for id, name in b_map.items()}
            self.br_combo.configure(values=list(self.branch_map.keys()))
            
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        try:
            college = self.controller.shared_data.get("college_name")
            hods = CentralAuth().get_hod_list(college)
            
            for f in hods:
                branch_id = str(f['assigned_department'])
                branch_name = "Unknown"
                if self.db:
                    branch_name = self.db.get_branch_map().get(branch_id, branch_id)
                
                row = ctk.CTkFrame(self.list_frame, fg_color="#12141E", corner_radius=10, border_width=1, border_color="#2A2E3F", height=60)
                row.pack(fill="x", pady=6, padx=20)
                row.pack_propagate(False)
                
                def on_enter(e, c=row): c.configure(fg_color="#1A1D2D", border_color="#00E5FF")
                def on_leave(e, c=row): c.configure(fg_color="#12141E", border_color="#2A2E3F")
                row.bind("<Enter>", on_enter)
                row.bind("<Leave>", on_leave)
                
                lbl_frame = ctk.CTkFrame(row, fg_color="transparent")
                lbl_frame.pack(side="left", padx=20, fill="both", expand=True)
                
                icon = ctk.CTkLabel(lbl_frame, text="🎓", font=("Outfit", 20))
                icon.pack(side="left")
                
                uname = ctk.CTkLabel(lbl_frame, text=f"{f['username']}", font=("Outfit", 16, "bold"), text_color="white")
                uname.pack(side="left", padx=(15, 5))
                
                bname = ctk.CTkLabel(lbl_frame, text=f"[{branch_name}]", font=("Inter", 12), text_color="#00E5FF")
                bname.pack(side="left")
                
                for child in (lbl_frame, icon, uname, bname):
                    child.bind("<Enter>", on_enter)
                    child.bind("<Leave>", on_leave)
                
                rev_btn = ctk.CTkButton(
                    row, 
                    text="REVOKE", 
                    fg_color="transparent", 
                    border_width=1,
                    border_color="#FF3D00",
                    text_color="#FF3D00", 
                    font=("Inter", 12, "bold"),
                    hover_color="#FF3D00",
                    width=90, 
                    corner_radius=6,
                    command=lambda u=f['username']: self.revoke(u)
                )
                
                def btn_enter(e, b=rev_btn): b.configure(text_color="white")
                def btn_leave(e, b=rev_btn): b.configure(text_color="#FF3D00")
                rev_btn.bind("<Enter>", btn_enter)
                rev_btn.bind("<Leave>", btn_leave)
                rev_btn.pack(side="right", padx=20, pady=10)
        except Exception as e:
            print(f"Error refreshing HODs: {e}")

    def add_hod(self):
        username = self.u_entry.get()
        password = self.p_entry.get()
        selection = self.br_combo.get()
        
        if username and password and selection != "Select Branch":
            branch_id = self.branch_map.get(selection)
            admin_user = self.controller.shared_data["username"]
            success, msg = CentralAuth().add_hod(admin_user, username, password, branch_id)
            if success:
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
# ====================================================

class AnalyticsPanel(ctk.CTkFrame, StudentListMixin, StudentDetailMixin, InsightsMixin):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.db = None
        self.ai = PredictionService()
        self.translator = None
        self.current_branch = None
        self.current_year = None
        self.current_filter = "All"

        self.header = ctk.CTkFrame(self, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        
        self.btn_back = ctk.CTkButton(
            self.header, 
            text="← Back", 
            width=70, 
            height=30, 
            corner_radius=6,
            fg_color="transparent",
            hover_color="#2A2E3F",
            border_width=1,
            border_color="#2A2E3F",
            command=self.go_back
        )
        
        self.lbl_title = ctk.CTkLabel(
            self.header, 
            text="Dashboard", 
            font=("Outfit", 24, "bold"), 
            text_color="#00E5FF"
        )
        self.lbl_title.pack(side="left", padx=20, pady=15)
        
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True, padx=20, pady=10)

    def refresh(self):
        self.current_branch = None
        self.current_year = None
        
        erp_conf = self.controller.shared_data.get("erp_config")
        if erp_conf:
            if getattr(self, "db", None):
                try: self.db.close()
                except Exception: pass
            self.db = DBHandler(erp_conf)
            self.translator = BranchTranslator(self.db)
            
        if not self.db or not self.db.connected:
            self.show_error("Database connection missing. Access ERP setup.")
            return
            
        user_type = self.controller.shared_data.get("user_type")
        if user_type in ["Faculty", "HOD"]:
            assigned = self.controller.shared_data.get("assigned_branch") or self.controller.shared_data.get("assigned_department")
            if assigned:
                self.current_branch = assigned
                self.show_year_selection()
                return
                
        self.show_branch_selection()

    def go_back(self):
        if self.current_year:
            self.current_year = None
            self.show_year_selection()
        elif self.current_branch:
            user_type = self.controller.shared_data.get("user_type")
            if user_type == "Admin":
                self.current_branch = None
                self.show_branch_selection()

    def show_branch_selection(self):
        self.header.pack(fill="x", padx=20, pady=(20, 10), before=self.content_area)
        self._clear()
        self.lbl_title.configure(text="Select Department")
        self.btn_back.pack_forget()
        
        user_type = self.controller.shared_data.get("user_type")
        
        # Container for charts (if Admin)
        self.charts_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.charts_frame.pack(fill="x", pady=(5, 10))
        
        if user_type == "Admin":
            loading_lbl = ctk.CTkLabel(self.charts_frame, text="Loading Institution Charts...", text_color="gray")
            loading_lbl.pack(pady=20)
            
            def load_charts():
                try:
                    from logic.session_cache import get_dashboard_summary
                    summary_data = get_dashboard_summary()
                    
                    global_stats = {"High": 0, "Medium": 0, "Low": 0}
                    branch_stats = {}
                    
                    if summary_data:
                        for row in summary_data:
                            lvl = row["risk_level"]
                            if lvl not in ["High", "Medium", "Low"]: continue
                            bname = row["branch_name"]
                            if bname not in branch_stats:
                                branch_stats[bname] = {"High": 0, "Medium": 0, "Low": 0}
                            global_stats[lvl] += row["count"]
                            branch_stats[bname][lvl] += row["count"]
                        
                    self.after(0, lambda: self._draw_admin_charts(global_stats, branch_stats, loading_lbl))
                except Exception as e:
                    print(f"Chart render fail: {e}")
                    self.after(0, loading_lbl.destroy)
                    
            import threading
            threading.Thread(target=load_charts, daemon=True).start()
            
        # Department Grid
        branch_ids = self.db.get_all_branches()
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        # Determine number of columns based on branch count
        cols = 3
        for c in range(cols):
            scroll.grid_columnconfigure(c, weight=1, uniform="col")
            
        for i, bid in enumerate(branch_ids):
            name = self.translator.get_name(bid)
            card = ctk.CTkFrame(scroll, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
            card.grid(row=i//cols, column=i%cols, padx=10, pady=10, sticky="nsew")
            
            def make_bindings(c_card, c_bid):
                def on_enter(e): c_card.configure(fg_color="#1A1D2D", border_color="#00E5FF")
                def on_leave(e): c_card.configure(fg_color="#12141E", border_color="#2A2E3F")
                def on_click(e): self.select_branch(c_bid)
                
                c_card.bind("<Enter>", on_enter)
                c_card.bind("<Leave>", on_leave)
                c_card.bind("<Button-1>", on_click)
                for child in c_card.winfo_children():
                    child.bind("<Enter>", on_enter)
                    child.bind("<Leave>", on_leave)
                    child.bind("<Button-1>", on_click)
                    for ch in child.winfo_children():
                        ch.bind("<Enter>", on_enter)
                        ch.bind("<Leave>", on_leave)
                        ch.bind("<Button-1>", on_click)
                        
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=25, pady=25)
            
            lbl = ctk.CTkLabel(inner, text=name, font=("Outfit", 20, "bold"), text_color="#00E5FF")
            lbl.pack(side="left")
            
            arr = ctk.CTkLabel(inner, text="→", font=("Arial", 24, "bold"), text_color="white")
            arr.pack(side="right")
            
            make_bindings(card, bid)

    def select_branch(self, bid):
        self.current_branch = bid
        self.show_year_selection()

    def select_year(self, yr):
        self.current_year = yr
        self.show_student_list()

    def show_year_selection(self):
        self.header.pack(fill="x", padx=20, pady=(20, 10), before=self.content_area)
        self._clear()
        name = self.translator.get_name(self.current_branch)
        self.lbl_title.configure(text=f"{name} - Department Overview")
        
        user_type = self.controller.shared_data.get("user_type")
        if user_type == "Admin":
            self.btn_back.pack(side="left", padx=(0, 10))
            
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        # --- Department Drill-Down Analytics ---
        kpi_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(kpi_frame, text="Loading Department Analytics...", text_color="gray").pack(pady=20)
        
        def load_dept_analytics():
            try:
                from logic.session_cache import get_dashboard_summary
                summary_data = get_dashboard_summary()
                
                target_bid = str(self.current_branch)
                stats = {
                    "avg_attendance": 0, "avg_cgpa": 0, "avg_backlogs": 0,
                    "health_score": 0, "High": 0, "Medium": 0, "Low": 0, "Pending": 0,
                    "top_drivers": ["Attendance & Academics"]
                }
                
                total = 0
                att_sum = 0
                cgpa_sum = 0
                bkl_sum = 0
                
                for row in summary_data:
                    if str(row["branch_id"]) != target_bid: continue
                    lvl = row["risk_level"]
                    cnt = row["count"]
                    
                    if lvl in stats: stats[lvl] += cnt
                    total += cnt
                    att_sum += (row["avg_att"] or 0) * cnt
                    cgpa_sum += (row["avg_cgpa"] or 0) * cnt
                    bkl_sum += (row["avg_bkl"] or 0) * cnt
                    
                if total > 0:
                    stats["avg_attendance"] = att_sum / total
                    stats["avg_cgpa"] = cgpa_sum / total
                    stats["avg_backlogs"] = bkl_sum / total
                    
                    h = stats["High"]
                    m = stats["Medium"]
                    
                    health = 100 - ((h * 1.0) + (m * 0.5)) / total * 100
                    stats["health_score"] = max(0, min(100, health))
                    
                data = {"ranked_departments": [ (target_bid, stats) ]}
                self.after(0, lambda: self._render_dept_analytics(kpi_frame, data))
            except Exception as e:
                self.after(0, lambda e=e: ctk.CTkLabel(kpi_frame, text=f"Error loading analytics: {e}").pack())
                
        import threading
        threading.Thread(target=load_dept_analytics, daemon=True).start()
            
        # --- Year Selection Section ---
        ctk.CTkLabel(scroll, text="Select Year to View Students", font=("Outfit", 16, "bold"), text_color="#00E5FF").pack(anchor="w", pady=(20, 15))
        grid = ctk.CTkFrame(scroll, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 20))
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        
        for i, yr in enumerate(["1st Year", "2nd Year", "3rd Year", "4th Year"]):
            yr_card = ctk.CTkFrame(grid, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
            yr_card.grid(row=i//2, column=i%2, padx=10, pady=10, sticky="nsew")
            
            # Using closures to avoid late-binding loop variable issues
            def make_bindings(card, year):
                def on_enter(e): card.configure(fg_color="#1A1D2D", border_color="#00E5FF")
                def on_leave(e): card.configure(fg_color="#12141E", border_color="#2A2E3F")
                def on_click(e): self.select_year(year)
                
                card.bind("<Enter>", on_enter)
                card.bind("<Leave>", on_leave)
                card.bind("<Button-1>", on_click)
                for child in card.winfo_children():
                    child.bind("<Enter>", on_enter)
                    child.bind("<Leave>", on_leave)
                    child.bind("<Button-1>", on_click)
                    for c in child.winfo_children():
                        c.bind("<Enter>", on_enter)
                        c.bind("<Leave>", on_leave)
                        c.bind("<Button-1>", on_click)
                        
            inner = ctk.CTkFrame(yr_card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=25, pady=25)
            
            lbl = ctk.CTkLabel(inner, text=yr, font=("Outfit", 20, "bold"), text_color="white")
            lbl.pack(side="left")
            
            arr = ctk.CTkLabel(inner, text="→", font=("Arial", 24, "bold"), text_color="#00E5FF")
            arr.pack(side="right")
            
            make_bindings(yr_card, yr)

    def show_error(self, msg):
        self._clear()
        err_lbl = ctk.CTkLabel(self.content_area, text=msg, font=FONTS["h3"], text_color="orange")
        err_lbl.pack(pady=100)

    def _clear(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

# ====================================================
#  ENTERPRISE ERP WIZARD
# ====================================================

from ui.erp_wizard import ERPWizard

# ====================================================
#  DASHBOARD SCREEN
# ====================================================

class DashboardScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = Sidebar(self, controller, self)
        
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        
        self.view_order = ["Analytics", "Overview", "Insights", "Faculty", "HODMgr", "ModelEval", "NotesArchive", "ERP"]
        self.current_view_name = None
        self.is_view_animating = False

        from ui.institution_overview import InstitutionOverviewPanel
        self.overview = InstitutionOverviewPanel(self.content_container, controller)
        self.analytics = AnalyticsPanel(self.content_container, controller)
        self.faculty = FacultyManagerPanel(self.content_container, controller)
        self.hod_mgr = HODManagerPanel(self.content_container, controller)
        
        from ui.model_evaluation import ModelEvaluationPanel
        from ui.notes_archive import NotesArchivePanel
        self.model_eval = ModelEvaluationPanel(self.content_container, controller)
        self.notes_archive = NotesArchivePanel(self.content_container, controller)
        
        from ui.advanced_insights import AdvancedInsightsPanel
        self.insights = AdvancedInsightsPanel(self.content_container, controller)
        self.erp = ERPWizard(self.content_container, controller, self)
        
        self.panels = {
            "Overview": self.overview,
            "Analytics": self.analytics,
            "Insights": self.insights,
            "ModelEval": self.model_eval,
            "NotesArchive": self.notes_archive,
            "Faculty": self.faculty,
            "HODMgr": self.hod_mgr,
            "ERP": self.erp
        }

    def on_show(self):
        self.sidebar.refresh()
        needed = self.controller.shared_data.get("erp_setup_needed")
        
        if needed:
            self.content_container.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.erp.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.sidebar.grid_forget()
        else:
            self.content_container.grid(row=0, column=1, columnspan=1, sticky="nsew")
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            user_type = self.controller.shared_data.get("user_type")
            # Dashboard opens only after LoadingScreen has fully populated
            # the session cache. No background sync is needed here.
            self.show_view("Analytics")



    # NOTE: start_background_sync(), _sync_progress(), _sync_finished() removed.
    # Cache synchronization now happens exclusively in LoadingScreen via SyncWorker.
    # All panels read from the fully-populated session cache (logic/session_cache.py).


    def show_view(self, name):
        if self.is_view_animating or self.current_view_name == name:
            return

        new_panel = self.panels.get(name)
        if not new_panel:
            return

        if self.current_view_name is None:
            new_panel.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.current_view_name = name
            if hasattr(new_panel, 'refresh'):
                new_panel.refresh()
            return

        old_panel = self.panels[self.current_view_name]
        old_idx = self.view_order.index(self.current_view_name) if self.current_view_name in self.view_order else 0
        new_idx = self.view_order.index(name) if name in self.view_order else 0
        
        direction = 1 if new_idx > old_idx else -1
        self.is_view_animating = True
        
        start_rely = 1 if direction == 1 else -1
        new_panel.place(relx=0, rely=start_rely, relwidth=1, relheight=1)
        new_panel.tkraise()
        
        self.animate_vertical(old_panel, new_panel, 0, direction, name)

    def animate_vertical(self, old_panel, new_panel, step, direction, new_name):
        speed = 0.08
        step += speed
        if step >= 1.0:
            step = 1.0
            
        ease = 1 - pow(1 - step, 3)
        old_rely = -ease if direction == 1 else ease
        old_panel.place(relx=0, rely=old_rely, relwidth=1, relheight=1)
        
        new_rely = (1 - ease) if direction == 1 else (-1 + ease)
        new_panel.place(relx=0, rely=new_rely, relwidth=1, relheight=1)
        
        if step < 1.0:
            self.after(16, lambda: self.animate_vertical(old_panel, new_panel, step, direction, new_name))
        else:
            old_panel.place_forget()
            self.current_view_name = new_name
            self.is_view_animating = False
            if hasattr(new_panel, 'refresh'):
                new_panel.refresh()

    def open_change_pass(self):
        top = ctk.CTkToplevel(self)
        top.geometry("450x550")
        top.title("AcaDesk - Security Settings")
        top.attributes("-topmost", True)
        top.configure(fg_color="#0B0E14")
        
        main_card = ctk.CTkFrame(top, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        main_card.pack(fill="both", expand=True, padx=25, pady=25)
        
        header_icon = ctk.CTkLabel(main_card, text="🔒", font=("Outfit", 28, "bold"))
        header_icon.pack(pady=(30, 10))
        
        header = ctk.CTkLabel(main_card, text="UPDATE PASSWORD", font=("Outfit", 22, "bold"), text_color="#00E5FF")
        header.pack(pady=(0, 20))
        
        # Current Password
        ctk.CTkLabel(main_card, text="Current Password", text_color="#7A849C", font=("Inter", 13)).pack(anchor="w", padx=40)
        e_curr = ctk.CTkEntry(main_card, show="*", height=40, fg_color="#1A1D2D", border_width=0, corner_radius=6, placeholder_text="Enter current password")
        e_curr.pack(fill="x", padx=40, pady=(5, 15))
        
        # New Password
        ctk.CTkLabel(main_card, text="New Password", text_color="#7A849C", font=("Inter", 13)).pack(anchor="w", padx=40)
        e_new = ctk.CTkEntry(main_card, show="*", height=40, fg_color="#1A1D2D", border_width=0, corner_radius=6, placeholder_text="Enter new password")
        e_new.pack(fill="x", padx=40, pady=(5, 15))
        
        # Confirm Password
        ctk.CTkLabel(main_card, text="Confirm New Password", text_color="#7A849C", font=("Inter", 13)).pack(anchor="w", padx=40)
        e_conf = ctk.CTkEntry(main_card, show="*", height=40, fg_color="#1A1D2D", border_width=0, corner_radius=6, placeholder_text="Confirm new password")
        e_conf.pack(fill="x", padx=40, pady=(5, 25))
        
        def attempt_save():
            p_curr = e_curr.get()
            p_new = e_new.get()
            p_conf = e_conf.get()
            
            if not p_curr or not p_new or not p_conf:
                import tkinter.messagebox as mb
                mb.showerror("Error", "All fields are required!")
                return
                
            if p_new != p_conf:
                import tkinter.messagebox as mb
                mb.showerror("Error", "New passwords do not match!")
                return
                
            username = self.controller.shared_data.get("username")
            user_type = self.controller.shared_data.get("user_type")
            
            from logic.central_auth import CentralAuth
            success, msg = CentralAuth().update_password(username, user_type, p_curr, p_new)
            
            if success:
                top.destroy()
                ModernMessagebox("Success", "Security settings updated successfully.", "success")
            else:
                import tkinter.messagebox as mb
                mb.showerror("Error", f"Failed to update password: {msg}")
                
        btn_save = ctk.CTkButton(
            main_card, 
            text="SAVE CHANGES", 
            height=45, 
            font=("Outfit", 14, "bold"),
            fg_color="#00E5FF", 
            text_color="black",
            hover_color="#00B3CC",
            corner_radius=6,
            command=attempt_save
        )
        btn_save.pack(fill="x", padx=40, pady=(0, 30))

    def open_ai_simulator(self):
        sim = ctk.CTkToplevel(self)
        sim.geometry("500x600")
        sim.title("AcaDesk AI Sandbox")
        sim.attributes("-topmost", True)
        
        head = ctk.CTkLabel(sim, text="AI RISK SANDBOX", font=FONTS["h2"], text_color="#00E5FF")
        head.pack(pady=20)
        
        att_v = ctk.IntVar(value=75)
        mrk_v = ctk.IntVar(value=60)
        bkl_v = ctk.IntVar(value=0)
        
        def trigger_calc(*args):
            at = att_v.get()
            mk = mrk_v.get()
            bk = bkl_v.get()
            res = self.ai.analyze({"attendance_pct": at, "internal_marks": mk, "backlog_count": bk, "year": 2})
            
            level = res['level']
            action = res['action']
            
            if level == "High":
                l_col = COLORS["danger"]
            else:
                l_col = COLORS["success"]
                
            risk_disp.configure(text=f"RISK: {level}", text_color=l_col)
            act_disp.configure(text=f"Action: {action}")
            
        # UI Sliders
        s1 = ctk.CTkSlider(sim, from_=0, to=100, variable=att_v, command=trigger_calc)
        s1.pack(pady=5)
        ctk.CTkLabel(sim, text="Attendance %").pack()
        
        s2 = ctk.CTkSlider(sim, from_=0, to=100, variable=mrk_v, command=trigger_calc)
        s2.pack(pady=5)
        ctk.CTkLabel(sim, text="Marks %").pack()
        
        s3 = ctk.CTkSlider(sim, from_=0, to=10, variable=bkl_v, command=trigger_calc)
        s3.pack(pady=5)
        ctk.CTkLabel(sim, text="Backlogs").pack()
        
        risk_disp = ctk.CTkLabel(sim, text="RISK: ...", font=FONTS["h1"])
        risk_disp.pack(pady=20)
        
        act_disp = ctk.CTkLabel(sim, text="Action: ...", wraplength=400)
        act_disp.pack()
        
        trigger_calc()