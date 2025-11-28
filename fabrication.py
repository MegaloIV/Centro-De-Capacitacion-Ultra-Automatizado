# Archivo: fabrication.py
# EL ESCRITOR: Generación de PDF Profesional con RAG

import os
import markdown2
from xhtml2pdf import pisa
from typing import List
import unicodedata # <--- NUEVA IMPORTACIÓN CRÍTICA PARA ELIMINAR TILDES

# RAG
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import settings
from data_models import Syllabus

# Rutas
CHROMA_PATH = settings.CHROMA_DB_PATH
OUTPUT_PATH = "cursos_generados/" # Carpeta física
# URL Base (Cambia localhost por tu dominio real cuando subas a producción)
BASE_URL = f"http://{settings.API_HOST}:{settings.API_PORT}/cursos/"

# --- 1. CONFIGURACIÓN ---

def cargar_memoria():
    if not os.path.exists(CHROMA_PATH):
        raise FileNotFoundError("Memoria vacía.")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

def setup_escritor():
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL, 
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.3
    )

def recuperar_contexto(db, query: str) -> str:
    docs = db.similarity_search(query, k=2) # Top 2 fragmentos
    return "\n".join([d.page_content for d in docs])

# --- 2. GENERADOR DE PDF ---

def convertir_md_a_pdf(contenido_md: str, nombre_archivo: str) -> str:
    """Convierte Markdown a HTML y luego a PDF."""
    
    # 1. Convertir Markdown a HTML
    html_content = markdown2.markdown(contenido_md)
    
    # 2. Añadir estilos CSS para que parezca profesional
    estilos = """
    <style>
        @page { size: A4; margin: 2cm; }
        body { font-family: Helvetica, sans-serif; line-height: 1.5; color: #333; }
        h1 { color: #2563eb; text-align: center; border-bottom: 2px solid #2563eb; padding-bottom: 10px; }
        h2 { color: #1e40af; margin-top: 20px; border-bottom: 1px solid #ddd; }
        h3 { color: #374151; margin-top: 15px; }
        p { text-align: justify; }
        strong { color: #111; }
        .footer { position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 10px; color: #999; }
    </style>
    """
    
    html_completo = f"""
    <html>
    <head>{estilos}</head>
    <body>
        {html_content}
        <div class='footer'>Generado por Centro de Capacitación AI - Ultra Automatizado</div>
    </body>
    </html>
    """
    
    # 3. Guardar PDF
    ruta_pdf = os.path.join(OUTPUT_PATH, nombre_archivo)
    with open(ruta_pdf, "wb") as f:
        pisa_status = pisa.CreatePDF(html_completo, dest=f)
    
    if pisa_status.err:
        print("❌ Error generando PDF")
        return ""
        
    return ruta_pdf

# --- 3. ESCRITURA ---

def generar_contenido_leccion(escritor, titulo: str, objetivo: str, contexto: str) -> str:
    prompt = ChatPromptTemplate.from_template("""
    Eres un profesor experto. Escribe una lección educativa.
    TEMA: {titulo} ({objetivo})
    CONTEXTO TÉCNICO: {contexto}
    
    Escribe el contenido en formato Markdown. Sé claro, usa ejemplos y subtítulos.
    """)
    chain = prompt | escritor | StrOutputParser()
    return chain.invoke({"titulo": titulo, "objetivo": objetivo, "contexto": contexto})

# --- 4. MAESTRO FABRICANTE ---

def fabricar_curso_completo(syllabus: Syllabus) -> str:
    """Genera el curso y devuelve el LINK DE DESCARGA."""
    print(f"\n🏭 FABRICACIÓN: Escribiendo '{syllabus.curso_propuesto}'...")
    
    if not os.path.exists(OUTPUT_PATH): os.makedirs(OUTPUT_PATH)
    
    # Preparar
    try:
        db = cargar_memoria()
    except:
        print("⚠️ Memoria no encontrada, escribiendo con conocimiento general.")
        db = None
        
    escritor = setup_escritor()
    
    # Estructura del Documento
    md_total = f"# {syllabus.curso_propuesto}\n\n**Descripción:** {syllabus.descripcion_corta}\n\n---\n\n"
    
    # Escribir Módulos
    for i, mod in enumerate(syllabus.modulos):
        md_total += f"## Módulo {i+1}: {mod.titulo}\n\n"
        for j, lec in enumerate(mod.lecciones):
            print(f"   📝 Redactando: {lec.titulo}...")
            
            contexto = ""
            if db: contexto = recuperar_contexto(db, f"{lec.titulo} {lec.objetivo_base}")
            
            contenido = generar_contenido_leccion(escritor, lec.titulo, lec.objetivo_base, contexto)
            md_total += f"### {i+1}.{j+1} {lec.titulo}\n{contenido}\n\n"
    
    # --- CORRECCIÓN DE NOMBRE DE ARCHIVO ---
    # Convertimos "Programación" en "Programacion" para evitar errores 404
    texto_limpio = unicodedata.normalize('NFKD', syllabus.curso_propuesto).encode('ascii', 'ignore').decode('ascii')
    safe_name = "".join([c for c in texto_limpio if c.isalnum()]) + ".pdf"
    
    convertir_md_a_pdf(md_total, safe_name)
    
    # Generar Link
    link_final = f"{BASE_URL}{safe_name}"
    print(f"✅ CURSO LISTO: {link_final}")
    
    return link_final