import os
import re

path = 'escolas/templates/escolas/dashboard.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Apply the same regex fix for split tags and missing spaces as before
def fix_tag(match):
    return match.group(0).replace('\n', ' ').replace('\r', '').replace('  ', ' ')

content = re.sub(r'\{% if .*?%\}', fix_tag, content, flags=re.DOTALL)

# Ensure the spaces are present for the operators
content = content.replace("selected_escola_id=='all'", "selected_escola_id == 'all'")
content = content.replace("selected_period==key", "selected_period == key")
content = content.replace("selected_escola_id==escola", "selected_escola_id == escola")

content = re.sub(r'(<option value="\{\{ escola\.pk \}\}"\s+)\{% if selected_escola_id == escola\.pk\|stringformat:"s"\s+\}(selected)\{% endif %\}', 
                 r'\1{% if selected_escola_id == escola.pk|stringformat:"s" %}selected{% endif %}', 
                 content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Arquivo de template limpo!")
