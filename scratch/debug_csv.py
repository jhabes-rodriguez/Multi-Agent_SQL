import pandas as pd
import csv
import os

def safe_read_csv(path, nrows=None):
    with open(path, 'r', encoding='latin1') as f:
        reader = csv.reader(f, delimiter=',')
        rows = list(reader)
        
    if not rows:
        return pd.DataFrame()
        
    fixed_rows = []
    header_len = len(rows[0])
    print(f"Header length: {header_len}")
    print(f"Total rows in reader: {len(rows)}")
    
    for r in rows:
        if len(r) == 1 and header_len > 1 and ',' in r[0]:
            try:
                sub_reader = csv.reader([r[0]], delimiter=',')
                sub_r = list(sub_reader)[0]
                fixed_rows.append(sub_r)
            except Exception:
                fixed_rows.append(r)
        else:
            fixed_rows.append(r)
            
    if nrows is not None:
        fixed_rows = fixed_rows[:nrows+1]
    
    if fixed_rows:
        header_len = len(fixed_rows[0])
        normalized = [fixed_rows[0]]
        for row in fixed_rows[1:]:
            if len(row) > header_len:
                normalized.append(row[:header_len])
            elif len(row) < header_len:
                normalized.append(row + [''] * (header_len - len(row)))
            else:
                normalized.append(row)
        fixed_rows = normalized
        
    df = pd.DataFrame(fixed_rows[1:], columns=fixed_rows[0]) if fixed_rows else pd.DataFrame()
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='ignore')
    return df

path = r'c:\Users\IVONNE ENRIQUEZ\Documents\Multi-Agentn(SQL\data\datasets\bmw_sales_data_(2010-2024).csv'
df = safe_read_csv(path)
print(f"Final DF shape: {df.shape}")
print(df.head())
