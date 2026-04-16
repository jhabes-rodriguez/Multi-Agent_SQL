import json
from typing import List, Dict, Any
from groq import AsyncGroq
from config import settings

try:
    client = AsyncGroq(api_key=settings.groq_api_key)
except Exception:
    client = None

def parse_time_to_numeric(val: Any) -> Any:
    """Convierte strings de tiempo (H:MM, M:SS) a minutos (float) para graficar."""
    if not isinstance(val, str) or ":" not in val:
        return val
    try:
        parts = val.split(":")
        if len(parts) == 2:  # MM:SS o H:MM
            return int(parts[0]) + (int(parts[1]) / 60.0)
        elif len(parts) == 3:  # H:MM:SS
            return (int(parts[0]) * 60) + int(parts[1]) + (int(parts[2]) / 60.0)
    except Exception:
        return val
    return val

def get_semantic_hint(col: str) -> str:
    """Identifica el propósito de la columna para guiar al grafico."""
    name = col.lower()
    if any(k in name for k in ["view", "hit", "popul", "visto"]):
        return "Métrica de popularidad (RECOMENDADA para ránkings de 'más vistos')"
    if any(k in name for k in ["runtime", "durat", "time", "len"]):
        return "Duración/Tiempo (SOLO si piden duración, NO para popularidad)"
    if any(k in name for k in ["date", "year", "lanz"]):
        return "Fecha o serie temporal"
    return ""

async def generate_chart_config(data: List[Dict[str, Any]], intent: dict, user_query: str) -> dict:
    if not data or not isinstance(data, list) or len(data) == 0:
        return {}
    
    first_row = data[0]
    columns_list = list(first_row.keys())
    
    # Construir metadatos de columnas con pistas semánticas
    cols_metadata = []
    for col in columns_list:
        hint = get_semantic_hint(col)
        cols_metadata.append(f"- {col} (Tipo: {type(first_row[col]).__name__}) {'| PISTA: ' + hint if hint else ''}")
    
    cols_str = "\n".join(cols_metadata)
    
    chart_type = "bar"
    x_col = columns_list[0]
    y_col = columns_list[-1] if len(columns_list) > 1 else columns_list[0]
    title = f"Visualización de Datos"
    
    if client:
        prompt = f"""
        Actúa como un experto en Plotly JS y analítica de datos.
        El usuario ha proporcionado la siguiente consulta: "{user_query}"
        
        COLUMNAS DISPONIBLES EN LOS DATOS:
        {cols_str}
        
        REGLAS DE SELECCIÓN:
        1. Si el usuario pide "más vistos", "Top películas", etc., la columna 'y' DEBE ser una de popularidad (ej. Views, Hits).
        2. NO uses 'Runtime' (duración) para ránkings de popularidad a menos que se pida explícitamente duración.
        3. Identifica la mejor columna para el eje X (usualmente nombres de series/películas/categorías).
        
        Devuelve estrictamente un JSON con este esquema:
        {{"chart_type": "bar|line|scatter|pie", "x_col": "nombre_columna_x", "y_col": "nombre_columna_y", "title": "Titulo descriptivo"}}
        """
        try:
            chat_completion = await client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.groq_model,
                response_format={"type": "json_object"},
                temperature=0.1
            )
            resp = json.loads(chat_completion.choices[0].message.content)
            chart_type = resp.get("chart_type", "bar")
            x_col = resp.get("x_col", x_col)
            y_col = resp.get("y_col", y_col)
            title = resp.get("title", title)
        except Exception:
            pass

    # Prevenir fallos si las columnas inventadas no existen en los datos
    if x_col not in first_row: x_col = columns_list[0]
    if y_col not in first_row: y_col = columns_list[-1] if len(columns_list) > 1 else columns_list[0]

    x_data = [row.get(x_col) for row in data]
    raw_y_data = [row.get(y_col) for row in data]
    
    # Intentar convertir datos de Y a números si son tiempos
    y_data = [parse_time_to_numeric(v) for v in raw_y_data]
    
    # Detectar si se hizo conversión para ajustar el label
    y_label = y_col
    if any(isinstance(v, str) and ":" in v for v in raw_y_data[:5]):
         if any(isinstance(v, (int, float)) for v in y_data[:5]):
             y_label = f"{y_col} (convertido a minutos)"
    
    trace = {}
    
    if chart_type == "bar":
        trace = {"type": "bar", "x": x_data, "y": y_data, "marker": {"color": "#7c3aed", "opacity": 0.8}}
    elif chart_type == "line":
        trace = {"type": "scatter", "mode": "lines+markers", "x": x_data, "y": y_data, "line": {"color": "#10b981", "width": 3}}
    elif chart_type == "scatter":
        trace = {"type": "scatter", "mode": "markers", "x": x_data, "y": y_data, "marker": {"color": "#f59e0b", "size": 10}}
    elif chart_type == "pie":
        trace = {"type": "pie", "labels": x_data, "values": y_data, "hole": 0.4}
    else:
        # Fallback a bar
        trace = {"type": "bar", "x": x_data, "y": y_data, "marker": {"color": "#7c3aed"}}

    config = {
        "data": [trace],
        "layout": {
            "title": {"text": title, "font": {"color": "#f1f5f9", "size": 18, "family": "Inter"}},
            "paper_bgcolor": "#16213e",
            "plot_bgcolor": "#16213e",
            "font": {"color": "#94a3b8", "family": "Inter, sans-serif"},
            "xaxis": {"title": x_col, "gridcolor": "#1e293b", "zerolinecolor": "#1e293b"},
            "yaxis": {"title": y_label, "gridcolor": "#1e293b", "zerolinecolor": "#1e293b"},
            "margin": {"l": 50, "r": 30, "t": 60, "b": 50},
            "showlegend": True if chart_type == "pie" else False
        }
    }
    return config
