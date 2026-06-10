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
    from logic.predictor import RiskPredictor
    from logic.risk_engine import AdvancedRiskPredictor
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
        self.configure(fg_color="#1a1a1a")
        
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
            font=("Arial", 16, "bold"), 
            text_color=color
        )
        title_lbl.pack(pady=(25, 10))
        
        # Message Label
        msg_lbl = ctk.CTkLabel(
            self, 
            text=message, 
            font=("Arial", 12), 
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
            font=("Arial", 12, "bold"), 
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
        
        # App Logo
        logo = ctk.CTkLabel(
            self, 
            text="AcaDesk", 
            font=FONTS["h1"], 
            text_color="#00E5FF"
        )
        logo.pack(pady=(40, 10))
        
        # User display
        self.lbl_user = ctk.CTkLabel(
            self, 
            text="User: ...", 
            text_color=COLORS["text_gray"]
        )
        self.lbl_user.pack(pady=(0, 40))
        
        # Sidebar Menu Buttons
        self.btn_dash = self.add_btn("📊  Dashboard", lambda: self.dash.show_view("Analytics"))
        self.btn_hod = self.add_btn("👔  HOD Manager", lambda: self.dash.show_view("HOD"))
        self.btn_fac = self.add_btn("👥  Faculty Manager", lambda: self.dash.show_view("Faculty"))
        self.btn_sim = self.add_btn("🧠  AI Simulator", self.dash.open_ai_simulator)
        self.btn_pass = self.add_btn("🔒  Change Password", self.dash.open_change_pass) 
        
        # Logout Button
        logout_btn = ctk.CTkButton(
            self, 
            text="LOGOUT", 
            fg_color="#330000", 
            text_color=COLORS["danger"], 
            command=lambda: self.controller.show_frame("WelcomeScreen")
        )
        logout_btn.pack(side="bottom", fill="x", padx=20, pady=40)

    def add_btn(self, txt, cmd):
        btn = ctk.CTkButton(
            self, 
            text=txt, 
            fg_color="transparent", 
            text_color=COLORS["accent"],
            anchor="w", 
            height=DIMS["btn_height"], 
            hover_color="#222", 
            command=cmd
        )
        btn.pack(fill="x", padx=10)
        return btn

    def refresh(self):
        username = self.controller.shared_data.get('username', 'User')
        self.lbl_user.configure(text=f"User: {username}")
        
        user_type = self.controller.shared_data.get("user_type")
        
        self.btn_hod.pack_forget()
        self.btn_fac.pack_forget()
        self.btn_sim.pack_forget()
        
        if user_type == "Admin":
            self.btn_hod.pack(fill="x", padx=10)
            self.btn_fac.pack(fill="x", padx=10)
            self.btn_sim.pack(fill="x", padx=10, pady=2)
        elif user_type == "HOD":
            self.btn_fac.pack(fill="x", padx=10, pady=2)

# ====================================================
#  FACULTY MANAGER
# ====================================================

class FacultyManagerPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.db = None
        self.branch_map = {}
        
        title = ctk.CTkLabel(
            self, 
            text="FACULTY ACCESS CONTROL", 
            text_color="#00E5FF",
            font=FONTS["h1"]
        )
        title.pack(anchor="w", padx=40, pady=(40, 20))
        
        # Entry Form
        form_card = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=10)
        form_card.pack(fill="x", padx=40, pady=10)
        
        row_frame = ctk.CTkFrame(form_card, fg_color="transparent")
        row_frame.pack(fill="x", padx=20, pady=20)
        
        self.u_entry = ctk.CTkEntry(row_frame, placeholder_text="Username", width=180)
        self.u_entry.pack(side="left", padx=5)
        
        self.p_entry = ctk.CTkEntry(row_frame, placeholder_text="Password", width=180, show="*")
        self.p_entry.pack(side="left", padx=5)
        
        self.br_combo = ctk.CTkComboBox(row_frame, width=140)
        self.br_combo.set("Select Branch")
        self.br_combo.pack(side="left", padx=5)
        
        add_btn = ctk.CTkButton(
            row_frame, 
            text="+ ADD", 
            fg_color=COLORS["accent"], 
            text_color="black", 
            width=100, 
            command=self.add_faculty
        )
        add_btn.pack(side="left", padx=5)
        
        # Faculty List Scroll Area
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20)

    def refresh(self):
        erp_conf = self.controller.shared_data.get("erp_config")
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
                self.br_combo.configure(state="normal")
            
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        try:
            college = self.controller.shared_data.get("college_name")
            faculties = CentralAuth().get_faculty_list(college)
            
            user_type = self.controller.shared_data.get("user_type")
            if user_type == "HOD":
                assigned_dept = self.controller.shared_data.get("assigned_department")
                faculties = [f for f in faculties if str(f['assigned_branch']).lower() == str(assigned_dept).lower()]
            
            for f in faculties:
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
                rev_btn.pack(side="right", padx=15)
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



# ====================================================


