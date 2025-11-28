# Archivo: models/data_models.py (CORREGIDO FINAL: Campos de Cotización Agregados)

from pydantic import BaseModel, Field
from typing import List, Optional

# --- Estructura para la Extracción Inicial (Macroproceso 1.2) ---

class Habilidad(BaseModel):
    """Habilidad clave identificada en el prompt del cliente."""
    tipo: str = Field(description="Clasifica la habilidad como 'Blanda' o 'Tecnica'.")
    nombre: str = Field(description="Nombre descriptivo de la habilidad (ej. 'Manejo de objeciones').")
    mapeo_competencia: str = Field(description="Etiqueta interna para la búsqueda en la biblioteca (ej. 'Negociación Avanzada').")

class PropuestaCurso(BaseModel):
    """Análisis inicial del prompt del cliente (Fase de Entendimiento)."""
    # Campos del Portero (Subproceso 1.1)
    es_solicitud_valida: bool = Field(description="True si el usuario especificó un tema claro.")
    pregunta_clarificacion: Optional[str] = Field(default=None, description="Pregunta para pedir detalles si es necesario.")
    
    audiencia_objetivo: Optional[str] = Field(default=None, description="Descripción de la audiencia.")
    resumen_necesidad: Optional[str] = Field(default=None, description="Resumen conciso de la necesidad.")
    habilidades_identificadas: List[Habilidad] = Field(default_factory=list)

# --- Estructura para la Cotización Dinámica ---

class Cotizacion(BaseModel):
    """Estructura de la cotización dinámica, esencial para la transacción (Fase 3)."""
    precio_base: float = Field(default=0.0, description="Costo total calculado.")
    precio_por_usuario: float = Field(default=0.0, description="Costo mensual de suscripción por usuario.")
    
    # --- CAMPOS FALTANTES AGREGADOS AQUÍ ---
    precio_por_modulo: float = Field(default=0.0, description="Costo unitario por módulo.")
    precio_por_leccion: float = Field(default=0.0, description="Costo unitario por lección.")
    # ---------------------------------------
    
    moneda: str = Field(default="USD", description="Moneda de la cotización.")
    tiempo_estimado_horas: float = Field(default=0.0, description="Tiempo total estimado.")

# --- Estructura para la Generación del Syllabus (Macroproceso 1.3) ---

class Leccion(BaseModel):
    """Lección individual dentro de un módulo."""
    titulo: str = Field(description="Título descriptivo de la lección.")
    objetivo_base: str = Field(description="Objetivo de aprendizaje conciso.")

class Modulo(BaseModel):
    """Módulo principal del curso."""
    titulo: str
    lecciones: List[Leccion]

class Syllabus(BaseModel):
    """Estructura final del Plan de Estudios."""
    curso_propuesto: str = Field(default="Consulta en Progreso...", description="Título del curso.")
    descripcion_corta: str = Field(default="", description="Descripción breve.")
    
    modulos: List[Modulo] = Field(default_factory=list)
    cotizacion: Optional[Cotizacion] = None
    
    mensaje_agente: Optional[str] = Field(default=None, description="Mensaje directo de la IA al usuario.")

class PromptRequest(BaseModel):
    """Modelo de entrada para la API."""
    prompt: str = Field(description="Solicitud del cliente.")