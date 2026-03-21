import sqlite3
import os

def get_counts(db_path):
    if not os.path.exists(db_path):
        return f"{db_path} does not exist"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    results = {}
    try:
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        results['tables'] = tables
        
        # Count students
        if 'student_studentprofile' in tables:
            cursor.execute("SELECT COUNT(*) FROM student_studentprofile")
            results['student_profiles'] = cursor.fetchone()[0]
        
        # Count faculty
        if 'faculty_facultyprofile' in tables:
            cursor.execute("SELECT COUNT(*) FROM faculty_facultyprofile")
            results['faculty_profiles'] = cursor.fetchone()[0]
        
        # Count users
        if 'authentication_user' in tables:
            cursor.execute("SELECT role, COUNT(*) FROM authentication_user GROUP BY role")
            results['user_roles'] = dict(cursor.fetchall())
            
    except Exception as e:
        results['error'] = str(e)
    
    conn.close()
    return results

dbs = ['db_v2.sqlite3', 'db_backup.sqlite3', 'db.sqlite3']
for db in dbs:
    print(f"--- {db} ---")
    print(get_counts(db))
    print()
