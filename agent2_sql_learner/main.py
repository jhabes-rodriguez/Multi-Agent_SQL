"""
Agent 2 — SQL Learner
Interfaz principal de terminal con menú interactivo.

Flujo:
  1. Conectar con la API Central
  2. Elegir un dataset
  3. Hacer split train/test
  4. Hacer preguntas en lenguaje natural → Groq → SQL → Resultado
  5. Ver insights y cache
"""

import os
import sys
import json
import sqlite3
from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.rule import Rule

from agent2_sql_learner.sql_engine   import (
    cargar_dataset_desde_api,
    montar_en_sqlite,
    ejecutar_query,
    hacer_split,
    estadisticas_basicas,
    obtener_esquema,
    listar_datasets_api,
)
from agent2_sql_learner.groq_client  import (
    nl_to_sql,
    generar_insight,
    analizar_split,
    sugerir_queries,
)
from agent2_sql_learner.cache        import (
    buscar_en_cache,
    guardar_en_cache,
    top_queries_cacheadas,
    limpiar_cache,
)
from agent2_sql_learner.insights     import (
    resumen_dataset,
    comparar_train_test,
    guardar_insight_api,
    guardar_query_api,
)

console = Console()

# ─────────────────────────────────────────────
# HELPERS de visualización
# ─────────────────────────────────────────────

def mostrar_bienvenida():
    console.print()
    console.print(Panel.fit(
        "[bold violet]🧠  Agent 2 — SQL Learner[/bold violet]\n"
        "[dim]Powered by Groq · llama-3.3-70b-versatile · SQLite3[/dim]",
        border_style="bright_magenta",
    ))
    console.print()


def mostrar_tabla_resultados(datos: list[dict], titulo: str = "Resultados"):
    if not datos:
        console.print("[yellow]⚠  Sin resultados para esta query.[/yellow]")
        return

    tabla = Table(
        title=titulo,
        box=box.ROUNDED,
        border_style="bright_cyan",
        header_style="bold bright_cyan",
        show_lines=True,
    )

    for col in datos[0].keys():
        tabla.add_column(str(col), overflow="fold")

    for fila in datos[:50]:  # Máximo 50 filas en pantalla
        tabla.add_row(*[str(v) for v in fila.values()])

    console.print(tabla)
    if len(datos) > 50:
        console.print(f"[dim]... y {len(datos) - 50} filas más[/dim]")


def mostrar_datasets(datasets: list[dict]):
    tabla = Table(
        title="📁 Datasets Disponibles",
        box=box.ROUNDED,
        border_style="bright_green",
        header_style="bold bright_green",
    )
    tabla.add_column("ID",          style="bold white", justify="right")
    tabla.add_column("Nombre",      style="cyan")
    tabla.add_column("Filas",       justify="right")
    tabla.add_column("Columnas",    justify="right")
    tabla.add_column("Descripción", style="dim")

    for ds in datasets:
        tabla.add_row(
            str(ds["id"]),
            ds["name"],
            str(ds.get("rows_count", "?")),
            str(ds.get("columns_count", "?")),
            ds.get("description", "")[:50],
        )
    console.print(tabla)


# ─────────────────────────────────────────────
# FLUJO PRINCIPAL
# ─────────────────────────────────────────────

def elegir_dataset() -> tuple[int, str]:
    """Muestra listado de datasets y permite elegir uno."""
    with Progress(SpinnerColumn(), TextColumn("[cyan]Conectando con API Central..."), transient=True) as p:
        p.add_task("", total=None)
        try:
            datasets = listar_datasets_api()
        except Exception as e:
            console.print(f"[red]❌ No se pudo conectar con la API Central: {e}[/red]")
            console.print("[dim]Asegúrate de que la API esté corriendo: python start_api.py[/dim]")
            sys.exit(1)

    if not datasets:
        console.print("[yellow]⚠  No hay datasets disponibles. Pide a la Compañera A que suba uno primero.[/yellow]")
        sys.exit(0)

    mostrar_datasets(datasets)
    console.print()

    ids_validos = [str(ds["id"]) for ds in datasets]
    dataset_id = IntPrompt.ask(
        "[bold]Elige el ID del dataset[/bold]",
        console=console,
    )

    seleccionado = next((ds for ds in datasets if ds["id"] == dataset_id), None)
    if not seleccionado:
        console.print("[red]ID no válido.[/red]")
        sys.exit(1)

    return dataset_id, seleccionado["name"]


