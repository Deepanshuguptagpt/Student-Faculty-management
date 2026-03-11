import pandas as pd
import json

df = pd.read_excel('CSE1.xlsx')
cols = list(df.columns)
data = df.head(3).to_dict('records')

with open('excel_out.json', 'w') as f:
    json.dump({"columns": cols, "data": data}, f, indent=2)
