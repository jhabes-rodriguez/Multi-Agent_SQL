"""
Groq Client — Agent 2
Maneja:
  - Traducción lenguaje natural → SQL
  - Generación de insights
  - Análisis de train/test
"""

import os
from dotenv import load_dotenv
from groq import Groq

# El orquestador inyecta GROQ_API_KEY como variable de entorno del proceso.
# Si se ejecuta directamente, se toma del .env raíz o local.
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODELO       = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY no encontrado. "
        "Configúrala en el .env raíz o usa el orquestador (start_orchestrator.py)."
    )

client = Groq(api_key=GROQ_API_KEY)


# ─────────────────────────────────────────────
# NL → SQL
# ─────────────────────────────────────────────

def nl_to_sql(pregunta: str, esquema: str, nombre_tabla: str) -> str:
    """
    Convierte una pregunta en lenguaje natural a una query SQL válida.

    Args:
        pregunta:     Lo que el usuario quiere saber.
        esquema:      Descripción de columnas y tipos.
        nombre_tabla: Nombre de la tabla SQLite a usar.

    Returns:
        String con la query SQL lista para ejecutar.
    """
    prompt_sistema = f"""Eres un experto en SQL. Tu única tarea es convertir preguntas en español a queries SQL para SQLite.

REGLAS ESTRICTAS:
1. Solo devuelve la query SQL pura, sin explicaciones, sin markdown, sin bloques de código.
2. La tabla se llama exactamente: {nombre_tabla}
3. Usa solo las columnas del esquema proporcionado.
4. Si hay columnas de texto, usa LIKE para búsquedas.
5. Siempre agrega LIMIT 100 al final a menos que la pregunta pida un conteo o agregación.
6. No uses comillas dobles para nombres de columnas, usa backticks o ninguno.

ESQUEMA DE LA TABLA {nombre_tabla}:
{esquema}"""

    respuesta = client.chat.completions.create(
        model=MODELO,
        messages=[
            {"role": "system",  "content": prompt_sistema},
            {"role": "user",    "content": f"Pregunta: {pregunta}"},
        ],
        temperature=0.1,
        max_tokens=500,
    )

    sql = respuesta.choices[0].message.content.strip()

    # Limpiar si viene con markdown
    if "```" in sql:
        sql = sql.split("```")[1]
        if sql.lower().startswith("sql"):
            sql = sql[3:]
        sql = sql.strip()

    return sql


# ─────────────────────────────────────────────
# GENERAR INSIGHT
# ─────────────────────────────────────────────

def generar_insight(pregunta: str, sql: str, datos: list, nombre_dataset: str) -> str:
    """
    Analiza los resultados de una query y genera un insight en español.

    Args:
        pregunta:        Pregunta original del usuario.
        sql:             Query SQL ejecutada.
        datos:           Lista de dicts con los resultados.
        nombre_dataset:  Nombre del dataset analizado.

    Returns:
        Texto con el insight generado por el LLM.
    """
    # Resumir datos para no sobrecargar el contexto
    muestra = datos[:20] if len(datos) > 20 else datos
    resumen = f"Total de filas: {len(datos)}\nMuestra de resultados:\n{muestra}"

    respuesta = client.chat.completions.create(
        model=MODELO,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un analista de datos experto. Analiza los resultados de una consulta SQL "
                    "y genera insights útiles, claros y accionables en español. "
                    "Sé específico con números y porcentajes cuando los haya. "
                    "Máximo 3 párrafos cortos."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Dataset: {nombre_dataset}\n"
                    f"Pregunta del usuario: {pregunta}\n"
                    f"SQL ejecutado: {sql}\n\n"
                    f"Resultados:\n{resumen}\n\n"
                    "Genera un insight conciso con los hallazgos más relevantes."
                ),
            },
        ],
        temperature=0.5,
        max_tokens=600,
    )
    return respuesta.choices[0].message.content.strip()


# ─────────────────────────────────────────────
# ANÁLISIS TRAIN/TEST
# ─────────────────────────────────────────────

def analizar_split(
    nombre_dataset: str,
    total_filas: int,
    train_filas: int,
    test_filas: int,
    columnas: list,
    estadisticas_train: dict,
    estadisticas_test: dict,
) -> str:
    """
    Genera un análisis comparativo entre el conjunto de entrenamiento y prueba.

    Returns:
        Texto con el análisis del split.
    """
    respuesta = client.chat.completions.create(
        model=MODELO,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un científico de datos. Analiza la división train/test de un dataset "
                    "y comenta si la distribución es adecuada, si hay posible data leakage, "
                    "y qué se puede aprender de la diferencia entre ambos conjuntos. "
                    "Sé conciso y en español."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Dataset: {nombre_dataset}\n"
                    f"Total filas: {total_filas} | Train: {train_filas} (80%) | Test: {test_filas} (20%)\n"
                    f"Columnas: {columnas}\n\n"
                    f"Estadísticas Train:\n{estadisticas_train}\n\n"
                    f"Estadísticas Test:\n{estadisticas_test}\n\n"
                    "Analiza el split y da recomendaciones."
                ),
            },
        ],
        temperature=0.4,
        max_tokens=500,
    )
    return respuesta.choices[0].message.content.strip()


# ─────────────────────────────────────────────
# SUGERIR QUERIES
# ─────────────────────────────────────────────

def sugerir_queries(nombre_dataset: str, esquema: str) -> list[str]:
    """
    Dado un dataset, sugiere 5 preguntas interesantes que el usuario podría hacer.

    Returns:
        Lista de preguntas sugeridas.
    """
    respuesta = client.chat.completions.create(
        model=MODELO,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un analista de datos. Dado el esquema de un dataset, "
                    "sugiere exactamente 5 preguntas interesantes que se podrían hacer en lenguaje natural. "
                    "Las preguntas deben ser en español, simples y directas. "
                    "Devuelve solo las 5 preguntas, una por línea, sin numeración ni explicaciones."
                ),
            },
            {
                "role": "user",
                "content": f"Dataset: {nombre_dataset}\nEsquema:\n{esquema}",
            },
        ],
        temperature=0.7,
        max_tokens=300,
    )
    texto = respuesta.choices[0].message.content.strip()
    preguntas = [p.strip() for p in texto.split("\n") if p.strip()]
    return preguntas[:5]
