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
    from logic.risk_engine import AdvancedRiskPredictor
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
            logo_path = os.path.join(root_dir, "logo.png")
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

class AnalyticsPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.db = None
        self.ai = AdvancedRiskPredictor()
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
                    # Create a local db connection for background thread to avoid race conditions
                    from logic.db_handler import DBHandler
                    local_db = DBHandler(self.controller.shared_data.get("erp_config"))
                    all_students = local_db.get_all_students()
                    local_db.close()
                    
                    if not all_students:
                        self.after(0, loading_lbl.destroy)
                        return
                        
                    global_stats, branch_stats_raw = self.ai.batch_analyze(all_students)
                    branch_stats = {self.translator.get_name(bid): s for bid, s in branch_stats_raw.items()}
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

    def _draw_admin_charts(self, global_stats, branch_stats, loading_lbl):
        loading_lbl.destroy()
        
        self.charts_frame.grid_columnconfigure(0, weight=1)
        self.charts_frame.grid_columnconfigure(1, weight=2)
        
        # Left: Overall Risk (Matplotlib Pie Chart)
        l_outer = ctk.CTkFrame(self.charts_frame, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        l_outer.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        
        ctk.CTkLabel(l_outer, text="OVERALL INSTITUTION RISK", font=("Inter", 12, "bold"), text_color="#7A849C").pack(pady=(10, 0))
        
        total = global_stats["High"] + global_stats["Medium"] + global_stats["Low"]
        if total > 0:
            pie_container = ctk.CTkFrame(l_outer, fg_color="transparent")
            pie_container.pack(fill="both", expand=True, padx=5, pady=5)
            
            import matplotlib.pyplot as plt
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            fig1 = Figure(figsize=(2.2, 2.2), dpi=100)
            fig1.patch.set_facecolor("#12141E")
            ax1 = fig1.add_subplot(111)
            
            labels = ["High Risk", "Medium", "Safe"]
            counts = [global_stats["High"], global_stats["Medium"], global_stats["Low"]]
            colors = ["#FF3D00", "#FF9100", "#00E676"]
            
            filtered_labels = []
            filtered_counts = []
            filtered_colors = []
            for lbl, count, color in zip(labels, counts, colors):
                if count > 0:
                    filtered_labels.append(lbl)
                    filtered_counts.append(count)
                    filtered_colors.append(color)
            
            wedges, texts, autotexts = ax1.pie(filtered_counts, labels=filtered_labels, colors=filtered_colors, autopct='%1.1f%%', 
                                               textprops={'color':"white", 'fontsize': 8, 'weight': 'bold'}, 
                                               pctdistance=0.75, 
                                               wedgeprops=dict(width=0.3, edgecolor="#12141E", linewidth=2))
            
            centre_circle = plt.Circle((0,0),0.70,fc="#12141E")
            fig1.gca().add_artist(centre_circle)
            
            fig1.tight_layout(pad=0)
            canvas1 = FigureCanvasTkAgg(fig1, master=pie_container)
            canvas1.draw()
            canvas1.get_tk_widget().pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(l_outer, text="No Data Available", text_color="gray").pack(expand=True)

        # Right: Risk by Department (Native Stacked Bar)
        r_outer = ctk.CTkFrame(self.charts_frame, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        r_outer.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        
        ctk.CTkLabel(r_outer, text="RISK BY DEPARTMENT", font=("Inter", 12, "bold"), text_color="#7A849C").pack(pady=(10, 0))
        
        dept_names = list(branch_stats.keys())
        if dept_names:
            bars_frame = ctk.CTkFrame(r_outer, fg_color="transparent")
            bars_frame.pack(fill="both", expand=True, padx=20, pady=(2, 5))
            
            for d in dept_names:
                row = ctk.CTkFrame(bars_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                
                ctk.CTkLabel(row, text=d, font=("Inter", 10, "bold"), text_color="white", width=50, anchor="e").pack(side="left", padx=(0, 8))
                
                h = branch_stats[d].get("High", 0)
                m = branch_stats[d].get("Medium", 0)
                l = branch_stats[d].get("Low", 0)
                tot = h + m + l
                
                track = ctk.CTkFrame(row, fg_color="#1A1D2D", height=6, corner_radius=3)
                track.pack(side="left", fill="x", expand=True)
                track.pack_propagate(False)
                
                if tot > 0:
                    pw_l = l/tot
                    pw_m = m/tot
                    pw_h = h/tot
                    
                    if pw_l > 0:
                        ctk.CTkFrame(track, fg_color="#00E676", width=1, corner_radius=3).place(relx=0, rely=0, relwidth=pw_l, relheight=1)
                    if pw_m > 0:
                        ctk.CTkFrame(track, fg_color="#FF9100", width=1, corner_radius=3 if pw_h==0 else 0).place(relx=pw_l, rely=0, relwidth=pw_m, relheight=1)
                    if pw_h > 0:
                        ctk.CTkFrame(track, fg_color="#FF3D00", width=1, corner_radius=3).place(relx=pw_l+pw_m, rely=0, relwidth=pw_h, relheight=1)
        else:
            ctk.CTkLabel(r_outer, text="No Data Available", text_color="gray").pack(expand=True)

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
                from logic.institutional_analytics import InstitutionalAnalytics
                flipped_map = {name: str(bid) for bid, name in self.translator.map.items()}
                data = InstitutionalAnalytics.compute_dashboard_data(self.db, self.ai, flipped_map, target_branch_id=self.current_branch)
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

    def _render_dept_analytics(self, frame, data):
        for w in frame.winfo_children(): w.destroy()
        if not data or not data["ranked_departments"]:
            ctk.CTkLabel(frame, text="No data available for this department.", text_color="gray").pack()
            return
            
        stats = data["ranked_departments"][0][1]
        
        # 1. The Big 3 Core Health Pulse Cards
        pulse_frame = ctk.CTkFrame(frame, fg_color="transparent")
        pulse_frame.pack(fill="x", pady=(0, 20))
        pulse_frame.grid_columnconfigure((0,1,2), weight=1)
        
        pulses = [
            ("Avg Attendance", f"{stats.get('avg_attendance', 0):.1f}%", "#00E676" if stats.get('avg_attendance', 0) > 75 else "#FF3D00"),
            ("Avg CGPA/Marks", f"{stats.get('avg_cgpa', 0):.1f}%", "#00E5FF"),
            ("Dept Health Score", f"{int(stats.get('health_score', 0))}/100", "#00E676" if stats.get('health_score', 0) > 75 else "#FF3D00")
        ]
        
        for i, (title, val, color) in enumerate(pulses):
            card = ctk.CTkFrame(pulse_frame, fg_color="#12141E", corner_radius=12)
            card.grid(row=0, column=i, padx=8, sticky="nsew")
            
            top_glow = ctk.CTkFrame(card, height=4, fg_color=color, corner_radius=0)
            top_glow.pack(fill="x")
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=25, pady=25)
            ctk.CTkLabel(content, text=title, font=("Inter", 12, "bold"), text_color="#7A849C").pack(anchor="w")
            ctk.CTkLabel(content, text=val, font=("Outfit", 36, "bold"), text_color=color).pack(anchor="w", pady=(5, 0))
            
        # 2. Risk Density Pill & Alert Tags
        bottom_metrics = ctk.CTkFrame(frame, fg_color="transparent")
        bottom_metrics.pack(fill="x", pady=(0, 10))
        
        # Left side: Risk Pill
        risk_frame = ctk.CTkFrame(bottom_metrics, fg_color="#12141E", corner_radius=20, border_width=1, border_color="#2A2E3F")
        risk_frame.pack(side="left", padx=(8, 0), ipady=5)
        
        ctk.CTkLabel(risk_frame, text="RISK DENSITY:", font=("Inter", 11, "bold"), text_color="#7A849C").pack(side="left", padx=(20, 10))
        
        high = stats.get("High", 0)
        med = stats.get("Medium", 0)
        low = stats.get("Low", 0)
        
        def make_risk_badge(parent, count, label, color):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(side="left", padx=10)
            ctk.CTkLabel(f, text=str(count), font=("Outfit", 18, "bold"), text_color=color).pack(side="left", padx=(0, 5))
            ctk.CTkLabel(f, text=label, font=("Inter", 11, "bold"), text_color="#aaa").pack(side="left")
            
        if high > 0: make_risk_badge(risk_frame, high, "HIGH", "#FF3D00")
        if med > 0: make_risk_badge(risk_frame, med, "MED", "#FF9100")
        if low > 0: make_risk_badge(risk_frame, low, "LOW", "#00E676")
        if high == 0 and med == 0 and low == 0: make_risk_badge(risk_frame, 0, "STUDENTS", "#aaa")
        
        # Right side: Alert Tags
        alerts = ctk.CTkFrame(bottom_metrics, fg_color="transparent")
        alerts.pack(side="right", padx=(0, 8))
        
        bkl = stats.get('avg_backlogs', 0)
        bkl_color = "#FF3D00" if bkl > 1 else "#00E676"
        ctk.CTkLabel(alerts, text=f"⚠️ Avg Backlogs: {bkl:.1f}", font=("Inter", 12, "bold"), fg_color="#1A1D2D", text_color=bkl_color, corner_radius=8).pack(side="right", padx=5, ipadx=10, ipady=8)
        
        drivers = stats.get('top_drivers', ["N/A"])[0] if stats.get('top_drivers') else "N/A"
        ctk.CTkLabel(alerts, text=f"🔍 Driver: {drivers}", font=("Inter", 12, "bold"), fg_color="#1A1D2D", text_color="#FF9100", corner_radius=8).pack(side="right", padx=5, ipadx=10, ipady=8)

    def show_student_list(self):
        self.header.pack_forget()
        self._clear()
        name = self.translator.get_name(self.current_branch)
        
        # TOOLBAR (top bar)
        toolbar = ctk.CTkFrame(self.content_area, fg_color="#0d0d0d", height=56, corner_radius=0)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        left_tool = ctk.CTkFrame(toolbar, fg_color="transparent")
        left_tool.pack(side="left", fill="y", padx=20)
        
        btn_back = ctk.CTkButton(left_tool, text="←", width=36, height=36, corner_radius=8, 
                                 fg_color="#222", hover_color="#333", text_color="white", font=FONTS["h3"],
                                 command=self.go_back)
        btn_back.pack(side="left", pady=10)
        
        lbl_title = ctk.CTkLabel(left_tool, text=f"{name} > {self.current_year}", font=("Outfit", 22, "bold"), text_color="#00E5FF")
        lbl_title.pack(side="left", padx=15, pady=10)

        right_tool = ctk.CTkFrame(toolbar, fg_color="transparent")
        right_tool.pack(side="right", fill="y", padx=20)

        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.filter_list)
        search_ent = ctk.CTkEntry(right_tool, textvariable=self.search_var, placeholder_text="Search student name or ID...",
                                  width=250, height=34, corner_radius=17, fg_color=COLORS["card"], border_color=COLORS["border"], border_width=1)
        search_ent.pack(side="left", padx=(0, 15), pady=11)
        search_ent.bind("<FocusIn>", lambda e: search_ent.configure(border_color=COLORS["accent"]))
        search_ent.bind("<FocusOut>", lambda e: search_ent.configure(border_color=COLORS["border"]))

        exp_btn = ctk.CTkButton(right_tool, text="Export CSV", width=100, height=34, corner_radius=17,
                                fg_color=COLORS["card"], border_width=1, border_color=COLORS["accent"], text_color="white",
                                hover_color="#222", command=self.export_report)
        exp_btn.pack(side="left", pady=11)

        # FILTER BAR
        filter_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(20, 0), padx=20)
        
        self.filter_vars = {}
        self.current_filter = "All"
        self.btn_all = self._create_pill_btn(filter_frame, "ALL", "All", "#888888")
        self.btn_high = self._create_pill_btn(filter_frame, "HIGH RISK", "High", "#FF5555")
        self.btn_med = self._create_pill_btn(filter_frame, "MEDIUM RISK", "Medium", "#FF9100")
        self.btn_low = self._create_pill_btn(filter_frame, "LOW RISK", "Low", "#00C853")
        
        self.note_filter_var = ctk.StringVar(value="All Students")
        self.note_filter = ctk.CTkComboBox(filter_frame, values=["All Students", "No Notes", "Active Notes", "Follow-Up Required", "Critical Cases", "Closed Cases"], 
                                           variable=self.note_filter_var, command=self.filter_list, width=170, height=32, corner_radius=16, 
                                           fg_color=COLORS["card"], border_color=COLORS["border"], button_color=COLORS["card"])
        self.note_filter.pack(side="right")
        ctk.CTkLabel(filter_frame, text="Note Filter:", text_color="gray").pack(side="right", padx=(0, 10))

        # SUMMARY BAR
        self.summary_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.summary_frame.pack(fill="x", padx=20, pady=(10, 15))

        self.list_frame = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=10)
        
        from logic.central_auth import CentralAuth
        self.note_stats = CentralAuth().get_student_note_stats(department=None)
        
        self._update_filter_visuals()
        self.filter_list()

    def _create_pill_btn(self, p, text, val, color):
        btn = ctk.CTkButton(p, text=text, height=32, corner_radius=16,
                            fg_color="transparent", border_width=1, border_color=color,
                            text_color=color, hover_color=color,
                            command=lambda v=val: self.apply_filter(v))
        btn.pack(side="left", padx=(0, 10))
        btn.base_text = text
        btn.base_color = color
        self.filter_vars[val] = btn
        return btn

    def apply_filter(self, val):
        self.current_filter = val
        self._update_filter_visuals()
        self.filter_list()

    def _update_filter_visuals(self):
        for val, btn in self.filter_vars.items():
            if val == self.current_filter:
                btn.configure(fg_color=btn.base_color, text_color="white", font=FONTS["body"])
            else:
                btn.configure(fg_color="transparent", text_color=btn.base_color, font=FONTS["body"])

    def filter_list(self, *args):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        for widget in self.summary_frame.winfo_children():
            widget.destroy()
            
        loading_lbl = ctk.CTkLabel(self.list_frame, text="Analysing students...", font=FONTS["h2"], text_color="gray")
        loading_lbl.pack(pady=100)
        self.update()
        
        self.after(10, self._process_filter_list)

    def _process_filter_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        students = self.db.get_students(self.current_branch, self.current_year)
        query = self.search_var.get().lower()
        note_f = self.note_filter_var.get()
        
        filtered_students = []
        for s in students:
            stat = self.note_stats.get(s['id'], {})
            st = stat.get('latest_status', 'NONE') if stat else 'NONE'
            
            keep = True
            if note_f == "No Notes" and st != "NONE": keep = False
            elif note_f == "Active Notes" and st != "ACTIVE": keep = False
            elif note_f == "Follow-Up Required" and st != "FOLLOW_UP": keep = False
            elif note_f == "Critical Cases" and st != "CRITICAL": keep = False
            elif note_f == "Closed Cases" and st != "CLOSED": keep = False
            
            is_match = query in str(s['id']).lower() or query in str(s['name']).lower()
            if is_match and keep:
                filtered_students.append(s)

        processed_students = []
        counts = {"High": 0, "Medium": 0, "Low": 0, "All": 0}
        
        for s in filtered_students:
            report = self.ai.analyze(s)
            
            # Map AdvancedRiskPredictor output back to what dashboard expects
            if 'score' in report and 'risk_score' not in report:
                report['risk_score'] = report['score']
            if 'level' in report and 'risk_category' not in report:
                report['risk_category'] = report['level']
                
            counts["All"] += 1
            counts[report['level']] += 1
            processed_students.append((s, report))
            
        self.btn_all.configure(text=f"{self.btn_all.base_text}  •  {counts['All']}")
        self.btn_high.configure(text=f"{self.btn_high.base_text}  •  {counts['High']}")
        self.btn_med.configure(text=f"{self.btn_med.base_text}  •  {counts['Medium']}")
        self.btn_low.configure(text=f"{self.btn_low.base_text}  •  {counts['Low']}")
        
        sum_txt = ctk.CTkLabel(self.summary_frame, text="Showing ", font=FONTS["caption"], text_color="#888")
        sum_txt.pack(side="left")
        ctk.CTkLabel(self.summary_frame, text=f"{counts['All']} students", font=FONTS["caption"], text_color="white").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text="  |  ", font=FONTS["caption"], text_color="#444").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text=f"{counts['High']} High", font=FONTS["caption"], text_color="#FF5555").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text="  •  ", font=FONTS["caption"], text_color="#444").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text=f"{counts['Medium']} Medium", font=FONTS["caption"], text_color="#FF9100").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text="  •  ", font=FONTS["caption"], text_color="#444").pack(side="left")
        ctk.CTkLabel(self.summary_frame, text=f"{counts['Low']} Low", font=FONTS["caption"], text_color="#00C853").pack(side="left")

        displayed = 0
        for s, report in processed_students:
            if self.current_filter == "All" or report['level'] == self.current_filter:
                self._draw_modern_row(s, report)
                displayed += 1
                
        if displayed == 0:
            empty_f = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            empty_f.pack(pady=50)
            ctk.CTkLabel(empty_f, text="👤\u200d\u2205", font=("Arial", 48), text_color="#444").pack(pady=(0, 10))
            ctk.CTkLabel(empty_f, text="No students found", font=("Arial", 16, "bold"), text_color="#888").pack()
            ctk.CTkLabel(empty_f, text="Try adjusting your search or filter", font=("Arial", 12), text_color="#444").pack()

    def _draw_modern_row(self, s, report):
        import tkinter as tk
        row_wrapper = ctk.CTkFrame(self.list_frame, fg_color=COLORS["card"], corner_radius=8, border_width=1, border_color=COLORS["border"], height=64)
        row_wrapper.pack(fill="x", pady=5, padx=10)
        row_wrapper.pack_propagate(False)
        
        def on_enter(e, rw=row_wrapper): rw.configure(fg_color="#242424")
        def on_leave(e, rw=row_wrapper): rw.configure(fg_color=COLORS["card"])
        row_wrapper.bind("<Enter>", on_enter)
        row_wrapper.bind("<Leave>", on_leave)

        level = report.get('level', 'Low')
        if level == "High": r_col, dim_col = "#FF5555", "#4d0000"
        elif level == "Medium": r_col, dim_col = "#FF9100", "#4d2b00"
        else: r_col, dim_col = "#00C853", "#004d20"
        
        strip = tk.Canvas(row_wrapper, width=4, height=64, bg=r_col, highlightthickness=0)
        strip.pack(side="left", fill="y")
        
        avatar_f = ctk.CTkFrame(row_wrapper, width=40, height=40, corner_radius=20, fg_color=dim_col)
        avatar_f.pack(side="left", padx=(15, 15), pady=12)
        avatar_f.pack_propagate(False)
        
        name_str = str(s.get('name', ''))
            
        initials_lbl = ctk.CTkLabel(avatar_f, text="👤", font=("Arial", 18), text_color="white")
        initials_lbl.place(relx=0.5, rely=0.5, anchor="center")
        
        for child in [strip, avatar_f, initials_lbl]:
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)

        info_f = ctk.CTkFrame(row_wrapper, fg_color="transparent")
        info_f.pack(side="left", fill="both", expand=True, pady=10)
        
        name_f = ctk.CTkFrame(info_f, fg_color="transparent")
        name_f.pack(anchor="w")
        
        lbl_name = ctk.CTkLabel(name_f, text=name_str, font=("Arial", 14, "bold"), text_color="#00E5FF")
        lbl_name.pack(side="left")
        
        if report.get('is_first_year'):
            pill = ctk.CTkFrame(name_f, fg_color="#4a0080", corner_radius=10, height=20)
            pill.pack(side="left", padx=10)
            ctk.CTkLabel(pill, text="1st Year", font=("Arial", 10, "bold"), text_color="white").pack(padx=8, pady=0)
            
        lbl_id = ctk.CTkLabel(info_f, text=str(s.get('id', '')), font=("Arial", 12), text_color="#888888")
        lbl_id.pack(anchor="w", pady=(0, 0))
        
        for child in [info_f, name_f, lbl_name, lbl_id]:
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)

        btn_diag = ctk.CTkButton(row_wrapper, text="DIAGNOSE →", width=100, height=34, corner_radius=17,
                                 fg_color="transparent", border_width=1, border_color="#00E5FF", text_color="#00E5FF",
                                 hover_color="#00E5FF", command=lambda d=s, r=report: self.open_deep_analysis(d, r))
        def diag_enter(e, b=btn_diag, rw=row_wrapper): b.configure(text_color="black"); rw.configure(fg_color="#242424")
        def diag_leave(e, b=btn_diag, rw=row_wrapper): b.configure(text_color="#00E5FF"); rw.configure(fg_color=COLORS["card"])
        btn_diag.bind("<Enter>", diag_enter, add="+")
        btn_diag.bind("<Leave>", diag_leave, add="+")
        btn_diag.pack(side="right", padx=15, pady=15)

        metrics_f = ctk.CTkFrame(row_wrapper, fg_color="transparent")
        metrics_f.pack(side="right", padx=15, pady=15)
        
        score_pill = ctk.CTkFrame(metrics_f, fg_color=dim_col, corner_radius=12, height=24)
        score_pill.pack(side="left", padx=5)
        ctk.CTkLabel(score_pill, text=f"Score: {report.get('risk_score', 0):.1f}", font=("Arial", 11), text_color=r_col).pack(padx=8, pady=2)
        
        if s.get('avg_attendance') is not None:
            att_pill = ctk.CTkFrame(metrics_f, fg_color="#222222", corner_radius=12, height=24)
            att_pill.pack(side="left", padx=5)
            ctk.CTkLabel(att_pill, text=f"Att: {float(s['avg_attendance']):.1f}%", font=("Arial", 11), text_color="#ccc").pack(padx=8, pady=2)
            
        conf_pill = ctk.CTkFrame(metrics_f, fg_color="#222222", corner_radius=12, height=24)
        conf_pill.pack(side="left", padx=5)
        ctk.CTkLabel(conf_pill, text=f"Conf: {report.get('confidence_score', 0)}%", font=("Arial", 11), text_color="#ccc").pack(padx=8, pady=2)
        
        stat = self.note_stats.get(s['id'], {})
        st = stat.get('latest_status', 'NONE') if stat else 'NONE'
        tot = stat.get('total_notes', 0) if stat else 0
        if st == 'CRITICAL': n_icon, n_color = "🔴", "#FF5555"
        elif st == 'FOLLOW_UP': n_icon, n_color = "🟡", "yellow"
        elif st == 'ACTIVE': n_icon, n_color = "🟢", "#4ADE80"
        elif st == 'CLOSED': n_icon, n_color = "✅", "cyan"
        else: n_icon, n_color = "⚪", "gray"
        
        note_pill = ctk.CTkFrame(metrics_f, fg_color="#222222", corner_radius=12, height=24, cursor="hand2")
        note_pill.pack(side="left", padx=5)
        note_lbl = ctk.CTkLabel(note_pill, text=f"{n_icon} {tot}" if tot > 0 else f"{n_icon}", text_color=n_color, font=("Arial", 11))
        note_lbl.pack(padx=8, pady=2)
        
        def show_quick_view(ev, st_stat=stat):
            if not st_stat: return
            q = ctk.CTkToplevel(self)
            q.title("Note Quick View")
            q.geometry("400x250")
            q.attributes("-topmost", True)
            q.configure(fg_color="#111")
            ctk.CTkLabel(q, text=f"Total Notes: {st_stat.get('total_notes', 0)}", font=FONTS["body"]).pack(pady=(15,5))
            ctk.CTkLabel(q, text=f"Status: {st_stat.get('latest_status', 'NONE')}", text_color=n_color).pack()
            dt = st_stat.get('latest_date')
            dt_str = dt.strftime("%b %d, %Y") if dt else "N/A"
            ctk.CTkLabel(q, text=f"Last Updated: {dt_str} by {st_stat.get('latest_faculty', 'N/A')}", font=FONTS["badge"]).pack()
            ctk.CTkLabel(q, text=st_stat.get('latest_text', ''), wraplength=350, justify="left").pack(pady=10)
            
        note_pill.bind("<Double-1>", show_quick_view)
        note_lbl.bind("<Double-1>", show_quick_view)
        
        def note_enter(ev, st_stat=stat, rw=row_wrapper):
            rw.configure(fg_color="#242424")
            if not st_stat: return
            if not hasattr(self, 'tooltip'):
                self.tooltip = ctk.CTkToplevel(self)
                self.tooltip.overrideredirect(True)
                self.tooltip.configure(fg_color="#222")
                dt = st_stat.get('latest_date')
                dt_str = dt.strftime("%b %d, %Y") if dt else "N/A"
                txt = f"Date: {dt_str}\nFaculty: {st_stat.get('latest_faculty', 'N/A')}\nStatus: {st_stat.get('latest_status')}\nNote: {st_stat.get('latest_text', '')}"
                ctk.CTkLabel(self.tooltip, text=txt, justify="left", font=FONTS["badge"], wraplength=250, text_color="white", corner_radius=5, fg_color="#222").pack(padx=10, pady=5)
                x = ev.widget.winfo_rootx() + 25
                y = ev.widget.winfo_rooty() + 25
                self.tooltip.geometry(f"+{x}+{y}")
                
        def note_leave(ev, rw=row_wrapper):
            rw.configure(fg_color=COLORS["card"])
            if hasattr(self, 'tooltip') and self.tooltip:
                self.tooltip.destroy()
                del self.tooltip
                
        note_pill.bind("<Enter>", note_enter)
        note_pill.bind("<Leave>", note_leave)
        note_lbl.bind("<Enter>", note_enter)
        note_lbl.bind("<Leave>", note_leave)
            
        for p in metrics_f.winfo_children():
            if p.cget("cursor") != "hand2":
                p.bind("<Enter>", on_enter)
                p.bind("<Leave>", on_leave)
                for c in p.winfo_children():
                    c.bind("<Enter>", on_enter)
                    c.bind("<Leave>", on_leave)
    def open_deep_analysis(self, data, report):
        top = ctk.CTkToplevel(self)
        top.geometry("1100x850")
        top.title("AcaDesk - Student Diagnosis")
        top.attributes("-topmost", True)
        top.configure(fg_color=COLORS["bg"])

        # Color configurations
        r_color = COLORS["success"]
        if report['level'] == "High": r_color = COLORS["danger"]
        elif report['level'] == "Medium": r_color = COLORS["warning"]

        p_email = data.get('parent_email', 'Not Provided')
        is_email_missing = p_email == 'Not Provided' or not p_email
        branch_name = self.translator.get_name(self.current_branch)

        def send_email_alert():
            from logic.email_service import EmailService
            
            emails_to_send = []
            if data.get("email"): emails_to_send.append(data["email"])
            if data.get("parent_email"): emails_to_send.append(data["parent_email"])
            
            if not emails_to_send:
                ModernMessagebox("No Contact Info", "No email addresses found for this student.", "warning")
                return
                
            es = EmailService()
            success = es.send_early_warning_alert(
                to_emails=emails_to_send,
                student_name=data.get("display_name", data.get("name", "Student")),
                student_id=data.get("registration_no", data.get("id", "Unknown")),
                college_name=self.controller.shared_data.get("college_name", "Your College"),
                risk_level=report.get("level", "Unknown"),
                dominant_factor=list(report.get("drivers", {}).keys())[0] if report.get("drivers") else "Multiple Factors"
            )
            
            if success:
                ModernMessagebox("Success", f"Alert successfully sent to {', '.join(emails_to_send)}", "success")
            else:
                ModernMessagebox("Error", "Failed to send email alert. Check console.", "error")

        # --- LEFT PANEL (320px, Fixed Summary) ---
        left_panel = ctk.CTkFrame(top, width=320, fg_color=COLORS["sidebar"], corner_radius=0, border_width=0, border_color=COLORS["border"])
        left_panel.pack(side="left", fill="y")
        left_panel.pack_propagate(False)

        # Avatar Circle: 64px circle
        avatar_frame = ctk.CTkFrame(left_panel, width=64, height=64, corner_radius=32, fg_color=r_color)
        avatar_frame.pack(pady=(40, 10))
        avatar_frame.pack_propagate(False)
        
        name_str = data.get("name", "Student")
        name_parts = name_str.split()
        initials = "".join([p[0] for p in name_parts[:2]]).upper() if name_parts else "S"
        
        avatar_lbl = ctk.CTkLabel(avatar_frame, text=initials, font=("Roboto", 24, "bold"), text_color="black" if r_color in [COLORS["success"], COLORS["warning"]] else "white")
        avatar_lbl.pack(expand=True)

        ctk.CTkLabel(left_panel, text=data.get("name", "Student"), font=("Roboto", 16, "bold"), text_color="white", wraplength=280).pack(pady=(5, 2))
        ctk.CTkLabel(left_panel, text=f"ID: {data.get('id', 'N/A')}", font=FONTS["body"], text_color="gray").pack(pady=(0, 20))

        ctk.CTkFrame(left_panel, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(left_panel, text=f"{report['score']}", font=("Roboto", 48, "bold"), text_color=r_color).pack(pady=(10, 2))
        ctk.CTkLabel(left_panel, text=f"{report['level'].upper()} RISK", font=FONTS["h3"], text_color=r_color).pack(pady=(0, 2))
        ctk.CTkLabel(left_panel, text=f"Confidence: {report.get('confidence', 0)}%", font=FONTS["body"], text_color="gray").pack(pady=(0, 20))

        ctk.CTkFrame(left_panel, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=20, pady=10)

        info_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=10)
        
        def add_info_row(parent, label, value):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, font=FONTS["body"], text_color="gray", width=90, anchor="w").pack(side="left")
            val_lbl = ctk.CTkLabel(row, text=value, font=FONTS["body"], text_color="white", anchor="w", wraplength=170, justify="left")
            val_lbl.pack(side="left", fill="x", expand=True)
            return val_lbl
            
        add_info_row(info_frame, "Department:", branch_name)
        add_info_row(info_frame, "Year:", str(data.get("year", "N/A")))
        
        contact_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        contact_row.pack(fill="x", pady=5)
        ctk.CTkLabel(contact_row, text="Contact:", font=FONTS["body"], text_color="gray", width=90, anchor="w").pack(side="left")
        
        contact_txt = p_email if p_email != 'Not Provided' else str(data.get('phone', data.get('email', 'Not Provided')))
        ctk.CTkLabel(contact_row, text=contact_txt, font=FONTS["body"], text_color="white", anchor="w", wraplength=170, justify="left").pack(side="left", fill="x", expand=True)
        
        if is_email_missing:
            btn_add_contact = ctk.CTkButton(
                left_panel, 
                text="✎ Add Contact", 
                width=180,
                height=30,
                fg_color="transparent",
                border_width=1,
                border_color=COLORS["accent"],
                text_color=COLORS["accent"],
                font=FONTS["caption"],
                command=lambda: self._open_edit_contact_dialog(data)
            )
            btn_add_contact.pack(pady=10)

        btn_notify = ctk.CTkButton(
            left_panel, 
            text="🔔 Notify", 
            fg_color="#00E5FF", 
            hover_color="#00B8D4",
            text_color="black",
            font=FONTS["h3"],
            height=40,
            command=send_email_alert
        )
        btn_notify.pack(side="bottom", fill="x", padx=20, pady=20)

        # --- RIGHT PANEL (Scrollable Content) ---
        scroll = ctk.CTkScrollableFrame(top, fg_color="transparent")
        scroll.pack(side="left", fill="both", expand=True, padx=20, pady=10)

        def make_section_title(parent, text):
            title_frame = ctk.CTkFrame(parent, fg_color="transparent")
            title_frame.pack(anchor="w", fill="x", pady=(20, 10))
            accent = ctk.CTkFrame(title_frame, width=4, height=18, fg_color="#00E5FF")
            accent.pack(side="left", padx=(5, 10))
            lbl = ctk.CTkLabel(title_frame, text=text, font=("Roboto", 12, "bold"), text_color="#00E5FF", anchor="w")
            lbl.pack(side="left")

        # 1. AI ASSESSMENT
        nlg_report = report.get('explanation', report.get('nlg_report', ''))
        if nlg_report:
            make_section_title(scroll, "AI ASSESSMENT")
            outer_nlg = ctk.CTkFrame(scroll, fg_color="#00E5FF", corner_radius=8)
            outer_nlg.pack(fill="x", pady=5)
            nlg_card = ctk.CTkFrame(outer_nlg, fg_color=COLORS["card"], border_width=0, corner_radius=8)
            nlg_card.pack(fill="both", expand=True, padx=(4, 0))
            ctk.CTkLabel(nlg_card, text=nlg_report, text_color="white", font=FONTS["body"], wraplength=700, justify="left").pack(anchor="w", padx=20, pady=15)

        # 2. ACADEMIC SNAPSHOT
        make_section_title(scroll, "ACADEMIC SNAPSHOT")
        pill_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        pill_frame.pack(fill="x", pady=5)

        def get_pill_color(key, value):
            try:
                val = float(value)
            except (ValueError, TypeError):
                return "gray"
            if key == "attendance":
                return COLORS["success"] if val >= 80 else (COLORS["warning"] if val >= 65 else COLORS["danger"])
            elif key == "cgpa":
                return COLORS["success"] if val >= 7.0 else (COLORS["warning"] if val >= 5.5 else COLORS["danger"])
            elif key == "backlogs":
                return COLORS["success"] if val == 0 else (COLORS["warning"] if val <= 2 else COLORS["danger"])
            elif key == "internal":
                return COLORS["success"] if val >= 70 else (COLORS["warning"] if val >= 50 else COLORS["danger"])
            elif key == "mid":
                return COLORS["success"] if val >= 65 else (COLORS["warning"] if val >= 50 else COLORS["danger"])
            elif key == "lab":
                return COLORS["success"] if val >= 75 else (COLORS["warning"] if val >= 55 else COLORS["danger"])
            elif key == "assignments":
                return COLORS["success"] if val >= 75 else (COLORS["warning"] if val >= 60 else COLORS["danger"])
            return "gray"

        attendance_val = data.get('avg_attendance', data.get('attendance_pct', 0))
        cgpa_val = data.get('cgpa', round(data.get('avg_marks', 0)/10.0, 2) if data.get('avg_marks') else 0)
        backlogs_val = data.get('backlogs', 0)
        internal_val = data.get('internal_marks', data.get('internal_percentage', data.get('internals', 72)))
        mid_val = data.get('mid_exam_score', data.get('mid_sem', 68))
        lab_val = data.get('lab_performance', data.get('lab_marks', 80))
        assignments_val = data.get('assignments_percentage', data.get('assignments', 85))

        metrics = [
            ("Attendance", "attendance", attendance_val, "%"),
            ("CGPA", "cgpa", cgpa_val, ""),
            ("Backlogs", "backlogs", backlogs_val, ""),
            ("Internal", "internal", internal_val, "%"),
            ("Mid Exam", "mid", mid_val, "%"),
            ("Lab", "lab", lab_val, "%"),
            ("Assignments", "assignments", assignments_val, "%")
        ]
        
        for label, key, val, unit in metrics:
            p_color = get_pill_color(key, val)
            val_str = f"{val}{unit}" if val is not None else "N/A"
            pill = ctk.CTkFrame(pill_frame, fg_color=COLORS["card"], corner_radius=8, border_width=1, border_color=COLORS["border"], height=60, width=95)
            pill.pack(side="left", padx=5, fill="both", expand=True)
            pill.pack_propagate(False)
            ctk.CTkLabel(pill, text=label, font=FONTS["caption"], text_color="gray").pack(pady=(8, 2))
            ctk.CTkLabel(pill, text=val_str, font=FONTS["body"], text_color=p_color).pack(pady=(0, 8))

        # 3. FACTOR CONTRIBUTIONS
        make_section_title(scroll, "FACTOR CONTRIBUTIONS")
        chart_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], border_width=1, border_color=COLORS["border"], corner_radius=8)
        chart_card.pack(fill="x", pady=5)
        
        try:
            fig_r = Figure(figsize=(7, 2.8), dpi=100)
            fig_r.patch.set_facecolor(COLORS["card"])
            ax_r = fig_r.add_subplot(111)
            ax_r.set_facecolor(COLORS["card"])
            
            c_data = report.get('contributions', {"Att": 30, "Marks": 50, "Bkl": 20})
            sorted_contribs = sorted(c_data.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            sorted_contribs.reverse()
            
            c_keys = [k[:12] for k, v in sorted_contribs]
            c_vals = [abs(v) for k, v in sorted_contribs]
            c_colors = [COLORS["danger"] if v > 15 else COLORS["accent"] for v in c_vals]
            
            title = "Top Risk Drivers (SHAP)" if report.get('shap_values') else "Factor Contributions"
            ax_r.set_title(title, color="white", fontsize=10)
            ax_r.barh(c_keys, c_vals, color=c_colors)
            ax_r.tick_params(colors='white', labelsize=8)
            ax_r.set_xlim(0, max(max(c_vals) + 10, 100) if c_vals else 100)
            fig_r.tight_layout()
            
            can_r = FigureCanvasTkAgg(fig_r, master=chart_card)
            wid_r = can_r.get_tk_widget()
            wid_r.pack(fill="both", expand=True, padx=10, pady=10)
        except Exception as e:
            pass

        # 4. TREND ANALYSIS
        trend_info = report.get('trend_info')
        has_trend_visuals = trend_info and trend_info.get("history") and len(trend_info["history"]) > 1
        has_trend_line = not report.get('is_first_year', False)
        
        if has_trend_visuals or has_trend_line:
            make_section_title(scroll, "TREND ANALYSIS")
            
            if has_trend_visuals:
                trend_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], border_width=1, border_color=COLORS["border"], corner_radius=8)
                trend_card.pack(fill="x", pady=5)
                
                t_head = ctk.CTkFrame(trend_card, fg_color="transparent")
                t_head.pack(fill="x", padx=20, pady=(15, 10))
                
                t_status = trend_info.get("trend_status", "Unknown")
                t_color = COLORS["success"] if "Improving" in t_status else (COLORS["danger"] if "Decline" in t_status else "gray")
                
                ctk.CTkLabel(t_head, text=f"Trend Score: {trend_info.get('trend_score', 0)}/100", font=FONTS["body"], text_color="white").pack(side="left")
                ctk.CTkLabel(t_head, text=f"Status: {t_status}", font=FONTS["body"], text_color=t_color).pack(side="right")
                
                try:
                    TrendVisuals.create_trend_charts(trend_card, trend_info)
                except Exception as e:
                    print(f"Failed to render trend visuals: {e}")
            
            if has_trend_line:
                t_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], border_width=1, border_color=COLORS["border"], corner_radius=8)
                t_card.pack(fill="x", pady=10)
                
                try:
                    fig_t = Figure(figsize=(7, 2.2), dpi=100)
                    fig_t.patch.set_facecolor(COLORS["card"])
                    ax_t = fig_t.add_subplot(111)
                    ax_t.set_facecolor(COLORS["card"])
                    
                    trend_vals = report.get('trends', {}).get('risk') or report.get('trend')
                    if not trend_vals:
                        trend_vals = [65, 70, 62, 68]
                        
                    t_len = len(trend_vals)
                    ax_t.set_xticks(range(t_len))
                    t_labels = [f"Sem {i+1}" for i in range(t_len)]
                    if t_len > 0:
                        t_labels[-1] = "Current"
                        
                    ax_t.set_xticklabels(t_labels, color='white')
                    ax_t.plot(trend_vals, marker='o', color=COLORS["accent"], linewidth=2)
                    ax_t.tick_params(colors='white', labelsize=8)
                    fig_t.tight_layout()
                    
                    can_t = FigureCanvasTkAgg(fig_t, master=t_card)
                    wid_t = can_t.get_tk_widget()
                    wid_t.pack(fill="both", expand=True, padx=10, pady=10)
                except Exception as e:
                    pass

        # 5. RECOMMENDED ACTIONS
        recs = report.get('recommendations', [])
        if recs:
            make_section_title(scroll, "RECOMMENDED ACTIONS")
            for r in recs:
                p_color = COLORS['danger'] if r.get('priority', 1) == 1 else COLORS['warning'] if r.get('priority', 2) == 2 else COLORS['success']
                outer_rec = ctk.CTkFrame(scroll, fg_color=p_color, corner_radius=8)
                outer_rec.pack(fill="x", pady=5)
                
                r_card = ctk.CTkFrame(outer_rec, fg_color=COLORS["card"], border_width=0, corner_radius=8)
                r_card.pack(fill="both", expand=True, padx=(4, 0))
                
                badge_lbl = ctk.CTkLabel(r_card, text=f"Priority {r.get('priority', 1)}", fg_color=p_color, text_color="white", corner_radius=4, font=FONTS["badge"], width=70, height=20)
                badge_lbl.pack(side="left", padx=15, pady=15)
                
                text_frame = ctk.CTkFrame(r_card, fg_color="transparent")
                text_frame.pack(side="left", fill="both", expand=True, pady=10, padx=(0, 15))
                
                ctk.CTkLabel(text_frame, text=r['action'], font=FONTS["h3"], anchor="w", justify="left").pack(anchor="w")
                ctk.CTkLabel(text_frame, text=f"Rationale: {r.get('rationale', r.get('reason', ''))}", text_color="gray", font=FONTS["caption"], wraplength=500, anchor="w", justify="left").pack(anchor="w", pady=(2, 0))

        # Embedded functions for Faculty Notes
        def load_history():
            for w in history_frame.winfo_children(): w.destroy()
            st_id = data.get("id", data.get("student_id", ""))
            notes = CentralAuth().get_notes_for_student(st_id)
            if not notes:
                ctk.CTkLabel(history_frame, text="No previous notes for this student.", text_color="#555", font=FONTS["caption"]).pack(pady=10)
                return
            for n in notes:
                st = n.get('note_status', 'ACTIVE')
                if st == 'CRITICAL': c = "#FF5555"
                elif st == 'FOLLOW_UP': c = "yellow"
                elif st == 'ACTIVE': c = "#4ADE80"
                else: c = "cyan"
                
                b_frame = ctk.CTkFrame(history_frame, fg_color="transparent")
                b_frame.pack(fill="x", pady=5, padx=10)
                
                f_card = ctk.CTkFrame(b_frame, fg_color=c, corner_radius=8)
                f_card.pack(anchor="w", fill="x")
                
                inner_card = ctk.CTkFrame(f_card, fg_color="#18181b", corner_radius=6)
                inner_card.pack(fill="both", expand=True, padx=(4, 1), pady=1)
                
                author = n.get('faculty_username', 'Unknown')
                dt = n.get('created_at')
                dt_str = dt.strftime("%b %d, %Y %I:%M %p") if dt else "Unknown Date"
                
                head_f = ctk.CTkFrame(inner_card, fg_color="transparent")
                head_f.pack(fill="x", padx=10, pady=(8,0))
                
                ctk.CTkLabel(head_f, text=f"{author}", font=FONTS["body"], text_color="#e4e4e7").pack(side="left")
                ctk.CTkLabel(head_f, text=f" • {dt_str}", font=FONTS["badge"], text_color="#aaa").pack(side="left", padx=5)
                
                badge = ctk.CTkLabel(head_f, text=f" {st} ", font=FONTS["badge"], text_color="#000", fg_color=c, corner_radius=4)
                badge.pack(side="right", padx=(10,0))
                
                ctk.CTkLabel(inner_card, text=n.get('note_text', ''), font=FONTS["body"], text_color="#a1a1aa", wraplength=450, justify="left").pack(anchor="w", padx=10, pady=(8,10))

        def save_note():
            nt = self.txt_note.get("1.0", "end-1c").strip()
            if not nt: return
            fac_usr = self.controller.shared_data.get("username", "Unknown")
            st_id = data.get("id")
            dept = branch_name
            st = self.note_status_var.get()
            try:
                from logic.central_auth import CentralAuth
                CentralAuth().save_faculty_note(st_id, fac_usr, dept, nt, note_status=st)
                self.txt_note.delete("1.0", "end")
                ModernMessagebox("Saved", "Faculty note successfully added.", "success")
                load_history()
                
                self.note_stats = CentralAuth().get_student_note_stats(department=None)
                if hasattr(self, "filter_list"):
                    self.filter_list()
            except Exception as e:
                import traceback
                traceback.print_exc()
                ModernMessagebox("Error", f"Failed to save note: {str(e)}", "error")

        # 6. NOTES HISTORY
        make_section_title(scroll, "NOTES HISTORY")
        history_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], border_width=1, border_color=COLORS["border"], corner_radius=8)
        history_card.pack(fill="x", pady=5)
        
        history_frame = ctk.CTkScrollableFrame(history_card, height=180, fg_color="transparent")
        history_frame.pack(fill="x", padx=15, pady=15)
        load_history()
        
        # 7. ADD NEW NOTE
        make_section_title(scroll, "ADD NEW NOTE")
        new_note_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], border_width=1, border_color=COLORS["border"], corner_radius=8)
        new_note_card.pack(fill="x", pady=5)
        
        controls_f = ctk.CTkFrame(new_note_card, fg_color="transparent")
        controls_f.pack(fill="x", padx=15, pady=(15, 10))
        ctk.CTkLabel(controls_f, text="Note Status:", font=FONTS["caption"], text_color="#a1a1aa").pack(side="left", padx=(0, 10))
        self.note_status_var = ctk.StringVar(value="ACTIVE")
        self.note_status_combo = ctk.CTkComboBox(controls_f, values=["ACTIVE", "FOLLOW_UP", "CRITICAL", "CLOSED"], variable=self.note_status_var, width=130, fg_color="#1e1e24", border_color="#3f3f46", button_color="#3f3f46")
        self.note_status_combo.pack(side="left")
        
        input_wrapper = ctk.CTkFrame(new_note_card, fg_color="#1e1e24", corner_radius=12, border_width=1, border_color="#3f3f46")
        input_wrapper.pack(fill="x", padx=15, pady=(0, 15))
        
        self.txt_note = ctk.CTkTextbox(input_wrapper, height=50, fg_color="transparent", text_color="white", border_width=0, font=FONTS["body"])
        self.txt_note.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        
        send_btn = ctk.CTkButton(input_wrapper, text="➤", width=40, height=40, corner_radius=8, font=FONTS["h2"], fg_color="#38bdf8", text_color="black", hover_color="#0284c7", command=save_note)
        send_btn.pack(side="right", padx=10, pady=10)

        # 8. CLOSE DIAGNOSIS
        close_btn = ctk.CTkButton(scroll, text="CLOSE DIAGNOSIS", fg_color="#3f3f46", hover_color="#52525b", text_color="white", corner_radius=8, font=FONTS["body"], command=top.destroy, height=40)
        close_btn.pack(fill="x", pady=(20, 20))

    def _open_edit_contact_dialog(self, data):
        diag = ctk.CTkToplevel(self)
        diag.geometry("400x300")
        diag.title("Update Parent Contact")
        diag.attributes("-topmost", True)
        diag.configure(fg_color="#111")
        
        ctk.CTkLabel(diag, text="Update Contact Info", font=FONTS["h2"]).pack(pady=20)
        
        ctk.CTkLabel(diag, text="Parent Email:").pack()
        email_ent = ctk.CTkEntry(diag, width=250)
        email_ent.pack(pady=5)
        
        ctk.CTkLabel(diag, text="Parent Phone:").pack()
        phone_ent = ctk.CTkEntry(diag, width=250)
        phone_ent.pack(pady=5)
        
        def save():
            new_email = email_ent.get().strip()
            new_phone = phone_ent.get().strip()
            import tkinter.messagebox as mb
            mb.showinfo("Success", "Contact info updated in local view. (Requires ERP write access to persist)")
            data['parent_email'] = new_email
            data['parent_phone'] = new_phone
            diag.destroy()
            
        ctk.CTkButton(diag, text="Save", fg_color=COLORS["success"], command=save).pack(pady=20)

    def _open_notify_parent_dialog(self, data, report):
        diag = ctk.CTkToplevel(self)
        diag.geometry("500x600")
        diag.title("AcaDesk - Parent Notification (Email)")
        diag.attributes("-topmost", True)
        diag.configure(fg_color="#111")
        
        ctk.CTkLabel(diag, text="DISPATCH ALERT", font=FONTS["h2"], text_color=COLORS["accent"]).pack(pady=(20, 5))
        
        p_email = data.get('parent_email', 'Not Provided')
        p_phone = data.get('parent_phone', 'Not Provided')
        
        info_frame = ctk.CTkFrame(diag, fg_color=COLORS["card"])
        info_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(info_frame, text=f"Student: {data['name']}", font=FONTS["h3"]).pack(anchor="w", padx=15, pady=(15, 2))
        ctk.CTkLabel(info_frame, text=f"Parent Email: {p_email}", text_color="gray").pack(anchor="w", padx=15, pady=2)
        ctk.CTkLabel(info_frame, text=f"Parent Phone: {p_phone}", text_color="gray").pack(anchor="w", padx=15, pady=(2, 15))
        
        ctk.CTkLabel(diag, text="Message Body:", anchor="w").pack(fill="x", padx=20, pady=(10, 0))
        msg_box = ctk.CTkTextbox(diag, height=150, fg_color=COLORS["input_bg"])
        msg_box.pack(fill="x", padx=20, pady=5)
        
        default_msg = (
            f"Dear Parent,\n\n"
            f"This is an automated alert from AcaDesk regarding your ward, {data['name']}. "
            f"Our AI system has flagged a {report['level']} risk in their academic progress.\n\n"
            f"Attendance: {data.get('avg_attendance', 'N/A')}%\n"
            f"Please contact the HOD/Faculty immediately."
        )
        msg_box.insert("0.0", default_msg)
        
        cred_frame = ctk.CTkFrame(diag, fg_color="transparent")
        cred_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(cred_frame, text="Gmail App Password:", font=FONTS["body"]).pack(side="left", padx=5)
        pass_entry = ctk.CTkEntry(cred_frame, show="*", width=200, placeholder_text="16-letter App Password")
        pass_entry.pack(side="left", padx=5)
        
        def send_email_action():
            import tkinter.messagebox as mb
            from logic.email_sender import send_email_notification
            
            pwd = pass_entry.get().strip()
            if not pwd:
                mb.showerror("Error", "Please enter your Gmail App Password to send real emails.")
                return
                
            if p_email == 'Not Provided':
                mb.showerror("Error", "No parent email found on record!")
                return
                
            body = msg_box.get("0.0", "end").strip()
            success, msg = send_email_notification(p_email, f"AcaDesk Alert for {data['name']}", body, pwd)
            
            if success:
                mb.showinfo("Success", msg)
                diag.destroy()
            else:
                mb.showerror("Failed", msg)
                
        btn_send = ctk.CTkButton(diag, text="Send Email", fg_color=COLORS["success"], font=FONTS["h3"], height=40, command=send_email_action)
        btn_send.pack(pady=20)
        
        close_btn = ctk.CTkButton(scroll, text="CLOSE DIAGNOSIS", command=top.destroy)
        close_btn.pack(pady=10)

    def export_report(self):
        try:
            students = self.db.get_students(self.current_branch, self.current_year)
            fname = f"Risk_Report_{int(time.time())}.csv"
            pd.DataFrame(students).to_csv(fname, index=False)
            ModernMessagebox("Success", f"Saved: {fname}", "success")
        except Exception as e:
            ModernMessagebox("Error", str(e), "error")

    def add_line(self, p, l, v, color="white"):
        line_f = ctk.CTkFrame(p, fg_color="transparent")
        line_f.pack(fill="x", padx=10)
        
        lbl = ctk.CTkLabel(line_f, text=l, text_color="gray", width=120, anchor="w")
        lbl.pack(side="left")
        
        val = ctk.CTkLabel(line_f, text=v, text_color=color, font=FONTS["caption"])
        val.pack(side="left")
        
    def _profile_badge(self, parent, label_text, value_text):
        badge_frame = ctk.CTkFrame(parent, fg_color="transparent")
        badge_frame.pack(side="left", fill="x", expand=True, padx=10, pady=15)
        
        lbl = ctk.CTkLabel(badge_frame, text=label_text, text_color="gray", font=FONTS["caption"])
        lbl.pack(anchor="center")
        
        val = ctk.CTkLabel(badge_frame, text=value_text, text_color="white", font=FONTS["h3"])
        val.pack(anchor="center")

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
            # Always default to the student-level dashboard (Analytics) upon login
            self.show_view("Analytics")

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