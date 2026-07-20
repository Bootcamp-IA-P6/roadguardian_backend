"""Forma de la respuesta de /analyze.

Declararla con Pydantic no es burocracia: es lo que hace que /docs se dibuje
solo, que FastAPI valide la salida, y que el frontend sepa qué campos hay sin
preguntarle a nadie.
"""

from pydantic import BaseModel, Field


class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class Deteccion(BaseModel):
    clase: str = Field(description="Tipo de daño detectado")
    confianza: float = Field(description="0 a 1")
    superficie_pct: float = Field(description="% de la imagen que ocupa el daño")
    bbox: BBox


class Imagen(BaseModel):
    width: int
    height: int


class Veredicto(BaseModel):
    nivel_alerta: str = Field(description="ESTABLE, BAJA, MEDIA, ALTA o CRITICO")
    accion: str
    detalles: str


class AnalisisResponse(BaseModel):
    filename: str
    imagen: Imagen
    total_detecciones: int
    detecciones: list[Deteccion]
    veredicto: Veredicto

    # El informe es opcional a propósito: si el LLM se cae o agota la cuota,
    # el veredicto del motor de reglas sigue siendo válido y se entrega igual.
    # Un informe sin prosa es mejor que un error 500.
    informe: str | None = Field(
        default=None, description="Informe técnico en markdown. Null si el LLM falló."
    )
    informe_error: str | None = Field(
        default=None, description="Por qué no hay informe, si es que no lo hay."
    )
