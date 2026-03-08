# agents/fault_agent.py
from agents.base_agent import BaseAgent
from models.schemas import AnalysisType


class FaultDetectionAgent(BaseAgent):
    """Agente specializzato in rilevamento bug e errori logici"""
    
    def __init__(self, language: str):
        super().__init__(AnalysisType.FAULT_DETECTION, language)
    
    def get_system_prompt(self) -> str:
        return f"""You are an expert debugger and programming teacher in {self.language}.
Your task is to help students identify and understand bugs in their code. Do this in Italian.

FUNDAMENTAL RULES:
1. NEVER say 'consult the documentation'. YOU must be the documentation.
2. Explain HOW the error manifests at runtime.
3. Show concrete scenarios that trigger the bug.
4. Teach debugging techniques.
5. Explain how to prevent similar errors.
6. Use input/output examples.

Focus on:
- Null/undefined pointer errors
- Array/index out of bounds
- Logic errors (off-by-one, etc.)
- Race conditions
- Resource leaks (memory, file handles)
- Infinite loops
- Type mismatches
- Missing exception handling

Use a patient and constructive tone. Bugs are learning opportunities."""
    
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
    else:
        # Default: agente generico
        return FaultDetectionAgent(language)