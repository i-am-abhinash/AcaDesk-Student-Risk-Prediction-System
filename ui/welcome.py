import customtkinter as ctk

class WelcomeScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color="#050505")  # Deep Void Black

        # --- HERO SECTION ---
        hero_frame = ctk.CTkFrame(self, fg_color="transparent")
        hero_frame.place(relx=0.5, rely=0.45, anchor="center")

        # The "Brand"
        ctk.CTkLabel(hero_frame, text="AcaDesk", font=("Helvetica", 90, "bold"), 
                     text_color="#ffffff").pack()
        
        # Subtitle
        ctk.CTkLabel(hero_frame, text="ACADEMIC INTELLIGENCE ENGINE", font=("Roboto", 14, "bold"), 
                     text_color="#666666").pack(pady=(5, 50))

        # --- PROFESSIONAL BUTTONS ---
        btn_frame = ctk.CTkFrame(hero_frame, fg_color="transparent")
        btn_frame.pack()

        # 1. Admin Button (The "Ghost" Style - Sleek & Modern)
        self.create_modern_btn(btn_frame, "ADMINISTRATOR", 
                               fg_color="transparent", 
                               border_color="#ffffff", 
                               text_color="#ffffff",
                               hover_color="#1a1a1a",
                               cmd=lambda: self.safe_switch("Admin"))
        
        # Spacer
        ctk.CTkFrame(btn_frame, width=30, height=1, fg_color="transparent").pack(side="left")

        # 2. Faculty Button (The "Solid" Style - Trustworthy Blue)
        self.create_modern_btn(btn_frame, "FACULTY PORTAL", 
                               fg_color="#0056b3", 
                               border_color="#0056b3", 
                               text_color="#ffffff", 
                               hover_color="#004494",
                               cmd=lambda: self.safe_switch("Faculty"))

        # --- FOOTER ---
        footer = ctk.CTkFrame(self, height=40, fg_color="#0a0a0a")
        footer.pack(side="bottom", fill="x")
        
        # Status Indicators
        status_frame = ctk.CTkFrame(footer, fg_color="transparent")
        status_frame.pack(pady=10)
        
        self.create_status_dot(status_frame, "#00ff00", "System Operational")
        ctk.CTkLabel(status_frame, text="  |  ", text_color="#333").pack(side="left")
        self.create_status_dot(status_frame, "#00ccff", "Secure Connection")

    def create_modern_btn(self, parent, text, fg_color, border_color, text_color, hover_color, cmd):
        btn = ctk.CTkButton(parent, text=text, width=240, height=55, corner_radius=8,
                            fg_color=fg_color, 
                            border_width=2,
                            border_color=border_color,
                            text_color=text_color, 
                            font=("Roboto Medium", 13),
                            hover_color=hover_color,
                            command=cmd)
        btn.pack(side="left")

    def create_status_dot(self, parent, color, text):
        dot = ctk.CTkLabel(parent, text="●", text_color=color, font=("Arial", 10))
        dot.pack(side="left", padx=(0, 5))
        lbl = ctk.CTkLabel(parent, text=text, text_color="#555", font=("Roboto", 10, "bold"))
        lbl.pack(side="left")

    def safe_switch(self, u_type):
        self.controller.show_frame("LoginScreen", user_type=u_type)