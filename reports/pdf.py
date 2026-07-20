"""Composición del informe en PDF."""

import io
import re
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as RLImage,
)
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from reports.draw import anotar

COLOR_NIVEL = {
    "CRITICO": colors.HexColor("#dc2626"),
    "ALTA": colors.HexColor("#ea580c"),
    "MEDIA": colors.HexColor("#ca8a04"),
    "BAJA": colors.HexColor("#65a30d"),
    "ESTABLE": colors.HexColor("#059669"),
}

_ANCHO_UTIL = A4[0] - 40 * mm

# Fuente incrustada. Por defecto reportlab usa Helvetica, que NO va dentro del
# PDF: da por hecho que el lector la tiene (es una de las 14 estándar del
# formato). Un informe que se entrega a una administración no puede depender
# de eso. Las Bitstream Vera vienen con reportlab y son de licencia libre.
FUENTE = "Vera"
FUENTE_BOLD = "Vera-Bold"


def _registrar_fuentes() -> None:
    if FUENTE in pdfmetrics.getRegisteredFontNames():
        return

    ruta = Path(reportlab.__file__).parent / "fonts"
    pdfmetrics.registerFont(TTFont(FUENTE, ruta / "Vera.ttf"))
    pdfmetrics.registerFont(TTFont(FUENTE_BOLD, ruta / "VeraBd.ttf"))
    pdfmetrics.registerFont(TTFont("Vera-Italic", ruta / "VeraIt.ttf"))
    pdfmetrics.registerFont(TTFont("Vera-BoldItalic", ruta / "VeraBI.ttf"))

    # Sin esto, las etiquetas <b> y <i> de los Paragraph seguirían tirando de
    # Helvetica: registrar la fuente no basta, hay que decirle cuál es su
    # negrita y cuál su cursiva.
    pdfmetrics.registerFontFamily(
        FUENTE, normal=FUENTE, bold=FUENTE_BOLD, italic="Vera-Italic", boldItalic="Vera-BoldItalic"
    )


def _estilos():
    _registrar_fuentes()
    hoja = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=hoja["Title"], fontName=FUENTE_BOLD, fontSize=18, spaceAfter=2
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=hoja["Normal"], fontName=FUENTE, fontSize=8.5,
            textColor=colors.HexColor("#64748b"), spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "h2", parent=hoja["Heading2"], fontName=FUENTE_BOLD, fontSize=11.5,
            spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#0f172a"),
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo", parent=hoja["Normal"], fontName=FUENTE, fontSize=9, leading=13.5,
            alignment=TA_JUSTIFY,
        ),
        "pie": ParagraphStyle(
            "pie", parent=hoja["Normal"], fontName=FUENTE, fontSize=7,
            textColor=colors.HexColor("#94a3b8"),
        ),
    }


def _markdown_a_flowables(texto: str, estilos: dict) -> list:
    """Convierte el markdown del LLM a elementos de reportlab.

    No es un parser de markdown completo: solo cubre lo que el prompt pide
    (cabeceras ##, negritas y listas). Traer una librería entera para esto
    sería pagar mucho por un subconjunto conocido.
    """
    elementos = []
    bloque: list[str] = []
    vinetas: list[str] = []

    def cerrar_parrafo():
        if bloque:
            elementos.append(Paragraph(_inline(" ".join(bloque)), estilos["cuerpo"]))
            bloque.clear()

    def cerrar_lista():
        if vinetas:
            elementos.append(
                ListFlowable(
                    [ListItem(Paragraph(_inline(v), estilos["cuerpo"]), leftIndent=10) for v in vinetas],
                    bulletType="bullet", bulletFontSize=6, leftIndent=12,
                    # Sin esto el puntito de la viñeta usaría Helvetica, y con
                    # una sola referencia el PDF ya deja de ser autocontenido.
                    bulletFontName=FUENTE,
                )
            )
            vinetas.clear()

    for linea in texto.splitlines():
        limpia = linea.strip()

        if not limpia:
            cerrar_parrafo()
            cerrar_lista()
            continue

        if limpia.startswith("#"):
            cerrar_parrafo()
            cerrar_lista()
            elementos.append(Paragraph(_inline(limpia.lstrip("#").strip()), estilos["h2"]))
            continue

        if re.match(r"^[-*•]\s+|^\d+\.\s+", limpia):
            cerrar_parrafo()
            vinetas.append(re.sub(r"^[-*•]\s+|^\d+\.\s+", "", limpia))
            continue

        cerrar_lista()
        bloque.append(limpia)

    cerrar_parrafo()
    cerrar_lista()
    return elementos


