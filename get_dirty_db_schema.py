import sqlite3
import json

def get_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema = {}
    for table_name in tables:
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [row[1] for row in cursor.fetchall()]
        
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        sample = cursor.fetchone()
        
        schema[table_name] = {
            'columns': columns,
            'sample': sample
        }
        
    conn.close()
    return schema

if __name__ == "__main__":
    db_path = r"c:\Users\Klisman rDs\Documents\Inscrição Django - 2026\banco_cadastro.db"
    info = get_schema(db_path)
    print(json.dumps(info, indent=2))
