"""
Insights — Agent 2
Genera análisis estadísticos automáticos de los datasets.
"""

import pandas as pd
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def resumen_dataset(df: pd.DataFrame, nombre: str) -> dict:
    """
    Genera un resumen estadístico completo del dataset.

    Returns:
        Dict con estadísticas generales, por columna numérica y categórica.
    """
    resumen = {
        "nombre":         nombre,
        "total_filas":    len(df),
        "total_columnas": len(df.columns),
        "columnas":       list(df.columns),
        "tipos":          {col: str(dtype) for col, dtype in df.dtypes.items()},
        "nulos_por_col":  df.isna().sum().to_dict(),
        "porcentaje_nulos": (df.isna().mean() * 100).round(2).to_dict(),
    }

    # Estadísticas numéricas
    numericas = df.select_dtypes(include="number")
    if not numericas.empty:
        resumen["estadisticas_numericas"] = (
            numericas.describe().round(4).to_dict()
        )

    # Columnas categóricas — top valores
    categoricas = df.select_dtypes(include=["object", "category"])
    if not categoricas.empty:
        cat_info = {}
        for col in categoricas.columns:
            top = df[col].value_counts().head(5)
            cat_info[col] = {
                "valores_unicos": int(df[col].nunique()),
                "top_5": top.to_dict(),
            }
        resumen["estadisticas_categoricas"] = cat_info

    return resumen


def comparar_train_test(
    train: pd.DataFrame,
    test:  pd.DataFrame,
) -> dict:
    """
    Compara estadísticas básicas entre train y test para detectar sesgos.

    Returns:
        Dict con comparación columna por columna.
    """
    numericas = train.select_dtypes(include="number").columns.tolist()
    comparacion = {}

    for col in numericas:
        if col in test.columns:
            comparacion[col] = {
                "train_mean": round(float(train[col].mean()), 4),
                "test_mean":  round(float(test[col].mean()),  4),
                "diferencia": round(float(abs(train[col].mean() - test[col].mean())), 4),
                "train_std":  round(float(train[col].std()),  4),
                "test_std":   round(float(test[col].std()),   4),
            }

    return {
        "train_filas": len(train),
        "test_filas":  len(test),
        "ratio":       f"{len(train)/(len(train)+len(test))*100:.1f}% / {len(test)/(len(train)+len(test))*100:.1f}%",
        "columnas":    comparacion,
    }


def guardar_insight_api(
    dataset_id: int,
    titulo:     str,
    contenido:  str,
    query_id:   int | None = None,
) -> int | None:
    """
    Envía un insight a la API Central para que sea consumido por el Agent 3.

    Returns:
        insight_id si se guardó correctamente, None si falló.
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}/insights/save",
            json={
                "dataset_id": dataset_id,
                "query_id":   query_id,
                "title":      titulo,
                "content":    contenido,
            },
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json().get("insight_id")
    except Exception as e:
        print(f"⚠️  No se pudo guardar el insight: {e}")
        return None


def guardar_query_api(
    dataset_id:       int,
    natural_language: str,
    sql_query:        str,
    resultado:        list,
    execution_time:   float = 0.0,
) -> int | None:
    """
    Guarda el resultado de una query en la API Central.

    Returns:
        query_id si se guardó correctamente, None si falló.
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}/queries/run",
            json={
                "dataset_id":       dataset_id,
                "natural_language": natural_language,
                "sql_query":        sql_query,
                "result":           resultado,
                "execution_time":   execution_time,
            },
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json().get("query_id")
    except Exception as e:
        print(f"⚠️  No se pudo guardar la query: {e}")
        return None
