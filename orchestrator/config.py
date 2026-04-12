"""
orchestrator/config.py
======================
Gestión centralizada de API keys y configuración por agente.

Cada agente tiene su propia sección en el .env raíz:
  AGENT2_GROQ_API_KEY   → Agente 2 (SQL Learner)
  AGENT3_GROQ_API_KEY   → Agente 3 (Visualizer)

Si solo existe GROQ_API_KEY (fallback), todos los agentes la comparten.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Cargar .env desde la raíz del proyecto
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=_env_path, override=True)

console = Console()


@dataclass
class AgentConfig:
    """Configuración completa de un agente individual."""
    name: str
    agent_id: int
    groq_api_key: str
    groq_model: str
    api_base_url: str
    port: Optional[int] = None
    # Agente 3 extras
    frontend_port: Optional[int] = None

    def as_env_dict(self) -> dict:
        """Devuelve un diccionario de variables de entorno para inyectar al proceso del agente."""
        env = {
            "GROQ_API_KEY":  self.groq_api_key,
            "GROQ_MODEL":    self.groq_model,
            "API_BASE_URL":  self.api_base_url,
        }
        if self.port is not None:
            env["PORT"] = str(self.port)

        return env

    def is_valid(self) -> bool:
        """Verifica que la configuración mínima esté completa."""
        return bool(self.groq_api_key and self.api_base_url)


def _get(key: str, *fallbacks: str, default: str = "") -> str:
    """Lee una variable de entorno con fallbacks en orden."""
    for k in [key, *fallbacks]:
        val = os.getenv(k, "").strip()
        if val:
            return val
    return default


class OrchestratorConfig:
    """
    Configuración maestra del orquestador.
    Lee el .env raíz y distribuye las API keys correctas a cada agente.
    """

    def __init__(self):
        # Fallback compartido (si no se definen keys por agente)
        _shared_groq_key   = _get("GROQ_API_KEY")
        _shared_groq_model = _get("GROQ_MODEL", default="llama-3.3-70b-versatile")
        _api_base_url      = _get("API_BASE_URL", default="http://localhost:8000")


        # ── Agente 2 — SQL Learner ─────────────────────────────────────────
        self.agent2 = AgentConfig(
            name         = "Agente 2 - SQL Learner",
            agent_id     = 2,
            groq_api_key = _get("AGENT2_GROQ_API_KEY", "GROQ_API_KEY", default=_shared_groq_key),
            groq_model   = _get("AGENT2_GROQ_MODEL",   "GROQ_MODEL",   default=_shared_groq_model),
            api_base_url = _get("AGENT2_API_BASE_URL", "API_BASE_URL", default=_api_base_url),
        )

        # ── Agente 3 — Visualizer ──────────────────────────────────────────
        self.agent3 = AgentConfig(
            name         = "Agente 3 - Visualizer",
            agent_id     = 3,
            groq_api_key = _get("AGENT3_GROQ_API_KEY", "GROQ_API_KEY", default=_shared_groq_key),
            groq_model   = _get("AGENT3_GROQ_MODEL",   "GROQ_MODEL",   default=_shared_groq_model),
            api_base_url = _get("AGENT3_API_BASE_URL", "API_BASE_URL", default=_api_base_url),
            port         = int(_get("AGENT3_PORT", "PORT", default="8080")),
        )

        # ── API Central ────────────────────────────────────────────────────
        self.api_port    = int(_get("PORT", default="8000"))
        self.api_base_url = _api_base_url
        self.db_path      = _get("DATABASE_PATH",  default="./data/multiagent.db")
        self.datasets_dir = _get("DATASETS_DIR",   default="./data/datasets")
        self.cache_db     = _get("CACHE_DB",        default="./data/cache.db")

    def all_agents(self) -> list[AgentConfig]:
        return [self.agent2, self.agent3]

    def validate(self) -> bool:
        """Valida la configuración de todos los agentes y reporta problemas."""
        all_valid = True
        for agent in self.all_agents():
            if not agent.is_valid():
                console.print(f"[red]❌ {agent.name}: Configuración inválida — falta GROQ_API_KEY o API_BASE_URL[/red]")
                all_valid = False
        return all_valid

    def print_summary(self):
        """Imprime en pantalla un resumen de la configuracion de cada agente."""
        table = Table(
            title="Configuracion de API Keys por Agente",
            box=box.ROUNDED,
            border_style="bright_cyan",
            header_style="bold bright_cyan",
            show_lines=True,
        )
        table.add_column("Agente",    style="bold white")
        table.add_column("Groq Key",  style="yellow")
        table.add_column("Modelo",    style="cyan")
        table.add_column("API URL",   style="dim")
        table.add_column("Estado",    justify="center")

        for agent in self.all_agents():
            masked_key = (
                agent.groq_api_key[:8] + "..." + agent.groq_api_key[-4:]
                if len(agent.groq_api_key) > 12
                else "[red]NO CONFIGURADA[/red]"
            )
            estado = "[green]OK[/green]" if agent.is_valid() else "[red]ERROR[/red]"
            table.add_row(
                agent.name,
                masked_key,
                agent.groq_model,
                agent.api_base_url,
                estado,
            )

        console.print()
        console.print(table)
        console.print()


# Singleton global
config = OrchestratorConfig()
