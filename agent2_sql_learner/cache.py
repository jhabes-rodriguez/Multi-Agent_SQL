"""
Cache — Agent 2
Almacena queries y resultados en SQLite para no repetir llamadas.
La clave de cache es un hash de (dataset_id + pregunta_normalizada).
"""

import sqlite3
import hashlib
import json
import os
import requests

CACHE_DB     = os.getenv("CACHE_DB", "./data/cache.db")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# ─────────────────────────────────────────────
# Inicialización local
# ─────────────────────────────────────────────

def _get_local_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(CACHE_DB), exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            cache_key     TEXT PRIMARY KEY,
            sql_query     TEXT,
            result_json   TEXT,
            hit_count     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now')),
            last_accessed TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_key(dataset_id: int, pregunta: str) -> str:
    """Genera un hash único para el par (dataset, pregunta)."""
    texto = f"{dataset_id}::{pregunta.strip().lower()}"
    return hashlib.md5(texto.encode()).hexdigest()


# ─────────────────────────────────────────────
# Operaciones de cache
# ─────────────────────────────────────────────

def buscar_en_cache(dataset_id: int, pregunta: str) -> dict | None:
    """
    Busca si ya existe un resultado para esta pregunta y dataset.

    Returns:
        Dict con {sql_query, result, hit_count} si existe, None si no.
    """
    key  = _make_key(dataset_id, pregunta)
    conn = _get_local_conn()

    try:
        row = conn.execute(
            "SELECT * FROM cache WHERE cache_key = ?", (key,)
        ).fetchone()

        if row:
            # Actualizar contador de hits
            conn.execute(
                "UPDATE cache SET hit_count = hit_count + 1, last_accessed = datetime('now') WHERE cache_key = ?",
                (key,),
            )
            conn.commit()

            return {
                "sql_query": row["sql_query"],
                "result":    json.loads(row["result_json"]),
                "hit_count": row["hit_count"] + 1,
            }
        return None
    finally:
        conn.close()


def guardar_en_cache(
    dataset_id: int,
    pregunta:   str,
    sql_query:  str,
    resultado:  list,
) -> None:
    """
    Guarda un resultado en el cache local y lo sincroniza con la API Central.
    """
    key         = _make_key(dataset_id, pregunta)
    result_json = json.dumps(resultado, ensure_ascii=False)

    # Cache local
    conn = _get_local_conn()
    try:
        existing = conn.execute(
            "SELECT hit_count FROM cache WHERE cache_key = ?", (key,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE cache SET hit_count = hit_count + 1, last_accessed = datetime('now') WHERE cache_key = ?",
                (key,),
            )
        else:
            conn.execute(
                "INSERT INTO cache (cache_key, sql_query, result_json) VALUES (?, ?, ?)",
                (key, sql_query, result_json),
            )
        conn.commit()
    finally:
        conn.close()

    # Sincronizar con API Central (sin lanzar error si falla)
    try:
        requests.post(
            f"{API_BASE_URL}/cache/save",
            json={"cache_key": key, "sql_query": sql_query, "result_json": result_json},
            timeout=3,
        )
    except Exception:
        pass


def top_queries_cacheadas(n: int = 10) -> list[dict]:
    """Retorna las N queries más accedidas del cache local."""
    conn = _get_local_conn()
    try:
        rows = conn.execute(
            "SELECT cache_key, sql_query, hit_count, last_accessed FROM cache ORDER BY hit_count DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def limpiar_cache() -> int:
    """Elimina todas las entradas del cache local. Retorna el número de entradas eliminadas."""
    conn = _get_local_conn()
    try:
        count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        conn.execute("DELETE FROM cache")
        conn.commit()
        return count
    finally:
        conn.close()
