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
            text_color=COLORS["text"]
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
        if user_type == "Admin": 
            self.btn_fac.pack(fill="x", padx=10, pady=2)
        else: 
            self.btn_fac.pack_forget()

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
                    font=FONTS["h3"]
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
        if user_type == "Faculty":
            assigned = self.controller.shared_data.get("assigned_branch")
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
            btn = ctk.CTkButton(
                scroll, 
                text=name, 
                font=("Arial", 16, "bold"), 
                height=80, 
                fg_color=COLORS["card"], 
                command=lambda b=bid: self.select_branch(b)
            )
            btn.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")

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
            btn = ctk.CTkButton(
                grid, 
                text=yr, 
                font=("Arial", 18, "bold"), 
                height=80, 
                fg_color=COLORS["card"], 
                command=lambda y=yr: self.select_year(y)
            )
            btn.grid(row=i//2, column=i%2, padx=20, pady=15, sticky="nsew")

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
        query = self.search_var.get().lower()
        
        for s in students:
            is_match = query in str(s['id']).lower() or query in str(s['name']).lower()
            if is_match:
                report = self.ai.analyze_student(s['avg_attendance'], s['avg_marks'], s['backlogs'], 7)
                
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
                    
                    name_lbl = ctk.CTkLabel(row, text=f"{s['id']} - {s['name']}", font=("Roboto", 12, "bold"))
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
        
        r_color = COLORS["success"]
        if report['level'] == "High":
            r_color = COLORS["danger"]
        elif report['level'] == "Medium":
            r_color = COLORS["warning"]
            
        name_lbl = ctk.CTkLabel(header_card, text=f"🎓 {data['name']}", font=("Arial", 24, "bold"))
        name_lbl.pack(side="left", padx=20, pady=15)
        
        score_lbl = ctk.CTkLabel(header_card, text=f"RISK SCORE: {report['score']} / 100", font=("Arial", 22, "bold"), text_color=r_color)
        score_lbl.pack(side="right", padx=20)
        
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
        contact_info = str(data.get('phone', data.get('email', 'Not Provided')))
        self._profile_badge(profile_bar, "Contact Info:", contact_info)
        
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
        
        att_val = str(data['avg_attendance'])
        self.add_line(l_info, "Attendance:", f"{att_val}%")
        
        bkl_val = str(data['backlogs'])
        self.add_line(l_info, "Backlogs:", bkl_val)

        # Right Charts Panel
        r_info = ctk.CTkFrame(grid_frame, fg_color=COLORS["card"])
        r_info.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        try:
            fig_r = Figure(figsize=(4, 2), dpi=80)
            fig_r.patch.set_facecolor(COLORS["card"])
            
            ax_r = fig_r.add_subplot(111)
            ax_r.set_facecolor(COLORS["card"])
            
            c_data = report.get('contributions', {"Att": 30, "Marks": 50, "Bkl": 20})
            
            c_keys = list(c_data.keys())
            c_vals = list(c_data.values())
            c_colors = [COLORS["accent"], COLORS["danger"], "orange"]
            
            ax_r.barh(c_keys, c_vals, color=c_colors)
            ax_r.tick_params(colors='white', labelsize=8)
            
            can_r = FigureCanvasTkAgg(fig_r, master=r_info)
            wid_r = can_r.get_tk_widget()
            wid_r.pack(fill="both", expand=True, padx=10)
        except Exception as e:
            pass

        # Bottom Trend Line Chart
        t_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"])
        t_card.pack(fill="x", pady=20)
        
        try:
            fig_t = Figure(figsize=(8, 2.5), dpi=80)
            fig_t.patch.set_facecolor(COLORS["card"])
            
            ax_t = fig_t.add_subplot(111)
            ax_t.set_facecolor(COLORS["card"])
            
            trend_vals = report.get('trend', [65, 70, 62, 68])
            t_len = len(trend_vals)
            ax_t.set_xticks(range(t_len))
            
            t_labels = ['Sem 1', 'Sem 2', 'Sem 3', 'Current']
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

class ERPWizard(ctk.CTkFrame):
    def __init__(self, parent, controller, dash):
        super().__init__(parent, fg_color="#111")
        self.controller = controller
        self.dash = dash
        self.current_step = 1
        
        self.s1 = None
        self.s2 = None
        self.s3 = None
        
        self.container = ctk.CTkFrame(self, corner_radius=20, fg_color="#1a1a1a")
        self.container.pack(fill="both", expand=True, padx=120, pady=40)
        
        self.header = ctk.CTkFrame(self.container, fg_color="transparent")
        self.header.pack(fill="x", pady=(30, 10), padx=30)
        
        head_lbl = ctk.CTkLabel(self.header, text="ENTERPRISE ERP SETUP", font=("Arial Black", 24))
        head_lbl.pack(anchor="w")
        
        self.step_lbl = ctk.CTkLabel(self.header, text="Step 1 of 3", text_color="gray")
        self.step_lbl.pack(anchor="w")
        
        self.main_body = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_body.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.footer = ctk.CTkFrame(self.container, fg_color="transparent")
        self.footer.pack(fill="x", padx=40, pady=20, side="bottom")
        
        self.btn_back = ctk.CTkButton(self.footer, text="← BACK", height=45, fg_color="#333", command=self.prev_step)
        self.btn_next = ctk.CTkButton(self.footer, text="NEXT STEP →", height=45, fg_color="#00E5FF", text_color="black", command=self.next_step)
        self.btn_save = ctk.CTkButton(self.footer, text="SAVE CONFIG", height=45, fg_color="#00C853", state="disabled", command=self.save)
        
        self.init_steps()
        self.show_step(1)

    def init_steps(self):
        # Step 1
        self.s1, f1 = self.create_layout("1. Connection", "Provide Server Credentials.")
        self.db_tech = self.add_labeled_dropdown(f1, "Database Technology:", ["MySQL / MariaDB", "PostgreSQL", "MS SQL Server", "Oracle"])
        self.host = self.add_labeled_entry(f1, "Host IP:", "localhost")
        self.port = self.add_labeled_entry(f1, "Port:", "3306")
        self.db_name = self.add_labeled_entry(f1, "DB Name:", "engineering_college")
        self.user = self.add_labeled_entry(f1, "User:", "root")
        self.pwd = self.add_labeled_entry(f1, "Password:", "", True)
        
        # Step 2
        self.s2, f2 = self.create_layout("2. Architecture", "Define table relationships.")
        self.t_stud = self.add_labeled_entry(f2, "Student Table:", "student")
        self.t_acad = self.add_labeled_entry(f2, "Academics Table:", "academics")
        self.t_bran = self.add_labeled_entry(f2, "Branch Table:", "branch")
        self.k_stud = self.add_labeled_entry(f2, "Student Key:", "student_id")
        self.k_bran = self.add_labeled_entry(f2, "Branch Key:", "branch_id")
        
        # Step 3
        self.s3, f3 = self.create_layout("3. Mapping", "Finalize column logic mapping.")
        self.c_id = self.add_labeled_entry(f3, "Reg No Col:", "roll_no")
        self.c_na = self.add_labeled_entry(f3, "Name Col:", "name")
        self.c_br = self.add_labeled_entry(f3, "Branch Name Col:", "branch_name")
        self.c_at = self.add_labeled_entry(f3, "Attendance Col:", "attendance")
        self.c_mk = self.add_labeled_entry(f3, "Marks/GPA Col:", "internal_marks")
        self.c_bk = self.add_labeled_entry(f3, "Backlogs Col:", "backlogs")

    def create_layout(self, title, desc):
        frame = ctk.CTkFrame(self.main_body, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        
        form_scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        form_scroll.pack(side="left", fill="both", expand=True, padx=10)
        
        info_panel = ctk.CTkFrame(frame, fg_color=COLORS["card"], corner_radius=15, width=300)
        info_panel.pack(side="right", fill="y", padx=10)
        info_panel.pack_propagate(False)
        
        ctk.CTkLabel(info_panel, text=title, font=("Arial", 18, "bold"), text_color="#00E5FF").pack(pady=20)
        ctk.CTkLabel(info_panel, text=desc, text_color="#ccc", wraplength=250, justify="left").pack(padx=20)
        
        return frame, form_scroll

    def add_labeled_entry(self, parent, label_text, default_value, secret=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=12)
        row.grid_columnconfigure(1, weight=1)
        
        lbl = ctk.CTkLabel(row, text=label_text, font=("Arial", 12, "bold"), anchor="w", width=180)
        lbl.grid(row=0, column=0, sticky="w")
        
        entry = ctk.CTkEntry(row, height=45)
        entry.insert(0, default_value)
        if secret: 
            entry.configure(show="*")
            
        entry.grid(row=0, column=1, sticky="ew", padx=(20, 50))
        return entry

    def add_labeled_dropdown(self, parent, lbl_text, values):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=10)
        row.grid_columnconfigure(1, weight=1)
        
        lbl = ctk.CTkLabel(row, text=lbl_text, width=180, anchor="w", font=("Arial", 12, "bold"))
        lbl.grid(row=0, column=0, sticky="w")
        
        dropdown = ctk.CTkComboBox(row, values=values, height=45)
        dropdown.grid(row=0, column=1, sticky="ew", padx=(20, 50))
        return dropdown

    def show_step(self, s):
        self.current_step = s
        
        self.s1.pack_forget()
        self.s2.pack_forget()
        self.s3.pack_forget()
        
        self.btn_back.pack_forget()
        self.btn_next.pack_forget()
        self.btn_save.pack_forget()
        
        self.step_lbl.configure(text=f"Step {s} of 3")
        
        if s == 1:
            self.s1.pack(fill="both", expand=True)
            self.btn_next.configure(text="NEXT STEP →")
            self.btn_next.pack(side="right")
        elif s == 2:
            self.s2.pack(fill="both", expand=True)
            self.btn_back.pack(side="left")
            self.btn_next.configure(text="NEXT STEP →")
            self.btn_next.pack(side="right")
        elif s == 3:
            self.s3.pack(fill="both", expand=True)
            self.btn_back.pack(side="left")
            self.btn_next.configure(text="OVERALL TEST ⚡", fg_color="#FF9100")
            self.btn_next.pack(side="right", padx=10)
            self.btn_save.pack(side="right")

    def next_step(self):
        if self.current_step < 3:
            self.show_step(self.current_step + 1)
        else:
            self.perform_overall_test()

    def perform_overall_test(self):
        # --- LAYER 1: FORM VALIDATION (Pre-Checks) ---
        host_val = self.host.get().strip()
        user_val = self.user.get().strip()
        pass_val = self.pwd.get().strip()
        db_val = self.db_name.get().strip()
        port_raw = self.port.get().strip()
        
        tech = self.db_tech.get()
        
        # Check if any connection fields are empty
        if not host_val:
            ModernMessagebox("Missing Information", "Please enter the Database Host Address (e.g., localhost or an IP).", "warning")
            return
        if not user_val:
            ModernMessagebox("Missing Information", "Please enter the Database Username (e.g., root).", "warning")
            return
        if not pass_val:
            ModernMessagebox("Missing Information", "The Password field is empty. Please enter your database password.", "warning")
            return
        if not db_val:
            ModernMessagebox("Missing Information", "Please specify the Database Name you want to connect to.", "warning")
            return
        if not port_raw.isdigit():
            ModernMessagebox("Invalid Port", "The Port number must be a valid number (e.g., 3306).", "warning")
            return
            
        port_val = int(port_raw)
        
        # Check if any Schema Mapping fields are empty
        student_tbl = self.t_stud.get().strip()
        acad_tbl = self.t_acad.get().strip()
        id_col = self.c_id.get().strip()
        name_col = self.c_na.get().strip()
        att_col = self.c_at.get().strip()
        join_key = self.k_stud.get().strip()
        
        if not all([student_tbl, acad_tbl, id_col, name_col, att_col, join_key]):
            ModernMessagebox("Missing Mapping", "Please ensure all table and column mapping fields are filled out.", "warning")
            return

        try:
            # Build the universal SQL test query
            sql_test = f"SELECT s.{id_col}, s.{name_col}, a.{att_col} FROM {student_tbl} s JOIN {acad_tbl} a ON s.{join_key} = a.{join_key} LIMIT 3"
            samples = []

            # --- LAYER 2: DATABASE CONNECTION LOGIC ---
            if tech == "MySQL / MariaDB":
                import mysql.connector
                conn = mysql.connector.connect(
                    host=host_val, user=user_val, password=pass_val, 
                    database=db_val, port=port_val, connect_timeout=3
                )
                cursor = conn.cursor(dictionary=True)
                cursor.execute(sql_test)
                samples = cursor.fetchall()
                conn.close()

            elif tech == "PostgreSQL":
                import psycopg2
                import psycopg2.extras
                conn = psycopg2.connect(
                    host=host_val, user=user_val, password=pass_val, 
                    dbname=db_val, port=port_val, connect_timeout=3
                )
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cursor.execute(sql_test)
                samples = [dict(row) for row in cursor.fetchall()]
                conn.close()

            elif tech == "MS SQL Server":
                import pyodbc
                conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={host_val},{port_val};DATABASE={db_val};UID={user_val};PWD={pass_val}"
                conn = pyodbc.connect(conn_str, timeout=3)
                cursor = conn.cursor()
                cursor.execute(sql_test)
                columns = [column[0] for column in cursor.description]
                samples = [dict(zip(columns, row)) for row in cursor.fetchall()]
                conn.close()

            elif tech == "Oracle":
                import oracledb
                dsn = f"{host_val}:{port_val}/{db_val}"
                conn = oracledb.connect(user=user_val, password=pass_val, dsn=dsn)
                cursor = conn.cursor()
                cursor.execute(sql_test)
                columns = [col[0].lower() for col in cursor.description]
                samples = [dict(zip(columns, row)) for row in cursor.fetchall()]
                conn.close()

            # --- LAYER 3: PREVIEW GENERATION ---
            if samples:
                msg_body = "VERIFIED! Sample Data Retrieved:\n"
                msg_body += "-" * 40 + "\n"
                for row in samples:
                    row_vals = list(row.values())
                    msg_body += f"ID: {row_vals[0]} | Name: {row_vals[1]} | Att: {row_vals[2]}%\n"
                
                # Unlock the SAVE button now that the test passed
                self.btn_save.configure(state="normal")
                ModernMessagebox("System Verified", msg_body, "success")
            else:
                raise ValueError("handshake success but no student data found")

        # --- LAYER 4: HUMAN-FRIENDLY ERROR TRANSLATION ---
        except Exception as e:
            raw_error = str(e).lower()
            
            # 1. Login/Password Issues
            if "access denied" in raw_error or "authentication failed" in raw_error or "password" in raw_error or "logon failed" in raw_error:
                friendly_msg = "Access Denied: The username or password you entered is incorrect."
                
            # 2. Database Name Issues
            elif "unknown database" in raw_error or "does not exist" in raw_error or "ora-12154" in raw_error:
                friendly_msg = f"Database Not Found: We couldn't find a database named '{db_val}'. Please check the spelling."
                
            # 3. Connection / Offline Issues
            elif "connection refused" in raw_error or "timeout" in raw_error or "network" in raw_error or "target machine actively refused" in raw_error:
                friendly_msg = f"Server Offline: Could not reach the server at '{host_val}'. Please check if your database software is running and the port is open."
                
            # 4. Table Mapping Issues
            elif "doesn't exist" in raw_error or "invalid table" in raw_error or "not found" in raw_error:
                friendly_msg = "Table Missing: The student or academic table you typed in the setup wizard does not exist in this database."
                
            # 5. Column Mapping Issues
            elif "unknown column" in raw_error or "invalid identifier" in raw_error:
                friendly_msg = "Column Mismatch: One of the column names you mapped in the wizard does not match the actual database columns."
                
            # 6. Empty Data Catch
            elif "handshake success but no student data found" in raw_error:
                friendly_msg = "Data Empty: The system connected successfully, but the tables you specified are completely empty."
                
            # Fallback for weird system errors
            else:
                friendly_msg = f"An unexpected system error occurred:\n\n{str(e)}"

            # Show the friendly error message
            ModernMessagebox("Connection Failed", friendly_msg, "error")

    def prev_step(self):
        self.show_step(self.current_step - 1)
    
    def save(self):
        college = self.controller.shared_data["college_name"]
        tech = self.db_tech.get()
        host = self.host.get()
        port = self.port.get()
        db = self.db_name.get()
        user = self.user.get()
        pwd = self.pwd.get()
        
        mapping = {
            "tbl_student": self.t_stud.get(), 
            "tbl_academic": self.t_acad.get(), 
            "tbl_branch": self.t_bran.get(), 
            "col_student_join": self.k_stud.get(), 
            "col_branch_join": self.k_bran.get(), 
            "col_id": self.c_id.get(), 
            "col_name": self.c_na.get(), 
            "col_branch_name": self.c_br.get(), 
            "col_att": self.c_at.get(), 
            "col_marks": self.c_mk.get(), 
            "col_backlogs": self.c_bk.get(), 
            "col_year": "year", 
            "col_email": "email"
        }
        
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
            self.dash.on_show()

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
        self.erp = ERPWizard(self, controller, self)

    def on_show(self):
        self.sidebar.refresh()
        needed = self.controller.shared_data.get("erp_setup_needed")
        
        if needed:
            self.erp.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.sidebar.grid_forget()
        else:
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.show_view("Analytics")

    def show_view(self, name):
        self.analytics.grid_forget()
        self.faculty.grid_forget()
        self.erp.grid_forget()
        
        if name == "Analytics":
            self.analytics.grid(row=0, column=1, sticky="nsew")
            self.analytics.refresh()
        elif name == "Faculty":
            self.faculty.grid(row=0, column=1, sticky="nsew")
            self.faculty.refresh()

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