"""
orchestrator/runner.py
======================
Lanzadores de subprocesos para cada agente.
Cada agente recibe sus variables de entorno propias (API key, modelo, etc.)
inyectadas por el orquestador -- sin modificar los archivos .env de cada carpeta.
"""

import os
import sys
import time
import subprocess
import threading
from typing import Optional
from rich.console import Console

from orchestrator.config import AgentConfig, config as orch_config

console = Console()


def _build_env(agent_cfg: AgentConfig) -> dict:
    """
    Construye el entorno completo del proceso: hereda el entorno actual del sistema
    y sobreescribe/agrega las variables propias del agente.
    Siempre fuerza UTF-8 para que los emojis funcionen en Windows.
    """
    env = os.environ.copy()
    # Forzar UTF-8 en los procesos hijos (evita UnicodeEncodeError en Windows CP1252)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"]       = "1"
    env.update(agent_cfg.as_env_dict())
    return env


# ─────────────────────────────────────────────────────────────────────────────
# API CENTRAL
# ─────────────────────────────────────────────────────────────────────────────

def launch_api(wait: bool = True) -> Optional[subprocess.Popen]:
    """
    Inicia la API Central (FastAPI/Uvicorn).
    Retorna el objeto Popen para que el orquestador pueda monitorearlo.
    """
    root = os.path.dirname(os.path.dirname(__file__))
    env  = os.environ.copy()
    # Forzar UTF-8 para que Uvicorn/FastAPI no tenga problemas en Windows
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"]       = "1"
    env["PORT"]          = str(orch_config.api_port)
    env["DATABASE_PATH"] = orch_config.db_path
    env["DATASETS_DIR"]  = orch_config.datasets_dir
    env["CACHE_DB"]      = orch_config.cache_db

    console.print(f"[bold cyan]>> Iniciando API Central[/bold cyan] (puerto {orch_config.api_port})")
    proc = subprocess.Popen(
        [sys.executable, "start_api.py"],
        cwd=root,
        env=env,
    )

    if wait:
        # Esperar a que la API este lista (max 15 s)
        import requests
        for _ in range(30):
            time.sleep(0.5)
            try:
                r = requests.get(f"{orch_config.api_base_url}/health", timeout=1)
                if r.status_code == 200:
                    console.print("[green]API Central lista[/green]")
                    return proc
            except Exception:
                pass
        console.print("[yellow]API Central tardando mas de lo esperado -- continuando[/yellow]")

    return proc



# ─────────────────────────────────────────────────────────────────────────────
# AGENTE 2 -- SQL Learner
# ─────────────────────────────────────────────────────────────────────────────

def launch_agent2(interactive: bool = True) -> Optional[subprocess.Popen]:
    """
    Lanza el Agente 2 (SQL Learner) con su propia API key.
    """
    root = os.path.dirname(os.path.dirname(__file__))
    env = _build_env(orch_config.agent2)

    console.print(
        f"[bold violet]>> Iniciando {orch_config.agent2.name}[/bold violet] "
        f"[dim](key: {orch_config.agent2.groq_api_key[:8]}...)[/dim]"
    )

    kwargs = dict(cwd=root, env=env)
    if interactive:
        proc = subprocess.Popen([sys.executable, "start_agent2.py"], **kwargs)
    else:
        proc = subprocess.Popen(
            [sys.executable, "start_agent2.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs,
        )

    return proc


# ─────────────────────────────────────────────────────────────────────────────
# AGENTE 3 -- Visualizer
# ─────────────────────────────────────────────────────────────────────────────

def launch_agent3() -> Optional[subprocess.Popen]:
    """
    Lanza el Agente 3 (Visualizer / Chat web) como servidor en background.
    """
    root = os.path.dirname(os.path.dirname(__file__))
    agent_dir = os.path.join(root, "agent3_visualizer")
    env = _build_env(orch_config.agent3)
    env["PORT"] = str(orch_config.agent3.port or 8080)

    console.print(
        f"[bold magenta]>> Iniciando {orch_config.agent3.name}[/bold magenta] "
        f"[dim](puerto {orch_config.agent3.port or 8080}, key: {orch_config.agent3.groq_api_key[:8]}...)[/dim]"
    )

    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=agent_dir,
        env=env,
    )
    return proc


# ─────────────────────────────────────────────────────────────────────────────
# HELPER -- stream output de proceso en thread separado
# ─────────────────────────────────────────────────────────────────────────────

def _stream_output(proc: subprocess.Popen, prefix: str, color: str = "white"):
    """Lee stdout/stderr de un proceso en un thread y lo imprime con prefijo."""
    def _reader(stream, label):
        for line in stream:
            console.print(f"[{color}][{label}][/{color}] {line.rstrip()}")

    if proc.stdout:
        threading.Thread(target=_reader, args=(proc.stdout, prefix), daemon=True).start()
    if proc.stderr:
        threading.Thread(target=_reader, args=(proc.stderr, f"{prefix}:err"), daemon=True).start()
