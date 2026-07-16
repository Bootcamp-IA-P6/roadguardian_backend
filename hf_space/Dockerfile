# 1. Usar una imagen de Python ligera y rápida
FROM python:3.11-slim

# 2. Crear una carpeta de trabajo dentro del servidor
WORKDIR /app

# 3. Instalar dependencias ocultas del sistema que necesita OpenCV
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Copiar e instalar los requirements primero (aprovecha la caché de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el código de la API
COPY main.py .

# 6. REQUISITO ESTRICTO DE HUGGING FACE: Crear un usuario sin permisos de administrador
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# 7. Exponer el puerto por el que escuchará la API
EXPOSE 7860

# 8. Comando para arrancar el servidor web
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]