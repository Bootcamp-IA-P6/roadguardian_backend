# prioritization/priority_engine.py
from prioritization.rules import calculate_bbox_area, get_damage_percentage, SEVERITY_LEVELS

def evaluate_single_damage(detection: dict, image_area: float) -> str:
    """Evalúa un daño individual y devuelve su nivel de prioridad."""
    damage_class = detection["class"]
    bbox = detection["bbox"]
    conf = detection["confidence"]

    # 1. Filtro de seguridad: ignorar detecciones muy dudosas
    if conf < 0.25:
        return "BAJA"

    # 2. Calcular el tamaño del daño
    area = calculate_bbox_area(bbox)
    pct = get_damage_percentage(area, image_area)

    # 3. Aplicar reglas de negocio según la clase (Estos números los podemos ajustar)
    if damage_class == "Alligator Crack" or damage_class == "Alligator_Crack":
        # El bbox sobreestima el area real en esta clase por la perspectiva
        # de las fotos en carretera (caso 23/07/2026: 67.5% no era una
        # emergencia real). Umbrales mas altos que en el resto de clases.
        if pct > 85:
            return "CRITICO"
        elif pct > 20:
            return "ALTA"
        else:
            return "MEDIA"

    if damage_class == "Pothole":
        # Los baches revientan neumáticos. Si es grande, es crítico.
        return "CRITICO" if pct > 5 else "ALTA"

    if damage_class == "Transverse Crack" or damage_class == "Transverse_Crack":
        # Grietas transversales. Molestas pero menos críticas a no ser que sean enormes.
        return "ALTA" if pct > 2 else "MEDIA"

    if damage_class == "Longitudinal Crack" or damage_class == "Longitudinal_Crack":
        # Grietas longitudinales. Suelen ser el primer síntoma.
        return "MEDIA" if pct > 2 else "BAJA"

    return "BAJA"

def evaluate_road_image(yolo_data: dict) -> dict:
    """Recibe el JSON completo de YOLO y devuelve el veredicto final."""
    detections = yolo_data.get("detections", [])

    if not detections:
        return {
            "nivel_alerta": "ESTABLE",
            "accion": "Ninguna acción requerida.",
            "detalles": "No se detectaron anomalías en el asfalto."
        }

    # Sin dimensiones no se puede medir nada: preferimos fallar a inventarnos
    # un tamaño de referencia y devolver porcentajes falsos en silencio.
    image = yolo_data.get("image") or {}
    width, height = image.get("width"), image.get("height")
    if not width or not height:
        raise ValueError(
            "El JSON de YOLO no trae 'image.width'/'image.height'. Sin las "
            "dimensiones reales no se puede calcular el tamaño de los daños."
        )
    image_area = width * height

    highest_level = "BAJA"
    # Diccionario para saber qué nivel "pesa" más a la hora de comparar
    priority_order = {"BAJA": 0, "MEDIA": 1, "ALTA": 2, "CRITICO": 3}

    # Evaluar todos los daños y quedarse con el peor
    for det in detections:
        lvl = evaluate_single_damage(det, image_area)
        if priority_order[lvl] > priority_order[highest_level]:
            highest_level = lvl

    return {
        "nivel_alerta": highest_level,
        "accion": SEVERITY_LEVELS[highest_level],
        "detalles": f"Se evaluaron {len(detections)} daños. El nivel máximo detectado es {highest_level}."
    }