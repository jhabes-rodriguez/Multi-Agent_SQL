import pandas as pd
import csv

def greedy_split(line, expected_cols, delimiter=','):
    parts = line.split(delimiter)
    if len(parts) == expected_cols:
        return [p.strip().strip('"').strip() for p in parts]
    
    fixed = []
    temp = ""
    in_quote = False
    
    for p in parts:
        clean_p = p.strip()
        starts_quote = clean_p.startswith('"')
        
        if starts_quote and not in_quote:
            in_quote = True
            temp = p
            if clean_p.count('"') % 2 == 0 and clean_p.count('"') > 0:
                in_quote = False
                fixed.append(temp.strip().strip('"').strip())
                temp = ""
        elif in_quote:
            temp += delimiter + p
            if clean_p.count('"') % 2 != 0:
                in_quote = False
                fixed.append(temp.strip().strip('"').strip())
                temp = ""
        else:
            fixed.append(p.strip().strip('"').strip())
            
    if len(fixed) > expected_cols:
        last_val = delimiter.join(fixed[expected_cols-1:])
        fixed = fixed[:expected_cols-1] + [last_val]
    elif len(fixed) < expected_cols:
        fixed += [""] * (expected_cols - len(fixed))
        
    return fixed

# Caso MIXTO: Header con TABS, Data con COMMAS
header_line = "SEDE_CODIGO\tPERIODO_ID\tPERIODO_ANIO\tACTIVIDAD_ID\tACTIVIDAD_CODIGO\tACTIVIDAD_NOMBRE"
data_line = '105001000001,9,2022,5,05,""Consulta de contenidos pedagógicos, mediante buscadores en internet'

print(f"Header: {repr(header_line)}")
print(f"Data:   {repr(data_line)}")

# 1. Detectar delimitador de header
possible = [',', ';', '\t']
best_sep = ','
max_cols = 0
for s in possible:
    cols = len(header_line.split(s))
    if cols > max_cols:
        max_cols = cols
        best_sep = s

print(f"Detected Header Sep: {repr(best_sep)} (cols: {max_cols})")

# 2. Intentar parsear data con ese sep
data_cols = len(data_line.split(best_sep))
print(f"Data cols with best_sep: {data_cols}")

# Si hay discrepancia, re-evaluar el delimitador para la data
if data_cols == 1 and max_cols > 1:
    print("WARNING: Data doesn't match header sep. Trying to fix data.")
    # Si la data no tiene el separador del header, intentamos detectar el de la data
    data_best_sep = ','
    data_max_cols = 0
    for s in possible:
        cols = len(data_line.split(s))
        if cols > data_max_cols:
            data_max_cols = cols
            data_best_sep = s
    print(f"Detected Data Sep: {repr(data_best_sep)} (cols: {data_max_cols})")
    
    # Usar el splitter con el delimitador de la data para alcanzar el count del header
    result = greedy_split(data_line, max_cols, delimiter=data_best_sep)
    print(f"Result (len {len(result)}): {result}")
