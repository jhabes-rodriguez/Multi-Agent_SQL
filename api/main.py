"""
API Central — Multi-Agent System
FastAPI + SQLite3 (sin dependencias externas de BD)
Puerto: 8000
"""

import os
import json
import shutil
import time
from contextlib import asynccontextmanager
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.database import get_db, init_db, DATASETS_DIR

load_dotenv()


@asynccontextmanager
async def lifespan(app):
    os.makedirs(DATASETS_DIR, exist_ok=True)
    init_db()
    print("[API] Base de datos inicializada")
    yield


app = FastAPI(
    title="Multi-Agent Central API",
    description="API central que conecta los 3 agentes del sistema",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.get("/health")
def health():
    return {"status": "ok", "service": "Multi-Agent Central API"}


@app.get("/")
def root():
    return {
        "message": "Multi-Agent Central API corriendo",
        "version": "1.0.0",
        "endpoints": [
            "POST /datasets/upload",
            "GET  /datasets/list",
            "GET  /datasets/{id}/data",
            "POST /queries/run",
            "GET  /queries/results/{id}",
            "GET  /queries/history",
            "POST /insights/save",
            "GET  /insights/latest",
            "GET  /cache/hits",
            "GET  /datasets/{id}/download",
        ]
    }


# ─────────────────────────────────────────────
# DATASETS
# ─────────────────────────────────────────────

@app.post("/datasets/upload", summary="Subir un dataset CSV")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str        = Form(...),
    description: str = Form(""),
    source_url: str  = Form(""),
    votes: int       = Form(0),
):
    """
    Recibe un archivo CSV y lo guarda.
    Registra metadata en SQLite (nombre, filas, columnas, etc.).
    """
    os.makedirs(DATASETS_DIR, exist_ok=True)
    safe_name = name.replace(" ", "_").lower()
    file_path = os.path.join(DATASETS_DIR, f"{safe_name}.csv")

    # Guardar archivo
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Contar filas y columnas
    try:
        df = safe_read_csv(file_path)
        rows_count    = len(df)
        columns_count = len(df.columns)
        columns_names = list(df.columns)
    except Exception as e:
        import traceback
        print("Error uploading", traceback.format_exc())
        rows_count    = 0
        columns_count = 0
        columns_names = []

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO datasets
                (name, description, source_url, votes, rows_count, columns_count, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (safe_name, description, source_url, votes, rows_count, columns_count, file_path),
        )
        conn.commit()
        dataset = conn.execute(
            "SELECT id FROM datasets WHERE name = ?", (safe_name,)
        ).fetchone()
        dataset_id = dataset["id"]
    finally:
        conn.close()

    return {
        "success":    True,
        "dataset_id": dataset_id,
        "name":       safe_name,
        "rows":       rows_count,
        "columns":    columns_count,
        "columns_names": columns_names,
    }


@app.delete("/datasets/clear", summary="Limpiar todas las bases de datos. Ideal para reseteo al recargar el front.")
def clear_datasets():
    conn = get_db()
    try:
        conn.execute("DELETE FROM datasets")
        conn.commit()
    finally:
        conn.close()
    return {"message": "Bases de datos limpiadas exitosamente."}

@app.get("/datasets/list", summary="Listar todos los datasets")
def list_datasets():
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, name, description, source_url, votes,
                   rows_count, columns_count, created_at
            FROM datasets
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def safe_read_csv(path, nrows=None):
    import pandas as pd
    import csv
    
    with open(path, 'r', encoding='latin1') as f:
        reader = csv.reader(f, delimiter=',')
        rows = list(reader)
        
    if not rows:
        return pd.DataFrame()
        
    fixed_rows = []
    header_len = len(rows[0])
    
    for r in rows:
        # Si la fila fue forzadamente unificada en 1 columna por comillas gigantes, pero debería tener más
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
    
    # Normalizar filas al largo del header (truncar o rellenar)
    if fixed_rows:
        header_len = len(fixed_rows[0])
        normalized = [fixed_rows[0]]  # header
        for row in fixed_rows[1:]:
            if len(row) > header_len:
                normalized.append(row[:header_len])   # truncar columnas extra
            elif len(row) < header_len:
                normalized.append(row + [''] * (header_len - len(row)))  # rellenar
            else:
                normalized.append(row)
        fixed_rows = normalized
        
    # Convertir a pandas
    df = pd.DataFrame(fixed_rows[1:], columns=fixed_rows[0]) if fixed_rows else pd.DataFrame()
    
    # Autocasteo para evitar que todo sea object (string)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='ignore')
        
    return df

