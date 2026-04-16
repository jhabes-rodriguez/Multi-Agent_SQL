"""
query_engine.py — Agente 3 (Visualizer)
Motor de consultas SQL para el chat web.
Convierte preguntas en lenguaje natural a SQL usando Groq y ejecuta en SQLite.
"""

import sqlite3
import pandas as pd
from groq import AsyncGroq
from config import settings


def get_semantic_hint(df: pd.DataFrame, col: str) -> str:
    """Retorna una pista sobre el significado de la columna basada en su nombre y contenido."""
    name = col.lower()
    if any(k in name for k in ["view", "hit", "popul", "visto"]):
        return "Métrica de popularidad/visualizaciones. Úsala para ránkings de 'más vistos'."
    if any(k in name for k in ["runtime", "durat", "time", "len"]):
        return "Duración o tiempo. NO confundas con popularidad."
    if any(k in name for k in ["date", "year", "lanz"]):
        return "Fecha o año de lanzamiento."
    if any(k in name for k in ["count", "total"]):
        return "Conteo o total acumulado."
    return ""

async def nl_to_sql(question: str, schema: str) -> str:
    """Convierte una pregunta en español a SQL usando Groq."""
    client = AsyncGroq(api_key=settings.groq_api_key)

    system_prompt = f"""Eres un motor ORM experto (SQLite). Tu misión es entender la INTENCIÓN del usuario y mapearla a la columna correcta.

REGLAS DE ORO:
1. Solo devuelve SQL puro.
2. ANALIZA LA SEMÁNTICA: 
   - "Más vistos" -> Usa columnas de Views/Popularidad y SUM().
   - "Más largos" -> Usa columnas de Runtime/Duration y AVG() o MAX().
3. GROUP BY OBLIGATORIO: Si piden "Top X" o comparaciones por categoría, usa GROUP BY (ej: Title) para evitar duplicados.
4. NÚMEROS: Las columnas de vistas ya son numéricas. No las trates como texto.
5. ESPACIOS EN COLUMNAS: ¡SIEMPRE usa comillas dobles para los nombres de las columnas que existen en el esquema (ej. `"Hours Viewed"`, `"Available Globally?"`) para evitar errores de sintaxis!

EJEMPLOS (Basados en Netflix):
- Pregunta: "Top 5 películas más vistas"
  SQL: SELECT "Title", SUM("Views") as Total_Views FROM ds_tabla GROUP BY "Title" ORDER BY Total_Views DESC LIMIT 5
- Pregunta: "Película con más horas vistas"
  SQL: SELECT "Title", MAX("Hours Viewed") FROM ds_tabla GROUP BY "Title" ORDER BY MAX("Hours Viewed") DESC LIMIT 1

ESQUEMA CON PISTAS:
{schema}"""

    try:
        resp = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Petición: {question}"},
            ],
            temperature=0.1,
            max_tokens=600,
        )
        sql = resp.choices[0].message.content.strip()
    except Exception as e:
        return f"SELECT 'Error en LLM Groq: {str(e)}' as error"

    if "```" in sql:
        sql = sql.split("```")[1]
        if sql.lower().startswith("sql"):
            sql = sql[3:]
        sql = sql.strip()

    return sql


def load_all_to_sqlite(datasets_data: list) -> tuple[sqlite3.Connection, str]:
    """Carga multiples datasets (nombre_tabla, data) en SQLite."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    schema_lines = []
    
    for table_name, data in datasets_data:
        if not data: continue
        df = pd.DataFrame(data)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        
        schema_lines.append(f"TABLA: {table_name}")
        schema_lines.append("Columnas:")
        for col in df.columns:
            dtype = str(df[col].dtype)
            ejemplo = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
            hint = get_semantic_hint(df, col)
            schema_lines.append(f"  - {col} ({dtype}) | ej: {ejemplo} {'| PISTA: ' + hint if hint else ''}")
        schema_lines.append("")

    return conn, "\n".join(schema_lines)


# Sentencias SQL prohibidas por seguridad
_BLOCKED_SQL = ("DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE", "TRUNCATE", "ATTACH", "DETACH")


def execute_sql(conn: sqlite3.Connection, sql: str) -> list[dict]:
    """Ejecuta una query SQL y retorna los resultados como lista de dicts. Evita sobreescritura si hay columnas repetidas."""
    # ── Guard de seguridad: solo SELECT ──
    sql_check = sql.strip().upper().lstrip("(")
    first_word = sql_check.split()[0] if sql_check.split() else ""
    if first_word in _BLOCKED_SQL or not sql_check.startswith("SELECT"):
        raise ValueError(
            f"⛔ Consulta bloqueada por seguridad. Solo se permiten SELECT.\n"
            f"Sentencia detectada: {first_word}\nQuery: {sql[:100]}"
        )

    cursor = conn.execute(sql)
    if cursor.description is None:
        return []
        
    raw_columns = [desc[0] for desc in cursor.description]
    columns = []
    seen = {}
    for col in raw_columns:
        if col in seen:
            seen[col] += 1
            columns.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 1
            columns.append(col)
            
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]
