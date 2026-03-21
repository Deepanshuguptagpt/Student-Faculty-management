import sqlite3
import os

def check_db(db_path):
    if not os.path.exists(db_path):
        return f"{db_path} does not exist"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    results = {}
    try:
        # Check student_profile table
        cursor.execute("SELECT COUNT(*) FROM student_studentprofile")
        results['students'] = cursor.fetchone()[0]
        
        # Check faculty_facultyprofile table
        cursor.execute("SELECT COUNT(*) FROM faculty_facultyprofile")
        results['faculty'] = cursor.fetchone()[0]
        
        # Check User table roles
        cursor.execute("SELECT role, COUNT(*) FROM authentication_user GROUP BY role")
        results['roles'] = dict(cursor.fetchall())
        
    except sqlite3.OperationalError as e:
        results['error'] = str(e)
    
    conn.close()
    return results

print("Checking db_v2.sqlite3:")
print(check_db('db_v2.sqlite3'))
print("\nChecking db_backup.sqlite3:")
print(check_db('db_backup.sqlite3'))
