import os
import re

def fix_bare_excepts(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # We need to replace `except:` with `except Exception as e: print(f"Error in {file_path}: {e}");`
    # However, Python formatting matters. If it's `except: pass`, it becomes `except Exception as e: print(f"Error: {e}"); pass`
    # If it's `except: return None`, it becomes `except Exception as e: print(f"Error: {e}"); return None`
    # If it's just `except:\n`, it becomes `except Exception as e:\n    print(f"Error: {e}")\n`
    
    # Let's do this line by line to preserve indentation
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        if re.search(r'^\s*except:\s*$', line):
            # Bare except on its own line
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}except Exception as e:")
            new_lines.append(f"{indent}    print(f\"Exception caught: {{e}}\")")
        elif re.search(r'^\s*except:\s+(.*)$', line):
            # Bare except with statement on same line
            match = re.search(r'^(\s*)except:\s+(.*)$', line)
            indent = match.group(1)
            stmt = match.group(2)
            new_lines.append(f"{indent}except Exception as e:")
            new_lines.append(f"{indent}    print(f\"Exception caught: {{e}}\")")
            new_lines.append(f"{indent}    {stmt}")
        else:
            new_lines.append(line)
            
    new_content = '\n'.join(new_lines)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {file_path}")

target_files = [
    "logic/central_auth.py",
    "logic/config_manager.py",
    "logic/db_handler.py",
    "logic/encryption.py",
    "logic/first_year_predictor.py",
    "logic/risk_engine.py",
    "ui/insight_center.py"
]

for tf in target_files:
    path = os.path.join("D:/AcaDesk1", tf)
    if os.path.exists(path):
        fix_bare_excepts(path)
