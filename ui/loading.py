"""
AcaDesk Loading Screen — Startup Initialization Gate
======================================================
Displayed after successful login and before the Dashboard opens.

This screen is the ONLY entry point to the Dashboard.
The Dashboard will never open until this screen reports SUCCESS.

Flow:
  Login → LoadingScreen → (SyncWorker runs) → DashboardScreen
                                             ↘ Error state (Retry / Return to Login)

Architecture constraints:
  - All UI updates from the background thread are dispatched via self.after()
  - SyncWorker is started here; Dashboard is never responsible for syncing
  - This frame is registered in the main app's frame dictionary
"""

from __future__ import annotations
import logging
import math
import customtkinter as ctk
from ui.styles import COLORS, FONTS

_log = logging.getLogger(__name__)

# Progress stage definitions — (progress_value, label_text)
STAGES = [
    (0.00, "Initializing"),
    (0.10, "Validating ERP Connection"),
    (0.20, "Validating Schema Mapping"),
    (0.35, "Analysing Database Schema"),
    (0.50, "Retrieving Student Records"),
    (0.70, "Loading Academic History"),
    (0.85, "Building Session Cache"),
    (0.90, "Running AI Risk Analysis"),
    (0.95, "Validating Cache Integrity"),
    (1.00, "Ready — Launching Dashboard"),
]


