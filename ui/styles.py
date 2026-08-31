# ui/styles.py
import customtkinter as ctk

# --- COLOR PALETTE ---
COLORS = {
    "bg": "#0B0E14",             # Main Background
    "sidebar": "#12141E",        # Sidebar Background
    "card": "#151A22",           # Card/Box Background
    "border": "#2A2E3F",         # Border Color
    "accent": "#00E5FF",         # Cyan Highlight
    "text": "#FFFFFF",           # Main Text
    "text_gray": "#8B949E",      # Subtitle Text
    "danger": "#FF1744",         # Red (High Risk)
    "warning": "#FFEA00",        # Yellow/Orange (Med Risk)
    "success": "#00E676",        # Green (Safe)
    "input_bg": "#1A1D2D",       # Entry Box Background
}

# --- FONTS ---
FONTS = {
    "h1": ("Montserrat", 24, "bold"),
    "h2": ("Roboto", 20, "bold"),
    "h3": ("Roboto", 16, "bold"),
    "body": ("Roboto", 12),
    "code": ("Consolas", 12),
    "badge": ("Arial", 10, "bold"),
    "caption": ("Roboto", 11),
}

# --- LAYOUT DIMENSIONS ---
DIMS = {
    "sidebar_width": 250,
    "card_height": 60,
    "btn_height": 42,
}

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

