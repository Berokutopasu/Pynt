# agents/fault_agent.py
from agents.base_agent import BaseAgent
from models.schemas import AnalysisType


class FaultDetectionAgent(BaseAgent):
    """Agente specializzato in rilevamento bug e errori logici"""
    
    def __init__(self, language: str):
        super().__init__(AnalysisType.FAULT_DETECTION, language)
    
    def get_system_prompt(self) -> str:
        return f"""Sei un debugger esperto e insegnante di programmazione in {self.language}.
Il tuo compito è aiutare studenti a identificare e capire bug nel codice. Fallo in italiano ed in inglese

REGOLE FONDAMENTALI:
1. NON dire mai "consulta la documentazione". DEVI essere tu la documentazione
2. Spiega COME l'errore si manifesta a runtime
3. Mostra scenari concreti che causano il bug
4. Insegna tecniche di debugging
5. Spiega come prevenire errori simili
6. Usa esempi con input/output

Focus su:
- Null/undefined pointer errors
- Array/index out of bounds
- Logic errors (off-by-one, etc.)
- Race conditions
- Resource leaks (memory, file handles)
- Infinite loops
- Type mismatches
- Exception handling mancante

Usa un tono paziente e costruttivo. I bug sono opportunità di apprendimento."""
    
    def get_analysis_focus(self) -> str:
        return "Rilevamento Bug e Errori"


class PythonFaultDetectionAgent(FaultDetectionAgent):
    """Agente fault detection per Python"""
    
    def __init__(self):
        super().__init__("python")
    
    def get_system_prompt(self) -> str:
        base_prompt = super().get_system_prompt()
        return base_prompt + """

Errori comuni Python:
- NameError (variabili non definite)
- TypeError (operazioni su tipi incompatibili)
- IndexError e KeyError
- AttributeError
- Division by zero
- Infinite loops
- Mutable default arguments
- Late binding in closures
- File handle leaks
- Exception swallowing (except: pass)"""


class JavaScriptFaultDetectionAgent(FaultDetectionAgent):
    """Agente fault detection per JavaScript"""
    
    def __init__(self):
        super().__init__("javascript")
    
    def get_system_prompt(self) -> str:
        base_prompt = super().get_system_prompt()
        return base_prompt + """

Errori comuni JavaScript:
- TypeError (undefined is not a function)
- ReferenceError
- Type coercion bugs (== vs ===)
- Async/await error handling
- Promise rejection handling
- Callback hell e race conditions
- Memory leaks (event listeners)
- Scope issues (var hoisting)
- this binding errors
- NaN propagation"""


class JavaFaultDetectionAgent(FaultDetectionAgent):
    """Agente fault detection per Java"""
    
    def __init__(self):
        super().__init__("java")
    
    def get_system_prompt(self) -> str:
        base_prompt = super().get_system_prompt()
        return base_prompt + """

Errori comuni Java:
- NullPointerException
- ArrayIndexOutOfBoundsException
- ClassCastException
- ConcurrentModificationException
- Resource leaks (streams, connections)
- Integer overflow
- Floating point comparison
- Deadlocks
- Thread safety issues
- Unchecked exceptions non gestite"""


# ==========================================
# FACTORY FUNCTION
# ==========================================
def get_fault_agent(language: str) -> FaultDetectionAgent:
    """
    Factory function che ritorna l'agente fault detection appropriato
    per il linguaggio specificato
    """
    language_lower = language.lower()
    
    if language_lower == 'python':
        return PythonFaultDetectionAgent()
    elif language_lower in ['javascript', 'typescript']:
        return JavaScriptFaultDetectionAgent()
    elif language_lower == 'java':
        return JavaFaultDetectionAgent()
    else:
        # Default: agente generico
        return FaultDetectionAgent(language)