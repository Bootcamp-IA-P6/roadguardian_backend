import os
import cv2
import gradio as gr
import spaces
from huggingface_hub import hf_hub_download
from ultralytics import YOLO

# ==========================
# CONFIGURACIÓN
# ==========================

USER_HF = os.environ.get("HF_USER", "Gemita284")
HF_REPO = f"{USER_HF}/roadguardian-model"
MODEL_FILENAME = "yolo11m_roadguardian.pt"

# Variable global donde se guardará el modelo
model = None


# ==========================
# CARGA DEL MODELO (solo una vez)
# ==========================

def get_model():
    global model

    if model is None:
        print(f"⬇️ Descargando {MODEL_FILENAME} desde {HF_REPO}...")

        model_path = hf_hub_download(
            repo_id=HF_REPO,
            filename=MODEL_FILENAME
        )

        print("🧠 Cargando modelo en memoria con Ultralytics...")

        model = YOLO(model_path)

        print("✅ ¡Modelo cargado correctamente!")

    return model


# ==========================
# PREDICCIÓN
# ==========================

@spaces.GPU
def predict(filepath):

    if filepath is None:
        return {"error": "No se recibió ninguna imagen."}

    # Cargar el modelo (solo la primera vez)
    model = get_model()

    # Leer la imagen
    img = cv2.imread(filepath)

    if img is None:
        return {"error": "No se ha podido decodificar la imagen."}

    # Dimensiones
    height, width = img.shape[:2]

    # Inferencia
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

    filename = os.path.basename(filepath)

    return {
        "filename": filename,
        "image": {
            "width": width,
            "height": height
        },
        "total_detections": len(detections),
        "detections": detections
    }


# ==========================
# INTERFAZ
# ==========================

app = gr.Interface(
    fn=predict,
    inputs=gr.Image(
        type="filepath",
        label="Sube una foto del asfalto"
    ),
    outputs=gr.JSON(label="Resultado de Inferencia"),
    title="RoadGuardian AI Microservice",
    description="API dedicada exclusivamente a la inferencia de daños en asfalto con YOLO11m"
)


if __name__ == "__main__":
    app.launch()