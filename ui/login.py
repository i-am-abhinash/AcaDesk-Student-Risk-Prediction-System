import customtkinter as ctk
from tkinter import messagebox

# --- CONSTANTS ---
BG_COLOR = "#050505"
CARD_COLOR = "#141414"
INPUT_BG = "#1F1F1F"
ACCENT_CYAN = "#00E5FF"

# (Placeholder LoginScreen class to prevent any import errors if it's referenced, 
# though your main.py uses WelcomeScreen)
class LoginScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)

# --- REFINED REGISTER SCREEN (Big) - EXACTLY AS YOU UPLOADED ---
class RegisterScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=BG_COLOR)

        self.card = ctk.CTkFrame(self, width=550, height=700, corner_radius=10, fg_color=CARD_COLOR)
        self.card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(self.card, text="NEW NODE SETUP", font=("Arial", 24, "bold"), text_color="white").pack(pady=(50, 5))
        ctk.CTkLabel(self.card, text="Initialize College Administrator", text_color="gray", font=("Roboto", 14)).pack(pady=(0, 40))

        # Form Fields
        self.college = self.make_input("College Name")
        self.u = self.make_input("Admin Username")
        self.p = self.make_input("Secure Password", show="*")
        self.code = self.make_input("Confirm Password", show="*") # Changed to Confirm Password for functionality

        ctk.CTkButton(self.card, text="REGISTER ADMIN", width=360, height=55, corner_radius=6, 
                      fg_color="#00E5FF", text_color="black", font=("Roboto Black", 14), 
                      command=self.do_register).pack(pady=40)
        
        ctk.CTkButton(self.card, text="Cancel", fg_color="transparent", text_color="gray", hover_color="#222", font=("Roboto", 12),
                      command=lambda: controller.show_frame("WelcomeScreen")).pack()

    def make_input(self, placeholder, show=None):
        entry = ctk.CTkEntry(self.card, placeholder_text=placeholder, width=360, height=50, corner_radius=6,
                             fg_color=INPUT_BG, border_color="#333", text_color="white", show=show,
                             font=("Roboto", 14))
        entry.pack(pady=10)
        return entry

    def do_register(self):
        college_val = self.college.get().strip()
        u_val = self.u.get().strip()
        p_val = self.p.get()
        conf_val = self.code.get()

        if not u_val or not p_val or not college_val:
            messagebox.showwarning("Incomplete", "All fields are required.")
            return
            
        if p_val != conf_val:
            messagebox.showwarning("Error", "Passwords do not match.")
            return

        try:
            from logic.central_auth import CentralAuth
            auth = CentralAuth()
            
            # The backend now returns False if the college already has an admin
            success, msg = auth.register_admin(college_val, u_val, p_val)
            
            if success:
                self.controller.shared_data["username"] = u_val
                self.controller.shared_data["user_type"] = "Admin"
                self.controller.shared_data["college_name"] = college_val
                self.controller.shared_data["erp_setup_needed"] = True
                
                messagebox.showinfo("Success", f"Node Registered for {college_val}.\nRedirecting to ERP Connection Wizard...")
                self.controller.show_frame("DashboardScreen")
            else:
                # This will now display the specific "An Administrator is already registered" message
                messagebox.showerror("Registration Denied", msg)
            
        except Exception as e:
            messagebox.showerror("System Error", f"Critical Failure: {str(e)}")