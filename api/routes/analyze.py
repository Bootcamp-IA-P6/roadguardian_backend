"""POST /analyze — el flujo completo: foto → detecciones → gravedad → informe."""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from api.config import MAX_UPLOAD_BYTES
from api.schemas.analysis import AnalisisResponse
from api.services.yolo_client import YoloError, detect
from llm.report import generate_report
from prioritization.priority_engine import evaluate_road_image
from prioritization.rules import calculate_bbox_area, get_damage_percentage

logger = logging.getLogger(__name__)
router = APIRouter()

TIPOS_ACEPTADOS = ("image/jpeg", "image/png", "image/webp")


def _validar(file: UploadFile, contenido: bytes) -> None:
    if not contenido:
        raise HTTPException(400, "El archivo está vacío.")

    if len(contenido) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            f"La imagen pesa {len(contenido) / 1024 / 1024:.1f} MB y el máximo "
            f"son {MAX_UPLOAD_BYTES / 1024 / 1024:.0f} MB.",
        )

    # El content_type lo manda el cliente y puede mentir, así que esto no es
    # seguridad: es cortesía. Un error claro y barato para el caso honesto de
    # subir un vídeo o un PDF sin querer. La comprobación de verdad la hace
    # YOLO al intentar decodificar la imagen.
    if file.content_type not in TIPOS_ACEPTADOS:
        raise HTTPException(
            415,
            f"Tipo '{file.content_type}' no admitido. Se aceptan: "
            f"{', '.join(TIPOS_ACEPTADOS)}. Esta API analiza fotografías, no vídeos.",
        )


def _formatear_detecciones(yolo_data: dict) -> list[dict]:
    area = yolo_data["image"]["width"] * yolo_data["image"]["height"]
    return [
        {
            "clase": d["class"],
            "confianza": d["confidence"],
            "superficie_pct": round(get_damage_percentage(calculate_bbox_area(d["bbox"]), area), 2),
            "bbox": d["bbox"],
        }
        for d in yolo_data["detections"]
    ]


@router.post("/analyze", response_model=AnalisisResponse, summary="Analiza una foto de firme")
async def analyze(file: UploadFile = File(..., description="Fotografía del firme")):
    """Detecta daños, calcula su gravedad y redacta un informe técnico.

    Si el LLM falla, se devuelve igualmente el veredicto sin el informe.
    """
    contenido = await file.read()
    _validar(file, contenido)

    # 1. YOLO. Sin detecciones no hay nada que hacer: esto sí es fatal.
    try:
        yolo_data = await detect(contenido, file.filename or "imagen.jpg")
    except YoloError as e:
        logger.warning("YOLO no disponible: %s", e)
        raise HTTPException(503, f"El servicio de detección no está disponible. {e}") from e

    # 2. Motor de reglas. Determinista y nuestro: si peta, es un bug y queremos
    #    que se note, no taparlo.
    veredicto = evaluate_road_image(yolo_data)

    # 3. LLM. Es la guinda, no el pastel: si se cae, entregamos lo demás.
    informe = None
    informe_error = None
    try:
        informe = await generate_report(contenido, yolo_data, veredicto)
    except Exception as e:
        logger.exception("El LLM no pudo redactar el informe")
        informe_error = f"No se ha podido generar el informe ({type(e).__name__}). El nivel de alerta sí es válido."

    return {
        "filename": file.filename or "imagen.jpg",
        "imagen": yolo_data["image"],
        "total_detecciones": len(yolo_data["detections"]),
        "detecciones": _formatear_detecciones(yolo_data),
        "veredicto": veredicto,
        "informe": informe,
        "informe_error": informe_error,
    }
