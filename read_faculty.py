import pandas as pd
df = pd.read_excel('Facultylist.xlsx')
print(df.columns.tolist())
print(df.head())
