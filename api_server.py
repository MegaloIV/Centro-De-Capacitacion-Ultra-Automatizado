# Archivo: api_server.py (FINAL Y CORREGIDO)

import os
import uvicorn
import unicodedata # <--- IMPORTANTE: Para quitar tildes de los nombres de archivo
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # <--- IMPORTANTE: Para servir los PDFs

# Importaciones del Proyecto
from config import settings
from data_models import Syllabus, PromptRequest 
from logic import run_macroproceso_1
from integrations import crear_orden_paypal
from ingestion import ejecutar_ingesta_autonoma 
from fabrication import fabricar_curso_completo 

# 0. PREPARACIÓN INICIAL
# Aseguramos que la carpeta de PDFs exista para que StaticFiles no falle al arrancar
if not os.path.exists("cursos_generados"):
    os.makedirs("cursos_generados")

# 1. CONFIGURACIÓN DE LA APP
app = FastAPI(
    title="Centro de Capacitación Ultra-Automatizado API",
    description="Endpoints para la automatización de propuestas y fabricación de cursos."
)

# CORS (Permitir acceso desde Lovable)
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",      
    allow_credentials=True,     
    allow_methods=["*"],        
    allow_headers=["*"],        
)

# MONTAR CARPETA DE DESCARGAS
# Esto hace accesible la carpeta física "cursos_generados" en la URL "/cursos"
app.mount("/cursos", StaticFiles(directory="cursos_generados"), name="cursos")


# 2. ENDPOINTS BÁSICOS

@app.get("/api/v1/health", response_model=Dict[str, Any])
def health_check():
    """Verifica que el servidor esté corriendo."""
    return {"status": "ok", "service": "Centro de Capacitación Backend"}

# 3. MACROPROCESO 1: DEFINICIÓN (CEREBRO)

@app.post("/api/v1/proceso-definicion", response_model=Syllabus)
async def generar_propuesta(request: PromptRequest):
    """Genera el Syllabus y la Cotización con IA."""
    print(f"\n--- API SOLICITUD ---")
    print(f"Solicitud recibida: {request.prompt}")
    
    syllabus = run_macroproceso_1(request.prompt)
    
    if syllabus is None:
        raise HTTPException(status_code=500, detail="Error generando el Syllabus.")
    
    print("--- API RESPUESTA ---")
    print(f"✅ Propuesta lista: {syllabus.curso_propuesto}")
    return syllabus

# 4. FASE 3: TRANSACCIÓN (PAYPAL)

@app.post("/api/v1/crear-orden-paypal")
async def iniciar_orden_paypal(syllabus_data: Syllabus):
    """Crea la orden de pago en PayPal."""
    try:
        # Convertimos Pydantic a Dict para la función de integración
        datos_cotizacion = syllabus_data.cotizacion.dict()

        orden_info = await crear_orden_paypal(datos_cotizacion)    
            
        print(f"\n[API PAYPAL] -> Orden creada. Link enviado.")
        
        return {
            "order_id": orden_info["order_id"],
            "approval_link": orden_info["approval_link"]
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ ERROR FATAL en crear-orden-paypal: {e}")
        raise HTTPException(status_code=500, detail="Error interno procesando pago.")

# 5. MACROPROCESO 2: FABRICACIÓN (MANOS Y BOCA)

def proceso_completo_fabricacion(syllabus: Syllabus):
    """
    TAREA EN SEGUNDO PLANO:
    1. Busca en internet y aprende (Ingestión).
    2. Escribe el curso y genera PDF (Fabricación).
    """
    # Paso 1: Ingesta
    try:
        ejecutar_ingesta_autonoma(syllabus.curso_propuesto)
    except Exception as e:
        print(f"⚠️ Error no crítico en ingesta: {e}")
    
    # Paso 2: Fabricación
    try:
        link_pdf = fabricar_curso_completo(syllabus)
        print(f"✨ CURSO FINALIZADO: {link_pdf}")
    except Exception as e:
        print(f"❌ Error crítico fabricando curso: {e}")

@app.post("/api/v1/iniciar-fabricacion")
async def iniciar_fabricacion(syllabus: Syllabus, background_tasks: BackgroundTasks):
    """
    Recibe la confirmación de pago y lanza la fabricación en background.
    """
    print(f"\n🏭 INICIANDO FABRICACIÓN PARA: {syllabus.curso_propuesto}")
    
    # --- PREDICCIÓN DE NOMBRE DE ARCHIVO (Lógica idéntica a fabrication.py) ---
    # 1. Normalizar (quitar tildes: ó -> o, ñ -> n)
    texto_limpio = unicodedata.normalize('NFKD', syllabus.curso_propuesto).encode('ascii', 'ignore').decode('ascii')
    # 2. Quitar caracteres no alfanuméricos
    safe_name = "".join([c for c in texto_limpio if c.isalnum()]) + ".pdf"
    
    # Generar el enlace futuro
    link_predicho = f"http://{settings.API_HOST}:{settings.API_PORT}/cursos/{safe_name}"
    
    # Lanzar tarea en segundo plano
    background_tasks.add_task(proceso_completo_fabricacion, syllabus)
    
    return {
        "status": "procesando", 
        "mensaje": "Fabricación iniciada.",
        "link_descarga_futuro": link_predicho 
    }
    
if __name__ == "__main__":
    print("Iniciando servidor Uvicorn...")
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)