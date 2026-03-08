import pandas as pd

df = pd.read_excel('Facultylist.xlsx')
print("COLUMNS:")
for col in df.columns:
    print(repr(col))

print("\nDATA:")
print(df.head(2).to_dict('records'))
