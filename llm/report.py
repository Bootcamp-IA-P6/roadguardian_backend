"""Generación del informe técnico a partir de las detecciones de YOLO.

Los textos que se le mandan al modelo no están aquí: viven en llm/prompts/*.md.
"""

import os

from openai import OpenAI

from llm import prompts
from llm.image import to_data_url
from prioritization.rules import calculate_bbox_area, get_damage_percentage

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Baja a propósito: un informe de ingeniería debe ser reproducible. No queremos
# que la misma foto produzca un texto distinto cada vez.
TEMPERATURE = 0.2
TIMEOUT_SECONDS = 120


def _describe_detections(yolo_data: dict) -> str:
    """Resume las detecciones en texto, con el porcentaje real de superficie."""
    detections = yolo_data.get("detections", [])
    if not detections:
        return "El modelo no ha detectado ningún daño."

    image = yolo_data["image"]
    image_area = image["width"] * image["height"]

    lineas = []
    for i, det in enumerate(detections, 1):
        area = calculate_bbox_area(det["bbox"])
        pct = get_damage_percentage(area, image_area)
        lineas.append(
            f"{i}. {det['class']} — confianza {det['confidence']:.0%}, "
            f"ocupa el {pct:.1f}% de la superficie de la imagen"
        )
    return "\n".join(lineas)


def build_user_prompt(yolo_data: dict, verdict: dict) -> str:
    image = yolo_data["image"]
    return prompts.render(
        "informe",
        ancho=image["width"],
        alto=image["height"],
        total=yolo_data.get("total_detections", 0),
        detecciones=_describe_detections(yolo_data),
        nivel_alerta=verdict["nivel_alerta"],
        accion=verdict["accion"],
    )


def generate_report(image_bytes: bytes, yolo_data: dict, verdict: dict) -> str:
    """Pide al LLM el informe técnico. Devuelve el texto en markdown."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("Falta OPENROUTER_API_KEY en el entorno.")

    model = os.getenv("MODEL_NAME")
    if not model:
        raise ValueError("Falta MODEL_NAME en el entorno.")

    client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=TIMEOUT_SECONDS)

    response = client.chat.completions.create(
        model=model,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": prompts.load("system")},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_user_prompt(yolo_data, verdict)},
                    {"type": "image_url", "image_url": {"url": to_data_url(image_bytes)}},
                ],
            },
        ],
    )

    return response.choices[0].message.content
