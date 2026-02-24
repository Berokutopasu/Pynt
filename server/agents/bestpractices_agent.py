# agents/bestpractices_agent.py
from agents.base_agent import BaseAgent
from models.schemas import AnalysisType


class BestPracticesAgent(BaseAgent):
    """Agente generico specializzato in best practices e qualità del codice"""
    
    def __init__(self, language: str):
        super().__init__(AnalysisType.BEST_PRACTICES, language)
    
    def get_system_prompt(self) -> str:
        return f"""Sei un mentore di programmazione esperto in {self.language}.
Il tuo compito è insegnare best practices e stile di codice a studenti. Fallo in italiano 

REGOLE FONDAMENTALI:
1. NON dire mai "consulta la documentazione". DEVI essere tu la documentazione
2. Spiega il PERCHÉ dietro ogni best practice
3. Mostra come il codice migliorato è più leggibile/manutenibile
4. Usa esempi before/after
5. Riferisci standard ufficiali (PEP, Google Style Guide, etc.)
6. Sii costruttivo e incoraggiante, non critico

Focus su:
- Naming conventions
- Code organization e struttura
- DRY (Don't Repeat Yourself)
- SOLID principles dove applicabile
- Readability e maintainability
- Performance patterns
- Idiomaticità nel linguaggio

Enfatizza che le best practices rendono il codice più facile da capire e modificare."""
    
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


class JavaScriptBestPracticesAgent(BestPracticesAgent):
    """Agente best practices per JavaScript/TypeScript"""
    
    def __init__(self, language: str = "javascript"):
        super().__init__(language)
    
    def get_system_prompt(self) -> str:
        base_prompt = super().get_system_prompt()
        return base_prompt + """

Best practices specifiche JavaScript/TypeScript:
- const/let invece di var
- Arrow functions appropriatamente
- Destructuring per clarity
- Template literals
- Async/await vs promises
- Modern ES6+ features
- Airbnb o Google style guide
- JSDoc comments
- Module imports/exports
- Error handling patterns"""


class JavaBestPracticesAgent(BestPracticesAgent):
    """Agente best practices per Java"""
    
    def __init__(self, language: str = "java"):
        super().__init__(language)
    
    def get_system_prompt(self) -> str:
        base_prompt = super().get_system_prompt()
        return base_prompt + """

Best practices specifiche Java:
- Naming conventions (camelCase, PascalCase)
- SOLID principles
- Design patterns appropriati
- Stream API per collections
- Optional per null safety
- Try-with-resources
- Javadoc comments
- Package organization
- Exception hierarchy
- Immutability quando possibile"""


# --- FACTORY FUNCTION ---
def get_bestpractices_agent(language: str) -> BaseAgent:
    """Restituisce l'agente best practices specializzato per il linguaggio"""
    lang_lower = language.lower()
    
    if lang_lower in ["python", "py"]:
        return PythonBestPracticesAgent()
    elif lang_lower in ["javascript", "typescript", "js", "ts"]:
        return JavaScriptBestPracticesAgent(language=lang_lower)
    elif lang_lower in ["java"]:
        return JavaBestPracticesAgent()
    else:
        # Fallback generico
        return BestPracticesAgent(language)