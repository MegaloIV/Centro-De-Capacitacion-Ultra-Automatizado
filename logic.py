# Archivo: logic.py (FINAL: Precios Estandarizados + Lógica de Clarificación)

# Importamos funciones individuales para controlar el flujo paso a paso
from chains import crear_cadena_extraccion, crear_cadena_syllabus, setup_llm, obtener_json_string
from data_models import Syllabus, Cotizacion
from typing import Optional
from config import settings 

# --- CONFIGURACIÓN DE TARIFAS (Tu Lógica de Negocio) ---
TARIFA_BASE_INICIAL = 50.0  # Costo fijo de arranque (Setup fee)
PRECIO_POR_MODULO = 150.00  # Costo por módulo
HORAS_POR_LECCION = 0.5     # Tiempo estimado por lección
PRECIO_POR_LECCION = 10.00  # Costo por lección

def calcular_precio_estandar(syllabus: Syllabus) -> Syllabus:
    """
    Toma el Syllabus generado por la IA y sobrescribe la cotización 
    con cálculos matemáticos exactos basados en tus tarifas.
    """
    # Programación Defensiva: Si no hay módulos (caso raro), retornamos sin calcular
    if not syllabus.modulos:
        return syllabus

    # 1. Analizar el Alcance (Contar lo que la IA generó)
    cantidad_modulos = len(syllabus.modulos)
    cantidad_lecciones = sum(len(m.lecciones) for m in syllabus.modulos)
    
    # 2. Calcular el Precio Total (Matemática Determinista)
    # Fórmula: Setup + (Módulos * $150) + (Lecciones * $10)
    precio_calculado = TARIFA_BASE_INICIAL + (cantidad_modulos * PRECIO_POR_MODULO) + (cantidad_lecciones * PRECIO_POR_LECCION)
    
    tiempo_total = cantidad_lecciones * HORAS_POR_LECCION
    
    # 3. Sobrescribir/Garantizar la Cotización en el objeto
    if not syllabus.cotizacion:
        syllabus.cotizacion = Cotizacion() # Inicializa con valores por defecto (0.0)

    # Asignación de valores finales
    syllabus.cotizacion.precio_base = round(precio_calculado, 2)
    # Llenamos los campos informativos para que la boleta los muestre si es necesario
    syllabus.cotizacion.precio_por_leccion = PRECIO_POR_LECCION 
    syllabus.cotizacion.precio_por_modulo = PRECIO_POR_MODULO
    syllabus.cotizacion.tiempo_estimado_horas = tiempo_total
    syllabus.cotizacion.moneda = "USD"
    
    print(f"💰 Cotización Estandarizada: {cantidad_modulos} Módulos + {cantidad_lecciones} Lecciones. Precio Final: ${syllabus.cotizacion.precio_base}")
    
    return syllabus

def run_macroproceso_1(prompt_cliente: str) -> Optional[Syllabus]:
    """
    Ejecuta el flujo con parada condicional (El Portero).
    Valida si la solicitud es clara antes de generar contenido y cobrar.
    """
    try:
        print(f"Lógica Core: Analizando intención para: '{prompt_cliente[:50]}...'")
        
        # Inicializamos el cerebro
        llm = setup_llm()
        
        # --- PASO 1: VALIDACIÓN Y EXTRACCIÓN (Subproceso 1.1 y 1.2) ---
        # Solo extraemos intención, no generamos curso todavía.
        extraccion_chain = crear_cadena_extraccion(llm)
        propuesta_inicial = extraccion_chain.invoke({"prompt_cliente": prompt_cliente})
        
        # --- EL PORTERO: ¿Es válida la solicitud? ---
        if not propuesta_inicial.es_solicitud_valida:
            print(f"⚠️ Solicitud ambigua. Pidiendo clarificación: {propuesta_inicial.pregunta_clarificacion}")
            
            # RETORNO TEMPRANO: No cobramos, no generamos syllabus.
            # Devolvemos un objeto Syllabus "vacío" que solo transporta la pregunta al Frontend.
            return Syllabus(
                curso_propuesto="Esperando detalles...",
                descripcion_corta="Se requiere más información.",
                modulos=[], # Lista vacía indica al Frontend que no hay curso aún
                cotizacion=None,
                mensaje_agente=propuesta_inicial.pregunta_clarificacion # La pregunta para el usuario
            )

        # --- PASO 2: GENERACIÓN DEL SYLLABUS (Solo si pasó el portero) ---
        print("✅ Solicitud válida. Generando Syllabus completo...")
        
        # Preparamos la entrada para la siguiente cadena
        json_propuesta = obtener_json_string(propuesta_inicial)
        
        # Ejecutamos la cadena de creación de contenido
        syllabus_chain = crear_cadena_syllabus(llm)
        syllabus_generado = syllabus_chain.invoke({"propuesta_json": json_propuesta})
        
        # --- PASO 3: ESTANDARIZACIÓN DE PRECIOS ---
        syllabus_final = calcular_precio_estandar(syllabus_generado)
        
        # Limpiamos el mensaje del agente para indicar éxito
        syllabus_final.mensaje_agente = "¡Propuesta lista! Revisa el plan de estudios."
        
        return syllabus_final
    
    except ValueError as ve:
        print(f"❌ Error de Configuración: {ve}")
        return None
    except Exception as e:
        print(f"❌ Error al ejecutar el Macroproceso 1 en logic.py: {e}")
        return None