import sqlite3
import pandas as pd

def show_rows(db_path, n=20):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM dados LIMIT ?", conn, params=(n,))
    print(df[['Nome', 'Cpf', 'datanasc', 'Bairro', 'Curso']].to_string(index=False))
    conn.close()

if __name__ == "__main__":
    db_path = r"c:\Users\Klisman rDs\Documents\Inscrição Django - 2026\banco_cadastro.db"
    show_rows(db_path)
