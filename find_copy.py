import sys
with open('backup_manual_23_04_2026.sql', 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('COPY '):
            print(line.strip())
