import uvicorn
import json
import os
import sys
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import BaseModel
from config import settings
from api_client import fetch_datasets, fetch_query_history, run_query
from explainer import interpret_message, generate_explanation, generate_chat_response
import subprocess
from chart_generator import generate_chart_config
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Agent 3: Visualizer & Explainer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

def dict_to_md_table(data_list):
    if not data_list or not isinstance(data_list, list): return ""
    cols = list(data_list[0].keys())
    md = "\n\n|" + "|".join(cols) + "|\n"
    md += "|" + "|".join(["---"] * len(cols)) + "|\n"
    for row in data_list:
        md += "|" + "|".join([str(row.get(c, ""))[:100] for c in cols]) + "|\n"
    return md

@app.post("/api/process")
async def process_message(request: ChatRequest):
    intent = await interpret_message(request.message)
    
    if intent.get("action") == "chat":
        chat_reply = await generate_chat_response(request.message)
        return {
            "intent": intent,
            "chart_config": None,
            "explanation": chat_reply
        }
        
    if intent.get("action") == "download":
        return {
            "intent": intent,
            "chart_config": None,
            "explanation": "⚠️ **El modo descarga automática (scraping) ha sido deshabilitado.**\n\nPor favor, **usa el botón de cargar base de datos** (📎) situado en el cuadro de texto abajo a la izquierda para subir tus archivos locales `.csv`."
        }
    data = await run_query(request.message, intent)
    
    if isinstance(data, dict) and "error" in data:
        return {"error": data["error"]}
        
    chart_config = None
    if intent.get("action") == "graph" or intent.get("chart_type") is not None:
        chart_config = await generate_chart_config(data, intent, request.message)
    
    md_table = ""
    if isinstance(data, list) and data:
        md_table = dict_to_md_table(data[:15]) # Máximo 15 filas en la tablita UI
        
    # Saltarse los insights pesados si el usuario solo pidio listar datos
    if intent.get("action") in ["list", "query"]:
        explanation = "Aquí tienes la información solicitada en base a tu consulta:\n" + md_table
    else:
        # Generar un párrafo de insights usando el LLM
        data_summary = json.dumps(data[:5]) if isinstance(data, list) else str(data)
        explanation = await generate_explanation(data_summary, request.message)
        explanation += md_table
    
    return {
        "intent": intent,
        "chart_config": chart_config,
        "explanation": explanation
    }

@app.post("/api/datasets/upload")
async def proxy_upload(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    source_url: str = Form(""),
    votes: int = Form(0)
):
    async with httpx.AsyncClient() as client:
        data = {
            "name": name,
            "description": description,
            "source_url": source_url,
            "votes": str(votes),
        }
        file_content = await file.read()
        files = {
            "file": (file.filename, file_content, file.content_type)
        }
        resp = await client.post(f"{settings.api_base_url}/datasets/upload", data=data, files=files)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()

@app.get("/api/datasets")
async def get_datasets():
    return await fetch_datasets()

@app.post("/api/session/reset")
async def session_reset():
    """Proxy para reiniciar la sesión en la API central."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{settings.api_base_url}/session/reset")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()

# Crear frontend dir temporalmente si no existe para que fastapi mount no falle
os.makedirs("frontend", exist_ok=True)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=settings.port)
