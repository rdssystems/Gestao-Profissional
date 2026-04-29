import sqlite3

def restore():
    print("Connecting to db.sqlite3...")
    conn = sqlite3.connect('db.sqlite3')
    
    print("Reading backup_manual_23_04_2026.sql...")
    with open('backup_manual_23_04_2026.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
    
    print("Executing script...")
    conn.executescript(sql)
    
    conn.commit()
    conn.close()
    print("Restore complete.")

if __name__ == "__main__":
    restore()
