import os

files = ['main.py', 'ui/dashboard.py', 'ui/insight_center.py', 'ui/drilldown_view.py', 'ui/startup.py', 'ui/welcome.py']

for f in files:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        content = content.replace('fg_color="#1a1a1a"', 'fg_color=COLORS["card"]')
        content = content.replace('fg_color="#1A1A1A"', 'fg_color=COLORS["card"]')
        
        content = content.replace('button_color="#1a1a1a"', 'button_color=COLORS["card"]')
        content = content.replace('hover_color="#1a1a1a"', 'hover_color=COLORS["card"]')
        
        content = content.replace('border_color="#2a2a2a"', 'border_color=COLORS["border"]')
        content = content.replace('border_color="#333"', 'border_color=COLORS["border"]')
        content = content.replace('border_color="#333333"', 'border_color=COLORS["border"]')
        
        content = content.replace('set_facecolor("#1a1a1a")', 'set_facecolor(COLORS["card"])')

        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Updated {f}")
