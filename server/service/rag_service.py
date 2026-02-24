# service/rag_service.py
import os
import time
from typing import List

# --- MODIFICA 1: Usiamo Embeddings Locali invece di Google ---
from langchain_community.embeddings import HuggingFaceEmbeddings 
# -----------------------------------------------------------

from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from config.settings import settings

class RAGService:
    _instance = None #variabile di classe per singleton
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.vector_store = None #indice vettoriale in memoria
        
        # --- MODIFICA 2: Inizializzazione Modello Locale ---
        print("🧠 RAG: Caricamento modello di embedding locale (HuggingFace)...")
        # 'all-MiniLM-L6-v2' è piccolo, veloce e molto accurato per il codice
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")# istruzione per caricare il modello di embedding locale
        print("🧠 RAG: Modello locale pronto!")
        # ---------------------------------------------------
        
        self.current_project_path = None
        self._initialized = True

    def ingest_project(self, project_path: str, language: str = "python"):
        """
        Indicizza l'intero progetto usando Embeddings Locali (No Rate Limits!)
        """
        # Evita re-indicizzazione inutile
        if self.current_project_path == project_path and self.vector_store:
            print(f"✅ RAG: Progetto {project_path} già in memoria.")
            return

        print(f"🔄 RAG: Lettura file da {project_path}...")
        
        glob_pattern = "**/*.py"
        lang_enum = Language.PYTHON
        
        if language.lower() in ["javascript", "typescript", "ts", "js"]:
            glob_pattern = "**/*.{js,ts,jsx,tsx}"
            lang_enum = Language.JS
        elif language.lower() == "java":
            glob_pattern = "**/*.java"
            lang_enum = Language.JAVA

        try:
            # 1. Caricamento File: scansiona la cartella del progetto e carica i file di codice (escludendo cartelle comuni come venv, node_modules, .git)
            loader = DirectoryLoader(
                project_path,
                glob=glob_pattern,#filtra in base al linguaggio
                loader_cls=TextLoader,
                show_progress=False,
                use_multithreading=True,
                exclude=["**/venv/**", "**/node_modules/**", "**/.git/**", "**/__pycache__/**"] #esclude cartelle comuni che non contengono codice sorgente rilevante
            )
            docs = loader.load()#legge fisicamente i file e li carica in memoria come documenti per l'indicizzazione

            if not docs:
                print("⚠️ RAG: Nessun file di codice trovato nella cartella.")
                return

            # 2. Splitting: divvide i file in chunk più piccoli (1000 token con 100 di overlap) per migliorare la precisione del recupero
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=lang_enum,
                chunk_size=1000, # ogni pezzo sarà di massimo 1000 token (circa 750 parole)
                chunk_overlap=100 # sovrapposizione di 100 token tra i chunk per mantenere il contesto
            )
            splits = splitter.split_documents(docs)
            
            print(f"🔄 RAG: Creazione indici vettoriali per {len(splits)} chunks...")

            # 3. Creazione Vector Store (LOCALE, quindi veloce e senza errori 429)
            self.vector_store = FAISS.from_documents(splits, self.embeddings)#crea l'indice vettoriale in memoria usando i chunk e gli embeddings locali
            
            self.current_project_path = project_path
            print(f"✅ RAG: Indicizzazione completata con successo!")

        except Exception as e:
            print(f"❌ RAG Error: {e}")
            import traceback
            traceback.print_exc()


    #prende una query e restituisce i chunk di codice più rilevanti per quella query, formattati con il nome del file e il contenuto. 
    # #Questi chunk saranno poi usati come contesto per l'LLM durante l'analisi.
    def retrieve_context(self, query: str, k: int = 40) -> str:
        """Recupera il codice rilevante"""
        if not self.vector_store:
            return ""
            
        try:
            # Cerca i documenti più simili
            docs = self.vector_store.similarity_search(query, k=k)
            
            context_parts = []
            for doc in docs:
                file_name = os.path.basename(doc.metadata.get('source', 'unknown'))
                # Aggiungiamo il path relativo per dare più contesto all'LLM
                rel_path = doc.metadata.get('source', '').replace(self.current_project_path, '')
                
                context_parts.append(f"FILE: {rel_path}\nCONTENUTO:\n{doc.page_content}")
            
            return "\n----------------\n".join(context_parts)
        except Exception as e:
            print(f"❌ RAG Retrieval Error: {e}")
            return ""