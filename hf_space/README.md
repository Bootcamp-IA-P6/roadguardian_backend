---
title: RoadGuardian API
emoji: 🛣️
colorFrom: gray
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# 🛣️ RoadGuardian AI Microservice

Microservicio backend alojado en Docker para la detección de daños en el asfalto (baches, grietas longitudinales, transversales y de cocodrilo). 

Este servidor expone una API REST construida con **FastAPI** que carga un modelo YOLO11m entrenado a medida y procesa inferencias en tiempo real.

## Endpoint Principal
* **`POST /predict`**: Recibe un archivo de imagen (`multipart/form-data`) y devuelve las coordenadas de las cajas delimitadoras (Bounding Boxes), la clase detectada y el nivel de confianza en formato JSON.

*Nota: Esta API descarga automáticamente los pesos (`best.pt`) desde el repositorio de modelos asociado de Hugging Face en el momento de arranque.*