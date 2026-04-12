import httpx
from typing import Dict, Any, List
from config import settings


async def fetch_datasets() -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(f"{settings.api_base_url}/datasets/list")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching datasets: {e}")
            return []


async def fetch_query_history() -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(f"{settings.api_base_url}/queries/history")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return []


async def fetch_latest_insight() -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(f"{settings.api_base_url}/insights/latest")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {}


async def run_query(query: str, intent: dict) -> Any:
    """
    Ejecuta una consulta SQL en memoria.
    Interpreta qué dataset usar según la intención extraída o usa el más reciente por defecto.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # 1. Obtener datasets disponibles
            ds_resp = await client.get(f"{settings.api_base_url}/datasets/list")
            ds_resp.raise_for_status()
            datasets = ds_resp.json()

            import re
            
            datasets_data_list = []
            
            for ds in datasets:
                ds_id = ds["id"]
                raw_name = ds["name"].replace("-", "_").replace(" ", "_")
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '', raw_name)
                table_name = f"ds_{safe_name}"
                
                # Obtener TODOS los datos del dataset (sin truncar a 500)
                data_resp = await client.get(
                    f"{settings.api_base_url}/datasets/{ds_id}/data",
                    params={"limit": 10000000},
                )
                if data_resp.status_code == 200:
                    raw_data = data_resp.json().get("data", [])
                    if raw_data:
                        datasets_data_list.append((table_name, raw_data))

            if not datasets_data_list:
                return {"error": "Los datasets disponibles están vacíos o no se pudieron descargar."}

            # 3. Cargar TODO en SQLite y generar esquema global
            from query_engine import load_all_to_sqlite, nl_to_sql, execute_sql

            conn, global_schema = load_all_to_sqlite(datasets_data_list)

            # 4. NL -> SQL con Groq
            sql = await nl_to_sql(query, global_schema)

            # 5. Ejecutar SQL
            try:
                results = execute_sql(conn, sql)
            except Exception as sql_e:
                conn.close()
                return {"error": f"Error SQL: {type(sql_e).__name__} - {str(sql_e)}\nQuery intentada: {sql}"}
                
            conn.close()

            return results

    except Exception as e:
        print(f"Error running query: {e}")
        return {"error": f"Error general al procesar la API: {type(e).__name__} - {str(e)}"}
