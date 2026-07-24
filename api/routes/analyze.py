"""POST /analyze — el flujo completo: foto → detecciones → gravedad → informe."""

import logging
import re
from datetime import datetime
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from api.config import MAX_UPLOAD_BYTES
from api.schemas.analysis import AnalisisResponse
from api.services.yolo_client import YoloError, detect
from llm.report import generate_report
from prioritization.priority_engine import evaluate_road_image
from prioritization.rules import calculate_bbox_area, get_damage_percentage
from reports.pdf import generar_pdf
from api.services.storage_service import upload_file
from api.services.supabase_service import (
    save_detections,
    save_inspection,
)



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


async def _analizar(file: UploadFile) -> tuple[dict, bytes, dict]:
    """El flujo completo. Devuelve (análisis, bytes de la foto, JSON de YOLO).

    Lo usan los dos endpoints: /analyze lo serializa a JSON y /analyze/pdf lo
    maqueta. La política de fallos vive aquí, en un solo sitio.
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

    analisis = {
        "filename": file.filename or "imagen.jpg",
        "imagen": yolo_data["image"],
        "total_detecciones": len(yolo_data["detections"]),
        "detecciones": _formatear_detecciones(yolo_data),
        "veredicto": veredicto,
        "informe": informe,
        "informe_error": informe_error,
    }
    return analisis, contenido, yolo_data


# @router.post("/analyze", response_model=AnalisisResponse, summary="Analiza una foto de firme")
# async def analyze(file: UploadFile = File(..., description="Fotografía del firme")):
#     """Detecta daños, calcula su gravedad y redacta un informe técnico.

#     Si el LLM falla, se devuelve igualmente el veredicto sin el informe.
#     """
#     analisis, _, _ = await _analizar(file)
#     return analisis
@router.post("/analyze", response_model=AnalisisResponse, summary="Analiza una foto de firme")
async def analyze(file: UploadFile = File(..., description="Fotografía del firme")):
    """Detecta daños, calcula su gravedad y redacta un informe técnico.

    Si el LLM falla, se devuelve igualmente el veredicto sin el informe.
    """
    analisis, contenido, yolo_data = await _analizar(file)
    
    image_path, pdf_path = _generate_storage_paths(
        file.filename or "imagen.jpg"
    )
    upload_file(
        bucket="originals",
        destination_path=image_path,
        file_bytes=contenido,
        content_type=file.content_type or "image/jpeg",
    )
    
    inspection_id = save_inspection(
    {
        "source_type": "image",
        "original_image": image_path,
        "original_filename": file.filename,
        "status": "completed",
        "total_detections": analisis["total_detecciones"],
        "alert_level": analisis["veredicto"]["nivel_alerta"],
        "recommended_action": analisis["veredicto"]["accion"],
    }
)

    print(f"Inspección guardada: {inspection_id}")
    print(yolo_data["detections"][0])
    
    save_detections(
    inspection_id=inspection_id,
    detections=yolo_data["detections"],
)


    return analisis


def _nombre_pdf(filename: str, nivel: str) -> str:
    """informe_CRITICO_foto_20260717.pdf, sin caracteres que rompan la cabecera."""
    base = re.sub(r"[^A-Za-z0-9_-]", "_", filename.rsplit(".", 1)[0])[:40]
    return f"informe_{nivel}_{base}_{datetime.now():%Y%m%d}.pdf"

# Esta funcion genera rutas únicas para guardar la imagen y el PDF en Supabase Storage. Se usa para evitar colisiones de nombres y organizar los archivos en carpetas separadas.

def _generate_storage_paths(filename: str) -> tuple[str, str]:
    """
    Genera rutas únicas para guardar la imagen y el PDF en Supabase Storage.
    """
    extension = Path(filename).suffix or ".jpg"
    unique_id = uuid.uuid4().hex

    image_path = f"{unique_id}{extension}"
    pdf_path = f"{unique_id}.pdf"

    return image_path, pdf_path


@router.post(
    "/analyze/pdf",
    summary="Analiza una foto y devuelve el informe en PDF",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "El informe en PDF"}},
)
async def analyze_pdf(file: UploadFile = File(..., description="Fotografía del firme")):
    """Igual que /analyze, pero devuelve un PDF maquetado en vez de JSON.

    Hace su propio análisis completo, así que pedir el JSON y el PDF de la
    misma foto cuesta dos llamadas al LLM. Se evitaría guardando el resultado
    y sirviéndolo por id, a cambio de tener que gestionar almacenamiento y
    caducidad: no compensa mientras no haga falta.
    """
    analisis, contenido, yolo_data = await _analizar(file)
    pdf = generar_pdf(contenido, analisis, yolo_data["detections"])

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_nombre_pdf(analisis["filename"], analisis["veredicto"]["nivel_alerta"])}"'
            )
        },
    )
