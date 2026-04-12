import pandas as pd
import io

csv_data = """SEDE_CODIGO,PERIODO_ID,PERIODO_ANIO,ACTIVIDAD_ID,ACTIVIDAD_CODIGO,ACTIVIDAD_NOMBRE
105001000001,10,2023,5,05,"Consulta de contenidos pedagógicos, mediante buscadores en internet"
105001000001,10,2023,7,7,Aprendizaje y evaluación del aprendizaje utilizando la plataforma virtual o multimedia digital
"""

print("--- Testing with sep=None, engine='python' ---")
df = pd.read_csv(io.StringIO(csv_data), sep=None, engine='python')
print(df)

print("\n--- Testing with sep=',' explicitly ---")
df2 = pd.read_csv(io.StringIO(csv_data), sep=',')
print(df2)
