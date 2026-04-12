# Sistema Multi-Agente para Ingestión y Análisis de Datos 🤖📊

Un poderoso sistema de inteligencia artificial compuesto por **2 agentes especializados** que interactúan entre sí a través de una **API Central (REST)**. Permite cargar bases de datos, entenderlas, convertirlas a consultas SQL desde lenguaje natural y finalmente graficarlas interactivamente.

## ✨ Características Principales

*   **Ingestión Directa**: Carga manual de datasets desde el panel web. Limpieza de CSV automática al ingresarlos para evitar errores de formato.
*   **Natural Language to SQL (NL2SQL)**: Traduce tus preguntas ("¿Cuál es el salario promedio por puesto?") a consultas analíticas SQL instantáneas.
*   **Generación de Gráficas Automática (Visualizer)**: Interpreta tus resultados SQL y genera automáticamente el formato más apto (barras, líneas, dispersión) renderizado de forma interactiva en la web.
*   **Insights y Estadísticas**: Análisis por IA del significado profundo de los datos para no solo listar números, sino *explicar* tendencias e insights ocultos.
*   **Caché Avanzado**: Las consultas frecuentes se responden de forma inmediata usando base de datos local sin sobrecargar al modelo de IA.

---

## 🏗️ Arquitectura y Flujo de Trabajo

El sistema está orquestado mediante módulos independientes que se desacoplan, asegurando estabilidad y escalabilidad:

```mermaid
graph TD
    USER((Usuario)) -->|Sube Datasets CSV por Interfaz Web| A3
    A3[Agent 3: Visualizer] <-->|Consulta Históricos y Genera UI Web| API
    API(API Central - localhost:8000) --- SQLite[(Local SQLite DB)]
    A2[Agent 2: SQL Learner] <-->|Lee y Guarda Queries y NLP| API
    USER -->|Interactúa y Visualiza en Chat Web| A3
    USER -->|Comandos CLI (Opcional)| A2
```

*   **API Central** (FastAPI): Centro de persistencia de todo el proyecto. Trabaja de forma asíncrona contra una base de datos local (SQLite). Alimenta a todos los agentes.
*   **Agent 2 SQL Learner (agent2_sql_learner)**: Interfaz de comandos interactivo y cerebro backend que domina Groq LLM (LLAMA-3) para inferir queries SQL exactas ante las preguntas del usuario.
*   **Agent 3 Visualizer (agent3_visualizer)**: Aplicación Full-Stack. Construida en HTML/JS y servida en Python que le permite al usuario chatear, visualizar tablas dinámicas interactuables, ver gráficas ricas y montar la analítica visual.

---

## 🚀 Requisitos

- **Python 3.10+**
- **Clave API de Groq** (gratuita)

## 🛠️ Instalación y Configuración

1. **Clonar Repositorio**:
   ```bash
   git clone <repo-url>
   cd Multi-Agent
   ```

2. **Crear y activar el Entorno Virtual**:
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En Mac/Linux:
   source venv/bin/activate
   ```

3. **Inyectar Variables de Entorno**:
   Renombra `.env.example` a `.env` en la raíz y establece tu API Key maestra.
   ```env
   GROQ_API_KEY=gsk_xyz............
   GROQ_MODEL=llama-3.3-70b-versatile
   API_BASE_URL=http://localhost:8000
   PORT=8000
   AGENT3_PORT=8080
   ```

4. **Instalar Dependencias Globales**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Importante: No hace falta instalar los requerimientos en los directorios individuales, instalar los de la raíz cubrirá todo el ecosistema)*

---

## 🎮 Ejecución Recomendada: El Orquestador

Para evitar tener terminales separadas, el **Orquestador Centraliza Todo**. Simplemente ejecuta:

```bash
python start_orchestrator.py
```
*Se mostrará un Menú Interactivo en la terminal.* Podrás arrancar todos tus agentes o lanzarlos individualmente.

**Comandos CLI rápidos del Orquestador:**
*   `python start_orchestrator.py --pipeline` : Ejecuta todo el sistema (API -> Agente 2 -> Agente 3).
*   `python start_orchestrator.py --api` : Encender puramente la base API.
*   `python start_orchestrator.py --agent3` : Enciende la API en background + Servidor de UI web de manera inmediata.

*(Accede al frontend interactivo en tu navegador desde: `http://localhost:8080` tras arrancar el Agente 3).*

---

## 💻 Ejemplos de Interacción en el Chat

Una vez abras tu Panel de Control Visual, puedes intentar:
1. *"¿Cuál es la tendencia del salario base de todos los gerentes registrados?"* -> Generará la SQL y retornará los resultados junto a una gráfica de regresión o línea de tiempo.
2. *"Muestra las ventas anuales por producto ordenadas de mayor a menor"* -> Generará grafica de barras.
3. *"Genera una tabla agrupando el promedio de edad por departamento"*
4. *"Sugerir"* -> Le dirá al cerebro de IA que analice la Metadata de todos los CSV alojados, y te provea con 5 preguntas ocultas que puedes investigar en los datos.

---

## 📡 API Reference (Ejemplos cURL)

La API puede ser interconectada a futuro muy fácilmente. Está documentada vía Swagger (OpenAPI) en `http://localhost:8000/docs`.

**1. Ver un JSON de Datasets listos en el motor:**
```bash
curl -X GET http://localhost:8000/datasets/list
```

**2. Evaluar desempeño y aciertos del Caché:**
```bash
curl -X GET http://localhost:8000/cache/hits
```
---

## 📁 Estructura del Sistema

```
Multi-Agent/
├── agent2_sql_learner/   # Cerebro de traducción de lenguaje NL a SQL 
├── agent3_visualizer/    # Inferencia final, gráficas y frontend
├── api/                  # Servidor de persistencia FastAPI (SQLite DB)
├── orchestrator/         # Modulo administrador del sistema Multiprocesamiento
├── data/                 # Caché y Bases de Datos (Ignorado en GIT local)
├── start_api.py          # Entrypoint de API aislada
├── start_agent2.py       # Entrypoint interactivo de Agente 2
└── start_orchestrator.py # Lanzador Maestro ⭐️
```