def _inline(texto: str) -> str:
    """Negritas y cursivas de markdown a las etiquetas de reportlab.

    Se escapa ANTES de meter las etiquetas: reportlab parsea el texto como
    XML, así que un '&' o un '<' del LLM reventaría la generación entera.
    """
    texto = escape(texto)
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    texto = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", texto)
    return texto


def _caja_veredicto(veredicto: dict, estilos: dict) -> Table:
    color = COLOR_NIVEL.get(veredicto["nivel_alerta"], colors.grey)
    contenido = [
        [
            Paragraph(
                f'<font color="white" size="15"><b>{escape(veredicto["nivel_alerta"])}</b></font>',
                estilos["cuerpo"],
            ),
            Paragraph(f'<font color="white">{escape(veredicto["accion"])}</font>', estilos["cuerpo"]),
        ]
    ]
    tabla = Table(contenido, colWidths=[38 * mm, _ANCHO_UTIL - 38 * mm])
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), color),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    return tabla


def _tabla_detecciones(detecciones: list[dict], estilos: dict) -> Table:
    filas = [["#", "Tipo de daño", "Confianza", "Superficie"]]
    for i, d in enumerate(detecciones, 1):
        filas.append([str(i), d["clase"], f"{d['confianza']:.0%}", f"{d['superficie_pct']:.1f} %"])

    tabla = Table(filas, colWidths=[10 * mm, _ANCHO_UTIL - 70 * mm, 30 * mm, 30 * mm])
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), FUENTE_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), FUENTE),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    return tabla


def _imagen_ajustada(image_bytes: bytes) -> RLImage:
    """Escala la foto al ancho útil conservando la proporción."""
    from PIL import Image as PILImage

    ancho_px, alto_px = PILImage.open(io.BytesIO(image_bytes)).size
    alto = _ANCHO_UTIL * alto_px / ancho_px

    # Una foto vertical se comería la página entera: la limitamos por altura.
    alto_max = 130 * mm
    if alto > alto_max:
        return RLImage(io.BytesIO(image_bytes), width=alto_max * ancho_px / alto_px, height=alto_max)
    return RLImage(io.BytesIO(image_bytes), width=_ANCHO_UTIL, height=alto)


def generar_pdf(image_bytes: bytes, analisis: dict, yolo_detections: list[dict]) -> bytes:
    """Compone el informe en PDF y lo devuelve como bytes."""
    estilos = _estilos()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Informe RoadGuardian — {analisis['filename']}",
        author="RoadGuardian",
    )

    ahora = datetime.now()
    elementos = [
        Paragraph("Informe de inspección de firme", estilos["titulo"]),
        Paragraph(
            f"RoadGuardian · {escape(analisis['filename'])} · "
            f"{analisis['imagen']['width']}×{analisis['imagen']['height']} px · "
            f"{ahora:%d/%m/%Y %H:%M}",
            estilos["subtitulo"],
        ),
        _caja_veredicto(analisis["veredicto"], estilos),
        Spacer(1, 10),
        _imagen_ajustada(anotar(image_bytes, yolo_detections)),
        Spacer(1, 10),
    ]

    if analisis["detecciones"]:
        elementos += [
            Paragraph("Daños detectados", estilos["h2"]),
            _tabla_detecciones(analisis["detecciones"], estilos),
        ]

    if analisis.get("informe"):
        elementos.append(PageBreak())
        elementos += _markdown_a_flowables(analisis["informe"], estilos)
    else:
        elementos += [
            Spacer(1, 10),
            Paragraph(
                f'<font color="#b45309"><b>Sin informe técnico.</b> '
                f'{escape(analisis.get("informe_error") or "")}</font>',
                estilos["cuerpo"],
            ),
        ]

    elementos += [
        Spacer(1, 14),
        Paragraph(
            "Documento generado automáticamente. Las detecciones proceden de un modelo YOLO11; "
            "el nivel de alerta, de un motor de reglas determinista; la redacción, de un modelo "
            "de lenguaje. Requiere validación por técnico competente antes de su uso.",
            estilos["pie"],
        ),
    ]

    doc.build(elementos)
    return buffer.getvalue()
