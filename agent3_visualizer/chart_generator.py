import json
from typing import List, Dict, Any
from groq import AsyncGroq
from config import settings

try:
    client = AsyncGroq(api_key=settings.groq_api_key)
except Exception:
    client = None

async def generate_chart_config(data: List[Dict[str, Any]], intent: dict, user_query: str) -> dict:
    if not data or not isinstance(data, list) or len(data) == 0:
        return {}
    
    first_row = data[0]
    columns_info = {k: type(v).__name__ for k, v in first_row.items()}
    columns_list = list(columns_info.keys())
    
    chart_type = "bar"
    x_col = columns_list[0]
    y_col = columns_list[-1] if len(columns_list) > 1 else columns_list[0]
    title = f"Visualización de Datos"
    
    if client:
        prompt = f"""
        Actúa como un experto en Plotly JS y analítica de datos.
        El usuario ha proporcionado la siguiente consulta para graficar: "{user_query}"
        
        Aquí está la estructura y primera fila de los datos devueltos por la base de datos SQL:
        {json.dumps(first_row)}
        
        Dado el contexto, decide estrictamente cuál es la MEJOR gráfica para este caso de uso y cuáles son las columnas 'x' e 'y' EXACTAMENTE COMO ESTÁN NOMBRADAS.
        Reglas:
        - Si los datos retornados YA ESTÁN agregados (ej. muestran una cuenta/COUNT o promedios por categoría), NO RECOMIENDES "histogram". Usa "bar" o "pie".
        - Usa "line" si x es una fecha/año o hay algo cronológico.
        - Usa "bar" para comparaciones de categorías vs totales/counts.
        - Devuelve estríctamente un JSON con este esquema exacto:
        {{"chart_type": "bar|line|scatter|pie", "x_col": "nombre_columna_x", "y_col": "nombre_columna_y", "title": "Titulo Bonito y Legible de la Grafica"}}
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
    y_data = [row.get(y_col) for row in data]
    
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
            "yaxis": {"title": y_col, "gridcolor": "#1e293b", "zerolinecolor": "#1e293b"},
            "margin": {"l": 50, "r": 30, "t": 60, "b": 50},
            "showlegend": True if chart_type == "pie" else False
        }
    }
    return config
