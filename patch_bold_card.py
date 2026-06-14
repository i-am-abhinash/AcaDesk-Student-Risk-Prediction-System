import re

dashboard_path = r"d:\AcaDesk1\ui\dashboard.py"
with open(dashboard_path, "r", encoding="utf-8") as f:
    content = f.read()

new_card_code = """
class SelectionCard(ctk.CTkFrame):
    def __init__(self, parent, primary_text, secondary_text, command=None, *args, **kwargs):
        super().__init__(parent, fg_color=COLORS["card"], corner_radius=5, *args, **kwargs)
        self.command = command
        
        # Left Accent Bar
        self.accent_bar = ctk.CTkFrame(self, fg_color="#00E5FF", width=6, corner_radius=0)
        self.accent_bar.pack(side="left", fill="y")
        
        # Content Container
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(side="left", fill="both", expand=True, padx=(15, 20), pady=25)
        
        self.lbl_primary = ctk.CTkLabel(self.content_frame, text=primary_text, font=("Arial", 20, "bold"), text_color="#00E5FF", anchor="w")
        self.lbl_primary.pack(fill="x", pady=(0, 5))
        
        self.lbl_secondary = ctk.CTkLabel(self.content_frame, text=secondary_text, font=("Arial", 12), text_color="#888", anchor="w")
        self.lbl_secondary.pack(fill="x")
        
        # Apply hover events to everything
        widgets = [self, self.accent_bar, self.content_frame, self.lbl_primary, self.lbl_secondary]
        for w in widgets:
            w.bind("<Enter>", self.on_enter)
            w.bind("<Leave>", self.on_leave)
            w.bind("<Button-1>", self.on_click)
            
    def on_enter(self, event):
        # Striking 'active' hover state
        self.configure(fg_color="#00E5FF")
        self.content_frame.configure(fg_color="#00E5FF")
        self.lbl_primary.configure(text_color="#000000")
        self.lbl_secondary.configure(text_color="#222222")
        
    def on_leave(self, event):
        # Revert to standard state
        self.configure(fg_color=COLORS["card"])
        self.content_frame.configure(fg_color="transparent")
        self.lbl_primary.configure(text_color="#00E5FF")
        self.lbl_secondary.configure(text_color="#888")
        
    def on_click(self, event):
        if self.command:
            self.command()
"""

# Extract the old SelectionCard class
pattern = re.compile(r'class SelectionCard\(ctk\.CTkFrame\):.*?def on_click\(self, event\):\s*if self\.command:\s*self\.command\(\)', re.DOTALL)

content = pattern.sub(new_card_code.strip(), content)

with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Bold Left-Accent Card applied.")
