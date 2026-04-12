#!/bin/bash
# start.sh: Inicia la base de datos (API) en background, y el Frontend en foreground

# Render.com inyecta su puerto publico en $PORT.
# Lo guardamos y forzamos a que la API interna siempre use 8000.
export PUBLIC_PORT=${PORT:-8080}
export PORT=8000 

echo "Iniciando API Central (Backend) en el puerto local 8000..."
python start_api.py &
API_PID=$!

echo "Esperando a que la API levante..."
sleep 3

echo "Iniciando Agente Visualizador (Frontend) en el puerto publico $PUBLIC_PORT..."
# Le decimos al Visualizer que use el puerto de Render
export AGENT3_PORT=$PUBLIC_PORT

# Nos movemos a la carpeta de agent3 para que funcione el montaje de archivos static
cd agent3_visualizer
python server.py
