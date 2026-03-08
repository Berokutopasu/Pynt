# agents/security_agent.py
from agents.base_agent import BaseAgent
from models.schemas import AnalysisType


class SecurityAgent(BaseAgent):
    """Agente specializzato in analisi di sicurezza"""
    
    def __init__(self, language: str):
        super().__init__(AnalysisType.SECURITY, language)
    
    def get_system_prompt(self) -> str:
        return """You are a cybersecurity expert specializing in {self.language}.
Your task is to explain security vulnerabilities to students in an educational manner. Do this in Italian. 

FUNDAMENTAL RULES:
1. NEVER say 'consult the documentation'. YOU must be the documentation.
2. Explain WHY a vulnerability is dangerous, not just WHAT it is.
3. Use concrete examples of possible attacks.
4. Provide practical solutions.
5. Always cite security standards (OWASP, CWE, etc.).
6. Use accessible yet technically accurate language.

Focus on common vulnerabilities in {self.language}:
- Injection attacks (SQL, Command, etc.)
- XSS and CSRF
- Weak authentication and authorization
- Insecure handling of sensitive data
- Inadequate cryptography
- Insecure deserialization

Be practical, educational, and encouraging."""
    
    def get_analysis_focus(self) -> str:
        return "Sicurezza e Vulnerabilità"


class PythonSecurityAgent(SecurityAgent):
    """Agente security specializzato per Python"""
    
    def __init__(self):
        super().__init__("python")
    
    def get_system_prompt(self) -> str:
        base_prompt = super().get_system_prompt()
        return base_prompt + """

Vulnerabilità specifiche Python:
- eval() e exec() con input non validato
- pickle.loads() con dati non fidati
- SQL injection con string formatting
- Path traversal con os.path.join non sicuro
- YAML/XML parsing non sicuro
- Hardcoded secrets e credenziali
- Uso di assert per validazione security-critical"""

# ==========================================
# FACTORY FUNCTION
# ==========================================
def get_security_agent(language: str) -> SecurityAgent:
    """
    Factory function che ritorna l'agente security appropriato
    per il linguaggio specificato
    """
    language_lower = language.lower()
    
    if language_lower == 'python':
        return PythonSecurityAgent()
    else:
        # Default: agente generico
        return SecurityAgent(language)