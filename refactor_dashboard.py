import re

def extract_methods(lines, method_names):
    extracted = []
    remaining = []
    in_method = False
    current_method = ""
    for line in lines:
        match = re.match(r'^    def ([a-zA-Z0-9_]+)\(', line)
        if match:
            if match.group(1) in method_names:
                in_method = True
                current_method = match.group(1)
            else:
                in_method = False
        
        if in_method:
            extracted.append(line)
        else:
            remaining.append(line)
    return extracted, remaining

with open('ui/dashboard.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

list_methods = [
    'show_student_list', '_create_pill_btn', 'apply_filter', '_update_filter_visuals',
    'filter_list', '_process_filter_list', '_render_filtered_list', '_draw_modern_row'
]
detail_methods = [
    'open_deep_analysis', '_open_edit_contact_dialog', '_open_notify_parent_dialog',
    'export_report', 'add_line', '_profile_badge'
]
insights_methods = [
    '_draw_admin_charts', '_render_dept_analytics'
]

# We must only extract from within AnalyticsPanel class
start = -1
end = -1
for i, line in enumerate(lines):
    if line.startswith('class AnalyticsPanel'):
        start = i
    elif start != -1 and line.startswith('class '):
        end = i
        break

if end == -1: end = len(lines)

panel_lines = lines[start:end]

# Extract
list_lines, panel_lines = extract_methods(panel_lines, list_methods)
detail_lines, panel_lines = extract_methods(panel_lines, detail_methods)
insights_lines, panel_lines = extract_methods(panel_lines, insights_methods)

# Reconstruct
new_lines = lines[:start] + panel_lines + lines[end:]

def write_mixin(filename, classname, mixin_lines):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("import customtkinter as ctk\n")
        f.write("from tkinter import messagebox, Toplevel, scrolledtext\n")
        f.write("import pandas as pd\n")
        f.write("import time\n")
        f.write("import os\n")
        f.write("from matplotlib.figure import Figure\n")
        f.write("from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg\n")
        f.write("from ui.styles import COLORS, FONTS, DIMS\n")
        f.write("try:\n    from ui.trend_visuals import TrendVisuals\nexcept ImportError:\n    pass\n\n")
        f.write(f"class {classname}:\n")
        if not mixin_lines:
            f.write("    pass\n")
        else:
            for l in mixin_lines:
                f.write(l)

write_mixin('ui/dashboard_student_list.py', 'StudentListMixin', list_lines)
write_mixin('ui/dashboard_student_detail.py', 'StudentDetailMixin', detail_lines)
write_mixin('ui/dashboard_insights.py', 'InsightsMixin', insights_lines)

# Update AnalyticsPanel class definition in new_lines
for i, line in enumerate(new_lines):
    if line.startswith('class AnalyticsPanel('):
        new_lines[i] = 'class AnalyticsPanel(ctk.CTkFrame, StudentListMixin, StudentDetailMixin, InsightsMixin):\n'
        break

# Prepend imports to dashboard.py
imports = "from ui.dashboard_student_list import StudentListMixin\nfrom ui.dashboard_student_detail import StudentDetailMixin\nfrom ui.dashboard_insights import InsightsMixin\n"

with open('ui/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(imports + "".join(new_lines))

print("Dashboard refactored!")
