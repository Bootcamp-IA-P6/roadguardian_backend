from api.services.supabase_client import supabase


def save_inspection(data: dict) -> str:
    """
    Guarda una inspección en la tabla inspections y devuelve su id.
    """

    response = (
        supabase.table("inspections")
        .insert(data)
        .execute()
    )

    return response.data[0]["id"]


from api.services.supabase_client import supabase


def save_detection(data: dict) -> None:
    """
    Guarda una detección en la tabla detections.
    """

    (
        supabase.table("detections")
        .insert(data)
        .execute()
    )


def save_detections(inspection_id: str, detections: list) -> None:
    """
    Guarda todas las detecciones de una inspección.
    """

    for detection in detections:
        save_detection(
            {
                "inspection_id": inspection_id,
                "damage_type": detection["class"],
                "confidence": detection["confidence"],
                "surface_pct": None,
                "bbox": detection["bbox"],
            }
        )

def get_inspections():
    """
    Devuelve el historial de inspecciones.
    """
    pass


def get_inspection():
    """
    Devuelve una inspección concreta.
    """
    pass


def delete_inspection():
    """
    Elimina una inspección.
    """
    pass