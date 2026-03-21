import sqlite3
import os

def get_counts(db_path):
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    s_count = 0
    f_count = 0
    u_count = 0
    
    if 'student_studentprofile' in tables:
        cursor.execute("SELECT COUNT(*) FROM student_studentprofile")
        s_count = cursor.fetchone()[0]
    
    if 'faculty_facultyprofile' in tables:
        cursor.execute("SELECT COUNT(*) FROM faculty_facultyprofile")
        f_count = cursor.fetchone()[0]
    
    if 'authentication_user' in tables:
        cursor.execute("SELECT COUNT(*) FROM authentication_user")
        u_count = cursor.fetchone()[0]
        
    conn.close()
    return (s_count, f_count, u_count)

for db in ['db_v2.sqlite3', 'db_backup.sqlite3']:
    counts = get_counts(db)
    if counts:
        print(f"{db}: Students={counts[0]}, Faculty={counts[1]}, Users={counts[2]}")
    else:
        print(f"{db}: Missing")
