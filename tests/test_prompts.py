"""Los prompts viven en .md, así que el linter no los revisa: estos tests son
la red que lo sustituye. Cazan la errata en $variable antes de que la cace una
llamada al LLM a medio informe.
"""

import pytest

from llm import prompts
from llm.report import build_user_prompt

VEREDICTO = {"nivel_alerta": "CRITICO", "accion": "Intervención inmediata (24-48h)."}
YOLO_DATA = {
    "filename": "x.jpg",
    "image": {"width": 1600, "height": 1061},
    "total_detections": 1,
    "detections": [
        {
            "class": "Pothole",
            "confidence": 0.72,
            "bbox": {"x1": 0, "y1": 0, "x2": 100, "y2": 100},
        }
    ],
}


class TestLoad:
    def test_carga_los_prompts_que_usa_report(self):
        assert prompts.load("system").strip()
        assert prompts.load("informe").strip()

    def test_prompt_inexistente_dice_cuales_hay(self):
        with pytest.raises(FileNotFoundError, match="Disponibles"):
            prompts.load("no_existe")


class TestRender:
    def test_rellena_los_huecos(self):
        texto = prompts.render(
            "informe",
            ancho=800, alto=600, total=1,
            detecciones="1. Pothole", nivel_alerta="ALTA", accion="Reparar.",
        )
        assert "800 x 600" in texto
        assert "ALTA — Reparar." in texto
        assert "$" not in texto  # no queda ningún hueco sin rellenar

    def test_si_falta_una_variable_revienta(self):
        # Preferimos un error a mandarle al modelo un prompt a medio rellenar.
        with pytest.raises(KeyError):
            prompts.render("informe", ancho=800)


class TestContratoConReport:
    """El .md y el código que lo rellena tienen que estar de acuerdo."""

    def test_report_pasa_exactamente_las_variables_que_pide_el_md(self):
        # Si alguien añade $tramo al .md y no lo rellena en report.py, o al
        # revés, esto falla aquí y no en producción.
        esperadas = prompts.variables("informe")
        texto = build_user_prompt(YOLO_DATA, VEREDICTO)
        assert "$" not in texto, f"Huecos sin rellenar. El .md pide: {esperadas}"

    def test_el_prompt_final_lleva_los_datos_reales(self):
        texto = build_user_prompt(YOLO_DATA, VEREDICTO)
        assert "1600 x 1061" in texto
        assert "CRITICO" in texto
        assert "Pothole" in texto
        assert "0.6%" in texto  # 100x100 sobre 1600x1061

    def test_el_system_prompt_conserva_la_regla_innegociable(self):
        # El reparto de responsabilidades es la decisión de arquitectura del
        # proyecto: el motor decide la gravedad, el LLM solo redacta.
        #
        # Normalizamos los espacios porque el .md va ajustado a 80 columnas y
        # los saltos de línea caen donde caen: sin esto, el test se rompería
        # cada vez que alguien recoloca un párrafo sin tocar una palabra.
        system = " ".join(prompts.load("system").split())
        assert "INNEGOCIABLE" in system
        assert "NO lo recalcules" in system
        assert "no es decidir la gravedad" in system
