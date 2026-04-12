import os
from dotenv import load_dotenv

# Cargar .env raiz para tener todas las variables
_root_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
_local_env = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_root_env, override=False)
load_dotenv(dotenv_path=_local_env, override=True)


class Settings:
    """Configuracion del Agente 3 (Visualizer)."""
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    port: int = int(os.getenv("AGENT3_PORT", "8080"))


settings = Settings()
