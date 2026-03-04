# main.py
from fastapi import FastAPI, HTTPException, Body, logger
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
import asyncio
from typing import List
from service.rag_service import RAGService 

from models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    Finding,
    AgentResponse,
    HealthResponse,
    AnalysisType
)
from config.settings import settings, validate_settings
from analyzers.semgrep_analyzer import SemgrepAnalyzer

# Importiamo le Factory Function per tutti gli agenti
from agents.security_agent import get_security_agent
from agents.bestpractices_agent import get_bestpractices_agent
from agents.fault_agent import get_fault_agent


# Global Analyzer
semgrep_analyzer = None
rag_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events per inizializzazione e cleanup"""
    global semgrep_analyzer, rag_service
    
    print("Inizializzazione Pynt Server...")
    
    # Valida configurazione
    try:
        validate_settings()
        print(f"Configurazione validata (Modello: {settings.DEFAULT_LLM_MODEL})")
    except ValueError as e:
        print(f"Errore configurazione: {e}")
        raise
    
    # Inizializza Semgrep e  RAG
    try:
        semgrep_analyzer = SemgrepAnalyzer()
        rag_service = RAGService()
        print("Semgrep inizializzato e RAG inizializzato")
    except Exception as e:
        print(f"Errore inizializzazione Semgrep o RAG: {e}")
        raise
    
    print("\n Pynt Server pronto!")
    print(f"Server: http://{settings.HOST}:{settings.PORT}")
    print(f"Docs: http://{settings.HOST}:{settings.PORT}/docs\n")
    
    yield
    
    print("\nShutdown Pynt Server...")


# Crea app FastAPI
app = FastAPI(
    title="Pynt API",
    description="Educational Code Analysis API",
    version="0.2.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "Pynt API",
        "version": "0.2.0",
        "llm_provider": "Google Gemini",
        "status": "running",
        "docs": "/docs",
        "available_routes": [
            "/analyze/security",
            "/analyze/best-practices",
            "/analyze/fault-detection",
            "/analyze/all"
        ]
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="0.2.0",
        agents_loaded=["security", "best_practices", "fault_detection"],
        langchain_configured=settings.GROQ_API_KEYS is not None
    )


@app.post("/analyze/security", response_model=AnalysisResponse)
async def analyze_security(request: AnalysisRequest):
    """Analizza codice per vulnerabilità di sicurezza"""
    return await analyze_with_single_agent(
        request.code,
        request.language,
        AnalysisType.SECURITY,
        project_path=request.projectPath,
        filename=request.filename
    )


@app.post("/analyze/best-practices", response_model=AnalysisResponse)
async def analyze_best_practices(request: AnalysisRequest):
    """Analizza codice per best practices"""
    return await analyze_with_single_agent(
        request.code,
        request.language,
        AnalysisType.BEST_PRACTICES,
        project_path=request.projectPath,
        filename=request.filename
    )


@app.post("/analyze/fault-detection", response_model=AnalysisResponse)
async def analyze_fault_detection(request: AnalysisRequest):
    """Analizza codice per rilevamento di bug e fault"""
    return await analyze_with_single_agent(
        request.code,
        request.language,
        AnalysisType.FAULT_DETECTION,
        project_path=request.projectPath,
        filename=request.filename
    )


@app.post("/analyze/all", response_model=AnalysisResponse)
async def analyze_all(request: AnalysisRequest):
    """Analizza codice con tutti gli agenti in parallelo"""
    start_time = time.time()
    
    try:
        # Esegui analisi in parallelo per tutti i tipi
        tasks = [
            analyze_with_agent(request.code, request.language, AnalysisType.SECURITY,project_path=request.projectPath, filename=request.filename),
            analyze_with_agent(request.code, request.language, AnalysisType.BEST_PRACTICES,project_path=request.projectPath, filename=request.filename),
            analyze_with_agent(request.code, request.language, AnalysisType.FAULT_DETECTION,project_path=request.projectPath, filename=request.filename)
        ]
        
        # Attendi tutte le analisi in parallelo
        agent_responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Raccogli findings
        all_findings: List[Finding] = []
        for response in agent_responses:
            if isinstance(response, Exception):
                print(f"Errore critico nel task di analisi: {response}")
                continue
            if isinstance(response, AgentResponse):
                all_findings.extend(response.findings)
        
        analysis_time = time.time() - start_time
        
        return AnalysisResponse(
            findings=all_findings,
            analysisTime=round(analysis_time, 2),
            language=request.language
        )
        
    except Exception as e:
        print(f"Errore generale: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante analisi: {str(e)}"
        )


async def analyze_with_single_agent(
    code: str,
    language: str,
    analysis_type: AnalysisType,
    project_path: str = None,
    filename: str = None
) -> AnalysisResponse:
    """Analizza con un singolo agente e ritorna AnalysisResponse"""
    start_time = time.time()
    print(f"\n [API DEBUG] Ricevuto project_path: {project_path}")
    if project_path:
        print(f"   (Il RAG dovrebbe attivarsi)")
    else:
        print(f"   (RAG disattivato perché manca il path)")
    try:
        agent_response = await analyze_with_agent(code, language, analysis_type, project_path=project_path, filename=filename)
        
        analysis_time = time.time() - start_time
        
        return AnalysisResponse(
            findings=agent_response.findings,
            analysisTime=round(analysis_time, 2),
            language=language
        )
        
    except Exception as e:
        print(f"Errore in analyze_with_single_agent ({analysis_type}): {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante analisi {analysis_type}: {str(e)}"
        )


async def analyze_with_agent(
    code: str,
    language: str,
    analysis_type: AnalysisType,
    project_path: str = None,
    filename: str = None
) -> AgentResponse:
    """Esegue analisi con un agente specifico"""
    start_time = time.time()
    
    try:
        # 1. Ottieni agente appropriato usando la Factory Function
        agent = None
        
        if analysis_type == AnalysisType.SECURITY:
            agent = get_security_agent(language)
        elif analysis_type == AnalysisType.BEST_PRACTICES:
            agent = get_bestpractices_agent(language)
        elif analysis_type == AnalysisType.FAULT_DETECTION:
            agent = get_fault_agent(language)
            
        if not agent:
            print(f" Nessun agente trovato per {analysis_type}")
            return AgentResponse(analysisType=analysis_type, findings=[], processingTime=0)

        # 2. ESECUZIONE UNIFICATA
        # Il nuovo BaseAgent fa tutto: chiama Semgrep (su thread) e poi LLM (su thread/async)
        # Non dobbiamo più chiamare semgrep_analyzer manualmente qui.
        
        findings = await agent.analyze(
            code=code, 
            language=language, 
            project_path=project_path, 
            rag_service=rag_service if project_path else None,
            filename=filename
        )
        
        processing_time = time.time() - start_time
        
        return AgentResponse(
            analysisType=analysis_type,
            findings=findings,
            processingTime=round(processing_time, 2)
        )
        
    except Exception as e:
        print(f" Errore in analyze_with_agent ({analysis_type}): {e}")
        import traceback
        print(traceback.format_exc()) # Utile per debuggare
        return AgentResponse(
            analysisType=analysis_type, 
            findings=[], 
            processingTime=round(time.time() - start_time, 2)
        )
@app.post("/analyze/deep-scan")
async def deep_scan(
    code: str = Body(..., embed=True),
    file_path: str = Body(..., embed=True),
    project_path: str = Body(None, embed=True),
    language: str = Body("python", embed=True)
):
    """
    Esegue un'analisi profonda (Deep Scan) per individuare Falsi Negativi.
    Incrocia i dati di Semgrep con il contesto RAG per generare report con esempi di correzione.
    """
    print(f"\n[DEEP SCAN] Richiesta ricevuta per: {file_path}")
    print(f"[DEEP SCAN] Linguaggio: {language}")
    
    start_time = time.time()
    
    try:
        # 1. ANALISI SEMGREP (Baseline)
        # Eseguiamo i 3 tipi di analisi per dare all'LLM il contesto di ciò che è già noto
        all_semgrep_findings = []
        analysis_types = [
            AnalysisType.SECURITY, 
            AnalysisType.BEST_PRACTICES, 
            AnalysisType.FAULT_DETECTION
        ]
        
        for a_type in analysis_types:
            try:
                findings = semgrep_analyzer.analyze(
                    code=code,
                    language=language,
                    analysis_type=a_type,
                    project_path=project_path,
                    filename=file_path  # <--- Questo attiva il tuo mapping e l'estensione .py
                )
                if findings:
                    all_semgrep_findings.extend(findings)
            except Exception as e:
                print(f"Errore Semgrep ({a_type}): {e}")

        # 2. GESTIONE RAG (Ingestione e Recupero Contesto)
        rag_context = ""
        if project_path and rag_service:
            try:
                # --- FASE 1: Ingestione/Indicizzazione Progetto ---
                print(f" [RAG] Verificando indicizzazione per: {project_path}")
                await asyncio.to_thread(
                    rag_service.ingest_project,
                    project_path,
                    language
                )

                # --- FASE 2: Recupero Contesto (Indipendente da Semgrep) ---
                # Query mirata alla sicurezza e alla generazione di esempi di correzione
                query = f"security validation, sanitization patterns and remediation examples for file {file_path} in {language}"
                print(f" [RAG] Recupero contesto per la query: {query[:50]}...")
                
                rag_context = await asyncio.to_thread(
                    rag_service.retrieve_context, 
                    query
                )

                if rag_context:
                    print(f" [RAG DEBUG] Trovato contesto ({len(rag_context)} caratteri)")
                else:
                    print(f" [RAG DEBUG] Nessun contesto rilevante trovato.")

            except Exception as e:
                print(f" [RAG ERROR] Errore durante il processo RAG: {e}")
                rag_context = "Contesto globale non disponibile causa errore tecnico."

        # 3. GENERAZIONE REPORT TRAMITE AGENTE
        
        agent = get_security_agent(language)
        
        # Generiamo il report. La logica dell'agente produrrà EXPLANATION, IMPORTS, FIX e CODE_EXAMPLE.
        deep_report = await agent.generate_deep_scan_report(
            code=code,
            semgrep_findings=all_semgrep_findings,
            rag_context=rag_context
        )
        
        duration = time.time() - start_time
        
        # Restituiamo il pacchetto completo al frontend, incluso il codice originale per la visualizzazione
        return {
            "status": "success",
            "file": file_path,
            "code": code,
            "findings_semgrep_count": len(all_semgrep_findings),
            "rag_active": bool(rag_context),
            "report": deep_report,
            "debug": {
                "processing_time": round(duration, 2)
            }
        }

    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)