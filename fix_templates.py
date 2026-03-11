import os
import re

template_dir = r"d:\Student-Faculty-management\templates"

def fix_templates():
    pattern = re.compile(r'{%\s*if\s+([a-zA-Z0-9_.]+)\s*==\s*([a-zA-Z0-9_.]+)\s*%}')
    for root, dirs, files in os.walk(template_dir):
        for f in files:
            if f.endswith('.html'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                new_content = pattern.sub(r'{% if \1 == \2 %}', content)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    print(f"Fixed {path}")

if __name__ == "__main__":
    fix_templates()
