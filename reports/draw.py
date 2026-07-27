"""Dibuja las detecciones de YOLO sobre la fotografía.

Se hace aquí y no en el microservicio a propósito: el Servicio A solo devuelve
coordenadas y así se mantiene tonto y rápido, mientras que aquí ya tenemos la
imagen, las cajas y Pillow.
"""

import io

from PIL import Image, ImageDraw, ImageFont

# Un color por tipo de daño. Rojo para lo que revienta ruedas, ámbar para el
# fallo estructural, amarillos para las grietas.
COLORES = {
    "Pothole": (220, 38, 38),
    "Alligator Crack": (234, 88, 12),
    "Transverse Crack": (202, 138, 4),
    "Longitudinal Crack": (161, 98, 7),
}
COLOR_POR_DEFECTO = (100, 116, 139)


def _color(clase: str) -> tuple[int, int, int]:
    # El modelo usa "Alligator Crack" pero algunos datasets usan guiones bajos.
    return COLORES.get(clase) or COLORES.get(clase.replace("_", " "), COLOR_POR_DEFECTO)


def _fuente(tamano: int):
    for ruta in ("/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(ruta, tamano)
        except OSError:
            continue
    # Si no hay ninguna, Pillow trae una diminuta. Fea, pero no rompe nada.
    return ImageFont.load_default()


def anotar(image_bytes: bytes, detections: list[dict]) -> bytes:
    """Devuelve la imagen con las cajas y etiquetas dibujadas encima."""
    imagen = Image.open(io.BytesIO(image_bytes))
    from PIL import ImageOps

    imagen = ImageOps.exif_transpose(imagen)
    if imagen.mode != "RGB":
        imagen = imagen.convert("RGB")

    lienzo = ImageDraw.Draw(imagen)

    # El grosor se escala con la imagen: 3 px en una foto de 4000 px de ancho
    # no se ven, y en una de 400 la tapan entera.
    grosor = max(2, round(min(imagen.size) / 250))
    fuente = _fuente(max(12, round(min(imagen.size) / 40)))

    for det in detections:
        caja = det["bbox"]
        color = _color(det["class"])
        x1, y1 = caja["x1"], caja["y1"]

        lienzo.rectangle([x1, y1, caja["x2"], caja["y2"]], outline=color, width=grosor)

        etiqueta = f" {det['class']} {det['confidence']:.0%} "
        izq, arriba, der, abajo = lienzo.textbbox((0, 0), etiqueta, font=fuente)
        alto_etiqueta = abajo - arriba + 6

        # Si la caja toca el borde superior, la etiqueta se sale de la imagen:
        # en ese caso se pinta por dentro en vez de por encima.
        y_etiqueta = y1 - alto_etiqueta if y1 - alto_etiqueta > 0 else y1

        lienzo.rectangle([x1, y_etiqueta, x1 + (der - izq) + 4, y_etiqueta + alto_etiqueta], fill=color)
        lienzo.text((x1 + 2, y_etiqueta + 2), etiqueta, fill=(255, 255, 255), font=fuente)

    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", quality=90)
    return salida.getvalue()
