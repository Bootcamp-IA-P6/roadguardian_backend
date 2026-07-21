# """Cliente del microservicio de YOLO.

# Todo lo que sabe el resto del proyecto sobre cómo se detectan daños está aquí.
# Si mañana YOLO se muda a Hugging Face, cambia de contrato o se le pone caché,
# se toca este fichero y nada más.
# """

#ESTE CODIGO SE CONSERVA PARA CUAANDO SE QUIERA USAR EN LOCAL O SUBIR A HUGGING FACE, CON VERSIVION HTTPX PORQUE AHORA ESTA CLIENTE DE GRADIO, Y NO HACE FALTA INSTALAR HTTPX

# import httpx

# from api.config import YOLO_API_URL, YOLO_TIMEOUT_SECONDS


# class YoloError(Exception):
#     """El servicio de YOLO no ha podido darnos detecciones."""


# async def detect(image_bytes: bytes, filename: str = "imagen.jpg") -> dict:
#     """Manda la imagen a YOLO y devuelve su JSON de detecciones.

#     Lanza YoloError si el servicio no está, tarda demasiado o responde algo
#     que no son detecciones.
#     """
#     try:
#         async with httpx.AsyncClient(timeout=YOLO_TIMEOUT_SECONDS) as client:
#             response = await client.post(
#                 f"{YOLO_API_URL}/predict",
#                 files={"file": (filename, image_bytes, "image/jpeg")},
#             )
#     except httpx.TimeoutException as e:
#         raise YoloError(
#             f"El servicio de YOLO no respondió en {YOLO_TIMEOUT_SECONDS:.0f}s. "
#             "Si está en un plan gratuito, puede estar despertando de una siesta."
#         ) from e
#     except httpx.RequestError as e:
#         raise YoloError(f"No se ha podido contactar con YOLO en {YOLO_API_URL}: {e}") from e

#     if response.status_code != 200:
#         raise YoloError(f"YOLO respondió {response.status_code}: {response.text[:200]}")

#     try:
#         data = response.json()
#     except ValueError as e:
#         raise YoloError(f"YOLO no devolvió JSON: {response.text[:200]}") from e

#     # OJO: el microservicio devuelve sus errores con código 200 y un campo
#     # "error" dentro, así que comprobar el status_code no basta.
#     if "error" in data:
#         raise YoloError(f"YOLO rechazó la imagen: {data['error']}")

#     # Sin dimensiones el motor de priorización no puede medir nada. Mejor
#     # enterarse aquí que tres capas más abajo.
#     if "image" not in data or "detections" not in data:
#         raise YoloError(
#             f"La respuesta de YOLO no tiene la forma esperada. Claves: {sorted(data)}"
#         )

#     return data

"""
Cliente del microservicio de YOLO alojado en Hugging Face.

El resto del proyecto solo conoce detect().
"""

import os
import tempfile

from gradio_client import Client, handle_file

from api.config import YOLO_SPACE


_client = None


def get_client() -> Client:
    """Crea el cliente solo la primera vez."""
    global _client

    if _client is None:
        _client = Client(YOLO_SPACE)

    return _client


class YoloError(Exception):
    """El servicio de YOLO no ha podido darnos detecciones."""


async def detect(image_bytes: bytes, filename: str = "imagen.jpg") -> dict:
    """
    Envía la imagen al Space de Hugging Face
    y devuelve el JSON generado por YOLO.
    """

    temp_path = None

    try:
        suffix = os.path.splitext(filename)[1] or ".jpg"

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp:

            temp.write(image_bytes)
            temp_path = temp.name

        client = get_client()

        result = client.predict(
            handle_file(temp_path),
            api_name="/predict",
        )

        if not isinstance(result, dict):
            raise YoloError("La respuesta del Space no es un JSON válido.")

        if "error" in result:
            raise YoloError(result["error"])

        return result

    except Exception as e:
        raise YoloError(f"No se pudo obtener la inferencia: {e}") from e

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)