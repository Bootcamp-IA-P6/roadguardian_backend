"""Preparación de imágenes para enviarlas a un modelo multimodal."""

import base64
import io

from PIL import Image

# Lado mayor al que se reduce la imagen antes de enviarla al LLM. El modelo
# solo tiene que confirmar si los daños que detectó YOLO están realmente ahí,
# y para eso 1024 px sobran. Más resolución son más tokens y ninguna respuesta
# mejor.
MAX_SIDE = 1024
JPEG_QUALITY = 85


def to_data_url(image_bytes: bytes, max_side: int = MAX_SIDE) -> str:
    """Convierte una imagen a un data URL listo para la API del LLM.

    La redimensiona si su lado mayor supera max_side. Devuelve una cadena
    'data:image/jpeg;base64,...', que es como se envían las imágenes por una
    API de chat: el JSON es texto, así que los bytes viajan en base64.
    """
    image = Image.open(io.BytesIO(image_bytes))

    # Los JPEG de móvil llevan la orientación en los metadatos EXIF en vez de
    # en los píxeles: sin esto, una foto vertical llega girada.
    image = _apply_exif_rotation(image)

    if image.mode != "RGB":
        image = image.convert("RGB")

    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    return f"data:image/jpeg;base64,{encoded}"


def _apply_exif_rotation(image: Image.Image) -> Image.Image:
    try:
        from PIL import ImageOps

        return ImageOps.exif_transpose(image)
    except Exception:
        # Si los EXIF están corruptos preferimos la imagen sin rotar a un fallo.
        return image
