import re
import os

path = r'alunos\templates\alunos\aluno_list.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix block 1
pattern1 = r'\{%\s*if escola_selecionada\|stringformat:"s"==escola\.id\|stringformat:"s"[\r\n\s]+%\}selected\{%\s*endif\s*%\}'
replace1 = '{% if escola_selecionada|stringformat:"s" == escola.id|stringformat:"s" %}selected{% endif %}'
content, subs1 = re.subn(pattern1, replace1, content)
print(f"Replaced {subs1} occurrences of pattern 1")

# Fix block 2
pattern2 = r'\{%\s*if not[\r\n\s]+forloop\.last\s*%\} \{%\s*endif\s*%\}'
replace2 = '{% if not forloop.last %} {% endif %}'
content, subs2 = re.subn(pattern2, replace2, content)
print(f"Replaced {subs2} occurrences of pattern 2")

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Done fixing file.")
