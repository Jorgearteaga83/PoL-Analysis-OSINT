import os
import re

def get_comment_for_line(line):
    stripped = line.strip()
    if not stripped or stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
        return None
    
    # Try to match patterns
    if re.match(r'^import\s+', stripped) or re.match(r'^from\s+[\w\.]+\s+import\s+', stripped):
        return "Import necessary module or component"
    if m := re.match(r'^def\s+([\w_]+)', stripped):
        return f"Define function {m.group(1)}"
    if m := re.match(r'^class\s+([\w_]+)', stripped):
        return f"Define class {m.group(1)}"
    if re.match(r'^if\s+', stripped):
        return "Check conditional statement"
    if re.match(r'^elif\s+', stripped):
        return "Check alternative condition"
    if re.match(r'^else\s*:', stripped):
        return "Execute if preceding conditions are false"
    if re.match(r'^for\s+', stripped):
        return "Iterate in a loop"
    if re.match(r'^while\s+', stripped):
        return "Loop while condition is met"
    if re.match(r'^try\s*:', stripped):
        return "Start of try block for exception handling"
    if re.match(r'^except\s*', stripped):
        return "Handle specific exceptions"
    if re.match(r'^finally\s*:', stripped):
        return "Execute cleanup code regardless of exceptions"
    if re.match(r'^return\s+', stripped) or stripped == 'return':
        return "Return value from function"
    if re.match(r'^yield\s+', stripped):
        return "Yield value for generator"
    if re.match(r'^print\(', stripped):
        return "Output information to console"
    if stripped == 'pass':
        return "No-op placeholder"
    if stripped == 'continue':
        return "Skip to next loop iteration"
    if stripped == 'break':
        return "Exit the current loop"
    if re.match(r'^with\s+', stripped):
        return "Use context manager"
    if re.match(r'^assert\s+', stripped):
        return "Assert a condition holds true"
    if re.match(r'^raise\s+', stripped):
        return "Raise an exception"
    if re.match(r'^global\s+', stripped) or re.match(r'^nonlocal\s+', stripped):
        return "Declare variable scope"
    if m := re.match(r'^([a-zA-Z_][\w\.\'\"\[\]]*)\s*([+\-*/%&|^]?=)\s*(.*)', stripped):
        return f"Assign value to {m.group(1)}"
    if re.match(r'^self\.[\w_]+\s*\(', stripped):
        return "Call instance method"
    if m := re.match(r'^([\w_]+)\s*\(', stripped):
        return f"Call function {m.group(1)}"
    if re.match(r'^@[\w_]+', stripped):
        return "Apply decorator"
    if stripped.endswith(']') or stripped.endswith('}') or stripped.endswith(')'):
        return "Close bracket/parenthesis"
    if stripped.startswith(']') or stripped.startswith('}') or stripped.startswith(')'):
        return "Close structure"
    
    return "Execute statement or expression"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    in_multiline_string = False
    for line in lines:
        stripped = line.strip()
        
        # Simple multiline string tracking
        str_count = stripped.count('"""') + stripped.count("'''")
        if str_count % 2 != 0:
            in_multiline_string = not in_multiline_string
            
        if in_multiline_string or (str_count % 2 != 0 and not in_multiline_string):
            new_lines.append(line)
            continue
            
        comment = get_comment_for_line(line)
        # Avoid lines that already have a comment
        if comment and not re.search(r'#.*', line):
            clean_line = line.rstrip()
            # Calculate indent
            indent = line[:len(line) - len(line.lstrip())]
            
            # If line is too long, add comment above
            if len(clean_line) > 100:
                new_lines.append(f"{indent}# {comment}\n")
                new_lines.append(line)
            else:
                # Add comment at the end
                new_lines.append(f"{clean_line}  # {comment}\n")
        else:
            new_lines.append(line)
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def find_and_process():
    root_dir = r"c:\Users\Lenovo ThinkPad\OneDrive - University of Greenwich\Year 4\POL OSINT toll github\PoL-Analysis-OSINT"
    exclude_dirs = {'venv', '.idea', '.git', '.pytest_cache'}
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for filename in filenames:
            if filename.endswith('.py') and filename != 'add_comments.py':
                filepath = os.path.join(dirpath, filename)
                try:
                    process_file(filepath)
                    print(f"Processed {filepath}")
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

if __name__ == '__main__':
    find_and_process()