"""Composición del informe en PDF — maquetado tipo informe técnico oficial."""

import io
import re
from datetime import datetime
from functools import partial
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
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image as RLImage,
)
from reportlab.platypus import (
    HRFlowable,
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

# Paleta coherente con el frontend (asfalto oscuro + ámbar).
AZUL_OSCURO = colors.HexColor("#0f172a")
AMBAR = colors.HexColor("#f59e0b")
GRIS_TEXTO = colors.HexColor("#334155")
GRIS_SUAVE = colors.HexColor("#94a3b8")
LINEA = colors.HexColor("#cbd5e1")
FICHA_BG = colors.HexColor("#f1f5f9")
FILA_ALT = colors.HexColor("#f8fafc")

COLOR_NIVEL = {
    "CRITICO": colors.HexColor("#dc2626"),
    "ALTA": colors.HexColor("#ea580c"),
    "MEDIA": colors.HexColor("#ca8a04"),
    "BAJA": colors.HexColor("#65a30d"),
    "ESTABLE": colors.HexColor("#059669"),
}

# Márgenes: dejamos hueco arriba para la banda de cabecera y abajo para el pie,
# que se pintan en cada página desde el lienzo (ver _LienzoNumerado).
_MARGEN_LAT = 20 * mm
_MARGEN_SUP = 26 * mm
_MARGEN_INF = 22 * mm
_ANCHO_UTIL = A4[0] - 2 * _MARGEN_LAT

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
            "titulo", parent=hoja["Title"], fontName=FUENTE_BOLD, fontSize=17, spaceAfter=1,
            alignment=0, textColor=AZUL_OSCURO,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=hoja["Normal"], fontName=FUENTE, fontSize=8.5,
            textColor=GRIS_SUAVE, spaceAfter=10,
        ),
        "seccion": ParagraphStyle(
            "seccion", parent=hoja["Normal"], fontName=FUENTE_BOLD, fontSize=9.5,
            textColor=AZUL_OSCURO, spaceBefore=4, spaceAfter=6,
            letterSpacing=0.6,
        ),
        "h2": ParagraphStyle(
            "h2", parent=hoja["Heading2"], fontName=FUENTE_BOLD, fontSize=11,
            spaceBefore=13, spaceAfter=2, textColor=AZUL_OSCURO,
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo", parent=hoja["Normal"], fontName=FUENTE, fontSize=9, leading=13.5,
            alignment=TA_JUSTIFY,
        ),
        "dato": ParagraphStyle(
            "dato", parent=hoja["Normal"], fontName=FUENTE, fontSize=8.5, leading=11.5,
        ),
        "caption": ParagraphStyle(
            "caption", parent=hoja["Normal"], fontName="Vera-Italic", fontSize=7.5,
            textColor=GRIS_SUAVE, alignment=1, spaceBefore=3,
        ),
    }


def _seccion(titulo: str, estilos: dict) -> list:
    """Cabecera de sección con regla ámbar debajo, estilo informe técnico."""
    return [
        Paragraph(escape(titulo.upper()), estilos["seccion"]),
        HRFlowable(width="100%", thickness=1.2, color=AMBAR, spaceAfter=8, spaceBefore=0),
    ]


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
                    bulletColor=AMBAR,
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
            # Las cabeceras del LLM ya vienen numeradas ("## 1. Verificación…");
            # las tratamos como secciones con su regla ámbar.
            elementos.extend(_seccion(limpia.lstrip("#").strip(), estilos))
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


def _ficha_tecnica(analisis: dict, referencia: str, ahora: datetime, estilos: dict) -> Table:
    """Bloque de metadatos del informe, tipo ficha de expediente."""
    nivel = analisis["veredicto"]["nivel_alerta"]
    color = COLOR_NIVEL.get(nivel, colors.grey)
    img = analisis["imagen"]

    def dato(valor: str):
        return Paragraph(escape(str(valor)), estilos["dato"])

    filas = [
        ["Referencia", dato(referencia)],
        ["Fecha de emisión", dato(f"{ahora:%d/%m/%Y · %H:%M} h")],
        ["Archivo analizado", dato(analisis["filename"])],
        ["Resolución", dato(f"{img['width']} × {img['height']} px")],
        ["Detecciones", dato(str(analisis["total_detecciones"]))],
        ["Nivel de alerta", Paragraph(f'<font color="white"><b>{escape(nivel)}</b></font>', estilos["dato"])],
    ]

    tabla = Table(filas, colWidths=[42 * mm, _ANCHO_UTIL - 42 * mm])
    tabla.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (0, -1), FUENTE_BOLD),
            ("FONTSIZE", (0, 0), (0, -1), 8.5),
            ("TEXTCOLOR", (0, 0), (0, -1), GRIS_TEXTO),
            ("BACKGROUND", (0, 0), (0, -1), FICHA_BG),
            ("GRID", (0, 0), (-1, -1), 0.4, LINEA),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            # Fila del nivel: la celda del valor va con el color de gravedad.
            ("BACKGROUND", (1, 5), (1, 5), color),
        ])
    )
    return tabla


