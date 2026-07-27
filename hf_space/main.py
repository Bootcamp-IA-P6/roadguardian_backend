import os
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File
from huggingface_hub import hf_hub_download
from ultralytics import YOLO
from dotenv import load_dotenv

# 1. Cargar las variables del entorno
load_dotenv()

# Comprobación de seguridad para evitar arrancar a ciegas
USER_HF = os.getenv("HF_USER")
if not USER_HF:
    raise ValueError("❌ Falla crítica: No se ha definido HF_USER en el entorno.")

app = FastAPI(
    title="RoadGuardian AI Microservice", 
    description="API dedicada exclusivamente a la inferencia de daños en asfalto con YOLO11m"
)

# --- CONFIGURACIÓN DINÁMICA ---
# Ahora se construye sola usando la variable de entorno
HF_REPO = f"{USER_HF}/roadguardian-model"
MODEL_FILENAME = "yolo11m_roadguardian.pt"

model = None

@app.on_event("startup")
def load_model():
    global model
    print(f"⬇️ Descargando {MODEL_FILENAME} desde el repositorio {HF_REPO}...")
    
    try:
        # Descarga el modelo usando el token implícito si el repositorio es privado
        model_path = hf_hub_download(repo_id=HF_REPO, filename=MODEL_FILENAME)
        print("🧠 Cargando modelo en memoria con Ultralytics...")
        model = YOLO(model_path)
        print("✅ ¡Microservicio listo para analizar carreteras!")
    except Exception as e:
        print(f"❌ Error al cargar el modelo: {e}")

@app.get("/")
def health_check():
    return {"status": "online", "model": MODEL_FILENAME, "user": USER_HF}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if not model:
        return {"error": "El modelo aún se está cargando o hubo un fallo."}

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return {"error": "No se ha podido decodificar la imagen."}

    # Las bbox salen en píxeles de esta imagen, así que sus dimensiones
    # viajan con ellas: sin esto, el consumidor no puede calcular áreas.
    height, width = img.shape[:2]

    results = model(img, conf=0.25)
    
    detections = []
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            
            detections.append({
                "class": class_name,
                "confidence": round(conf, 2),
                "bbox": {
                    "x1": round(x1, 1), 
                    "y1": round(y1, 1), 
                    "x2": round(x2, 1), 
                    "y2": round(y2, 1)
                }
            })
            
    return {
        "filename": file.filename,
        "image": {"width": width, "height": height},
        "total_detections": len(detections),
        "detections": detections
    }