def cargar_y_preparar(dataset_id: int, nombre: str):
    """Descarga el dataset, monta SQLite, hace split, muestra resumen."""
    console.print()
    console.print(Rule(f"[bold cyan]Cargando: {nombre}[/bold cyan]"))

    with Progress(SpinnerColumn(), TextColumn("[cyan]Descargando datos..."), transient=True) as p:
        p.add_task("", total=None)
        df, schema = cargar_dataset_desde_api(dataset_id)

    console.print(f"[green]✅ Dataset cargado:[/green] {len(df):,} filas · {len(df.columns)} columnas")

    # Split train/test
    train_df, test_df = hacer_split(df)
    console.print(f"[green]✅ Split:[/green] Train = {len(train_df):,} filas · Test = {len(test_df):,} filas")

    # Montar ambos en SQLite en memoria
    tabla = nombre.replace("-", "_").replace(" ", "_")
    conn_train = montar_en_sqlite(train_df, tabla)
    conn_test  = montar_en_sqlite(test_df,  tabla + "_test")

    # Esquema para el LLM
    esquema = obtener_esquema(df, tabla)

    # Resumen estadístico con Groq
    console.print()
    console.print(Rule("[bold magenta]Análisis del Split[/bold magenta]"))
    with Progress(SpinnerColumn(), TextColumn("[magenta]Analizando con Groq..."), transient=True) as p:
        p.add_task("", total=None)
        analisis = analizar_split(
            nombre_dataset      = nombre,
            total_filas         = len(df),
            train_filas         = len(train_df),
            test_filas          = len(test_df),
            columnas            = list(df.columns),
            estadisticas_train  = estadisticas_basicas(train_df),
            estadisticas_test   = estadisticas_basicas(test_df),
        )

    console.print(Panel(analisis, title="[bold]📊 Análisis Train/Test[/bold]", border_style="magenta"))

    # Guardar insight del split en la API
    guardar_insight_api(
        dataset_id = dataset_id,
        titulo     = f"Análisis Train/Test — {nombre}",
        contenido  = analisis,
    )

    return df, train_df, test_df, conn_train, esquema, tabla


def sugerir_y_mostrar_preguntas(nombre: str, esquema: str):
    """Muestra 5 preguntas sugeridas por el LLM."""
    with Progress(SpinnerColumn(), TextColumn("[dim]Generando sugerencias..."), transient=True) as p:
        p.add_task("", total=None)
        preguntas = sugerir_queries(nombre, esquema)

    console.print()
    console.print("[bold dim]💡 Preguntas sugeridas:[/bold dim]")
    for i, p in enumerate(preguntas, 1):
        console.print(f"  [dim]{i}.[/dim] [italic]{p}[/italic]")
    console.print()


