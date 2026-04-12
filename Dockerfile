# Usa una imagen oficial de Python ligera
FROM python:3.11-slim

# Establecer la carpeta de trabajo
WORKDIR /app

# Evitar que los archivos .pyc se escriban y que Python haga buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema requeridas 
# (por ejemplo, utilidades de compilación si algún paquete lo requiriese)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos
COPY requirements.txt .

# Instalar los requerimientos de Python globales del proyecto
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código al contenedor
COPY . .

# Exponer el puerto del Visualizador web (8080)
EXPOSE 8080

# Dar permisos de ejecución al script bash
RUN chmod +x start.sh

# Ejecutar el script que lanzará la API y el Frontend simultáneamente
CMD ["./start.sh"]
