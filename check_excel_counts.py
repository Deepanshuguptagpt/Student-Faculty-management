import pandas as pd
import os

files = [
    'CSE1.xlsx', 'CS2_with_emails.xlsx', 'CS3_with_emails.xlsx', 
    'aiml_with_correct_emails.xlsx', 'Ds-Student-List.xlsx', 
    'IT_list_with_emails.xlsx', 'Facultylist.xlsx'
]

for f in files:
    if os.path.exists(f):
        try:
            df = pd.read_excel(f)
            print(f"{f}: {len(df)} rows")
        except Exception as e:
            print(f"{f}: Error reading - {e}")
    else:
        print(f"{f}: Missing")