def loop_consultas(
    dataset_id: int,
    nombre:     str,
    conn:       sqlite3.Connection,
    esquema:    str,
    tabla:      str,
):
    """Bucle principal de consultas en lenguaje natural."""
    console.print(Rule("[bold cyan]Modo Consulta[/bold cyan]"))
    console.print("[dim]Escribe tu pregunta en español. Comandos: [bold]cache[/bold] · [bold]historial[/bold] · [bold]sugerir[/bold] · [bold]salir[/bold][/dim]")
    console.print()

    while True:
        pregunta = Prompt.ask("[bold bright_cyan]❓ Tu pregunta[/bold bright_cyan]").strip()

        if not pregunta:
            continue

        if pregunta.lower() == "salir":
            break

        if pregunta.lower() == "cache":
            top = top_queries_cacheadas(10)
            if not top:
                console.print("[dim]Cache vacío.[/dim]")
            else:
                t = Table(title="🗂  Top Queries Cacheadas", box=box.SIMPLE, border_style="dim")
                t.add_column("Hits", justify="right", style="bold yellow")
                t.add_column("SQL",  style="dim")
                for row in top:
                    t.add_row(str(row["hit_count"]), row["sql_query"][:80])
                console.print(t)
            continue

        if pregunta.lower() == "sugerir":
            sugerir_y_mostrar_preguntas(nombre, esquema)
            continue

        if pregunta.lower() == "historial":
            import requests
            try:
                resp = requests.get(f"{os.getenv('API_BASE_URL','http://localhost:8000')}/queries/history?limit=10")
                historial = resp.json()
                t = Table(title="📜 Historial de Queries", box=box.SIMPLE, border_style="dim")
                t.add_column("ID",      justify="right", style="bold")
                t.add_column("Dataset", style="cyan")
                t.add_column("Pregunta",style="white")
                t.add_column("Tiempo",  justify="right", style="dim")
                for q in historial:
                    t.add_row(str(q["id"]), q.get("dataset_name","?"), q["natural_language"][:60], f"{q['execution_time']}s")
                console.print(t)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
            continue

        # Verificar cache
        cached = buscar_en_cache(dataset_id, pregunta)
        if cached:
            console.print(f"[dim green]⚡ Cache hit — uso #{cached['hit_count']}[/dim green]")
            console.print(f"[dim]SQL: {cached['sql_query']}[/dim]")
            mostrar_tabla_resultados(cached["result"], f"Resultado (cache): {pregunta[:40]}...")
            console.print()
            continue

        # Traducir a SQL con Groq
        with Progress(SpinnerColumn(), TextColumn("[cyan]Generando SQL..."), transient=True) as p:
            p.add_task("", total=None)
            try:
                sql = nl_to_sql(pregunta, esquema, tabla)
            except Exception as e:
                console.print(f"[red]❌ Error con Groq: {e}[/red]")
                continue

        console.print(f"[dim]SQL generado → [bold]{sql}[/bold][/dim]")

        # Ejecutar SQL
        try:
            resultado, tiempo = ejecutar_query(conn, sql)
        except ValueError as e:
            console.print(f"[red]❌ {e}[/red]")

            # Intentar corregir con Groq
            if Confirm.ask("[yellow]¿Intentar corregir la query automáticamente?[/yellow]"):
                with Progress(SpinnerColumn(), TextColumn("[yellow]Corrigiendo..."), transient=True) as p:
                    p.add_task("", total=None)
                    sql_corregido = nl_to_sql(
                        f"Corrige este error y responde: {pregunta}\nError anterior: {e}",
                        esquema, tabla,
                    )
                try:
                    resultado, tiempo = ejecutar_query(conn, sql_corregido)
                    sql = sql_corregido
                    console.print(f"[green]✅ SQL corregido: {sql}[/green]")
                except ValueError as e2:
                    console.print(f"[red]❌ No se pudo corregir: {e2}[/red]")
                    continue
            else:
                continue

        mostrar_tabla_resultados(resultado, f"Resultado: {pregunta[:50]}")
        console.print(f"[dim]⏱  Tiempo de ejecución: {tiempo}s · {len(resultado)} filas[/dim]")

        # Guardar en cache
        guardar_en_cache(dataset_id, pregunta, sql, resultado)

        # Generar insight
        if resultado and Confirm.ask("[cyan]¿Generar insight con IA?[/cyan]", default=True):
            with Progress(SpinnerColumn(), TextColumn("[magenta]Generando insight..."), transient=True) as p:
                p.add_task("", total=None)
                insight_texto = generar_insight(pregunta, sql, resultado, nombre)

            console.print(Panel(
                insight_texto,
                title=f"[bold magenta]🔍 Insight[/bold magenta]",
                border_style="magenta",
            ))

            # Guardar en API
            query_id = guardar_query_api(dataset_id, pregunta, sql, resultado, tiempo)
            guardar_insight_api(
                dataset_id = dataset_id,
                titulo     = f"Insight: {pregunta[:60]}",
                contenido  = insight_texto,
                query_id   = query_id,
            )
            console.print("[dim green]✅ Insight guardado en la API Central[/dim green]")

        console.print()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    mostrar_bienvenida()

    dataset_id, nombre = elegir_dataset()
    df, train_df, test_df, conn_train, esquema, tabla = cargar_y_preparar(dataset_id, nombre)

    # Preguntas sugeridas al inicio
    sugerir_y_mostrar_preguntas(nombre, esquema)

    # Loop de consultas (sobre el conjunto de entrenamiento)
    loop_consultas(dataset_id, nombre, conn_train, esquema, tabla)

    console.print()
    console.print(Panel.fit(
        "[bold green]👋 ¡Hasta luego! Los insights fueron guardados en la API Central.[/bold green]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
