import pandas as pd
import json

df = pd.read_excel('Facultylist.xlsx')
df = df.fillna('')
records = df.to_dict('records')

with open('faculty_data.json', 'w', encoding='utf-8') as f:
    json.dump(records, f, indent=2)
