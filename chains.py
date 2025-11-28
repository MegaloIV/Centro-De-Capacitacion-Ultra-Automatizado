# Archivo: chains.py (CORREGIDO para incluir Cotización)

from data_models import PropuestaCurso, Syllabus, Cotizacion # <-- Importamos Cotizacion
from prompts import PROMPT_EXTRACCION, PROMPT_SYLLABUS
# IMPORTACIÓN CORREGIDA: Usamos el conector de Google
from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough
import json
# Importamos 'os' solo si es necesario para el RAG, por ahora lo dejamos
from config import settings

# --- Configuración del LLM ---
def setup_llm():
    """Inicializa y retorna el Modelo de Lenguaje Grande (LLM) con Gemini."""
    
    # Verificación de la clave de Gemini (importante)
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY no configurada. Por favor, verifica tu archivo .env.")
    
    # Inicializa el LLM de Google.
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL, 
        temperature=settings.GEMINI_TEMPERATURE,
        api_key=settings.GEMINI_API_KEY 
    ) 

# --- Funciones Auxiliares ---

def obtener_json_string(propuesta: PropuestaCurso) -> str:
    """Convierte el objeto Pydantic de la Propuesta a JSON String."""
    return json.dumps(propuesta.dict(), indent=2, ensure_ascii=False)

# --- Ensamblaje de las Cadenas ---

def crear_cadena_extraccion(llm: ChatGoogleGenerativeAI):
    """Crea la cadena para la Extracción de Entidades y Competencias (Subproceso 1.2.1)."""
    parser = PydanticOutputParser(pydantic_object=PropuestaCurso)
    
    return PROMPT_EXTRACCION.partial(
        format_instructions=parser.get_format_instructions()
    ) | llm | parser

def crear_cadena_syllabus(llm: ChatGoogleGenerativeAI):
    """Crea la cadena para la Generación del Syllabus y la Cotización (Subproceso 1.3.1 y 1.3.2)."""
    parser = PydanticOutputParser(pydantic_object=Syllabus)
    
    # El LLM ahora debe calcular y devolver los campos de Cotizacion
    return PROMPT_SYLLABUS.partial(
        format_instructions=parser.get_format_instructions()
    ) | llm | parser

def crear_macroproceso_1():
    """
    Ensambla el flujo completo de LangChain para la Interacción y Definición.
    """
    # Verificación de la clave de API (para un mejor manejo de errores en el inicio)
    if not settings.GEMINI_API_KEY:
        raise ValueError("Error de Configuración: GEMINI_API_KEY no encontrada. Por favor, revisa el archivo .env.")

    llm = setup_llm()
    
    extraccion_chain = crear_cadena_extraccion(llm)
    syllabus_chain = crear_cadena_syllabus(llm)
    
    # Ensambla la Cadena Secuencial usando LCEL:
    full_chain = (
        {"propuesta_json": extraccion_chain | obtener_json_string}
        | RunnablePassthrough.assign(syllabus=syllabus_chain)
    )
    
    return full_chain