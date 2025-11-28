# Archivo: ingestion.py
# SISTEMA DIGESTIVO TURBO (Embeddings Locales - Sin Límites)

import os
import shutil
import requests
import time
import re
from typing import List
from duckduckgo_search import DDGS

# Herramientas RAG
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
# CAMBIO CLAVE: Usamos HuggingFace para embeddings locales (CPU)
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_google_genai import ChatGoogleGenerativeAI # Solo usamos Gemini para generar texto, no para vectores
from langchain_core.documents import Document

from config import settings

# Rutas
DATA_PATH = "content/" 
CHROMA_PATH = settings.CHROMA_DB_PATH 

# --- 0. UTILIDADES ---

def extraer_palabras_clave(titulo_largo: str) -> str:
    """Simplifica títulos para búsqueda."""
    if ":" in titulo_largo: titulo_largo = titulo_largo.split(":")[0]
    stop_words = ["curso", "completo", "de", "en", "para", "el", "la", "introducción", "master", "maestría", "taller", "guía", "aprende"]
    palabras = re.sub(r'[^\w\s]', '', titulo_largo.lower()).split()
    palabras_clave = [p for p in palabras if p not in stop_words and len(p) > 2]
    query = " ".join(palabras_clave[:4])
    return query if query else titulo_largo[:30]

def verificar_contenido_existente() -> bool:
    """Revisa si ya hay PDFs o TXTs."""
    if not os.path.exists(DATA_PATH): return False
    files = os.listdir(DATA_PATH)
    return any(f.endswith('.pdf') or f.endswith('.txt') for f in files)

# --- 1. MOTOR DE BÚSQUEDA ---

def descargar_desde_url(url: str, tema: str, indice: int) -> bool:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        print(f"      ⬇️ Intentando: {url[:60]}...")
        response = requests.get(url, headers=headers, timeout=10, stream=True)
        content_type = response.headers.get('Content-Type', '').lower()
        
        if response.status_code == 200 and ('pdf' in content_type or url.endswith('.pdf')):
            safe_tema = "".join([c for c in tema if c.isalnum()])[:10]
            nombre_archivo = f"auto_{safe_tema}_{int(time.time())}_{indice}.pdf"
            ruta_archivo = os.path.join(DATA_PATH, nombre_archivo)
            
            with open(ruta_archivo, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"      ✅ GUARDADO: {nombre_archivo}")
            return True
    except: pass
    return False

def buscar_y_bajar_pdfs_reales(titulo_curso: str):
    tema_clave = extraer_palabras_clave(titulo_curso)
    print(f"\n🌍 AUTO-AGENTE: Buscando: '{tema_clave}'...")
    
    if not os.path.exists(DATA_PATH): os.makedirs(DATA_PATH)

    queries = [f"{tema_clave} filetype:pdf", f"{tema_clave} manual pdf"]
    archivos_bajados = 0
    
    try:
        with DDGS() as ddgs:
            for query in queries:
                if archivos_bajados >= 1: break 
                print(f"   🔎 Query: '{query}'")
                try:
                    resultados = list(ddgs.text(query, max_results=3))
                    if not resultados: continue
                    for i, r in enumerate(resultados):
                        url = r.get('href')
                        if not url: continue
                        if descargar_desde_url(url, tema_clave, i):
                            archivos_bajados += 1
                            if archivos_bajados >= 1: break
                except Exception as e:
                    time.sleep(1)
    except Exception as e: print(f"⚠️ Error DDGS: {e}")
    return archivos_bajados

# --- 2. GENERADOR SINTÉTICO ---

def generar_conocimiento_base(tema: str):
    print("⚠️ ALERTA: No se encontraron PDFs. Generando sintético...")
    # Gemini SOLO lo usamos para escribir el texto, eso consume muy poca quota.
    llm = ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL, google_api_key=settings.GEMINI_API_KEY)
    
    prompt = f"Escribe un manual técnico detallado sobre: {tema}. Mínimo 1500 palabras. Estructurado."
    try:
        contenido = llm.invoke(prompt).content
        if not os.path.exists(DATA_PATH): os.makedirs(DATA_PATH)
        ruta_txt = os.path.join(DATA_PATH, "conocimiento_sintetico.txt")
        with open(ruta_txt, "w", encoding="utf-8") as f: f.write(contenido)
        print(f"✅ SINTÉTICO CREADO.")
        time.sleep(2) 
        return True
    except Exception as e:
        print(f"❌ Error sintético: {e}")
        return False

# --- 3. PROCESAMIENTO VECTORIAL (MODO TURBO LOCAL) ---

def procesar_memoria():
    if not os.path.exists(DATA_PATH): return
    print(f"📂 Procesando biblioteca...")
    
    docs = []
    try: docs.extend(DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls=PyPDFLoader).load())
    except: pass
    try:
        for f in os.listdir(DATA_PATH):
            if f.endswith(".txt"):
                docs.extend(TextLoader(os.path.join(DATA_PATH, f), encoding="utf-8").load())
    except: pass
    
    if not docs: return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(docs)
    total_chunks = len(chunks)

    # --- CAMBIO CLAVE: MODELO LOCAL ---
    print(f"🧠 Cargando modelo de embeddings local (HuggingFace)...")
    # Este modelo se descargará solo la primera vez (aprox 80MB) y luego vive en tu PC.
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    if os.path.exists(CHROMA_PATH):
        try: shutil.rmtree(CHROMA_PATH)
        except: pass

    print(f"🚀 Vectorizando {total_chunks} fragmentos a máxima velocidad (CPU Local)...")
    
    try:
        # Ya no necesitamos batching ni pausas, tu CPU puede manejar esto rápido.
        Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
        print(f"✅ ¡MEMORIA CREADA CON ÉXITO! Sin límites.")
    except Exception as e:
        print(f"❌ Error vectorial: {e}")

# --- MAESTRO ---

def ejecutar_ingesta_autonoma(tema_curso: str):
    print(f"\n🚀 [BACKGROUND TASK] Iniciando: {tema_curso}")
    
    # 1. Intentar descargar
    buscar_y_bajar_pdfs_reales(tema_curso)
    
    # 2. Verificar si tenemos algo
    if not verificar_contenido_existente():
        generar_conocimiento_base(tema_curso)
    else:
        print("✅ Contenido suficiente detectado.")
    
    # 3. Procesar
    procesar_memoria()
    print(f"🏁 [BACKGROUND TASK] Finalizada.")

if __name__ == "__main__":
    t = input("Tema: ")
    ejecutar_ingesta_autonoma(t)