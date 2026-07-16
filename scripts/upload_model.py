import os
from dotenv import load_dotenv
from huggingface_hub import HfApi

# 1. Cargar las variables del archivo .env
load_dotenv()
USER_HF = os.getenv("HF_USER")

# Comprobación de seguridad
if not os.getenv("HF_TOKEN"):
    raise ValueError("❌ No se ha encontrado HF_TOKEN en el archivo .env")

# 2. Instanciamos la API (cogerá el token automáticamente del entorno)
api = HfApi()

repo_id = f"{USER_HF}/roadguardian-model"

print("Conectando con Hugging Face...")
try:
    api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
    print(f"✅ Repositorio {repo_id} listo.")
except Exception as e:
    print(f"⚠️ Nota al crear repo: {e}")

# 3. Subir el archivo
print("🚀 Subiendo best.pt al Hub...")
api.upload_file(
    path_or_fileobj="models/best.pt",
    path_in_repo="yolo11m_roadguardian.pt",
    repo_id=repo_id,
    repo_type="model"
)
print("✅ ¡Modelo subido con éxito de forma segura!")