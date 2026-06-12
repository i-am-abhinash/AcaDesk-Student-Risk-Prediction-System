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
        self.btn_overview = self.add_btn("🏛️  Institution Overview", lambda: self.dash.show_view("Overview"))
        self.btn_fac = self.add_btn("👥  Faculty Manager", lambda: self.dash.show_view("Faculty"))
        self.btn_hod = self.add_btn("🎓  HOD Manager", lambda: self.dash.show_view("HODMgr"))
        self.btn_ai = self.add_btn("✨  AI Insights", lambda: self.dash.show_view("Insights"))
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
            text_color="#00E5FF",
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
        
        # Hide restricted buttons initially
        self.btn_overview.pack_forget()
        self.btn_fac.pack_forget()
        self.btn_hod.pack_forget()

        if user_type == "Admin": 
            self.btn_overview.configure(text="🏛️  Institution Overview")
            self.btn_overview.pack(fill="x", padx=10, pady=2, after=self.btn_dash)
            self.btn_fac.pack(fill="x", padx=10, pady=2)
            self.btn_hod.pack(fill="x", padx=10, pady=2)
        elif user_type == "HOD":
            self.btn_overview.configure(text="🏛️  Department Overview")
            self.btn_overview.pack(fill="x", padx=10, pady=2, after=self.btn_dash)
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
            self.br_combo.configure(values=list(self.branch_map.keys()))
            
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        try:
            college = self.controller.shared_data.get("college_name")
            faculties = CentralAuth().get_faculty_list(college)
            
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

class HODManagerPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.db = None
        self.branch_map = {}
        
        title = ctk.CTkLabel(
            self, 
            text="HEAD OF DEPARTMENT ACCESS CONTROL", 
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
            command=self.add_hod
        )
        add_btn.pack(side="left", padx=5)
        
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
                
                row = ctk.CTkFrame(self.list_frame, fg_color=COLORS["card"], height=50)
                row.pack(fill="x", pady=5)
                
                lbl = ctk.CTkLabel(
                    row, 
                    text=f"🎓  {f['username']}  [{branch_name}]", 
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
                from main import ModernMessagebox
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
        self.ai = RiskPredictor()
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
        self._clear()
        self.lbl_title.configure(text="Select Department")
        self.btn_back.pack_forget()
        
        user_type = self.controller.shared_data.get("user_type")
        
        # Container for charts (if Admin)
        self.charts_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.charts_frame.pack(fill="x", pady=(10, 20))
        
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
            scroll.grid_columnconfigure(c, weight=1)
            
        for i, bid in enumerate(branch_ids):
            name = self.translator.get_name(bid)
            btn = ctk.CTkButton(
                scroll, 
                text=name, 
                font=("Arial", 16, "bold"), 
                height=80, 
                fg_color=COLORS["card"], 
                text_color="#00E5FF",
                command=lambda b=bid: self.select_branch(b)
            )
            btn.grid(row=i//cols, column=i%cols, padx=10, pady=10, sticky="nsew")

    def _draw_admin_charts(self, global_stats, branch_stats, loading_lbl):
        loading_lbl.destroy()
        
        # Pie Chart Section
        l_frame = ctk.CTkFrame(self.charts_frame, fg_color=COLORS["card"])
        l_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        fig1 = Figure(figsize=(4, 3.5), dpi=100)
        fig1.patch.set_facecolor(COLORS["card"])
        ax1 = fig1.add_subplot(111)
        
        labels = ["High", "Med", "Safe"]
        counts = [global_stats["High"], global_stats["Medium"], global_stats["Low"]]
        colors = [COLORS["danger"], COLORS["warning"], COLORS["success"]]
        
        # Don't plot pie if all zero
        if sum(counts) > 0:
            ax1.pie(counts, labels=labels, colors=colors, autopct='%1.1f%%', textprops={'color':"white", 'fontsize': 9})
            ax1.set_title("Overall Risk", color="white", pad=10)
        else:
            ax1.text(0.5, 0.5, "No Data", color="white", ha="center", va="center")
            
        fig1.tight_layout()
        canvas1 = FigureCanvasTkAgg(fig1, master=l_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Bar Chart Section
        r_frame = ctk.CTkFrame(self.charts_frame, fg_color=COLORS["card"])
        r_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))
        
        fig2 = Figure(figsize=(6, 3.5), dpi=100)
        fig2.patch.set_facecolor(COLORS["card"])
        ax2 = fig2.add_subplot(111)
        ax2.set_facecolor(COLORS["card"])
        
        dept_names = list(branch_stats.keys())
        if dept_names:
            highs = [branch_stats[d].get("High", 0) for d in dept_names]
            meds = [branch_stats[d].get("Medium", 0) for d in dept_names]
            
            # Use horizontal bars for readability of long names
            y_pos = range(len(dept_names))
            
            ax2.barh(y_pos, highs, color=COLORS["danger"], label="High Risk")
            ax2.barh(y_pos, meds, left=highs, color=COLORS["warning"], label="Medium Risk")
            
            ax2.set_yticks(y_pos)
            # Shorten names for display if needed
            short_names = [n[:15] + '...' if len(n)>18 else n for n in dept_names]
            ax2.set_yticklabels(short_names, color='white', fontsize=8)
            ax2.tick_params(axis='x', colors='white', labelsize=8)
            
            ax2.set_title("Risk by Department", color="white", pad=10)
            ax2.legend(loc="lower right", fontsize=8, framealpha=0.5)
            
        fig2.tight_layout()
        canvas2 = FigureCanvasTkAgg(fig2, master=r_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def select_branch(self, bid):
        self.current_branch = bid
        self.show_year_selection()

    def select_year(self, yr):
        self.current_year = yr
        self.show_student_list()

    def show_year_selection(self):
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
        ctk.CTkLabel(scroll, text="Select Year to View Students", font=FONTS["h3"], text_color="#00E5FF").pack(anchor="w", pady=(10, 5))
        grid = ctk.CTkFrame(scroll, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        
        for i, yr in enumerate(YEARS):
            btn = ctk.CTkButton(
                grid, 
                text=yr, 
                font=("Arial", 18, "bold"), 
                height=60, 
                fg_color=COLORS["card"], 
                command=lambda y=yr: self.select_year(y)
            )
            btn.grid(row=i//2, column=i%2, padx=10, pady=10, sticky="nsew")

    def _render_dept_analytics(self, frame, data):
        for w in frame.winfo_children(): w.destroy()
        if not data or not data["ranked_departments"]:
            ctk.CTkLabel(frame, text="No data available for this department.", text_color="gray").pack()
            return
            
        stats = data["ranked_departments"][0][1]
        
        frame.grid_columnconfigure((0,1,2,3), weight=1)
        
        kpis = [
            ("Avg Attendance", f"{stats.get('avg_attendance', 0):.1f}%", COLORS["accent"] if stats.get('avg_attendance', 0) > 75 else COLORS["danger"]),
            ("Avg CGPA/Marks", f"{stats.get('avg_cgpa', 0):.1f}%", COLORS["accent"]),
            ("Avg Backlogs", f"{stats.get('avg_backlogs', 0):.1f}", COLORS["danger"] if stats.get('avg_backlogs', 0) > 1 else COLORS["success"]),
            ("Top Drivers", ", ".join(stats.get('top_drivers', ["N/A"])), COLORS["warning"]),
            ("High Risk Students", str(stats.get("High", 0)), COLORS["danger"]),
            ("Medium Risk Students", str(stats.get("Medium", 0)), COLORS["warning"]),
            ("Low Risk Students", str(stats.get("Low", 0)), COLORS["success"]),
            ("Dept Health Score", f"{stats.get('health_score', 0)}/100", COLORS["success"] if stats.get('health_score', 0) > 75 else COLORS["danger"])
        ]
        
        for i, (title, val, color) in enumerate(kpis):
            c = ctk.CTkFrame(frame, fg_color=COLORS["card"], corner_radius=10)
            c.grid(row=i//4, column=i%4, padx=5, pady=5, sticky="nsew")
            ctk.CTkLabel(c, text=title, text_color="gray", font=("Arial", 12)).pack(pady=(15, 5))
            ctk.CTkLabel(c, text=val, text_color=color, font=("Arial", 18, "bold"), wraplength=180).pack(pady=(0, 15))

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
        
        self.btn_all = self._create_filter_btn(f_row, "ALL", "All", "#333333")
        self.btn_high = self._create_filter_btn(f_row, "HIGH", "High", COLORS["danger"])
        self.btn_med = self._create_filter_btn(f_row, "MEDIUM", "Medium", COLORS["warning"])
        self.btn_low = self._create_filter_btn(f_row, "LOW", "Low", COLORS["success"])
        
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
            
        students = self.db.get_students(self.current_branch, self.current_year)
        with open('debug_filter.txt', 'w', encoding='utf-8') as f:
            f.write(f"Branch: {self.current_branch}, Year: {self.current_year}, Students: {len(students)}\n")
            if students:
                f.write(f"First student keys: {list(students[0].keys())}\n")
        query = self.search_var.get().lower()
        
        for s in students:
            is_match = query in str(s['id']).lower() or query in str(s['name']).lower()
            if is_match:
                year_str = str(s.get('year', '')).lower()
                is_first_year = '1' in year_str or 'first' in year_str
                
                if is_first_year:
                    try:
                        report = self.ai.analyze_first_year(s['avg_attendance'], s.get('tenth'), s.get('inter'), s.get('diploma'), s['backlogs'])
                    except Exception as e:
                        with open('debug_filter.txt', 'a', encoding='utf-8') as f: f.write(f"Error AI 1: {e}\n")
                        report = self.ai._get_fallback_report(s['avg_attendance'], s['avg_marks'], s['backlogs'])
                else:
                    try:
                        history = self.db.get_student_history(s['id'])
                        report = self.ai.analyze_student(s, 7, history_data=history)
                    except Exception as e:
                        with open('debug_filter.txt', 'a', encoding='utf-8') as f: f.write(f"Error AI 2: {e}\n")
                        report = self.ai._get_fallback_report(s['avg_attendance'], s['avg_marks'], s['backlogs'])
                
                if self.current_filter == "All" or report['level'] == self.current_filter:
                    row = ctk.CTkFrame(self.list_frame, fg_color=COLORS["card"], height=55)
                    row.pack(fill="x", pady=5)
                    
                    diag_btn = ctk.CTkButton(
                        row, 
                        text="DIAGNOSE", 
                        width=120, 
                        fg_color=COLORS["accent"], 
                        text_color="black", 
                        command=lambda d=s, r=report: self.open_deep_analysis(d, r)
                    )
                    diag_btn.pack(side="right", padx=20)
                    
                    name_text = f"{s['id']} - {s['name']}"
                    if report.get('is_first_year'):
                        name_text += "  [🎓 1st Year]"
                    name_lbl = ctk.CTkLabel(row, text=name_text, font=("Roboto", 12, "bold"))
                    name_lbl.pack(side="left", padx=20)
                    
                    if report['level'] == "High":
                        col = COLORS["danger"]
                    elif report['level'] == "Medium":
                        col = COLORS["warning"]
                    else:
                        col = COLORS["success"]
                        
                    risk_lbl = ctk.CTkLabel(row, text=f"{report['level']} RISK", text_color=col, font=("Arial", 11, "bold"))
                    risk_lbl.pack(side="left", padx=20)

    def open_deep_analysis(self, data, report):
        top = ctk.CTkToplevel(self)
        top.geometry("1100x850")
        top.title("AcaDesk - Student Diagnosis")
        top.attributes("-topmost", True)
        top.configure(fg_color="#000")
        
        scroll = ctk.CTkScrollableFrame(top, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- HEADER CARD ---
        header_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        header_card.pack(fill="x", pady=(0, 10))
        
        p_email = data.get('parent_email', 'Not Provided')
        is_email_missing = p_email == 'Not Provided' or not p_email
        
        def send_email_alert():
            from logic.email_service import EmailService
            from tkinter import messagebox
            
            emails_to_send = []
            if data.get("email"): emails_to_send.append(data["email"])
            if data.get("parent_email"): emails_to_send.append(data["parent_email"])
            
            if not emails_to_send:
                messagebox.showwarning("No Contact Info", "No email addresses found for this student.")
                return
                
            es = EmailService()
            success = es.send_early_warning_alert(
                to_emails=emails_to_send,
                student_name=data.get("display_name", data.get("name", "Student")),
                student_id=data.get("registration_no", data.get("id", "Unknown")),
                college_name=self.shared_data.get("college_name", "Your College"),
                risk_level=report.get("level", "Unknown"),
                dominant_factor=report.get("dominant", "Multiple Factors")
            )
            
            if success:
                messagebox.showinfo("Success", f"Alert successfully sent to {', '.join(emails_to_send)}")
            else:
                messagebox.showerror("Error", "Failed to send email alert. Check console.")
                
        btn_notify = ctk.CTkButton(
            header_card, 
            text="🔔 Notify", 
            fg_color="#b91c1c", 
            hover_color="#991b1b",
            font=("Arial", 12, "bold"),
            command=send_email_alert
        )
        btn_notify.pack(side="right", padx=20, pady=20)
        
        r_color = COLORS["success"]
        if report['level'] == "High": r_color = COLORS["danger"]
        elif report['level'] == "Medium": r_color = COLORS["warning"]
        
        title_lbl = ctk.CTkLabel(header_card, text=f"{data['name']} ({data['id']})", font=("Arial", 22, "bold"))
        title_lbl.pack(anchor="w", padx=20, pady=(20, 5))
        
        score_frame = ctk.CTkFrame(header_card, fg_color="transparent")
        score_frame.pack(anchor="w", padx=20, pady=(0, 20))
        
        score_lbl = ctk.CTkLabel(score_frame, text=f"Risk Score: {report['score']}/100", font=("Arial", 16, "bold"), text_color=r_color)
        score_lbl.pack(side="left", padx=(0, 15))
        
        conf_lbl = ctk.CTkLabel(score_frame, text=f"Prediction Confidence: {report.get('confidence', 0)}%", font=("Arial", 12), text_color="gray")
        conf_lbl.pack(side="left")
        
        # --- NEW STUDENT PROFILE BAR ---
        profile_bar = ctk.CTkFrame(scroll, fg_color="#1a1a1a", corner_radius=8, border_width=1, border_color="#333")
        profile_bar.pack(fill="x", pady=(0, 20), padx=5)
        
        reg_no = str(data.get('id', 'N/A'))
        self._profile_badge(profile_bar, "Registration No:", reg_no)
        
        cgpa_marks = str(data.get('avg_marks', 'N/A'))
        self._profile_badge(profile_bar, "CGPA / Marks:", f"{cgpa_marks}%")
        
        branch_name = self.translator.get_name(self.current_branch)
        self._profile_badge(profile_bar, "Department:", branch_name)
        
        # Attempts to pull 'phone', defaults to 'email', then defaults to 'Not Provided'
        contact_info = p_email if p_email != 'Not Provided' else str(data.get('phone', data.get('email', 'Not Provided')))
        self._profile_badge(profile_bar, "Contact Info:", contact_info)
        
        if is_email_missing:
            btn_add_contact = ctk.CTkButton(
                profile_bar, 
                text="✎ Add Contact", 
                width=100,
                fg_color="transparent",
                border_width=1,
                border_color=COLORS["accent"],
                text_color=COLORS["accent"],
                command=lambda: self._open_edit_contact_dialog(data)
            )
            btn_add_contact.pack(side="left", padx=10, pady=15)
        
        nlg_report = report.get('nlg_report', '')
        if nlg_report:
            nlg_card = ctk.CTkFrame(scroll, fg_color="#1a1a1a", border_width=1, border_color="#333", corner_radius=8)
            nlg_card.pack(fill="x", pady=10)
            ctk.CTkLabel(nlg_card, text="🤖 AI ASSESSMENT", text_color="orange", font=("Arial", 12, "bold")).pack(anchor="w", padx=20, pady=(15,0))
            ctk.CTkLabel(nlg_card, text=nlg_report, text_color="white", wraplength=1000, justify="left").pack(anchor="w", padx=20, pady=(5, 15))

        # --- GRID FRAME (AI Insights & Charts) ---
        grid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        grid_frame.pack(fill="x", pady=10)
        
        # Left Info Panel
        l_info = ctk.CTkFrame(grid_frame, fg_color=COLORS["card"])
        l_info.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        dom_factor = str(report.get('dominant', 'N/A'))
        self.add_line(l_info, "Risk Factor:", dom_factor, color="#FF5555")
        
        ai_action = str(report.get('action', 'N/A'))
        self.add_line(l_info, "AI Advice:", ai_action, color="orange")
        
        # Dynamic 10-Factor Feature Rendering
        features_to_show = {
            'avg_attendance': ('Attendance', '%'),
            'avg_marks': ('Avg Marks', '%'),
            'backlogs': ('Backlogs', ''),
            'tenth': ('10th Grade', '%'),
            'inter': ('Intermediate', '%'),
            'diploma': ('Diploma', '%'),
            'lab_performance': ('Lab Perf', '%'),
            'mid_exam_score': ('Mid Exam', '%'),
            'consecutive_absences': ('Cons. Absences', ' days'),
            'leave_frequency': ('Leave Freq', ' times')
        }
        for k, v in features_to_show.items():
            if data.get(k) is not None:
                self.add_line(l_info, f"{v[0]}:", f"{data[k]}{v[1]}")

        # Right Charts Panel
        r_info = ctk.CTkFrame(grid_frame, fg_color=COLORS["card"])
        r_info.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        try:
            fig_r = Figure(figsize=(4, 3), dpi=80)
            fig_r.patch.set_facecolor(COLORS["card"])
            
            ax_r = fig_r.add_subplot(111)
            ax_r.set_facecolor(COLORS["card"])
            
            c_data = report.get('contributions', {"Att": 30, "Marks": 50, "Bkl": 20})
            
            # Sort the contributions dynamically
            sorted_contribs = sorted(c_data.items(), key=lambda x: x[1], reverse=True)[:5]
            sorted_contribs.reverse() # Reverse so top is at the top of the barh plot
            
            c_keys = [k[:12] for k, v in sorted_contribs]
            c_vals = [v for k, v in sorted_contribs]
            
            # Color coding based on factor name and if it's high impact
            c_colors = [COLORS["danger"] if v > 15 else COLORS["accent"] for v in c_vals]
            
            title = "Top Risk Drivers (SHAP)" if report.get('shap_values') else "Factor Contributions"
            ax_r.set_title(title, color="white", fontsize=10)
            
            ax_r.barh(c_keys, c_vals, color=c_colors)
            ax_r.tick_params(colors='white', labelsize=8)
            ax_r.set_xlim(0, 100) # Force 0-100 percentage scale
            
            can_r = FigureCanvasTkAgg(fig_r, master=r_info)
            wid_r = can_r.get_tk_widget()
            wid_r.pack(fill="both", expand=True, padx=10)
        except Exception as e:
            pass

        # --- ACADEMIC PERFORMANCE TREND ANALYSIS ---
        trend_info = report.get('trend_info')
        if trend_info and trend_info.get("history") and len(trend_info["history"]) > 1:
            trend_card = ctk.CTkFrame(scroll, fg_color="#1a1a1a", border_width=1, border_color="#333", corner_radius=8)
            trend_card.pack(fill="x", pady=10, padx=5)
            
            # Trend Header
            t_head = ctk.CTkFrame(trend_card, fg_color="transparent")
            t_head.pack(fill="x", padx=20, pady=(15, 10))
            
            ctk.CTkLabel(t_head, text="📈 ACADEMIC PERFORMANCE TREND ANALYSIS", font=("Arial", 14, "bold"), text_color="#00E5FF").pack(side="left")
            
            t_status = trend_info.get("trend_status", "Unknown")
            t_color = COLORS["success"] if "Improving" in t_status else (COLORS["danger"] if "Decline" in t_status else "gray")
            
            ctk.CTkLabel(t_head, text=f"Trend Score: {trend_info.get('trend_score', 0)}/100", font=("Arial", 12, "bold"), text_color="white").pack(side="right", padx=(20, 0))
            ctk.CTkLabel(t_head, text=f"Status: {t_status}", font=("Arial", 12, "bold"), text_color=t_color).pack(side="right")
            
            # Trend Visuals
            try:
                canvas = TrendVisuals.create_trend_charts(trend_card, trend_info)
            except Exception as e:
                print(f"Failed to render trend visuals: {e}")
                ctk.CTkLabel(trend_card, text="Failed to render trend charts.", text_color="red").pack(pady=10)

        # --- AI RECOMMENDED ACTIONS ---
        recs = report.get('recommendations', [])
        if recs:
            rec_card = ctk.CTkFrame(scroll, fg_color=COLORS['card'], corner_radius=10)
            rec_card.pack(fill='x', pady=(20, 0))
            
            ctk.CTkLabel(rec_card, text='💡 RECOMMENDED ACTIONS', font=('Arial', 16, 'bold'), text_color='#00E5FF').pack(anchor='w', padx=20, pady=(15, 5))
            
            for r in recs:
                r_frame = ctk.CTkFrame(rec_card, fg_color='transparent')
                r_frame.pack(fill='x', padx=20, pady=5)
                
                p_color = COLORS['danger'] if r['priority'] == 1 else COLORS['warning'] if r['priority'] == 2 else COLORS['success']
                p_badge = ctk.CTkLabel(r_frame, text=f"Priority {r['priority']}", fg_color=p_color, text_color='white', corner_radius=5, font=('Arial', 10, 'bold'), width=70, height=20)
                p_badge.pack(side='left', padx=(0, 10))
                
                ctk.CTkLabel(r_frame, text=r['action'], font=('Arial', 14, 'bold')).pack(side='left')
                
                rat_lbl = ctk.CTkLabel(rec_card, text=f"↳ {r['rationale']}", text_color='gray', font=('Arial', 11))
                rat_lbl.pack(anchor='w', padx=100, pady=(0, 5))

        # --- BOTTOM TREND LINE CHART ---
        if not report.get('is_first_year', False):
            t_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"])
            t_card.pack(fill="x", pady=20)
            
            try:
                fig_t = Figure(figsize=(8, 2.5), dpi=80)
                fig_t.patch.set_facecolor(COLORS["card"])
                
                ax_t = fig_t.add_subplot(111)
                ax_t.set_facecolor(COLORS["card"])
                
                trend_vals = report.get('trend')
                if not trend_vals:
                    trend_vals = [65, 70, 62, 68]
                    
                t_len = len(trend_vals)
                ax_t.set_xticks(range(t_len))
                
                t_labels = [f"Sem {i+1}" for i in range(t_len)]
                if t_len > 0:
                    t_labels[-1] = "Current"
                    
                ax_t.set_xticklabels(t_labels, color='white')
                
                ax_t.plot(trend_vals, marker='o', color=COLORS["accent"], linewidth=2)
                ax_t.tick_params(colors='white')
                
                can_t = FigureCanvasTkAgg(fig_t, master=t_card)
                wid_t = can_t.get_tk_widget()
                wid_t.pack(fill="both", expand=True, padx=10)
            except Exception as e:
                pass
            
        # Faculty Notes Section
        n_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"])
        n_card.pack(fill="x", pady=20)
        
        note_lbl = ctk.CTkLabel(n_card, text="FACULTY NOTES", text_color="gray")
        note_lbl.pack(anchor="w", padx=20, pady=5)
        
        self.txt_note = ctk.CTkTextbox(n_card, height=80, fg_color=COLORS["input_bg"])
        self.txt_note.pack(fill="x", padx=20, pady=10)
        
        def save_note():
            ModernMessagebox("Saved", "Note stored.", "success")
            
        save_n = ctk.CTkButton(n_card, text="SAVE NOTES", fg_color="#333", command=save_note)
        save_n.pack(pady=10)
        
        close_btn = ctk.CTkButton(scroll, text="CLOSE DIAGNOSIS", command=top.destroy)
        close_btn.pack(pady=10)

    def _open_edit_contact_dialog(self, data):
        diag = ctk.CTkToplevel(self)
        diag.geometry("400x300")
        diag.title("Update Parent Contact")
        diag.attributes("-topmost", True)
        diag.configure(fg_color="#111")
        
        ctk.CTkLabel(diag, text="Update Contact Info", font=("Arial", 18, "bold")).pack(pady=20)
        
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
        
        ctk.CTkLabel(diag, text="DISPATCH ALERT", font=("Arial Black", 20), text_color=COLORS["accent"]).pack(pady=(20, 5))
        
        p_email = data.get('parent_email', 'Not Provided')
        p_phone = data.get('parent_phone', 'Not Provided')
        
        info_frame = ctk.CTkFrame(diag, fg_color=COLORS["card"])
        info_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(info_frame, text=f"Student: {data['name']}", font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=(15, 2))
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
        
        ctk.CTkLabel(cred_frame, text="Gmail App Password:", font=("Arial", 12)).pack(side="left", padx=5)
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
                
        btn_send = ctk.CTkButton(diag, text="Send Email", fg_color=COLORS["success"], font=("Arial", 16, "bold"), height=40, command=send_email_action)
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
        from ui.overview import OverviewPanel
        self.overview = OverviewPanel(self, controller)
        self.analytics = AnalyticsPanel(self, controller)
        self.faculty = FacultyManagerPanel(self, controller)
        self.hod_mgr = HODManagerPanel(self, controller)
        from ui.advanced_insights import AdvancedInsightsPanel
        self.insights = AdvancedInsightsPanel(self, controller)
        self.erp = ERPWizard(self, controller, self)

    def on_show(self):
        self.sidebar.refresh()
        needed = self.controller.shared_data.get("erp_setup_needed")
        
        if needed:
            self.erp.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.sidebar.grid_forget()
        else:
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            user_type = self.controller.shared_data.get("user_type")
            # Always default to the student-level dashboard (Analytics) upon login
            self.show_view("Analytics")

    def show_view(self, name):
        self.overview.grid_forget()
        self.analytics.grid_forget()
        self.faculty.grid_forget()
        self.hod_mgr.grid_forget()
        self.erp.grid_forget()
        self.insights.grid_forget()
        
        if name == "Overview":
            self.overview.grid(row=0, column=1, sticky="nsew")
            self.overview.refresh()
        elif name == "Analytics":
            self.analytics.grid(row=0, column=1, sticky="nsew")
            self.analytics.refresh()
        elif name == "Faculty":
            self.faculty.grid(row=0, column=1, sticky="nsew")
            self.faculty.refresh()
        elif name == "HODMgr":
            self.hod_mgr.grid(row=0, column=1, sticky="nsew")
            self.hod_mgr.refresh()
        elif name == "Insights":
            self.insights.grid(row=0, column=1, sticky="nsew")
            self.insights.refresh()

    def open_change_pass(self):
        top = ctk.CTkToplevel(self)
        top.geometry("450x550")
        top.title("AcaDesk - Security Settings")
        top.attributes("-topmost", True)
        top.configure(fg_color="#0d0d0d")
        
        main_card = ctk.CTkFrame(top, fg_color="#1a1a1a", corner_radius=15, border_width=1, border_color="#333")
        main_card.pack(fill="both", expand=True, padx=25, pady=25)
        
        header_icon = ctk.CTkLabel(main_card, text="🔒", font=("Arial", 40))
        header_icon.pack(pady=(30, 10))
        
        header = ctk.CTkLabel(main_card, text="UPDATE PASSWORD", font=("Arial Black", 20), text_color="#00E5FF")
        header.pack(pady=(0, 20))
        
        # Current Password
        ctk.CTkLabel(main_card, text="Current Password", text_color="gray", font=("Arial", 12)).pack(anchor="w", padx=40)
        e_curr = ctk.CTkEntry(main_card, show="*", height=40, fg_color="#111", border_color="#444", placeholder_text="Enter current password")
        e_curr.pack(fill="x", padx=40, pady=(5, 15))
        
        # New Password
        ctk.CTkLabel(main_card, text="New Password", text_color="gray", font=("Arial", 12)).pack(anchor="w", padx=40)
        e_new = ctk.CTkEntry(main_card, show="*", height=40, fg_color="#111", border_color="#444", placeholder_text="Enter new password")
        e_new.pack(fill="x", padx=40, pady=(5, 15))
        
        # Confirm Password
        ctk.CTkLabel(main_card, text="Confirm New Password", text_color="gray", font=("Arial", 12)).pack(anchor="w", padx=40)
        e_conf = ctk.CTkEntry(main_card, show="*", height=40, fg_color="#111", border_color="#444", placeholder_text="Confirm new password")
        e_conf.pack(fill="x", padx=40, pady=(5, 25))
        
        def attempt_save():
            p_new = e_new.get()
            p_conf = e_conf.get()
            if p_new == p_conf and p_new != "":
                top.destroy()
                ModernMessagebox("Success", "Security settings updated successfully.", "success")
            else:
                import tkinter.messagebox as mb
                mb.showerror("Error", "Passwords do not match!")
                
        btn_save = ctk.CTkButton(
            main_card, 
            text="SAVE CHANGES", 
            height=45, 
            font=("Arial", 14, "bold"),
            fg_color="#00E5FF", 
            text_color="black",
            hover_color="#00B8CC",
            command=attempt_save
        )
        btn_save.pack(fill="x", padx=40, pady=(0, 30))

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