import customtkinter as ctk
from logic.central_auth import CentralAuth
from ui.styles import COLORS, FONTS

class NotesArchivePanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=COLORS["bg"])
        self.controller = controller
        self.ca = CentralAuth()
        
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(self, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 5))
        
        ctk.CTkLabel(header, text="📝 Notes Archive", font=("Outfit", 24, "bold"), text_color="#00E5FF").pack(side="left", padx=20, pady=15)
        
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        self.stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # We will populate the stats cards dynamically in refresh()
        self.stat_cards = []
        for i in range(3):
            c = ctk.CTkFrame(self.stats_frame, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
            c.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            lbl_title = ctk.CTkLabel(c, text="Loading...", text_color="#7A849C", font=("Inter", 13))
            lbl_title.pack(pady=(15, 5))
            lbl_val = ctk.CTkLabel(c, text="-", text_color="white", font=("Outfit", 28, "bold"))
            lbl_val.pack(pady=(0, 15))
            self.stat_cards.append((lbl_title, lbl_val))
        
        self.btn_refresh = ctk.CTkButton(header, text="🔄 Refresh", font=("Inter", 13, "bold"), fg_color="#1A1D2D", border_width=1, border_color="#2A2E3F", hover_color="#2A2E3F", width=100, corner_radius=6, command=self.refresh)
        self.btn_refresh.pack(side="right", padx=20, pady=15)
        
        # Search / Filter Bar
        search_f = ctk.CTkFrame(self, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
        search_f.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        
        ctk.CTkLabel(search_f, text="🔍 Search:", font=("Inter", 13, "bold"), text_color="#7A849C").pack(side="left", padx=15, pady=15)
        
        self.entry_student_id = ctk.CTkEntry(search_f, placeholder_text="Student Reg No...", width=160, fg_color="#1A1D2D", border_width=0, corner_radius=6)
        self.entry_student_id.pack(side="left", padx=10)
        
        self.entry_branch = ctk.CTkEntry(search_f, placeholder_text="Branch (e.g. CSE)...", width=160, fg_color="#1A1D2D", border_width=0, corner_radius=6)
        self.entry_branch.pack(side="left", padx=10)
        
        self.btn_search = ctk.CTkButton(search_f, text="Search", width=90, fg_color="#00E5FF", text_color="black", font=("Inter", 12, "bold"), hover_color="#00B3CC", corner_radius=6, command=self.refresh)
        self.btn_search.pack(side="left", padx=10)
        
        self.btn_clear = ctk.CTkButton(search_f, text="Clear", width=90, fg_color="#1A1D2D", text_color="white", font=("Inter", 12, "bold"), hover_color="#2A2E3F", corner_radius=6, command=self.clear_search)
        self.btn_clear.pack(side="left", padx=10)
        
        # List Area
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        
    def clear_search(self):
        self.entry_student_id.delete(0, "end")
        self.entry_branch.delete(0, "end")
        self.refresh()

    def refresh(self):
        for w in self.scroll.winfo_children(): w.destroy()
        
        user_type = self.controller.shared_data.get("user_type", "Faculty")
        
        if user_type == "Admin":
            notes = self.ca.get_all_notes()
        else:
            dept = self.controller.shared_data.get("assigned_department")
            if not dept:
                fac_usr = self.controller.shared_data.get("username", "Unknown")
                all_n = self.ca.get_all_notes()
                notes = [n for n in all_n if n.get('faculty_username') == fac_usr]
            else:
                erp_conf = self.controller.shared_data.get("erp_config")
                if erp_conf:
                    from logic.db_handler import DBHandler
                    db = DBHandler(erp_conf)
                    b_map = db.get_branch_map()
                    b_name = b_map.get(int(dept)) or b_map.get(str(dept)) or str(dept)
                    notes = self.ca.get_notes_by_department(b_name)
                    db.close()
                else:
                    notes = []
                
        # Apply filters
        q_sid = self.entry_student_id.get().strip().upper()
        q_branch = self.entry_branch.get().strip().upper()
        
        filtered_notes = []
        for n in notes:
            n_sid = str(n.get('student_id', '')).upper()
            n_br = str(n.get('department', '')).upper()
            
            if q_sid and q_sid not in n_sid:
                continue
            if q_branch and q_branch not in n_br:
                continue
            filtered_notes.append(n)
            
        notes = filtered_notes
            
        if not notes:
            self.stat_cards[0][0].configure(text="Total Notes")
            self.stat_cards[0][1].configure(text="0", text_color="#bb86fc")
            self.stat_cards[1][0].configure(text="Students Noted")
            self.stat_cards[1][1].configure(text="0", text_color="#bb86fc")
            self.stat_cards[2][0].configure(text="Faculty Authors")
            self.stat_cards[2][1].configure(text="0", text_color="#bb86fc")
            
            ctk.CTkLabel(self.scroll, text="No faculty notes found.", text_color="#777").pack(pady=40)
            return
            
        students_set = set()
        faculty_set = set()
        for n in notes:
            if 'student_id' in n: students_set.add(n['student_id'])
            if 'faculty_username' in n: faculty_set.add(n['faculty_username'])
            
        self.stat_cards[0][0].configure(text="Total Notes")
        self.stat_cards[0][1].configure(text=str(len(notes)), text_color="#B388FF")
        self.stat_cards[1][0].configure(text="Monitored Students")
        self.stat_cards[1][1].configure(text=str(len(students_set)), text_color="#B388FF")
        self.stat_cards[2][0].configure(text="Active Faculty")
        self.stat_cards[2][1].configure(text=str(len(faculty_set)), text_color="#B388FF")
        for n in notes:
            # Chat-style bubble
            b_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
            b_frame.pack(fill="x", pady=8, padx=10)
            
            st = n.get('note_status', 'ACTIVE')
            if st == 'CRITICAL': c = "#FF1744"
            elif st == 'FOLLOW_UP': c = "#FFEA00"
            elif st == 'ACTIVE': c = "#00E676"
            else: c = "#00E5FF"
            
            card = ctk.CTkFrame(b_frame, fg_color="#12141E", corner_radius=12, border_width=1, border_color="#2A2E3F")
            card.pack(fill="x", ipadx=5, ipady=5)
            
            def on_enter(e, c=card): c.configure(border_color="#00E5FF")
            def on_leave(e, c=card): c.configure(border_color="#2A2E3F")
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            
            # Header of note
            t_f = ctk.CTkFrame(card, fg_color="transparent")
            t_f.pack(fill="x", padx=15, pady=(10,0))
            
            author = n.get('faculty_username', 'Unknown')
            student_id = n.get('student_id', 'Unknown')
            dt = n.get('created_at')
            dt_str = dt.strftime("%b %d, %Y %I:%M %p") if dt else "Unknown Date"
            dept_str = n.get('department', '')
            
            title_lbl = ctk.CTkLabel(t_f, text=f"{author} ({dept_str}) → Student: {student_id}", font=("Outfit", 14, "bold"), text_color="white")
            title_lbl.pack(side="left")
            dt_lbl = ctk.CTkLabel(t_f, text=f" • {dt_str}", font=("Inter", 12), text_color="#7A849C")
            dt_lbl.pack(side="left", padx=5)
            
            badge = ctk.CTkLabel(t_f, text=f" {st} ", font=("Inter", 10, "bold"), text_color="#000", fg_color=c, corner_radius=6)
            badge.pack(side="right", padx=(10,0))
            
            # Body of note
            body_txt = n.get('note_text', '')
            body_lbl = ctk.CTkLabel(card, text=body_txt, font=("Inter", 14), text_color="#E0E6ED", justify="left", wraplength=800)
            body_lbl.pack(anchor="w", padx=15, pady=(10, 15))
            
            for child in (t_f, title_lbl, dt_lbl, body_lbl):
                child.bind("<Enter>", on_enter)
                child.bind("<Leave>", on_leave)
            
            # Actions
            current_user = self.controller.shared_data.get("username", "Unknown")
            if current_user == author or user_type == "Admin":
                act_f = ctk.CTkFrame(card, fg_color="transparent")
                act_f.pack(fill="x", padx=15, pady=(0, 10))
                
                # Delete
                def delete_note(nid=n['id']):
                    from main import ModernAskYesNo
                    from ui.dashboard import ModernMessagebox
                    def on_confirm():
                        from logic.central_auth import CentralAuth
                        CentralAuth().delete_faculty_note(nid)
                        ModernMessagebox("Deleted", "Note successfully deleted.", "success")
                        # Refresh
                        self.refresh()
                    ModernAskYesNo("Confirm Delete", "Are you sure you want to delete this note?", on_confirm)
                        
                del_btn = ctk.CTkButton(act_f, text="DELETE", width=70, height=24, fg_color="transparent", border_width=1, border_color="#FF1744", text_color="#FF1744", font=("Inter", 11, "bold"), hover_color="#FF1744", corner_radius=6, command=delete_note)
                del_btn.pack(side="right")
                
                def btn_enter(e, b=del_btn): b.configure(text_color="white")
                def btn_leave(e, b=del_btn): b.configure(text_color="#FF1744")
                del_btn.bind("<Enter>", btn_enter)
                del_btn.bind("<Leave>", btn_leave)
