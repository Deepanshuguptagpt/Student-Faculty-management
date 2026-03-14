import pandas as pd
try:
    df = pd.read_excel('aiml_with_correct_emails.xlsx')
    print("Columns:", df.columns.tolist())
    print("\nFirst 5 rows:")
    print(df.head())
except Exception as e:
    print(f"Error: {e}")
