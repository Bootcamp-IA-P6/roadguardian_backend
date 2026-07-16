import os
from dotenv import load_dotenv
from huggingface_hub import HfApi

# 1. Cargar credenciales seguras
load_dotenv()

USER_HF = os.getenv("HF_USER")

if not os.getenv("HF_TOKEN"):
    raise ValueError("❌ No se ha encontrado HF_TOKEN en el archivo .env")

api = HfApi()

# Cambia esto por tu usuario y el nombre que le quieras dar a tu API en HF
SPACE_ID = f"{USER_HF}/roadguardian-api" 

print(f"📡 Conectando con Hugging Face Spaces...")

# 2. Crea el Space (tipo Docker) si no existe
try:
    api.create_repo(
        repo_id=SPACE_ID, 
        repo_type="space", 
        space_sdk="docker", 
        exist_ok=True
    )
    print(f"✅ Space {SPACE_ID} preparado.")
except Exception as e:
    print(f"⚠️ Nota al crear Space: {e}")

# 3. Sube toda la carpeta hf_space de golpe
print("🚀 Subiendo el código de la API...")
api.upload_folder(
    folder_path="../hf_space", # Ruta relativa a la carpeta del microservicio
    repo_id=SPACE_ID,
    repo_type="space"
)

print(f"✅ ¡API desplegada con éxito!")
print(f"🌍 Tu microservicio estará disponible en: https://huggingface.co/spaces/{SPACE_ID}")