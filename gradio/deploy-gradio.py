import os
from dotenv import load_dotenv
from huggingface_hub import HfApi

# 1. Cargar el .env que está en la carpeta raíz (un nivel arriba)
load_dotenv(dotenv_path="../.env")

# 2. Leer las variables de entorno
USER_HF = os.getenv("HF_USER")
TOKEN = os.getenv("HF_TOKEN")
SPACE_NAME = "roadguardian-api" # El nombre que le quieras dar a la URL

# Control de seguridad
if not USER_HF or not TOKEN:
    raise ValueError("❌ Faltan HF_USER o HF_TOKEN en tu archivo .env")

REPO_ID = f"{USER_HF}/{SPACE_NAME}"
print(f"🚀 Iniciando despliegue automatizado en {REPO_ID}...")

# 3. Inicializar la API
api = HfApi(token=TOKEN)

# 4. Crear el Space automáticamente (si no existe)
api.create_repo(
    repo_id=REPO_ID,
    repo_type="space",
    space_sdk="gradio",
    exist_ok=True 
)

# 5. Subir los archivos clave
print("📦 Subiendo app.py...")
api.upload_file(
    path_or_fileobj="app.py",
    path_in_repo="app.py",
    repo_id=REPO_ID,
    repo_type="space"
)

print("📦 Subiendo requirements.txt...")
api.upload_file(
    path_or_fileobj="requirements.txt",
    path_in_repo="requirements.txt",
    repo_id=REPO_ID,
    repo_type="space"
)

print(f"✅ ¡Despliegue completado con éxito!")
print(f"🔗 Tu API estará viva en unos minutos en: https://huggingface.co/spaces/{REPO_ID}")