"""
orchestrator/orchestrator.py
============================
Logica central del orquestador Multi-Agent.

Pipeline completo:
  0. Validar configuracion (API keys por agente)
  1. Levantar API Central (FastAPI)
  2. Ejecutar Agente 2 (SQL Learner)   -- analiza y genera insights
  3. Levantar Agente 3 (Visualizer)    -- chat web con graficas

Modos:
  --pipeline   Modo secuencial completo (API -> 2 -> 3)
  --agent2     Solo Agente 2
  --agent3     Solo Agente 3 (+ API)
  --api        Solo API Central
"""

import os
import sys
import time
import signal
import threading
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.prompt import Confirm, Prompt
from rich import box
from rich.table import Table

from orchestrator.config import config as orch_config
from orchestrator.runner import (
    launch_api,
    launch_agent2,
    launch_agent3,
    _stream_output,
)

console = Console()

# Lista global de procesos para limpieza al salir
_running_processes = []


def _register(proc):
    if proc:
        _running_processes.append(proc)
    return proc


def _cleanup():
    """Termina todos los procesos hijos al salir."""
    for proc in _running_processes:
        try:
            if proc.poll() is None:
                proc.terminate()
        except Exception:
            pass


def _setup_signal_handlers():
    """Registra handlers para Ctrl+C y seniales de terminacion."""
    def handler(sig, frame):
        console.print("\n[yellow]Senal de interrupcion recibida. Cerrando todos los procesos...[/yellow]")
        _cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT,  handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handler)


# ─────────────────────────────────────────────────────────────────────────────
# PANTALLA DE BIENVENIDA
# ─────────────────────────────────────────────────────────────────────────────

def mostrar_bienvenida():
    console.print()
    console.print(Panel(
        "[bold bright_cyan]ORQUESTADOR MULTI-AGENT[/bold bright_cyan]\n"
        "[dim]Controla el pipeline completo: SQL -> Visualizacion[/dim]\n\n"
        "[white]Agente 2[/white] [dim]->[/dim] [violet]SQL Learner[/violet]    [dim](analisis con IA)[/dim]\n"
        "[white]Agente 3[/white] [dim]->[/dim] [magenta]Visualizer[/magenta]     [dim](chat web + graficas)[/dim]",
        border_style="bright_cyan",
        padding=(1, 3),
    ))
    console.print()


def mostrar_menu() -> str:
    """Menu interactivo del orquestador. Retorna la opcion elegida."""
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, border_style="dim")
    table.add_column("Opcion", style="bold bright_cyan", justify="right")
    table.add_column("Descripcion", style="white")

    opciones = [
        ("1", "Pipeline completo  (API -> Agente 2 -> Agente 3)"),
        ("2", "Solo Agente 2      (SQL Learner -- requiere API)"),
        ("3", "Solo Agente 3      (Visualizer web -- requiere API)"),
        ("4", "Solo API Central"),
        ("5", "Ver configuracion de API keys"),
        ("q", "Salir"),
    ]

    for op, desc in opciones:
        table.add_row(op, desc)

    console.print(table)
    opcion = Prompt.ask(
        "[bold bright_cyan]Elige una opcion[/bold bright_cyan]",
        choices=["1", "2", "3", "4", "5", "q"],
    )
    return opcion


# ─────────────────────────────────────────────────────────────────────────────
# MODOS DE EJECUCION
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline():
    """
    Pipeline completo secuencial:
      API Central -> Agente 1 -> Agente 2 -> Agente 3
    """
    console.print(Rule("[bold bright_cyan]PIPELINE COMPLETO[/bold bright_cyan]"))
    console.print()

    # 0. Validar configuracion
    if not orch_config.validate():
        console.print("[red]Corrige las API keys en el .env antes de continuar.[/red]")
        return

    # 1. API Central
    console.print(Rule("[cyan]Paso 1 -- API Central[/cyan]"))
    api_proc = _register(launch_api(wait=True))

    # 3. Agente 2 (interactivo)
    console.print()
    console.print(Rule("[violet]Paso 3 -- Agente 2: SQL Learner[/violet]"))
    console.print("[dim]Analiza los datasets subidos. Escribe 'salir' cuando termines.[/dim]")
    agent2_proc = _register(launch_agent2(interactive=True))
    agent2_proc.wait()
    console.print("[violet]Agente 2 finalizado.[/violet]")

    # 4. Agente 3 (servidor web en background)
    console.print()
    console.print(Rule("[magenta]Paso 4 -- Agente 3: Visualizer[/magenta]"))
    agent3_proc = _register(launch_agent3())
    time.sleep(2)
    a3_port = orch_config.agent3.port or 8080
    console.print(f"[magenta]Visualizer disponible en -> http://localhost:{a3_port}[/magenta]")

    # 5. Esperar al usuario
    console.print()
    console.print(Panel.fit(
        f"[bold green]PIPELINE COMPLETO ACTIVO[/bold green]\n\n"
        f"  API Central -> http://localhost:{orch_config.api_port}\n"
        f"  Visualizer  -> http://localhost:{a3_port}\n\n"
        f"[dim]Presiona Ctrl+C para apagar todos los servicios.[/dim]",
        border_style="green",
    ))

    try:
        agent3_proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        _cleanup()


def run_only_api():
    """Solo levanta la API Central."""
    console.print(Rule("[cyan]API Central[/cyan]"))
    if not orch_config.validate():
        return
    api_proc = _register(launch_api(wait=True))
    console.print(f"[cyan]API en -> http://localhost:{orch_config.api_port}/docs[/cyan]")
    console.print("[dim]Ctrl+C para apagar.[/dim]")
    try:
        api_proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        _cleanup()


def run_only_agent2():
    """Levanta API + Agente 2."""
    console.print(Rule("[violet]Agente 2 -- SQL Learner[/violet]"))
    if not orch_config.validate():
        return
    _register(launch_api(wait=True))
    agent2_proc = _register(launch_agent2(interactive=True))
    try:
        agent2_proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        _cleanup()


def run_only_agent3():
    """Levanta API + Agente 3 (servidor web)."""
    console.print(Rule("[magenta]Agente 3 -- Visualizer[/magenta]"))
    if not orch_config.validate():
        return
    _register(launch_api(wait=True))
    agent3_proc = _register(launch_agent3())
    a3_port = orch_config.agent3.port or 8080
    time.sleep(2)
    console.print(f"[magenta]Visualizer en -> http://localhost:{a3_port}[/magenta]")
    console.print("[dim]Ctrl+C para apagar.[/dim]")
    try:
        agent3_proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        _cleanup()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def run(args: list = None):
    """
    Punto de entrada del orquestador.
    Acepta argumentos de linea de comandos o abre el menu interactivo.
    """
    _setup_signal_handlers()

    if args is None:
        args = sys.argv[1:]

    mostrar_bienvenida()

    if "--config" in args or "--keys" in args:
        orch_config.print_summary()
        return

    if "--pipeline" in args:
        run_pipeline()
        return

    if "--api" in args:
        run_only_api()
        return


    if "--agent2" in args:
        run_only_agent2()
        return

    if "--agent3" in args:
        run_only_agent3()
        return

    # Menu interactivo
    orch_config.print_summary()

    while True:
        opcion = mostrar_menu()

        if opcion == "q":
            console.print("[dim]Saliendo...[/dim]")
            _cleanup()
            break
        elif opcion == "1":
            run_pipeline()
            break
        elif opcion == "2":
            run_only_agent2()
            break
        elif opcion == "3":
            run_only_agent3()
            break
        elif opcion == "4":
            run_only_api()
            break
        elif opcion == "5":
            orch_config.print_summary()
