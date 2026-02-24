# models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


class AnalysisType(str, Enum):
    SECURITY = "security"
    BEST_PRACTICES = "best_practices"
    FAULT_DETECTION = "fault_detection"


class SeverityLevel(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class AnalysisRequest(BaseModel):
    code: str = Field(..., description="Codice sorgente da analizzare")
    language: str = Field(..., description="Linguaggio di programmazione")
    filename: str = Field(..., description="Nome del file")
    projectPath: Optional[str] = Field(None, description="Path del progetto")
    analysisTypes: List[AnalysisType] = Field(
    default=[AnalysisType.SECURITY],
    description="Tipi di analisi da eseguire",
    
    )


class Finding(BaseModel):
    line: int = Field(..., description="Numero di riga (1-based)")
    column: int = Field(default=0, description="Colonna iniziale")
    endLine: int = Field(..., description="Riga finale")
    endColumn: int = Field(..., description="Colonna finale")
    severity: SeverityLevel = Field(..., description="Livello di severità")
    message: str = Field(..., description="Messaggio breve")
    educationalExplanation: str = Field(..., description="Spiegazione educativa dettagliata")
    suggestedFix: Optional[str] = Field(None, description="Suggerimento per la correzione")
    executableFix: Optional[str] = None # Codice puro per l'autofix
    codeExample: Optional[str] = Field(None, description="Esempio di codice corretto")
    references: Optional[List[str]] = Field(default=[], description="Link di riferimento")
    analysisType: AnalysisType = Field(..., description="Tipo di analisi")
    ruleId: str = Field(..., description="ID della regola violata")
    isFalsePositive: bool = False
    file_path: Optional[str] = None

class AgentResponse(BaseModel):
    analysisType: AnalysisType
    findings: List[Finding]
    processingTime: float = Field(..., description="Tempo di elaborazione in secondi")


class AnalysisResponse(BaseModel):
    findings: List[Finding]
    analysisTime: float = Field(..., description="Tempo totale in secondi")
    language: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SemgrepResult(BaseModel):
    """Struttura risultato Semgrep"""
    check_id: str
    path: str
    start: dict  # {line, col}
    end: dict    # {line, col}
    extra: dict  # {message, severity, metadata}


class HealthResponse(BaseModel):
    status: str
    version: str
    agents_loaded: List[str]
    langchain_configured: bool