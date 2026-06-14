import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class TrendVisuals:
    @staticmethod
    def create_trend_charts(parent, trend_info):
        """
        Generates 3 charts: Semester vs CGPA, Semester vs Attendance, Semester vs Backlogs
        and packs them into the given parent frame.
        """
        history = trend_info.get("history", [])
        if not history:
            return None
            
        semesters = [str(h.get('semester')) for h in history]
        cgpas = [float(h.get('cgpa', 0)) for h in history]
        atts = [float(h.get('attendance', 0)) for h in history]
        bkls = [float(h.get('backlogs', 0)) for h in history]
        
        # Dark theme configuration
        plt.style.use('dark_background')
        fig = Figure(figsize=(10, 3), dpi=100, facecolor='#1E1E1E')
        fig.subplots_adjust(wspace=0.4, bottom=0.2)
        
        # 1. CGPA Chart
        ax1 = fig.add_subplot(131, facecolor='#1E1E1E')
        ax1.plot(semesters, cgpas, marker='o', color='#00E5FF', linewidth=2, markersize=6)
        ax1.set_title("CGPA Trend", color='white', fontsize=10)
        ax1.set_xlabel("Semester", color='lightgray', fontsize=8)
        ax1.set_ylabel("CGPA", color='lightgray', fontsize=8)
        ax1.tick_params(colors='lightgray', labelsize=8)
        ax1.grid(True, linestyle='--', alpha=0.2, color='gray')
        ax1.set_ylim(0, 10.5)

        # 2. Attendance Chart
        ax2 = fig.add_subplot(132, facecolor='#1E1E1E')
        ax2.plot(semesters, atts, marker='s', color='#FF0055', linewidth=2, markersize=6)
        ax2.set_title("Attendance Trend", color='white', fontsize=10)
        ax2.set_xlabel("Semester", color='lightgray', fontsize=8)
        ax2.set_ylabel("Percentage (%)", color='lightgray', fontsize=8)
        ax2.tick_params(colors='lightgray', labelsize=8)
        ax2.grid(True, linestyle='--', alpha=0.2, color='gray')
        ax2.set_ylim(0, 105)

        # 3. Backlogs Chart
        ax3 = fig.add_subplot(133, facecolor='#1E1E1E')
        ax3.bar(semesters, bkls, color='#FFCC00', alpha=0.8, width=0.5)
        ax3.set_title("Backlogs per Semester", color='white', fontsize=10)
        ax3.set_xlabel("Semester", color='lightgray', fontsize=8)
        ax3.set_ylabel("Count", color='lightgray', fontsize=8)
        ax3.tick_params(colors='lightgray', labelsize=8)
        ax3.grid(True, linestyle='--', alpha=0.2, color='gray', axis='y')
        ax3.set_ylim(0, max(bkls + [3]) + 1)
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        return canvas