class SelectionCard(ctk.CTkFrame):
    def __init__(self, parent, primary_text, secondary_text, command=None, *args, **kwargs):
        # Base minimalist card: compact, subtle border
        super().__init__(parent, fg_color="#181818", corner_radius=8, border_width=1, border_color="#2A2A2A", *args, **kwargs)
        self.command = command
        
        # Content Container (Compact Padding)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=12)
        
        # Modern, compact typography
        self.lbl_primary = ctk.CTkLabel(self.content_frame, text=primary_text, font=("Arial", 14, "bold"), text_color=COLORS["accent"], anchor="w")
        self.lbl_primary.pack(fill="x", pady=(0, 2))
        
        # Apply hover events
        widgets = [self, self.content_frame, self.lbl_primary]
        
        if secondary_text:
            self.lbl_secondary = ctk.CTkLabel(self.content_frame, text=secondary_text, font=("Arial", 11), text_color="#666666", anchor="w")
            self.lbl_secondary.pack(fill="x")
            widgets.append(self.lbl_secondary)
            
        for w in widgets:
            w.bind("<Enter>", self.on_enter)
            w.bind("<Leave>", self.on_leave)
            w.bind("<Button-1>", self.on_click)
            
    def on_enter(self, event):
        # Subtle modern hover state
        self.configure(fg_color="#222222", border_color=COLORS["accent"])
        self.lbl_primary.configure(text_color=COLORS["accent"])
        
    def on_leave(self, event):
        # Revert to standard state
        self.configure(fg_color="#181818", border_color="#2A2A2A")
        self.lbl_primary.configure(text_color=COLORS["accent"])
        
    def on_click(self, event):
        if self.command:
            self.command()

class AnalyticsPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.db = None
        self.ai = RiskPredictor()          # batch dashboard charts
        self.adv_ai = None                  # advanced single-student engine (set in refresh)
        self.translator = None
        self.current_branch = None
        self.current_year = None
        self.current_filter = "All"

        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        
        self.btn_back = ctk.CTkButton(
            self.header, 
            text="← Back", 
            width=60, 
            height=30, 
            fg_color="#333", 
            command=self.go_back
        )
        
        self.lbl_title = ctk.CTkLabel(
            self.header, 
            text="Dashboard", 
            font=FONTS["h2"], 
            text_color="white"
        )
        self.lbl_title.pack(side="left")
        
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True, padx=20, pady=10)

    def refresh(self):
        self.current_branch = None
        self.current_year = None
        
        erp_conf = self.controller.shared_data.get("erp_config")
        if erp_conf:
            self.db = DBHandler(erp_conf)
            self.translator = BranchTranslator(self.db)
            try:
                self.adv_ai = AdvancedRiskPredictor(self.db)
            except Exception:
                self.adv_ai = None
            
        if not self.db or not self.db.connected:
            self.show_error("Database connection missing. Access ERP setup.")
            return
            
        user_type = self.controller.shared_data.get("user_type")
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
        self._clear()
        self.lbl_title.configure(text="Select Department",text_color="#00E5FF")
        self.btn_back.pack_forget()
        
        user_type = self.controller.shared_data.get("user_type")
        if user_type == "Admin":
            self._render_admin_charts()
            
        branch_ids = self.db.get_all_branches()
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)
        scroll.grid_columnconfigure(2, weight=1)
        
        for i, bid in enumerate(branch_ids):
            name = self.translator.get_name(bid)
            card = SelectionCard(
                scroll, 
                primary_text=name, 
                secondary_text="Department",
                command=lambda b=bid: self.select_branch(b)
            )
            card.grid(row=i//3, column=i%3, padx=15, pady=15, sticky="nsew")

    def _render_admin_charts(self):
        all_students = self.db.get_all_students()
        if not all_students:
            return
            
        try:
            global_stats, branch_stats_raw = self.ai.batch_analyze(all_students)
            branch_stats = {self.translator.get_name(bid): s for bid, s in branch_stats_raw.items()}
            
            row = ctk.CTkFrame(self.content_area, fg_color="transparent", height=250)
            row.pack(fill="x", pady=(10, 20))
            
            # Pie Chart Section
            l_frame = ctk.CTkFrame(row, fg_color=COLORS["card"])
            l_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
            
            fig1 = Figure(figsize=(4, 3), dpi=80)
            fig1.patch.set_facecolor(COLORS["card"])
            ax1 = fig1.add_subplot(111)
            
            labels = ["High", "Med", "Safe"]
            counts = [global_stats["High"], global_stats["Medium"], global_stats["Low"]]
            colors = [COLORS["danger"], COLORS["warning"], COLORS["success"]]
            
            ax1.pie(counts, labels=labels, colors=colors, autopct='%1.1f%%', textprops={'color':"white"})
            canvas1 = FigureCanvasTkAgg(fig1, master=l_frame)
            canvas1.get_tk_widget().pack(fill="both", expand=True)

            # Bar Chart Section
            r_frame = ctk.CTkFrame(row, fg_color=COLORS["card"])
            r_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))
            
            fig2 = Figure(figsize=(5, 3), dpi=80)
            fig2.patch.set_facecolor(COLORS["card"])
            ax2 = fig2.add_subplot(111)
            ax2.set_facecolor(COLORS["card"])
            
            dept_names = list(branch_stats.keys())
            if dept_names:
                highs = [branch_stats[d].get("High", 0) for d in dept_names]
                meds = [branch_stats[d].get("Medium", 0) for d in dept_names]
                
                ax2.bar(dept_names, highs, color=COLORS["danger"])
                ax2.bar(dept_names, meds, bottom=highs, color=COLORS["warning"])
                ax2.tick_params(axis='x', rotation=20, colors='white', labelsize=8)
                ax2.tick_params(axis='y', colors='white')
                
            canvas2 = FigureCanvasTkAgg(fig2, master=r_frame)
            canvas2.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e:
            print(f"Chart render fail: {e}")

    def select_branch(self, bid):
        self.current_branch = bid
        self.show_year_selection()

    def select_year(self, yr):
        self.current_year = yr
        self.show_student_list()

    def show_year_selection(self):
        self._clear()
        name = self.translator.get_name(self.current_branch)
        self.lbl_title.configure(text=f"{name} - Select Year")
        
        user_type = self.controller.shared_data.get("user_type")
        if user_type == "Admin":
            self.btn_back.pack(side="left", padx=(0, 10))
            
        grid = ctk.CTkFrame(self.content_area, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        
        for i, yr in enumerate(YEARS):
            card = SelectionCard(
                grid, 
                primary_text=yr, 
                secondary_text="",
                command=lambda y=yr: self.select_year(y)
            )
            card.grid(row=i//2, column=i%2, padx=20, pady=20, sticky="nsew")

    def show_student_list(self):
        self._clear()
        name = self.translator.get_name(self.current_branch)
        self.lbl_title.configure(text=f"{name} > {self.current_year}")
        self.btn_back.pack(side="left", padx=(0, 10))
        
        toolbar = ctk.CTkFrame(self.content_area, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 5))
        
        exp_btn = ctk.CTkButton(
            toolbar, 
            text="📥 Export CSV", 
            width=120, 
            command=self.export_report
        )
        exp_btn.pack(side="right", padx=10)
        
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.filter_list)
        
        search_ent = ctk.CTkEntry(
            toolbar, 
            textvariable=self.search_var, 
            placeholder_text="Search Name/ID...", 
            width=300
        )
        search_ent.pack(side="right")
        
        # Risk Filter Row
        f_row = ctk.CTkFrame(self.content_area, fg_color="transparent")
        f_row.pack(fill="x", pady=(0, 10))
        
        self.btn_all  = self._create_filter_btn(f_row, "ALL",    "All",    "#333333")
        self.btn_high = self._create_filter_btn(f_row, "HIGH",   "High",   COLORS["danger"])
        self.btn_med  = self._create_filter_btn(f_row, "MEDIUM",  "Medium", COLORS["warning"])
        self.btn_low  = self._create_filter_btn(f_row, "LOW",    "Low",    COLORS["success"])
        
        self.current_filter = "All"
        self._update_filter_visuals()
        
        self.list_frame = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True)
        self.filter_list()

    def _create_filter_btn(self, p, t, v, c):
        btn = ctk.CTkButton(
            p, text=t, height=30, width=100, 
            fg_color="transparent", border_width=2, border_color=c, 
            text_color="white", hover_color=c, 
            command=lambda val=v: self.apply_filter(val)
        )
        btn.pack(side="left", padx=5)
        return btn

    def apply_filter(self, val):
        self.current_filter = val
        self._update_filter_visuals()
        self.filter_list()

    def _update_filter_visuals(self):
        self.btn_all.configure(fg_color="transparent")
        self.btn_high.configure(fg_color="transparent")
        self.btn_med.configure(fg_color="transparent")
        self.btn_low.configure(fg_color="transparent")

        if self.current_filter == "All":
            self.btn_all.configure(fg_color="#333333")
        elif self.current_filter == "High":
            self.btn_high.configure(fg_color=COLORS["danger"])
        elif self.current_filter == "Medium":
            self.btn_med.configure(fg_color=COLORS["warning"])
        else:
            self.btn_low.configure(fg_color=COLORS["success"])

    def filter_list(self, *args):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        # Use full-column fetch for the advanced engine; fallback to basic fetch
        try:
            students_full = self.db.get_students_full(self.current_branch, self.current_year)
        except Exception:
            students_full = []

        # Build a lookup from display_reg_no → full row
        full_lookup: dict = {}
        for row in students_full:
            key = str(row.get('display_reg_no', '') or row.get(
                self.db.map.get('registration_no', ''), ''))
            full_lookup[key] = row

        students = self.db.get_students(self.current_branch, self.current_year)
        query = self.search_var.get().lower()

        for s in students:
            is_match = query in str(s.get('display_reg_no', '')).lower() or query in str(s.get('display_name', '')).lower()
            if not is_match:
                continue

            # Merge full row data if available
            reg_key = str(s.get('display_reg_no', ''))
            full_row = {**s, **full_lookup.get(reg_key, {})}

            # Run advanced analysis — pass year so first-year model activates
            if self.adv_ai:
                report = self.adv_ai.analyze(full_row, year=self.current_year)
            else:
                report = self.ai.analyze_student(
                    s['avg_attendance'], s['avg_marks'], s['backlogs'], 7)

            if self.current_filter != "All" and report['level'] != self.current_filter:
                continue

            row_frame = ctk.CTkFrame(self.list_frame, fg_color=COLORS["card"], height=55)
            row_frame.pack(fill="x", pady=5)

            diag_btn = ctk.CTkButton(
                row_frame,
                text="DIAGNOSE",
                width=120,
                fg_color=COLORS["accent"],
                text_color="black",
                command=lambda d=full_row, r=report: self.open_deep_analysis(d, r)
            )
            diag_btn.pack(side="right", padx=10)

            # Risk level badge — three-tier: Low / Medium / High
            lvl = report.get('level', 'Low')
            if lvl == "High":
                lvl_color = COLORS["danger"]
            elif lvl == "Medium":
                lvl_color = COLORS["warning"]
            else:
                lvl_color = COLORS["success"]

            score_val = report.get('score', 0)
            badge = report.get('status_badge', lvl.upper())
            score_lbl = ctk.CTkLabel(
                row_frame,
                text=f"{score_val:.0f}  {lvl.upper()} RISK",
                text_color=lvl_color,
                font=("Arial", 11, "bold"),
                width=155
            )
            score_lbl.pack(side="right", padx=5)

            badge_lbl = ctk.CTkLabel(
                row_frame,
                text=badge,
                fg_color=lvl_color,
                text_color="white",
                font=("Arial", 9, "bold"),
                corner_radius=4,
                width=70
            )
            badge_lbl.pack(side="right", padx=4)

            name_lbl = ctk.CTkLabel(
                row_frame,
                text=f"{s.get('display_reg_no', 'N/A')} - {s.get('display_name', 'Unknown')}",
                font=("Roboto", 12, "bold")
            )
            name_lbl.pack(side="left", padx=20)

    def open_deep_analysis(self, data, report):
        top = ctk.CTkToplevel(self)
        top.geometry("1100x900")
        top.title("AcaDesk - Student Diagnosis")
        top.attributes("-topmost", True)
        top.configure(fg_color="#000")

        scroll = ctk.CTkScrollableFrame(top, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # --- HEADER CARD ---
        lvl = report.get('level', 'Low')
        if lvl == "High":
            r_color = COLORS["danger"]
        elif lvl == "Medium":
            r_color = COLORS["warning"]
        else:
            r_color = COLORS["success"]

        header_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        header_card.pack(fill="x", pady=(0, 10))

        # Left: student name + status badge
        left_h = ctk.CTkFrame(header_card, fg_color="transparent")
        left_h.pack(side="left", padx=20, pady=12)
        ctk.CTkLabel(left_h, text=f"\U0001f393  {data.get('display_name', 'Unknown')}",
                     font=("Arial", 20, "bold"), text_color="white").pack(anchor="w")
        badge_txt = report.get('status_badge', lvl.upper())
        ctk.CTkLabel(left_h, text=badge_txt, fg_color=r_color, text_color="white",
                     font=("Arial", 9, "bold"), corner_radius=4, width=80).pack(anchor="w", pady=(3,0))

        # Right: score + model
        right_h = ctk.CTkFrame(header_card, fg_color="transparent")
        right_h.pack(side="right", padx=20, pady=12)
        score_val = report.get('score', 0)
        ctk.CTkLabel(right_h,
                     text=f"RISK SCORE: {score_val:.0f} / 100   |   {lvl.upper()} RISK",
                     font=("Arial", 17, "bold"), text_color=r_color).pack(anchor="e")
        model_txt = report.get('model_used', '')
        year_txt  = str(self.current_year) if self.current_year else ''
        ctk.CTkLabel(right_h, text=f"{model_txt}  ·  {year_txt}  ·  Confidence: {report.get('confidence','?')}",
                     font=("Arial", 10), text_color="#888").pack(anchor="e", pady=(3,0))

        # --- PROFILE BAR ---
        profile_bar = ctk.CTkFrame(scroll, fg_color="#1a1a1a", corner_radius=8,
                                   border_width=1, border_color="#333")
        profile_bar.pack(fill="x", pady=(0, 15), padx=5)
        self._profile_badge(profile_bar, "Reg No:", str(data.get('display_reg_no', 'N/A')))
        self._profile_badge(profile_bar, "Avg Marks:", f"{data.get('avg_marks', 'N/A')}%")
        self._profile_badge(profile_bar, "Attendance:", f"{data.get('avg_attendance', 'N/A')}%")
        self._profile_badge(profile_bar, "Backlogs:", str(data.get('backlogs', 0)))
        branch_name = self.translator.get_name(self.current_branch)
        self._profile_badge(profile_bar, "Department:", branch_name)
        self._profile_badge(profile_bar, "Year:", str(self.current_year or 'N/A'))

        # --- FACTOR BREAKDOWN + CONTRIBUTION CHART (side by side) ---
        grid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        grid_frame.pack(fill="x", pady=5)

        # Left: Factor scores
        l_info = ctk.CTkFrame(grid_frame, fg_color=COLORS["card"], corner_radius=8)
        l_info.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(l_info, text="RISK DOMAIN SCORES",
                     font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=12, pady=(10, 5))

        factors = report.get('domain_scores', {})
        if factors:
            for fname, fval in factors.items():
                label = fname.replace('_', ' ').title()
                if fval == "N/A" or fval is None:
                    self.add_line(l_info, f"  {label}:", "N/A", color="#555")
                    continue
                try:
                    fnum = float(fval)
                except (TypeError, ValueError):
                    self.add_line(l_info, f"  {label}:", str(fval), color="#555")
                    continue
                # domain_scores are 0-100 quality (100=perfect); invert for risk colour
                risk_pct = 100.0 - fnum
                fc = COLORS["danger"] if risk_pct >= 65 else (COLORS["warning"] if risk_pct >= 40 else COLORS["success"])
                self.add_line(l_info, f"  {label}:", f"{fnum:.1f} / 100", color=fc)

        # Right: Contribution bar chart
        r_info = ctk.CTkFrame(grid_frame, fg_color=COLORS["card"], corner_radius=8)
        r_info.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ctk.CTkLabel(r_info, text="FACTOR CONTRIBUTIONS TO RISK SCORE",
                     font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=12, pady=(10, 5))

        try:
            c_data = report.get('contributions', {})
            if not c_data:
                # Fallback: derive from domain_scores
                ds = report.get('domain_scores', {})
                c_data = {k.replace('_', ' ').title(): round(100.0 - float(v), 1)
                          for k, v in ds.items() if isinstance(v, (int, float))}
            c_keys = list(c_data.keys())[:8]
            c_vals = [float(c_data[k]) if isinstance(c_data[k], (int, float)) else 0.0 for k in c_keys]
            bar_colors = [
                COLORS["danger"] if v >= 70 else (COLORS["warning"] if v >= 40 else COLORS["success"])
                for v in c_vals
            ]
            fig_r = Figure(figsize=(4.5, max(2.0, len(c_keys) * 0.55)), dpi=80)
            fig_r.patch.set_facecolor(COLORS["card"])
            ax_r = fig_r.add_subplot(111)
            ax_r.set_facecolor(COLORS["card"])
            ax_r.barh(c_keys, c_vals, color=bar_colors, height=0.5)
            ax_r.set_xlim(0, 100)
            ax_r.tick_params(colors='white', labelsize=8)
            for spine in ax_r.spines.values():
                spine.set_color('#333')
            fig_r.tight_layout(pad=0.5)
            can_r = FigureCanvasTkAgg(fig_r, master=r_info)
            can_r.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)
        except Exception:
            pass

        # ═══════════════════════════════════════════════════════

        # --- AI INSIGHT PANEL ---
        # All values come from the real risk engine — no simulator.
        # ═══════════════════════════════════════════════════════
        ai_card = ctk.CTkFrame(scroll, fg_color="#0c1220", corner_radius=10,
                               border_width=1, border_color="#1e3a5f")
        ai_card.pack(fill="x", pady=8, padx=2)

        # ── Section header ──────────────────────────────────────
        hdr = ctk.CTkFrame(ai_card, fg_color="#0f1e35", corner_radius=0)
        hdr.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(hdr, text="🧠  AI RISK INSIGHT  —  Explainable Risk Analysis",
                     font=("Arial", 13, "bold"), text_color="#60A5FA").pack(side="left", padx=15, pady=10)
        model_used  = report.get('model_used', 'Senior-Year Model')
        confidence  = report.get('confidence', '?')
        year_label  = f"Year {report.get('year', '?')}"
        ctk.CTkLabel(hdr,
                     text=f"{model_used}  ·  {year_label}  ·  Confidence: {confidence}",
                     font=("Arial", 9), text_color="#4B6A8A").pack(side="right", padx=15)

        # ── Model selection explanation ─────────────────────────
        is_first = report.get('is_first_year', False)
        if is_first:
            model_reason = (
                "📌  First-Year Model selected — uses Academic Background (prior education) as a key "
                "predictor since no historical GPA or backlog data exists yet. Attendance, Internal "
                "Marks, and Mid Exam performance are the primary in-semester indicators."
            )
        else:
            model_reason = (
                "📌  Senior-Year Model selected — CGPA and Backlogs carry 25% each as the strongest "
                "predictors of progression risk. Attendance (20%) and internal performance (20%) are "
                "also weighted. All factors are normalized to active data only."
            )
        ctk.CTkLabel(ai_card, text=model_reason, wraplength=1000, justify="left",
                     font=("Arial", 10), text_color="#7CA9CC").pack(anchor="w", padx=15, pady=(6, 2))

        # ── Divider ─────────────────────────────────────────────
        ctk.CTkFrame(ai_card, height=1, fg_color="#1e3a5f").pack(fill="x", padx=15, pady=6)

        # ── Factor breakdown table header ───────────────────────
        ctk.CTkLabel(ai_card,
                     text="FACTOR ANALYSIS  —  What the AI used and why",
                     font=("Arial", 11, "bold"), text_color="#93C5FD").pack(anchor="w", padx=15, pady=(2, 4))

        # Column headers
        col_hdr = ctk.CTkFrame(ai_card, fg_color="#101c2e", corner_radius=4)
        col_hdr.pack(fill="x", padx=15, pady=(0, 3))
        for htext, w in [("Factor", 200), ("Your Value", 110), ("Risk Level", 100),
                          ("Contribution to Score", 200), ("Status", 100)]:
            ctk.CTkLabel(col_hdr, text=htext, font=("Arial", 9, "bold"),
                         text_color="#4B7CB3", width=w, anchor="w").pack(side="left", padx=6, pady=5)

        # ── Per-factor rows ─────────────────────────────────────
        FACTOR_INFO = {
            # domain_name → (display, weight_1st, weight_senior, value_key, unit, good_threshold)
            "attendance":          ("Attendance",         "25%", "20%", "attendance_pct",    "%",   "≥80% good"),
            "academic_background": ("Academic Background","20%", "—",   "tenth_percentage",  "%",   "≥60% good"),
            "internal_marks":      ("Internal Marks",     "15%", "10%", "internal_marks",    "%",   "≥75% good"),
            "mid_exam":            ("Mid Exam",           "15%", "10%", "mid_exam_score",    "%",   "≥75% good"),
            "assignments":         ("Assignments",        "10%", "5%",  "assignment_marks",  "%",   "≥75% good"),
            "lab":                 ("Lab Performance",    "5%",  "5%",  "lab_marks",         "%",   "≥75% good"),
            "cons_absences":       ("Consecutive Absences","5%","3%",   "consecutive_absences","days","0 is ideal"),
            "leave_frequency":     ("Leave Frequency",    "5%",  "3%",  "leave_frequency",   "days","≤2 ideal"),
            "cgpa_marks":          ("CGPA / GPA",         "—",   "25%", "cgpa",              "pts", "≥7.5 good"),
            "backlogs":            ("Active Backlogs",    "—",   "25%", "backlog_count",      "nos", "0 ideal"),
            "trend":               ("Performance Trend",  "—",   "5%",  None,                "",    "improving"),
        }

        raw_features = report.get('features', {})   # labeled dict
        domain_shap  = {}                            # compute from contributions
        # Map labeled contribution keys back to domain names
        LABEL_TO_DOMAIN = {
            "Attendance": "attendance", "Academic Background": "academic_background",
            "Internal Marks": "internal_marks", "Mid Exam": "mid_exam",
            "Assignments": "assignments", "Lab Performance": "lab",
            "Consecutive Absences": "cons_absences", "Leave Frequency": "leave_frequency",
            "CGPA / GPA": "cgpa_marks", "Backlogs": "backlogs",
            "Performance Trend": "trend",
        }
        contribs = report.get('contributions', {})
        for label_key, val in contribs.items():
            dom = LABEL_TO_DOMAIN.get(label_key, label_key.lower().replace(' ', '_'))
            domain_shap[dom] = val

        domain_scores_raw = report.get('domain_scores', {})
        total_score = report.get('score', 0)

        # Build rows for domains that are active (have a contribution)
        active_domains = list(domain_shap.keys())
        # Also include N/A domains so user sees what was MISSING
        all_domains = active_domains + [d for d in FACTOR_INFO if d not in active_domains]

        row_bg_toggle = ["#0c1a2e", "#0d1f35"]
        for i, domain in enumerate(all_domains):
            info = FACTOR_INFO.get(domain)
            if not info:
                continue
            disp_name, w1, w_sr, val_key, unit, good_str = info
            weight_used = w1 if is_first else w_sr
            if weight_used == "—":
                # This factor doesn't exist in the selected model — skip completely
                continue

            contrib = domain_shap.get(domain)
            quality  = domain_scores_raw.get(domain)

            # Determine displayed value
            displayed_val = "N/A"
            if val_key:
                # Try labeled feature dict first
                label_lookup = val_key.replace("_", " ").title()
                for k, v in raw_features.items():
                    if k.lower().replace(" ","_") == val_key:
                        displayed_val = f"{v:.1f} {unit}"
                        break
                else:
                    # Direct from data dict
                    for src_key in (val_key, val_key.replace("_pct",""),
                                    val_key.replace("_count","s")):
                        v = data.get(src_key)
                        if v is None:
                            v = data.get(f"avg_{src_key}")
                        if v is not None:
                            try:
                                displayed_val = f"{float(v):.1f} {unit}"
                            except Exception:
                                displayed_val = str(v)
                            break

            # Risk level for this factor
            if quality == "N/A" or quality is None:
                fac_risk = "N/A"
                fac_color = "#555"
            else:
                try:
                    q = float(quality)
                    if q >= 75:
                        fac_risk, fac_color = "Good", "#4ADE80"
                    elif q >= 55:
                        fac_risk, fac_color = "Acceptable", "#FCD34D"
                    elif q >= 35:
                        fac_risk, fac_color = "Concern", COLORS["warning"]
                    else:
                        fac_risk, fac_color = "High Risk", COLORS["danger"]
                except Exception:
                    fac_risk, fac_color = "N/A", "#555"

            # Contribution bar
            if contrib is not None and total_score > 0:
                bar_pct = min(100, round(contrib / total_score * 100))
                bar_txt = f"{contrib:.1f} pts  ({bar_pct}% of score)"
                bar_col = COLORS["danger"] if bar_pct >= 30 else (COLORS["warning"] if bar_pct >= 15 else "#2563EB")
            else:
                bar_txt = "Not used (data missing)"
                bar_col = "#333"
                bar_pct = 0

            # Status
            if contrib is None:
                status_txt, status_col = "Excluded", "#555"
            elif bar_pct >= 35:
                status_txt, status_col = "⚠ Major Driver", COLORS["danger"]
            elif bar_pct >= 15:
                status_txt, status_col = "▲ Contributing", COLORS["warning"]
            else:
                status_txt, status_col = "✓ Low Impact", "#4ADE80"

            row_bg = row_bg_toggle[i % 2]
            row_f = ctk.CTkFrame(ai_card, fg_color=row_bg, corner_radius=3)
            row_f.pack(fill="x", padx=15, pady=1)

            # Col 1: Factor name + weight
            col1 = ctk.CTkFrame(row_f, fg_color="transparent", width=200)
            col1.pack(side="left", padx=6, pady=5)
            ctk.CTkLabel(col1, text=disp_name,
                         font=("Arial", 10, "bold"), text_color="white",
                         width=200, anchor="w").pack(anchor="w")
            ctk.CTkLabel(col1, text=f"Weight: {weight_used}",
                         font=("Arial", 8), text_color="#4B6A8A",
                         width=200, anchor="w").pack(anchor="w")

            # Col 2: Value
            ctk.CTkLabel(row_f, text=displayed_val,
                         font=("Arial", 10), text_color="#CBD5E1",
                         width=110, anchor="w").pack(side="left", padx=6)

            # Col 3: Risk level
            ctk.CTkLabel(row_f, text=fac_risk,
                         font=("Arial", 10, "bold"), text_color=fac_color,
                         width=100, anchor="w").pack(side="left", padx=6)

            # Col 4: Contribution bar
            col4 = ctk.CTkFrame(row_f, fg_color="transparent", width=200)
            col4.pack(side="left", padx=6)
            ctk.CTkLabel(col4, text=bar_txt,
                         font=("Arial", 9), text_color=bar_col,
                         width=200, anchor="w").pack(anchor="w")
            if bar_pct > 0:
                bar_bg = ctk.CTkFrame(col4, fg_color="#1a2a3a", height=6,
                                      corner_radius=3, width=180)
                bar_bg.pack(anchor="w")
                bar_bg.pack_propagate(False)
                filled_w = max(4, int(bar_pct * 1.8))
                ctk.CTkFrame(bar_bg, fg_color=bar_col, height=6,
                              corner_radius=3, width=filled_w).pack(side="left")

            # Col 5: Status
            ctk.CTkLabel(row_f, text=status_txt,
                         font=("Arial", 9, "bold"), text_color=status_col,
                         width=120, anchor="w").pack(side="left", padx=6)

        # ── SHAP summary line ───────────────────────────────────
        ctk.CTkFrame(ai_card, height=1, fg_color="#1e3a5f").pack(fill="x", padx=15, pady=(8, 4))
        shap_parts = []
        for label_key, val in list(contribs.items())[:5]:
            shap_parts.append(f"{label_key}: +{val:.1f}")
        shap_line = "  |  ".join(shap_parts)
        if shap_parts:
            ctk.CTkLabel(ai_card,
                         text=f"SHAP BREAKDOWN  →  {shap_line}  →  Total: {total_score:.0f}/100",
                         font=("Courier", 9), text_color="#4B7CB3").pack(anchor="w", padx=15, pady=(0, 4))

        # ── Natural language explanation ────────────────────────
        ctk.CTkFrame(ai_card, height=1, fg_color="#1e3a5f").pack(fill="x", padx=15, pady=(0, 6))
        ctk.CTkLabel(ai_card, text="AI EXPLANATION",
                     font=("Arial", 10, "bold"), text_color="#93C5FD").pack(anchor="w", padx=15)
        explanation = report.get('explanation', '')
        ctk.CTkLabel(ai_card, text=explanation if explanation else "No explanation available.",
                     wraplength=1000, justify="left",
                     font=("Arial", 11), text_color="#D1D5DB").pack(anchor="w", padx=15, pady=(4, 10))

        # ── Early warning alerts ────────────────────────────────
        alerts = report.get('alerts', [])
        if alerts:
            ctk.CTkFrame(ai_card, height=1, fg_color="#1e3a5f").pack(fill="x", padx=15, pady=(0, 6))
            ctk.CTkLabel(ai_card, text="⚠  EARLY WARNING SIGNALS",
                         font=("Arial", 10, "bold"), text_color="#F59E0B").pack(anchor="w", padx=15)
            for alert in alerts:
                ctk.CTkLabel(ai_card, text=f"  {alert}", wraplength=1000, justify="left",
                             font=("Arial", 10), text_color="#FDE68A").pack(anchor="w", padx=18, pady=1)
            ctk.CTkFrame(ai_card, height=8, fg_color="transparent").pack()

        # ── Missing data note ───────────────────────────────────
        missing = report.get('missing', [])
        if missing:
            ctk.CTkLabel(ai_card,
                         text=f"ℹ  Data unavailable for: {', '.join(missing[:6])}  — these factors were excluded from scoring.",
                         wraplength=1000, justify="left",
                         font=("Arial", 9, "italic"), text_color="#374151").pack(anchor="w", padx=15, pady=(2, 10))

        # --- RECOMMENDATIONS ---
        recommendations = report.get('recommendations', [])
        if recommendations:
            rec_card = ctk.CTkFrame(scroll, fg_color="#0a1f0d", corner_radius=8,
                                    border_width=1, border_color="#166534")
            rec_card.pack(fill="x", pady=8)
            ctk.CTkLabel(rec_card, text="✅  RECOMMENDED ACTIONS",
                         font=("Arial", 13, "bold"), text_color="#4ADE80").pack(anchor="w", padx=15, pady=(12, 4))
            for rec in recommendations:
                if isinstance(rec, dict):
                    txt = f"{rec.get('action','?')} — {rec.get('reason','')}"
                else:
                    txt = str(rec)
                ctk.CTkLabel(rec_card, text=f"  •  {txt}", wraplength=980, justify="left",
                             font=("Arial", 11), text_color="#D1FAE5").pack(anchor="w", padx=15, pady=2)
            ctk.CTkFrame(rec_card, height=10, fg_color="transparent").pack()

        # --- PERFORMANCE TREND (only when present) ---
        trend_vals = report.get('trend', [])
        if trend_vals:
            t_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=8)
            t_card.pack(fill="x", pady=8)
            ctk.CTkLabel(t_card, text="PERFORMANCE TREND",
                         font=("Arial", 12, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=12, pady=(10, 2))
            try:
                fig_t = Figure(figsize=(8, 2.5), dpi=80)
                fig_t.patch.set_facecolor(COLORS["card"])
                ax_t = fig_t.add_subplot(111)
                ax_t.set_facecolor(COLORS["card"])
                t_len = len(trend_vals)
                ax_t.set_xticks(range(t_len))
                ax_t.set_xticklabels([f"Sem {i+1}" for i in range(t_len)], color='white')
                ax_t.plot(trend_vals, marker='o', color=COLORS["accent"], linewidth=2)
                ax_t.tick_params(colors='white')
                fig_t.tight_layout(pad=0.5)
                can_t = FigureCanvasTkAgg(fig_t, master=t_card)
                can_t.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)
            except Exception:
                pass

        # --- FACULTY NOTES ---
        n_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=8)
        n_card.pack(fill="x", pady=15)
        ctk.CTkLabel(n_card, text="FACULTY NOTES", text_color="gray",
                     font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(10, 2))
        self.txt_note = ctk.CTkTextbox(n_card, height=80, fg_color=COLORS["input_bg"])
        self.txt_note.pack(fill="x", padx=20, pady=5)

        def save_note():
            ModernMessagebox("Saved", "Note stored.", "success")

        ctk.CTkButton(n_card, text="SAVE NOTES", fg_color="#333", command=save_note).pack(pady=10)
        ctk.CTkButton(scroll, text="CLOSE DIAGNOSIS", fg_color=COLORS["danger"],
                      text_color="white", command=top.destroy).pack(pady=10)

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
        
        val = ctk.CTkLabel(line_f, text=v, text_color=color, font=("Arial", 11, "bold"))
        val.pack(side="left")
        
    def _profile_badge(self, parent, label_text, value_text):
        badge_frame = ctk.CTkFrame(parent, fg_color="transparent")
        badge_frame.pack(side="left", fill="x", expand=True, padx=10, pady=15)
        
        lbl = ctk.CTkLabel(badge_frame, text=label_text, text_color="gray", font=("Arial", 11))
        lbl.pack(anchor="center")
        
        val = ctk.CTkLabel(badge_frame, text=value_text, text_color="white", font=("Arial", 14, "bold"))
        val.pack(anchor="center")

    def show_error(self, msg):
        self._clear()
        err_lbl = ctk.CTkLabel(self.content_area, text=msg, font=("Arial", 16), text_color="orange")
        err_lbl.pack(pady=100)

    def _clear(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

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
        self.analytics = AnalyticsPanel(self, controller)
        self.faculty = FacultyManagerPanel(self, controller)
        self.hod_manager = HODManagerPanel(self, controller)

    def on_show(self):
        self.sidebar.refresh()
        # Always show the sidebar and analytics view
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.show_view("Analytics")

    def show_view(self, name):
        self.analytics.grid_forget()
        self.faculty.grid_forget()
        self.hod_manager.grid_forget()

        
        if name == "Analytics":
            self.analytics.grid(row=0, column=1, sticky="nsew")
            self.analytics.refresh()
        elif name == "Faculty":
            self.faculty.grid(row=0, column=1, sticky="nsew")
            self.faculty.refresh()
        elif name == "HOD":
            self.hod_manager.grid(row=0, column=1, sticky="nsew")
            self.hod_manager.refresh()

    def open_change_pass(self):
        top = ctk.CTkToplevel(self)
        top.geometry("400x520")
        top.title("AcaDesk - Security Update")
        top.attributes("-topmost", True)
        
        header = ctk.CTkLabel(top, text="Update Access Credentials", font=("Arial", 18, "bold"))
        header.pack(pady=20)
        
        ctk.CTkLabel(top, text="Current Password").pack(pady=(10, 0))
        e_curr = ctk.CTkEntry(top, show="*")
        e_curr.pack(pady=5)
        
        ctk.CTkLabel(top, text="New Password").pack(pady=(10, 0))
        e_new = ctk.CTkEntry(top, show="*")
        e_new.pack(pady=5)
        
        ctk.CTkLabel(top, text="Confirm New Password").pack(pady=(10, 0))
        e_conf = ctk.CTkEntry(top, show="*")
        e_conf.pack(pady=5)
        
        def attempt_save():
            p_new = e_new.get()
            p_conf = e_conf.get()
            if p_new == p_conf and p_new != "":
                top.destroy()
                ModernMessagebox("Success", "Security settings updated.", "success")
            else:
                ModernMessagebox("Error", "New passwords do not match.", "error")
                
        sub_btn = ctk.CTkButton(
            top, 
            text="SUBMIT", 
            command=attempt_save, 
            fg_color=COLORS["accent"], 
            text_color="black"
        )
        sub_btn.pack(pady=30)

    def open_ai_simulator(self):
        sim = ctk.CTkToplevel(self)
        sim.geometry("500x600")
        sim.title("AcaDesk AI Sandbox")
        sim.attributes("-topmost", True)
        
        head = ctk.CTkLabel(sim, text="AI RISK SANDBOX", font=("Arial", 20, "bold"), text_color="#00E5FF")
        head.pack(pady=20)
        
        att_v = ctk.IntVar(value=75)
        mrk_v = ctk.IntVar(value=60)
        bkl_v = ctk.IntVar(value=0)
        
        def trigger_calc(*args):
            at = att_v.get()
            mk = mrk_v.get()
            bk = bkl_v.get()
            res = RiskPredictor().analyze_student(at, mk, bk, 7)
            
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
        
        risk_disp = ctk.CTkLabel(sim, text="RISK: ...", font=("Arial", 24, "bold"))
        risk_disp.pack(pady=20)
        
        act_disp = ctk.CTkLabel(sim, text="Action: ...", wraplength=400)
        act_disp.pack()
        
        trigger_calc()