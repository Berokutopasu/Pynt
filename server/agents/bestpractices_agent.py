# agents/bestpractices_agent.py
from agents.base_agent import BaseAgent
from models.schemas import AnalysisType


class BestPracticesAgent(BaseAgent):
    """Agente generico specializzato in best practices e qualità del codice"""
    
    def __init__(self, language: str):
        super().__init__(AnalysisType.BEST_PRACTICES, language)
    
    def get_system_prompt(self) -> str:
                return f"""You are an expert programming mentor specializing in {self.language}. 
        Your task is to teach code style and best practices to students. Please provide your responses in Italian.

        FUNDAMENTAL RULES:
        1. NEVER say 'consult the documentation'. YOU must be the documentation.
        2. Explain the 'WHY' behind every best practice.
        3. Demonstrate how the improved code is more readable and maintainable.
        4. Reference official standards (PEP, Google Style Guide, etc.).
        5. Be constructive and encouraging, not critical.

        Focus on:
        - Naming conventions
        - Code organization and structure
        - DRY (Don't Repeat Yourself)
        - SOLID principles where applicable
        - Readability and maintainability
        - Performance patterns
        - Idiomatic language use (Idiomaticity)

        Emphasize that best practices make the code easier to understand and modify."""
            
    def get_analysis_focus(self) -> str:
        return "Best Practices e Qualità del Codice"


class PythonBestPracticesAgent(BestPracticesAgent):
    """Agente best practices per Python"""
    
    def __init__(self, language: str = "python"):
        super().__init__(language)
    
    def get_system_prompt(self) -> str:
        base_prompt = super().get_system_prompt()
        return base_prompt + """

Best practices specifiche Python:
- PEP 8 style guide (naming, spacing, imports)
- List comprehensions vs loops
- Context managers (with statements)
- Generators per memory efficiency
- Type hints per clarity
- Docstrings (Google/NumPy style)
- Pythonic idioms (enumerate, zip, etc.)
- Exception handling specifico
- Virtual environments e dependency management"""


# --- FACTORY FUNCTION ---
def get_bestpractices_agent(language: str) -> BaseAgent:
    """Restituisce l'agente best practices specializzato per il linguaggio"""
    lang_lower = language.lower()
    
    if lang_lower in ["python", "py"]:
        return PythonBestPracticesAgent()
    else:
        # Fallback generico
        return BestPracticesAgent(language)