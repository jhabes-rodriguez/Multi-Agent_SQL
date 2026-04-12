import json
from groq import AsyncGroq
from config import settings

# Ignorar si no hay API_KEY de momento o arrojar warning
try:
    client = AsyncGroq(api_key=settings.groq_api_key)
except Exception:
    client = None

async def interpret_message(user_message: str) -> dict:
    """
    Convierte el texto libre en JSON estructurado.
    Formato: {"action": "graph|explain|compare|list", "dataset": "nombre", "column": "columna", "chart_type": "bar|line|scatter|histogram|pie"}
    """
    if not client:
        # Mock si no hay groq disponible por key
        return {"action": "graph", "dataset": "mock", "column": "mock_col", "chart_type": "bar"}

    prompt = f"""
    Eres un asistente de análisis de datos en un sistema multi-agente. Identifica la intención de análisis de datos a partir del mensaje.
    Extrae la siguiente información y devuélvela estríctamente como un objeto JSON usando las siguientes llaves:
    - action: uno de ["graph", "explain", "compare", "list", "download", "chat"] (IMPORTANTE: Usa "chat" para saludos (hola), despedidas, o preguntas genéricas que NO involucren pedir un análisis o gráfica de datos). Usa "download" si piden bajar o buscar.
    - dataset: el exacto nombre del dataset o temática a descargar o analizar (si no especifica, null)
    - column: la columna o métrica específica mencionada (si se infiere, de otra forma null)
    - chart_type: el tipo de gráfica explícitamente pedida, uno de ["bar", "line", "scatter", "histogram", "pie"]. Si no se dice, null.

    Mensaje del usuario: "{user_message}"
    """
    
    try:
        chat_completion = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_model,
            response_format={"type": "json_object"},
            temperature=0.0
        )
        response_text = chat_completion.choices[0].message.content
        return json.loads(response_text)
    except Exception as e:
        print(f"Error interpretando mensaje: {e}")
        return {"action": "graph", "dataset": None, "column": None, "chart_type": "bar"}

async def generate_explanation(data_summary: str, original_query: str) -> str:
    """
    Genera explicación en español con insights, máximo 3 párrafos.
    """
    if not client:
        return "No processable sin llave de API."

    prompt = f"""
    Eres un analista de datos experto y súper amigable. Explica o resume esta información directo al grano.
    Si te pidieron 'dame las filas', ignora ser analista y solo escribe: "Aquí tienes los datos que solicitaste. ✨".
    Pero si piden insights o análisis, di 1 o 2 patrones importantes e interesantes usando MUCHOS EMOJIS relevantes acordes al tema (📈, 🤔, 💡, etc).
    MÁXIMO 1 PÁRRAFO CORTO (3 oraciones máximo). Responde en español directo.
    
    Petición original: "{original_query}"
    Resumen de datos: {data_summary}
    """
    
    try:
        chat_completion = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_model,
            temperature=0.7,
            max_tokens=250
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"No se pudo generar una explicación debido a un error: {e}"

async def generate_chat_response(user_message: str) -> str:
    """
    Habla de forma amigable como el Agente 3 del sistema.
    """
    if not client:
        return "Hola, soy el Agente 3. Estoy sin conexión LLM ahora mismo."

    prompt = f"""
    Eres el Agente Virtual Analista del sistema Multi-Agent SQL Workspace.
    El usuario te dice: "{user_message}"
    Responde con máximo 1 sola oración corta, muy amigable y LLENA DE EMOJIS divertidos y variados (👋📊✨🚀 etc).
    Pregunta qué base de datos desea explorar o invítalo a subir un CSV. 
    NO des explicaciones largas.
    """
    
    try:
        chat_completion = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_model,
            temperature=0.8,
            max_tokens=150
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"¡Hola! Soy el Agente. (Error interactuando con el cerebro: {e})"
