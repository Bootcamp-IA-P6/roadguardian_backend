import pytest

from prioritization.priority_engine import evaluate_road_image, evaluate_single_damage
from prioritization.rules import calculate_bbox_area, get_damage_percentage


def bbox(x1, y1, x2, y2):
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def deteccion(clase, caja, conf=0.9):
    return {"class": clase, "bbox": caja, "confidence": conf}


def yolo_json(detecciones, width, height):
    return {
        "filename": "test.jpg",
        "image": {"width": width, "height": height},
        "total_detections": len(detecciones),
        "detections": detecciones,
    }


class TestGetDamagePercentage:
    def test_mide_contra_el_area_que_se_le_pasa(self):
        # Una caja de 100x100 en una imagen de 200x200 ocupa un cuarto.
        assert get_damage_percentage(100 * 100, 200 * 200) == 25.0

    def test_el_area_de_referencia_cambia_el_resultado(self):
        # El mismo daño en una foto más grande pesa proporcionalmente menos.
        area_daño = 100 * 100
        assert get_damage_percentage(area_daño, 200 * 200) == 25.0
        assert get_damage_percentage(area_daño, 400 * 400) == 6.25

    def test_area_invalida_revienta(self):
        with pytest.raises(ValueError):
            get_damage_percentage(1000, 0)


class TestBugDelAreaFija:
    """El motor asumía IMAGE_AREA = 640*640 para toda imagen.

    Con fotos reales (que nunca son cuadradas de 640) inflaba los porcentajes
    y disparaba CRITICO de más. Estos casos usan dimensiones reales de las
    fotos de input/ y fallarían con la constante fija.
    """

    def test_grieta_fina_en_foto_grande_no_es_critica(self):
        # Foto 1600x1061 (1.697.600 px). Una grieta de 200x100 = 20.000 px
        # es el 1,2% real. Contra 640x640 daría 4,9%: MEDIA en vez de BAJA.
        datos = yolo_json(
            [deteccion("Longitudinal Crack", bbox(100, 100, 300, 200))],
            width=1600, height=1061,
        )
        assert evaluate_road_image(datos)["nivel_alerta"] == "BAJA"

    def test_mismo_dano_distinta_resolucion_da_distinto_nivel(self):
        # El mismo bache de 150x150 px pesa mucho más en una foto pequeña.
        caja = [deteccion("Pothole", bbox(0, 0, 150, 150))]

        pequena = evaluate_road_image(yolo_json(caja, 400, 400))   # 14% → CRITICO
        grande = evaluate_road_image(yolo_json(caja, 2000, 2000))  # 0,5% → ALTA

        assert pequena["nivel_alerta"] == "CRITICO"
        assert grande["nivel_alerta"] == "ALTA"


class TestEvaluateRoadImage:
    def test_sin_detecciones_es_estable(self):
        resultado = evaluate_road_image(yolo_json([], 640, 640))
        assert resultado["nivel_alerta"] == "ESTABLE"

    def test_sin_dimensiones_revienta_en_vez_de_inventarselas(self):
        datos = {"detections": [deteccion("Pothole", bbox(0, 0, 100, 100))]}
        with pytest.raises(ValueError, match="dimensiones"):
            evaluate_road_image(datos)

    def test_se_queda_con_el_peor_dano(self):
        datos = yolo_json(
            [
                deteccion("Longitudinal Crack", bbox(0, 0, 50, 50)),
                deteccion("Pothole", bbox(0, 0, 300, 300)),          # el peor
                deteccion("Transverse Crack", bbox(0, 0, 60, 60)),
            ],
            width=640, height=640,
        )
        assert evaluate_road_image(datos)["nivel_alerta"] == "CRITICO"

    def test_confianza_baja_se_ignora(self):
        # Un bache enorme pero con conf 0.1 no debe disparar CRITICO.
        datos = yolo_json(
            [deteccion("Pothole", bbox(0, 0, 600, 600), conf=0.1)],
            width=640, height=640,
        )
        assert evaluate_road_image(datos)["nivel_alerta"] == "BAJA"


class TestCalculateBboxArea:
    def test_area_de_una_caja(self):
        assert calculate_bbox_area(bbox(10, 20, 110, 220)) == 100 * 200
