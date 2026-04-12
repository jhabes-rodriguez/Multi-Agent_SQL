def greedy_split(line, expected_cols):
    # Primero separamos por todas las comas
    parts = line.split(',')
    if len(parts) == expected_cols:
        return parts
        
    fixed = []
    temp = ""
    in_quote = False
    
    for p in parts:
        # Detectar si estamos dentro de una cita (incluso si empieza con "" o ")
        clean_p = p.strip()
        
        # Lógica de inicio de cita
        starts_quote = clean_p.startswith('"')
        # Lógica de fin de cita (contar comillas al final)
        ends_quote = clean_p.endswith('"')
        
        if starts_quote and not in_quote:
            in_quote = True
            temp = p
            # Caso especial: la celda es solo una cita completa ej: "Hola"
            # Si tiene un número par de comillas (y > 0), podría estar cerrada en la misma parte
            if clean_p.count('"') % 2 == 0 and clean_p.count('"') > 0:
                in_quote = False
                fixed.append(temp.strip('"'))
                temp = ""
        elif in_quote:
            temp += "," + p
            # Si encontramos una comilla al final, cerramos (pero cuidado con el conteo total)
            if clean_p.count('"') % 2 != 0: # Una comilla sola o impar suele cerrar el bloque
                in_quote = False
                fixed.append(temp.strip('"'))
                temp = ""
        else:
            fixed.append(p)
            
    # Si después de todo tenemos más columnas de las esperadas y aún falta la última,
    # podríamos estar ante un caso donde la última columna tiene comas y no se cerró la cita
    if len(fixed) > expected_cols:
        # Re-unificar las columnas sobrantes en la última
        last_col = ",".join(fixed[expected_cols-1:])
        fixed = fixed[:expected_cols-1] + [last_col]
        
    return fixed

# Caso del usuario
test_line = '105001000001,10,2023,5,05,""Consulta de contenidos pedagógicos, mediante buscadores en internet'
header_len = 6

print(f"Original: {test_line}")
result = greedy_split(test_line, header_len)
print(f"Result (len {len(result)}): {result}")
