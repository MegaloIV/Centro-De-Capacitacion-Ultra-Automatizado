# Archivo: config.py (CORREGIDO para Gemini y Estabilidad de Red)

from pydantic_settings import BaseSettings
from typing import Optional

# No es necesario importar BaseSettings dos veces.

class Settings(BaseSettings):
    # --- Configuración de la IA (Cerebro Digital) ---
    # Clave de la API de Gemini (¡ESENCIAL!)
    GEMINI_API_KEY: str

    # Configuración del modelo de Gemini
    GEMINI_MODEL: str = "gemini-2.5-flash"  # Modelo rápido y eficiente para Syllabus
    GEMINI_TEMPERATURE: float = 0.2         # Parámetro para creatividad (0.0 es determinista)
    
    # --- Configuración del Sistema Circulatorio (API) ---
    # CORRECCIÓN CLAVE: Usamos 127.0.0.1 por defecto en desarrollo para evitar errores 400 Bad Request/CORS.
    API_HOST: str = "127.0.0.1" 
    API_PORT: int = 8000

    # ... (Paypal) ...
    PAYPAL_CLIENT_ID: str # <-- ID del Cliente de PayPal
    PAYPAL_SECRET: str    # <-- Secreto del Cliente de PayPal
    PAYPAL_MODE: str = 'sandbox' # o 'live'
    
    # --- Configuración de la Memoria a Largo Plazo (RAG) ---
    CHROMA_DB_PATH: str = "vector_db/"
    
    # --- Configuraciones Opcionales (Ejemplo: Stripe) ---
    STRIPE_API_KEY: Optional[str] = None
    
    # Clase de configuración interna de Pydantic Settings
    class Config:
        env_file = ".env"  # Pydantic buscará variables en este archivo
        env_file_encoding = 'utf-8'

# Instancia de configuración que se usa en toda la aplicación
settings = Settings()