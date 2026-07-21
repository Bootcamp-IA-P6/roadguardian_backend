"""Configuración del orquestador, leída del entorno en un único sitio.

Centralizarla aquí evita que os.getenv() aparezca esparcido por el código: así
hay una sola lista de lo que el servicio necesita, y falta se detecta al
arrancar y no en mitad de una petición.
"""

import os

from dotenv import load_dotenv

load_dotenv()

YOLO_API_URL = os.getenv("YOLO_API_URL", "http://localhost:7860").rstrip("/")
YOLO_SPACE = os.getenv("YOLO_SPACE", "Gemita284/roadguardian-api")

# Generoso a propósito: en Render el arranque en frío puede tardar más de un
# minuto (descarga el modelo en cada despertar). En local sobra de largo.
YOLO_TIMEOUT_SECONDS = float(os.getenv("YOLO_TIMEOUT_SECONDS", "120"))

# Tope de subida. Sin esto, cualquiera puede mandarnos un fichero de 2 GB.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "15")) * 1024 * 1024

# Orígenes autorizados para el frontend. En cuanto React viva en otro dominio,
# el navegador bloqueará las llamadas si su origen no está en esta lista.
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()
]


def check_required() -> list[str]:
    """Devuelve las variables imprescindibles que falten.

    Se llama al arrancar: más vale no levantar el servicio que descubrir que
    falta la clave a mitad de una petición de un usuario.
    """
    faltan = []
    if not os.getenv("OPENROUTER_API_KEY"):
        faltan.append("OPENROUTER_API_KEY")
    if not os.getenv("MODEL_NAME"):
        faltan.append("MODEL_NAME")
    return faltan
