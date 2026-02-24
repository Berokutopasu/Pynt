# config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from dotenv import load_dotenv

# Forza il caricamento del .env dalla root del progetto
load_dotenv()

class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # ==========================================
    # --- 1. API KEYS GROQ (Primary) ---
    # ==========================================
    GROQ_API_KEYS: Optional[str] = None

    @property
    def EFFECTIVE_GROQ_KEYS(self) -> List[str]:
        """Estrae la lista di chiavi Groq dalla stringa separata da virgola"""
        keys = []
        if self.GROQ_API_KEYS:
            keys = [k.strip() for k in self.GROQ_API_KEYS.split(",") if k.strip()]
        return keys

    # ==========================================
    # --- 2. API KEYS GOOGLE (Fallback) ---
    # ==========================================
    GOOGLE_API_KEYS: Optional[str] = None
    
    # Variabili opzionali per compatibilità
    ANTHROPIC_API_KEY: Optional[str] = None

    @property
    def EFFECTIVE_GOOGLE_KEYS(self) -> List[str]:
        """Logica esistente per Google"""
        keys = []
        if self.GOOGLE_API_KEYS:
            keys = [k.strip() for k in self.GOOGLE_API_KEYS.split(",") if k.strip()]
            
        # Fallback vecchia variabile singolare
        if not keys:
            legacy_key = os.getenv("GOOGLE_API_KEY")
            if legacy_key:
                keys.append(legacy_key)
        return keys

    # --- LLM Settings ---
    # Aggiorniamo il default a Llama 3 su Groq
    DEFAULT_LLM_MODEL: str = "llama-3.3-70b-versatile" 
    DEFAULT_TEMPERATURE: float = 0.0 # Per il coding meglio 0
    MAX_TOKENS: int = 4000
    
    # Semgrep
    SEMGREP_TIMEOUT: int = 30000
    SEMGREP_MAX_MEMORY: int = 4096
    
    # Agent Settings
    MAX_CONCURRENT_AGENTS: int = 5 # Alziamo a 5 perché Groq è veloce
    
    # Cache
    ENABLE_CACHE: bool = True
    CACHE_TTL: int = 3600
    
    class Config:
        env_file = ".env"
        extra = "ignore" 
        case_sensitive = True

# Singleton
settings = Settings()

def validate_settings():
    """Valida che ci siano le chiavi Groq (o Google come fallback)"""
    
    has_groq = len(settings.EFFECTIVE_GROQ_KEYS) > 0
    has_google = len(settings.EFFECTIVE_GOOGLE_KEYS) > 0

    if not has_groq and not has_google:
        raise ValueError(
            "❌ ERRORE CONFIGURAZIONE:\n"
            "Non è stata trovata nessuna API Key valida.\n"
            "Inserisci nel file .env:\n"
            "GROQ_API_KEYS=gsk_key1,gsk_key2 (Consigliato)\n"
            "oppure\n"
            "GOOGLE_API_KEYS=key1,key2"
        )
    
    print(f"✅ Configurazione OK. Trovate {len(settings.EFFECTIVE_GROQ_KEYS)} chiavi Groq.")
    return True