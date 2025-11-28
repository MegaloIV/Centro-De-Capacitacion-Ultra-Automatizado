# Archivo: api_server.py (Modificado para usar config.py y CORS)
from integrations import crear_orden_paypal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # <-- NUEVA IMPORTACIÓN
from logic import run_macroproceso_1
from models.data_models import Syllabus, PromptRequest 
from config import settings
import uvicorn
from typing import Dict, Any

# Crea la aplicación FastAPI
app = FastAPI(
    title="Centro de Capacitación Ultra-Automatizado API",
    description="Endpoints para la automatización de propuestas y fabricación de cursos con LangChain."
)

# Define los orígenes (dominios/puertos) que tienen permitido acceder a esta API.
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",      # Permite estos orígenes (Lovable)
    allow_credentials=True,     # Permite cookies de origen cruzado (si fueran necesarias)
    allow_methods=["*"],        # Permite todos los métodos (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],        # Permite todas las cabeceras
)

# Endpoint de Prueba para verificar que el servicio está activo
@app.get("/api/v1/health", response_model=Dict[str, Any])
def health_check():
    """Verifica que el servidor esté corriendo."""
    return {"status": "ok", "service": "LangChain Macroprocess 1 Backend"}

# Endpoint principal para la Interacción y Definición (Macroproceso 1)
@app.post("/api/v1/proceso-definicion", response_model=Syllabus)
async def generar_propuesta(request: PromptRequest):
    """
    Recibe el prompt del cliente desde Lovable, ejecuta la lógica de LangChain y 
    devuelve el Syllabus estructurado.
    """
    prompt_cliente = request.prompt
    
    print(f"\n--- API SOLICITUD ---")
    print(f"Solicitud de Lovable recibida. Prompt: {prompt_cliente}")
    
    # Llama a la lógica de LangChain
    syllabus = run_macroproceso_1(prompt_cliente)
    
    if syllabus is None:
        raise HTTPException(status_code=500, detail="Error en el motor de IA. No se pudo generar el Syllabus. Revise los logs del servidor.")
    
    print("--- API RESPUESTA ---")
    print(f"✅ Respuesta JSON lista para enviar a Lovable. Curso: {syllabus.curso_propuesto}")
    
    # FastAPI automáticamente serializa el objeto Pydantic Syllabus a JSON
    return syllabus

# Endpoint para iniciar la transacción de PayPal (Fase 3: La Transacción)
# Endpoint para iniciar la transacción de PayPal (Fase 3: La Transacción)
@app.post("/api/v1/crear-orden-paypal")
async def iniciar_orden_paypal(syllabus_data: Syllabus):
    """
    Recibe el Syllabus completo, crea una orden de pago en PayPal y devuelve
    el enlace de aprobación para que Lovable redirija al cliente.
    """
    try:
        # ESTA ES LA LÍNEA CLAVE. DEBE TENER AWAIT.
        # Si esta línea falla, el error 'coroutine was never awaited' desaparece.
        datos_cotizacion = syllabus_data.cotizacion.dict()

        orden_info = await crear_orden_paypal(datos_cotizacion)    
            
        print(f"\n[API PAYPAL] -> Orden creada para {syllabus_data.curso_propuesto}. Enlace listo.")
        
        # Devuelve el ID de la orden y el enlace de aprobación al Front-end Lovable
        return {
            "order_id": orden_info["order_id"],
            "approval_link": orden_info["approval_link"]
        }
    
    except HTTPException as e:
        # Captura errores específicos de PayPal
        raise e
    except Exception as e:
        # Este 'except' captura el error si 'await' NO se puso
        print(f"❌ ERROR FATAL en crear-orden-paypal: {e}")
        raise HTTPException(status_code=500, detail="Error interno al procesar la orden de pago.")
    
if __name__ == "__main__":
    # Usamos los parámetros de configuración de 'settings' para iniciar el servidor
    print("Iniciando servidor Uvicorn...")
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)