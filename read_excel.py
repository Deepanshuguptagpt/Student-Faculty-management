import pandas as pd

df = pd.read_excel('CSE1.xlsx')
print("COLUMNS:")
for col in df.columns:
    print(repr(col))

print("\nDATA:")
print(df.head(2).to_dict('records'))
