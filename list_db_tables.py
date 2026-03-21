import sqlite3
import os

def list_tables(db_path):
    if not os.path.exists(db_path):
        return f"{db_path} does not exist"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

print("Tables in db_v2.sqlite3:")
print(list_tables('db_v2.sqlite3'))
print("\nTables in db_backup.sqlite3:")
print(list_tables('db_backup.sqlite3'))