class LoadingScreen(ctk.CTkFrame):
    """
    Professional startup initialization screen.
    Blocks Dashboard access until cache sync is fully validated.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLORS["bg"])
        self.controller = controller
        self._anim_angle = 0
        self._anim_running = False
        self._current_progress = 0.0
        self._target_progress = 0.0
        self._error_state = False

        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ── Background subtle grid texture ────────────────────────────
        self.configure(fg_color=COLORS["bg"])

        # ── Central card ──────────────────────────────────────────────
        card = ctk.CTkFrame(
            self,
            width=620,
            height=420,
            fg_color=COLORS["card"],
            corner_radius=20,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        # ── Logo / wordmark ──────────────────────────────────────────
        logo_frame = ctk.CTkFrame(card, fg_color="transparent")
        logo_frame.pack(pady=(42, 0))

        ctk.CTkLabel(
            logo_frame,
            text="AcaDesk",
            font=("Outfit", 38, "bold"),
            text_color=COLORS["accent"],
        ).pack(side="left")

        ctk.CTkLabel(
            logo_frame,
            text=" ™",
            font=("Outfit", 14),
            text_color=COLORS["text_gray"],
        ).pack(side="left", anchor="s", pady=(0, 8))

        ctk.CTkLabel(
            card,
            text="INITIALIZING SYSTEM",
            font=("Roboto", 11, "bold"),
            text_color=COLORS["text_gray"],
        ).pack(pady=(0, 28))

        # ── Spinner canvas ───────────────────────────────────────────
        self._spinner_canvas = ctk.CTkCanvas(
            card, width=48, height=48,
            bg=COLORS["card"], highlightthickness=0
        )
        self._spinner_canvas.pack(pady=(0, 16))

        # ── Stage label ──────────────────────────────────────────────
        self._lbl_stage = ctk.CTkLabel(
            card,
            text="Connecting…",
            font=("Roboto", 13, "bold"),
            text_color=COLORS["text"],
        )
        self._lbl_stage.pack()

        # ── Progress bar ─────────────────────────────────────────────
        prog_frame = ctk.CTkFrame(card, fg_color="transparent")
        prog_frame.pack(pady=14)

        self._progressbar = ctk.CTkProgressBar(
            prog_frame,
            width=480,
            height=6,
            progress_color=COLORS["accent"],
            fg_color=COLORS["border"],
            corner_radius=3,
        )
        self._progressbar.set(0)
        self._progressbar.pack()

        # ── Detail sub-label ─────────────────────────────────────────
        self._lbl_detail = ctk.CTkLabel(
            card,
            text="",
            font=("Roboto", 11),
            text_color=COLORS["text_gray"],
        )
        self._lbl_detail.pack(pady=(4, 0))

        # ── Percentage label ─────────────────────────────────────────
        self._lbl_pct = ctk.CTkLabel(
            card,
            text="0%",
            font=("Roboto", 11, "bold"),
            text_color=COLORS["accent"],
        )
        self._lbl_pct.pack(pady=(2, 0))

        # ── Error panel (hidden by default) ──────────────────────────
        self._error_panel = ctk.CTkFrame(
            card,
            fg_color="#1A0A0A",
            corner_radius=10,
            border_width=1,
            border_color=COLORS["danger"],
        )
        # Not packed yet — shown only on error

        self._lbl_error = ctk.CTkLabel(
            self._error_panel,
            text="",
            font=("Roboto", 12),
            text_color=COLORS["danger"],
            wraplength=440,
            justify="center",
        )
        self._lbl_error.pack(padx=20, pady=(18, 10))

        btn_row = ctk.CTkFrame(self._error_panel, fg_color="transparent")
        btn_row.pack(pady=(0, 18))

        self._btn_retry = ctk.CTkButton(
            btn_row,
            text="↻  Retry",
            width=150,
            height=38,
            fg_color=COLORS["accent"],
            text_color="black",
            hover_color="#00B3CC",
            font=("Outfit", 13, "bold"),
            corner_radius=8,
            command=self._on_retry,
        )
        self._btn_retry.pack(side="left", padx=10)

        self._btn_back = ctk.CTkButton(
            btn_row,
            text="← Return to Login",
            width=160,
            height=38,
            fg_color="transparent",
            text_color=COLORS["text_gray"],
            hover_color=COLORS["border"],
            font=("Roboto", 12),
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            command=self._on_return_to_login,
        )
        self._btn_back.pack(side="left", padx=10)

        # Store card reference for error toggling
        self._card = card

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_show(self):
        """Called by the main app when this frame becomes visible."""
        self._reset_ui()
        self._start_spinner()
        self._start_sync()

    def _reset_ui(self):
        """Resets all UI elements to their initial loading state."""
        self._error_state = False
        self._current_progress = 0.0
        self._target_progress = 0.0
        self._progressbar.set(0)
        self._lbl_stage.configure(text="Connecting…", text_color=COLORS["text"])
        self._lbl_detail.configure(text="")
        self._lbl_pct.configure(text="0%")
        self._error_panel.pack_forget()

    # ------------------------------------------------------------------
    # Spinner Animation
    # ------------------------------------------------------------------

    def _start_spinner(self):
        self._anim_angle = 0
        self._anim_running = True
        self._animate_spinner()

    def _stop_spinner(self):
        self._anim_running = False

    def _animate_spinner(self):
        if not self._anim_running:
            return
        canvas = self._spinner_canvas
        canvas.delete("all")
        cx, cy, r = 24, 24, 18
        # Draw background circle
        canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=0, extent=359,
            outline=COLORS["border"], width=3, style="arc"
        )
        # Draw spinning arc
        start_angle = self._anim_angle % 360
        canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=start_angle, extent=90,
            outline=COLORS["accent"], width=3, style="arc"
        )
        self._anim_angle = (self._anim_angle + 6) % 360

        # Smooth progress bar animation
        if self._current_progress < self._target_progress:
            self._current_progress = min(
                self._target_progress,
                self._current_progress + 0.005
            )
            self._progressbar.set(self._current_progress)
            self._lbl_pct.configure(text=f"{int(self._current_progress * 100)}%")

        self.after(30, self._animate_spinner)

    # ------------------------------------------------------------------
    # Sync Worker Integration
    # ------------------------------------------------------------------

    def _start_sync(self):
        """Instantiates and starts the SyncWorker."""
        erp_config = self.controller.shared_data.get("erp_config")
        if not erp_config:
            self._show_error("No ERP configuration found. Please complete the ERP setup wizard.")
            return

        from logic.sync_worker import SyncWorker
        worker = SyncWorker(erp_config, self.controller.shared_data)

        def on_progress(progress: float, msg: str):
            self.after(0, lambda p=progress, m=msg: self._on_progress(p, m))

        def on_finished(result):
            self.after(0, lambda r=result: self._on_finished(r))

        worker.connect_progress(on_progress)
        worker.connect_finished(on_finished)
        worker.start()

    def _on_progress(self, progress: float, msg: str):
        """Receives progress updates from the SyncWorker thread (via after)."""
        if self._error_state:
            return
        self._target_progress = min(1.0, progress)
        self._lbl_stage.configure(text=msg)
        # Pick the most relevant stage label
        for threshold, label in reversed(STAGES):
            if progress >= threshold:
                self._lbl_detail.configure(text=label)
                break

    def _on_finished(self, result):
        """Receives the final SyncResult from the SyncWorker thread (via after)."""
        from logic.sync_worker import SyncResult
        if result.is_success:
            self._stop_spinner()
            self._target_progress = 1.0
            self._current_progress = 1.0
            self._progressbar.set(1.0)
            self._lbl_pct.configure(text="100%")
            self._lbl_stage.configure(
                text=f"Ready — {result.student_count} students loaded",
                text_color=COLORS["success"]
            )
            self._lbl_detail.configure(text="Launching dashboard…")
            # Short delay so the user sees "Ready" before the transition
            self.after(600, lambda: self.controller.show_frame("DashboardScreen"))
        else:
            self._stop_spinner()
            self._show_error(result)

    # ------------------------------------------------------------------
    # Error State
    # ------------------------------------------------------------------

    def _show_error(self, result):
        """Switches the loading card into error display mode."""
        self._error_state = True
        
        err_detail = getattr(result, 'error_details', None)
        title = "Initialization Failed"
        body = result.message
        tech_text = ""
        is_recoverable = False
        
        if err_detail:
            if err_detail.step == "branch_fetch":
                title = "Department Data Unavailable"
            elif err_detail.step == "schema_validation":
                title = "Schema Mapping Error"
            body = err_detail.message
            tech_text = err_detail.technical
            is_recoverable = err_detail.is_recoverable
            
        self._lbl_stage.configure(
            text=title,
            text_color=COLORS["danger"]
        )
        self._lbl_detail.configure(text=tech_text[:100] + "..." if len(tech_text) > 100 else tech_text)
        self._lbl_error.configure(text=f"{body}\n\nTechnical Details: {tech_text}" if tech_text else body)
        
        if is_recoverable:
            self._btn_retry.configure(text="⚙ Setup Schema", command=self._on_setup_schema)
        else:
            self._btn_retry.configure(text="↻ Retry", command=self._on_retry)
            
        self._error_panel.pack(fill="x", padx=30, pady=(10, 0))

    def _on_setup_schema(self):
        _log.info("[LoadingScreen] User navigating to Schema Setup.")
        self._stop_spinner()
        # Ensure we flag setup as needed
        self.controller.shared_data["erp_setup_needed"] = True
        self.controller.show_frame("ERPWizard")

    def _on_retry(self):
        """Re-attempts the full sync sequence."""
        _log.info("[LoadingScreen] User clicked Retry.")
        self._reset_ui()
        self._start_spinner()
        self._start_sync()

    def _on_return_to_login(self):
        """Returns the user to the login screen without opening Dashboard."""
        _log.info("[LoadingScreen] User returned to login.")
        self._stop_spinner()
        self.controller.show_frame("WelcomeScreen")