@app.get("/datasets/{dataset_id}/data", summary="Obtener datos de un dataset")
def get_dataset_data(dataset_id: int, limit: int = 500, offset: int = 0):
    conn = get_db()
    try:
        ds = conn.execute(
            "SELECT * FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        if not ds:
            raise HTTPException(status_code=404, detail="Dataset no encontrado")

        df = safe_read_csv(ds["file_path"])
        page = df.iloc[offset: offset + limit].copy()
        
        # Purificación exhaustiva
        for col in page.select_dtypes(include=['datetime64', 'timedelta64']).columns:
            page[col] = page[col].astype(str)
            
        page = page.fillna('')
        page = page.replace([float('inf'), float('-inf')], '')
        page_dict = page.to_dict(orient="records")

        return {
            "dataset_id":  dataset_id,
            "name":        ds["name"],
            "total_rows":  len(df),
            "columns":     list(df.columns),
            "dtypes":      {c: str(t) for c, t in df.dtypes.items()},
            "data":        page_dict,
        }
    except Exception as e:
        print(f"Error cargando archivo {ds['file_path']}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/datasets/{dataset_id}/schema", summary="Obtener esquema del dataset")
def get_dataset_schema(dataset_id: int):
    conn = get_db()
    try:
        ds = conn.execute(
            "SELECT * FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        if not ds:
            raise HTTPException(status_code=404, detail="Dataset no encontrado")

        df = safe_read_csv(ds["file_path"], nrows=5)

        return {
            "dataset_id":  dataset_id,
            "name":        ds["name"],
            "columns":     list(df.columns),
            "dtypes":      {c: str(t) for c, t in df.dtypes.items()},
            "sample":      df.fillna('').to_dict(orient="records"),
            "rows_count":  ds["rows_count"],
        }
    finally:
        conn.close()

@app.get("/datasets/{dataset_id}/download", summary="Descargar archivo CSV del dataset")
def download_dataset(dataset_id: int):
    conn = get_db()
    try:
        ds = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if not ds or not os.path.exists(ds["file_path"]):
            raise HTTPException(status_code=404, detail="Dataset o archivo no encontrado")
        
        return FileResponse(
            path=ds["file_path"],
            filename=f'{ds["name"]}.csv',
            media_type='text/csv'
        )
    finally:
        conn.close()


# ─────────────────────────────────────────────
# QUERIES
# ─────────────────────────────────────────────

class QuerySaveRequest(BaseModel):
    dataset_id:       int
    natural_language: str
    sql_query:        str
    result:           list
    execution_time:   float = 0.0


@app.post("/queries/run", summary="Guardar resultado de una query")
def save_query_result(req: QuerySaveRequest):
    conn = get_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO queries
                (dataset_id, natural_language, sql_query, result_json, execution_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                req.dataset_id,
                req.natural_language,
                req.sql_query,
                json.dumps(req.result, ensure_ascii=False),
                req.execution_time,
            ),
        )
        conn.commit()
        return {"success": True, "query_id": cursor.lastrowid}
    finally:
        conn.close()


@app.get("/queries/results/{query_id}", summary="Obtener resultado de una query")
def get_query_result(query_id: int):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM queries WHERE id = ?", (query_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Query no encontrada")
        result = dict(row)
        result["result"] = json.loads(result["result_json"])
        return result
    finally:
        conn.close()


@app.get("/queries/history", summary="Historial de queries ejecutadas")
def get_query_history(limit: int = 20):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT q.id, q.natural_language, q.sql_query,
                   q.execution_time, q.created_at,
                   d.name AS dataset_name
            FROM   queries q
            LEFT JOIN datasets d ON q.dataset_id = d.id
            ORDER  BY q.created_at DESC
            LIMIT  ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─────────────────────────────────────────────
# INSIGHTS
# ─────────────────────────────────────────────

class InsightRequest(BaseModel):
    dataset_id: int
    query_id:   Optional[int] = None
    title:      str
    content:    str


@app.post("/insights/save", summary="Guardar un insight")
def save_insight(req: InsightRequest):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO insights (dataset_id, query_id, title, content) VALUES (?, ?, ?, ?)",
            (req.dataset_id, req.query_id, req.title, req.content),
        )
        conn.commit()
        return {"success": True, "insight_id": cursor.lastrowid}
    finally:
        conn.close()


@app.get("/insights/latest", summary="Últimos insights generados")
def get_latest_insights(limit: int = 10):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT i.id, i.title, i.content, i.created_at,
                   d.name AS dataset_name
            FROM   insights i
            LEFT JOIN datasets d ON i.dataset_id = d.id
            ORDER  BY i.created_at DESC
            LIMIT  ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─────────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────────

class CacheSaveRequest(BaseModel):
    cache_key:   str
    sql_query:   str
    result_json: str


@app.post("/cache/save", summary="Guardar en cache")
def save_cache(req: CacheSaveRequest):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id, hit_count FROM query_cache WHERE cache_key = ?",
            (req.cache_key,),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE query_cache SET hit_count = ?, last_accessed = datetime('now') WHERE cache_key = ?",
                (existing["hit_count"] + 1, req.cache_key),
            )
        else:
            conn.execute(
                "INSERT INTO query_cache (cache_key, sql_query, result_json) VALUES (?, ?, ?)",
                (req.cache_key, req.sql_query, req.result_json),
            )
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


@app.get("/cache/get/{cache_key}", summary="Consultar cache por key")
def get_cache(cache_key: str):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM query_cache WHERE cache_key = ?", (cache_key,)
        ).fetchone()
        if not row:
            return {"hit": False}
        conn.execute(
            "UPDATE query_cache SET hit_count = hit_count + 1, last_accessed = datetime('now') WHERE cache_key = ?",
            (cache_key,),
        )
        conn.commit()
        return {"hit": True, **dict(row)}
    finally:
        conn.close()


@app.get("/cache/hits", summary="Top queries más usadas")
def get_cache_hits(limit: int = 10):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT cache_key, sql_query, hit_count, last_accessed FROM query_cache ORDER BY hit_count DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
