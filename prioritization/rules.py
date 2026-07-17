IMAGE_AREA = 640 * 640

# Diccionario de acciones según la gravedad
SEVERITY_LEVELS = {
    "CRITICO": "Intervención inmediata (24-48h). Riesgo alto de accidente.",
    "ALTA": "Planificar reparación a corto plazo (1-2 semanas).",
    "MEDIA": "Mantenimiento preventivo (1-3 meses).",
    "BAJA": "Monitorizar evolución en próximas inspecciones."
}

def calculate_bbox_area(bbox: dict) -> float:
    """Calcula el área en píxeles de la caja delimitadora de YOLO."""
    width = bbox["x2"] - bbox["x1"]
    height = bbox["y2"] - bbox["y1"]
    return width * height

def get_damage_percentage(bbox_area: float) -> float:
    """Calcula qué porcentaje de la imagen ocupa el daño."""
    return (bbox_area / IMAGE_AREA) * 100