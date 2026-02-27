import os

forms_path = r"cursos\forms.py"
with open(forms_path, 'r', encoding='utf-8') as f:
    forms_cnt = f.read()

forms_cnt = forms_cnt.replace("'class': 'form-control'", "'class': 'form-control form-control-premium'")
forms_cnt = forms_cnt.replace("'class': 'form-select'", "'class': 'form-select form-select-premium'")

with open(forms_path, 'w', encoding='utf-8') as f:
    f.write(forms_cnt)

print("Updated cursos/forms.py")
