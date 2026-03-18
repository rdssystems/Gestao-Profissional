import sqlite3
import pandas as pd

def inspect_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables in {db_path}:")
    for table in tables:
        table_name = table[0]
        print(f"\n- Table: {table_name}")
        
        # Get columns
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print("  Columns:")
        for col in columns:
            print(f"    - {col[1]} ({col[2]})")
            
        # Sample 5 rows
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5", conn)
            print("  Sample Data:")
            print(df.to_string(index=False))
        except Exception as e:
            print(f"  Error reading sample data: {e}")
            
    conn.close()

if __name__ == "__main__":
    db_path = r"c:\Users\Klisman rDs\Documents\Inscrição Django - 2026\banco_cadastro.db"
    inspect_db(db_path)
