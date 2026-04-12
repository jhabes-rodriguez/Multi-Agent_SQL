"""
Script de arranque de la API Central.
Ejecutar: python start_api.py
"""

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"[API] Iniciando API Central en http://localhost:{port}")
    print(f"[API] Documentacion: http://localhost:{port}/docs")
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
