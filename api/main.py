"""RoadGuardian — orquestador.

Este es el Servicio B: coordina el microservicio de YOLO, el motor de
priorización y el LLM. No lleva PyTorch ni carga modelos: solo hace llamadas,
aplica reglas y compone el resultado.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import CORS_ORIGINS, CORS_ORIGIN_REGEX, YOLO_SPACE, check_required
from api.routes import analyze

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RoadGuardian API",
    description="Analiza fotografías de firmes: detecta daños, evalúa su gravedad y redacta un informe técnico.",
    version="0.1.0",
)

# Sin esto, el navegador bloquea cualquier llamada desde React: origen distinto.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, tags=["análisis"])


@app.on_event("startup")
def avisar_de_lo_que_falta() -> None:
    faltan = check_required()
    if faltan:
        # No abortamos: sin LLM el servicio sigue dando el veredicto. Pero que
        # no pase desapercibido.
        logger.warning("⚠️  Faltan variables (%s): no habrá informes.", ", ".join(faltan))
    logger.info("🔗 YOLO en %s", YOLO_SPACE)


@app.get("/", tags=["salud"])
def health_check():
    return {
        "status": "online",
        "servicio": "orquestador",
        "yolo_space": YOLO_SPACE,
        "configuracion_completa": not check_required(),
    }
