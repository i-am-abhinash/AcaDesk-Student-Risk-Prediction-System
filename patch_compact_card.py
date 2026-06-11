import re

dashboard_path = r"d:\AcaDesk1\ui\dashboard.py"
with open(dashboard_path, "r", encoding="utf-8") as f:
    content = f.read()

new_card_code = """
class SelectionCard(ctk.CTkFrame):
    def __init__(self, parent, primary_text, secondary_text, command=None, *args, **kwargs):
        # Base minimalist card: compact, subtle border
        super().__init__(parent, fg_color="#181818", corner_radius=8, border_width=1, border_color="#2A2A2A", *args, **kwargs)
        self.command = command
        
        # Content Container (Compact Padding)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=12)
        
        # Modern, compact typography
        self.lbl_primary = ctk.CTkLabel(self.content_frame, text=primary_text, font=("Arial", 14, "bold"), text_color="#E0E0E0", anchor="w")
        self.lbl_primary.pack(fill="x", pady=(0, 2))
        
        self.lbl_secondary = ctk.CTkLabel(self.content_frame, text=secondary_text, font=("Arial", 11), text_color="#666666", anchor="w")
        self.lbl_secondary.pack(fill="x")
        
        # Apply hover events
        widgets = [self, self.content_frame, self.lbl_primary, self.lbl_secondary]
        for w in widgets:
            w.bind("<Enter>", self.on_enter)
            w.bind("<Leave>", self.on_leave)
            w.bind("<Button-1>", self.on_click)
            
    def on_enter(self, event):
        # Subtle modern hover state
        self.configure(fg_color="#222222", border_color="#00E5FF")
        self.lbl_primary.configure(text_color="#00E5FF")
        
    def on_leave(self, event):
        # Revert to standard state
        self.configure(fg_color="#181818", border_color="#2A2A2A")
        self.lbl_primary.configure(text_color="#E0E0E0")
        
    def on_click(self, event):
        if self.command:
            self.command()
"""

# Extract the old SelectionCard class
pattern = re.compile(r'class SelectionCard\(ctk\.CTkFrame\):.*?def on_click\(self, event\):\s*if self\.command:\s*self\.command\(\)', re.DOTALL)

content = pattern.sub(new_card_code.strip(), content)

with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Compact Modern Card applied.")
