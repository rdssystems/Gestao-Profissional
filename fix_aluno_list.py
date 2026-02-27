import os

path = 'alunos/templates/alunos/aluno_list.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

bad_tag = '{% if escola_selecionada|stringformat:"s"==escola.id|stringformat:"s"\n                    %}selected{% endif %}'
good_tag = '{% if escola_selecionada|stringformat:"s" == escola.id|stringformat:"s" %}selected{% endif %}'

content = content.replace(bad_tag, good_tag)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Alunos list fixed")
