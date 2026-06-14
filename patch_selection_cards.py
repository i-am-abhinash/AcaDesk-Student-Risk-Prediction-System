import re

dashboard_path = r"d:\AcaDesk1\ui\dashboard.py"
with open(dashboard_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Define SelectionCard class
selection_card_code = """
class SelectionCard(ctk.CTkFrame):
    def __init__(self, parent, primary_text, secondary_text, command=None, *args, **kwargs):
        super().__init__(parent, fg_color=COLORS["card"], corner_radius=10, border_width=1, border_color="#333", *args, **kwargs)
        self.command = command
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        
        self.lbl_primary = ctk.CTkLabel(self, text=primary_text, font=("Arial", 18, "bold"), text_color="#00E5FF")
        self.lbl_primary.pack(pady=(25, 5), padx=20)
        self.lbl_primary.bind("<Enter>", self.on_enter)
        self.lbl_primary.bind("<Leave>", self.on_leave)
        self.lbl_primary.bind("<Button-1>", self.on_click)
        
        self.lbl_secondary = ctk.CTkLabel(self, text=secondary_text, font=("Arial", 12), text_color="#aaa")
        self.lbl_secondary.pack(pady=(0, 25), padx=20)
        self.lbl_secondary.bind("<Enter>", self.on_enter)
        self.lbl_secondary.bind("<Leave>", self.on_leave)
        self.lbl_secondary.bind("<Button-1>", self.on_click)
        
    def on_enter(self, event):
        self.configure(fg_color="#1E1E1E", border_color="#00E5FF")
        self.lbl_primary.configure(text_color="#FFFFFF")
        
    def on_leave(self, event):
        self.configure(fg_color=COLORS["card"], border_color="#333")
        self.lbl_primary.configure(text_color="#00E5FF")
        
    def on_click(self, event):
        if self.command:
            self.command()

class AnalyticsPanel(ctk.CTkFrame):"""

content = content.replace("class AnalyticsPanel(ctk.CTkFrame):", selection_card_code)

# 2. Update show_branch_selection
branch_old = """        for i, bid in enumerate(branch_ids):
            name = self.translator.get_name(bid)
            btn = ctk.CTkButton(
                scroll, 
                text=name, 
                font=("Arial", 16, "bold"), 
                text_color="#00E5FF",
                height=80, 
                fg_color=COLORS["card"], 
                command=lambda b=bid: self.select_branch(b)
            )
            btn.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")"""

branch_new = """        for i, bid in enumerate(branch_ids):
            name = self.translator.get_name(bid)
            card = SelectionCard(
                scroll, 
                primary_text=name, 
                secondary_text="Department",
                command=lambda b=bid: self.select_branch(b)
            )
            card.grid(row=i//3, column=i%3, padx=15, pady=15, sticky="nsew")"""
content = content.replace(branch_old, branch_new)

# 3. Update show_year_selection
year_old = """        for i, yr in enumerate(YEARS):
            btn = ctk.CTkButton(
                grid, 
                text=yr, 
                font=("Arial", 18, "bold"), 
                text_color="#00E5FF",
                height=80, 
                fg_color=COLORS["card"], 
                command=lambda y=yr: self.select_year(y)
            )
            btn.grid(row=i//2, column=i%2, padx=20, pady=15, sticky="nsew")"""

year_new = """        year_labels = {
            "1st Year": "Foundation",
            "2nd Year": "Core Learning",
            "3rd Year": "Specialization",
            "4th Year": "Placement Stage"
        }
        for i, yr in enumerate(YEARS):
            desc = year_labels.get(yr, "Academic Year")
            card = SelectionCard(
                grid, 
                primary_text=yr, 
                secondary_text=desc,
                command=lambda y=yr: self.select_year(y)
            )
            card.grid(row=i//2, column=i%2, padx=20, pady=20, sticky="nsew")"""
content = content.replace(year_old, year_new)

with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch Selection Cards Applied")
