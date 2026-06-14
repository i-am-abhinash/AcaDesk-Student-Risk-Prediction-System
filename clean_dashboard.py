import os

filepath = r"d:\AcaDesk1\ui\dashboard.py"
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.strip() == "# ====================================================" and "HOD MANAGER" in lines[lines.index(line)+1]:
        skip = True
        
    if skip and line.startswith("class AnalyticsPanel"):
        skip = False
        # Add back the Analytics Panel header which might have been eaten
        new_lines.append("# ====================================================\n")
        new_lines.append("#  ANALYTICS PANEL\n")
        new_lines.append("# ====================================================\n\n")

    if not skip:
        new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("HODManagerPanel removed.")
