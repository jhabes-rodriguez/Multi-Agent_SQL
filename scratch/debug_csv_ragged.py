import pandas as pd
import io
import csv

csv_data = """SEDE_CODIGO,PERIODO_ID,PERIODO_ANIO,ACTIVIDAD_ID,ACTIVIDAD_CODIGO,ACTIVIDAD_NOMBRE
105001000001,9,2022,5,05,"Consulta de contenidos pedagógicos, mediante buscadores en internet"
105001000001,9,2022,7,7,Aprendizaje y evaluación del aprendizaje utilizando la plataforma virtual o multimedia digital
"""

print("--- Testing with Attempt 1 (sep=',', engine='c') ---")
try:
    df = pd.read_csv(io.StringIO(csv_data), sep=',', engine='c', quotechar='"', doublequote=True)
    print(df)
    print("Columns:", df.columns.tolist())
except Exception as e:
    print("Error:", e)

print("\n--- Testing with csv.reader directly ---")
reader = csv.reader(io.StringIO(csv_data), delimiter=',', quotechar='"')
rows = list(reader)
for i, row in enumerate(rows):
    print(f"Row {i} (len {len(row)}): {row}")
