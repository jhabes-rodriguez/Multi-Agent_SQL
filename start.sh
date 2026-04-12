#!/bin/bash
# start.sh: Inicia la base de datos (API) en background, y el Frontend en foreground

echo "Iniciando API Central (Backend) en el puerto 8000..."
python start_api.py &
API_PID=$!

echo "Esperando a que la API levante..."
sleep 3

echo "Iniciando Agente Visualizador (Frontend) en el puerto 8080..."
# Nos movemos a la carpeta de agent3 para que funcione el montaje de archivos static
cd agent3_visualizer
python server.py
