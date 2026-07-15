from pathlib import Path
from ultralytics import YOLO

# 1. Definir rutas dinámicas e infalibles
# BASE_DIR calcula automáticamente la carpeta raíz (roadguardian_backend)
BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / 'models' / 'best.pt'
INPUT_IMAGE = BASE_DIR / 'input' / 'bache_longitudinal.jpg'
OUTPUT_IMAGE = BASE_DIR / 'output' / 'bache_longitudinal_result.jpg'

def main():
    print(f"🧠 Cargando el modelo desde: {MODEL_PATH}")
    
    # Comprobación de seguridad por si el archivo no está
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"❌ No se encuentra el archivo best.pt en {MODEL_PATH}")
        
    model = YOLO(MODEL_PATH)
    
    print(f"📸 Analizando imagen: {INPUT_IMAGE}")
    
    if not INPUT_IMAGE.exists():
        raise FileNotFoundError(f"❌ No se encuentra la imagen de prueba en {INPUT_IMAGE}")
        
    # 3. Hacer la predicción
    resultados = model(INPUT_IMAGE, conf=0.25)
    
    # 4. Procesar y guardar los resultados
    for r in resultados:
        r.show() 
        r.save(filename=str(OUTPUT_IMAGE))
        
    print(f"✅ ¡Análisis completado! Revisa la carpeta output.")

if __name__ == '__main__':
    main()