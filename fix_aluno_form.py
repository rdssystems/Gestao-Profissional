import os
import re

# 1. Update forms.py
forms_path = r"alunos\forms.py"
with open(forms_path, 'r', encoding='utf-8') as f:
    forms_cnt = f.read()

forms_cnt = forms_cnt.replace("'class': 'form-control'", "'class': 'form-control form-control-premium'")
forms_cnt = forms_cnt.replace("'class': 'form-select'", "'class': 'form-select form-select-premium'")
# Also ensure widget tweaks for CustomAuthenticationForm and AlunoCSVUploadForm or UserCreationForm
# Actually the simple string replace handles all instances of those exact strings in the file.

with open(forms_path, 'w', encoding='utf-8') as f:
    f.write(forms_cnt)

print("Updated forms.py")

# 2. Update aluno_form.html
html_path = r"alunos\templates\alunos\aluno_form.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html_cnt = f.read()

# Remove style block
html_cnt = re.sub(r'<style>.*?</style>\s*', '', html_cnt, flags=re.DOTALL)

# Replace card form-card -> premium-card mb-4
html_cnt = html_cnt.replace('class="card form-card"', 'class="premium-card mb-4"')
html_cnt = html_cnt.replace('class="card form-card mb-4"', 'class="premium-card mb-4"')

# Replace card-header
html_cnt = re.sub(r'<div class="card-header">(.*?)</div>', r'<h5 class="text-muted fw-bold mb-4">\1</h5>', html_cnt)

# Remove card-body classes but keep a container div so closing tags match
html_cnt = html_cnt.replace('<div class="card-body p-4">', '<div>')

# Button replacements
html_cnt = html_cnt.replace('class="cancel-btn btn"', 'class="btn btn-premium-outline"')
html_cnt = html_cnt.replace('class="submit-btn btn"', 'class="btn btn-premium"')

# Write back
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_cnt)

print("Updated aluno_form.html")