def _banner_veredicto(veredicto: dict, estilos: dict) -> Table:
    color = COLOR_NIVEL.get(veredicto["nivel_alerta"], colors.grey)
    contenido = [
        [
            Paragraph(
                f'<font color="white" size="14"><b>{escape(veredicto["nivel_alerta"])}</b></font>',
                estilos["cuerpo"],
            ),
            Paragraph(
                f'<font color="white"><b>{escape(veredicto["accion"])}</b><br/>'
                f'<font size="8">{escape(veredicto.get("detalles") or "")}</font></font>',
                estilos["cuerpo"],
            ),
        ]
    ]
    tabla = Table(contenido, colWidths=[36 * mm, _ANCHO_UTIL - 36 * mm])
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), color),
            ("BACKGROUND", (1, 0), (1, 0), AZUL_OSCURO),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    return tabla


def _tabla_detecciones(detecciones: list[dict]) -> Table:
    filas = [["#", "Tipo de daño", "Confianza", "Superficie"]]
    for i, d in enumerate(detecciones, 1):
        filas.append([str(i), d["clase"], f"{d['confianza']:.0%}", f"{d['superficie_pct']:.1f} %"])

    tabla = Table(filas, colWidths=[10 * mm, _ANCHO_UTIL - 70 * mm, 30 * mm, 30 * mm])
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL_OSCURO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), FUENTE_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), FUENTE),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FILA_ALT]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINEA),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, AMBAR),
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
    alto_max = 120 * mm
    if alto > alto_max:
        return RLImage(io.BytesIO(image_bytes), width=alto_max * ancho_px / alto_px, height=alto_max)
    return RLImage(io.BytesIO(image_bytes), width=_ANCHO_UTIL, height=alto)


class _LienzoNumerado(canvas.Canvas):
    """Lienzo que pinta cabecera y pie en TODAS las páginas.

    El pie lleva "Página X de Y", y ese Y solo se conoce al final: por eso
    acumulamos el estado de cada página y las decoramos todas en save().
    """

    def __init__(self, *args, referencia: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas = []
        self._referencia = referencia
        _registrar_fuentes()

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self._cabecera()
            self._pie(total)
            super().showPage()
        super().save()

    def _cabecera(self):
        ancho, alto = A4
        banda = 15 * mm
        self.setFillColor(AZUL_OSCURO)
        self.rect(0, alto - banda, ancho, banda, stroke=0, fill=1)
        self.setFillColor(AMBAR)
        self.rect(0, alto - banda - 1.4, ancho, 1.4, stroke=0, fill=1)

        self.setFillColor(AMBAR)
        self.setFont(FUENTE_BOLD, 12)
        self.drawString(_MARGEN_LAT, alto - 9.5 * mm, "ROADGUARDIAN")

        self.setFillColor(colors.HexColor("#cbd5e1"))
        self.setFont(FUENTE, 7.5)
        self.drawRightString(ancho - _MARGEN_LAT, alto - 7.5 * mm, "INFORME DE INSPECCIÓN DE FIRME")
        if self._referencia:
            self.setFillColor(GRIS_SUAVE)
            self.setFont(FUENTE, 6.5)
            self.drawRightString(ancho - _MARGEN_LAT, alto - 11.5 * mm, self._referencia)

    def _pie(self, total: int):
        ancho = A4[0]
        self.setStrokeColor(LINEA)
        self.setLineWidth(0.5)
        self.line(_MARGEN_LAT, 14 * mm, ancho - _MARGEN_LAT, 14 * mm)

        self.setFillColor(GRIS_SUAVE)
        self.setFont(FUENTE, 6.5)
        self.drawString(
            _MARGEN_LAT, 10 * mm,
            "RoadGuardian · Documento generado automáticamente — requiere validación por técnico competente.",
        )
        self.setFillColor(GRIS_TEXTO)
        self.drawRightString(ancho - _MARGEN_LAT, 10 * mm, f"Página {self._pageNumber} de {total}")


def generar_pdf(image_bytes: bytes, analisis: dict, yolo_detections: list[dict]) -> bytes:
    """Compone el informe en PDF y lo devuelve como bytes."""
    estilos = _estilos()
    ahora = datetime.now()
    referencia = f"RG-{ahora:%Y%m%d-%H%M%S}"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=_MARGEN_LAT, rightMargin=_MARGEN_LAT,
        topMargin=_MARGEN_SUP, bottomMargin=_MARGEN_INF,
        title=f"Informe RoadGuardian — {analisis['filename']}",
        author="RoadGuardian",
    )

    elementos = [
        Paragraph("Informe de inspección de firme", estilos["titulo"]),
        Paragraph(
            "Diagnóstico automático del estado del pavimento a partir de imagen",
            estilos["subtitulo"],
        ),
        _ficha_tecnica(analisis, referencia, ahora, estilos),
        Spacer(1, 10),
        _banner_veredicto(analisis["veredicto"], estilos),
        Spacer(1, 12),
    ]

    elementos += _seccion("Documentación gráfica", estilos)
    elementos += [
        _imagen_ajustada(anotar(image_bytes, yolo_detections)),
        Paragraph("Fig. 1 — Imagen analizada con las detecciones señaladas.", estilos["caption"]),
        Spacer(1, 6),
    ]

    if analisis["detecciones"]:
        elementos += _seccion("Daños detectados", estilos)
        elementos.append(_tabla_detecciones(analisis["detecciones"]))

    if analisis.get("informe"):
        elementos.append(PageBreak())
        elementos += _seccion("Informe técnico", estilos)
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

    doc.build(elementos, canvasmaker=partial(_LienzoNumerado, referencia=referencia))
    return buffer.getvalue()
