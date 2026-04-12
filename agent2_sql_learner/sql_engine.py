"""
SQL Engine — Agent 2
Carga datasets desde la API, los monta en SQLite en memoria,
ejecuta queries y retorna resultados.
"""

import sqlite3
import time
import pandas as pd
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def obtener_esquema(df: pd.DataFrame, nombre_tabla: str) -> str:
    """Genera una descripción textual del esquema para pasarle al LLM."""
    lineas = [f"Tabla: {nombre_tabla}"]
    lineas.append("Columnas:")
    for col in df.columns:
        dtype = str(df[col].dtype)
        nulos = df[col].isna().sum()
        ejemplo = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
        lineas.append(f"  - {col} ({dtype}) | nulos: {nulos} | ejemplo: {ejemplo}")
    return "\n".join(lineas)


def cargar_dataset_desde_api(dataset_id: int) -> tuple[pd.DataFrame, dict]:
    """
    Descarga los datos de un dataset desde la API central.

    Returns:
        (DataFrame con los datos, metadata del dataset)
    """
    # Obtener metadata/schema primero
    schema_resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}/schema")
    schema_resp.raise_for_status()
    schema = schema_resp.json()

    total_rows = schema["rows_count"]

    # Descargar datos en páginas de 1000
    todos_los_datos = []
    offset = 0
    limit  = 1000

    while offset < total_rows:
        resp = requests.get(
            f"{API_BASE_URL}/datasets/{dataset_id}/data",
            params={"limit": limit, "offset": offset},
        )
        resp.raise_for_status()
        batch = resp.json()["data"]
        if not batch:
            break
        todos_los_datos.extend(batch)
        offset += limit

    df = pd.DataFrame(todos_los_datos)
    return df, schema


def montar_en_sqlite(df: pd.DataFrame, nombre_tabla: str) -> sqlite3.Connection:
    """
    Carga un DataFrame en una base de datos SQLite en memoria.

    Returns:
        Conexión SQLite con los datos cargados.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    df.to_sql(nombre_tabla, conn, if_exists="replace", index=False)
    return conn


# Sentencias SQL prohibidas por seguridad
_BLOCKED_SQL = ("DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE", "TRUNCATE", "ATTACH", "DETACH")


def ejecutar_query(conn: sqlite3.Connection, sql: str) -> tuple[list[dict], float]:
    """
    Ejecuta una query SQL y retorna los resultados y el tiempo de ejecución.
    Solo permite sentencias SELECT por seguridad.

    Returns:
        (lista de dicts con resultados, tiempo en segundos)
    """
    # ── Guard de seguridad: solo SELECT ──
    sql_check = sql.strip().upper().lstrip("(")
    first_word = sql_check.split()[0] if sql_check.split() else ""
    if first_word in _BLOCKED_SQL or not sql_check.startswith("SELECT"):
        raise ValueError(
            f"⛔ Consulta bloqueada por seguridad. Solo se permiten SELECT.\n"
            f"Sentencia detectada: {first_word}\nQuery: {sql[:100]}"
        )

    inicio = time.time()
    try:
        cursor = conn.execute(sql)
        raw_columns = [desc[0] for desc in cursor.description]

        # ── Fix: renombrar columnas duplicadas para evitar sobreescritura ──
        columnas = []
        seen = {}
        for col in raw_columns:
            if col in seen:
                seen[col] += 1
                columnas.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 1
                columnas.append(col)

        filas    = cursor.fetchall()
        resultado = [dict(zip(columnas, fila)) for fila in filas]
        tiempo = round(time.time() - inicio, 4)
        return resultado, tiempo
    except sqlite3.Error as e:
        raise ValueError(f"Error SQL: {e}\nQuery: {sql}")


def hacer_split(df: pd.DataFrame, porcentaje_train: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Divide el DataFrame en conjuntos de entrenamiento y prueba.

    Args:
        df:                DataFrame completo.
        porcentaje_train:  Proporción para entrenamiento (default 0.8 = 80%).

    Returns:
        (train_df, test_df)
    """
    df_mezclado = df.sample(frac=1, random_state=42).reset_index(drop=True)
    corte       = int(len(df_mezclado) * porcentaje_train)
    train_df    = df_mezclado.iloc[:corte].copy()
    test_df     = df_mezclado.iloc[corte:].copy()
    return train_df, test_df


def estadisticas_basicas(df: pd.DataFrame) -> dict:
    """
    Calcula estadísticas básicas de las columnas numéricas del DataFrame.

    Returns:
        Dict con estadísticas por columna numérica.
    """
    numericas = df.select_dtypes(include="number")
    if numericas.empty:
        return {}

    stats = {}
    for col in numericas.columns:
        stats[col] = {
            "min":    round(float(numericas[col].min()), 4),
            "max":    round(float(numericas[col].max()), 4),
            "mean":   round(float(numericas[col].mean()), 4),
            "median": round(float(numericas[col].median()), 4),
            "std":    round(float(numericas[col].std()), 4),
            "nulos":  int(numericas[col].isna().sum()),
        }
    return stats


def listar_datasets_api() -> list[dict]:
    """Obtiene la lista de datasets disponibles en la API Central."""
    resp = requests.get(f"{API_BASE_URL}/datasets/list")
    resp.raise_for_status()
    return resp.json()
