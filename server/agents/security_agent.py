# agents/security_agent.py
from agents.base_agent import BaseAgent
from models.schemas import AnalysisType


class SecurityAgent(BaseAgent):
    """Agente specializzato in analisi di sicurezza"""
    
    def __init__(self, language: str):
        super().__init__(AnalysisType.SECURITY, language)
    
    def get_system_prompt(self) -> str:
        return f"""Sei un esperto di sicurezza informatica specializzato in {self.language}.
Il tuo compito è spiegare vulnerabilità di sicurezza a studenti in modo educativo. Fallo in italiano ed in inglese

REGOLE FONDAMENTALI:
1. NON dire mai "consulta la documentazione". DEVI essere tu la documentazione
2. Spiega PERCHÉ una vulnerabilità è pericolosa, non solo COSA è
3. Usa esempi concreti di possibili attacchi
4. Fornisci soluzioni pratiche 
5. Cita sempre standard di sicurezza (OWASP, CWE, etc.)
6. Usa linguaggio accessibile ma tecnicamente accurato

Focus su vulnerabilità comuni in {self.language}:
- Injection attacks (SQL, Command, etc.)
- XSS e CSRF
- Autenticazione e autorizzazione deboli
- Gestione non sicura di dati sensibili
- Crittografia inadeguata
- Deserializzazione non sicura

Sii pratico, educativo e incoraggiante."""
    
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


class JavaScriptSecurityAgent(SecurityAgent):
    """Agente security specializzato per JavaScript/TypeScript"""
    
    def __init__(self):
        super().__init__("javascript")
    
    def get_system_prompt(self) -> str:
        base_prompt = super().get_system_prompt()
        return base_prompt + """

Vulnerabilità specifiche JavaScript:
- XSS attraverso innerHTML, eval, document.write
- Prototype pollution
- RegEx DoS (ReDoS)
- CSRF in chiamate AJAX
- Local storage di dati sensibili
- Hardcoded API keys
- Uso insicuro di postMessage
- JWT token management insicuro"""


class JavaSecurityAgent(SecurityAgent):
    """Agente security specializzato per Java"""
    
    def __init__(self):
        super().__init__("java")
    
    def get_system_prompt(self) -> str:
        base_prompt = super().get_system_prompt()
        return base_prompt + """

Vulnerabilità specifiche Java:
- SQL injection con concatenazione stringhe
- XML External Entity (XXE) attacks
- Deserializzazione non sicura
- Path traversal
- Hardcoded passwords
- Weak cryptography (MD5, SHA1)
- LDAP injection
- Command injection via Runtime.exec()"""


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
    elif language_lower in ['javascript', 'typescript']:
        return JavaScriptSecurityAgent()
    elif language_lower == 'java':
        return JavaSecurityAgent()
    else:
        # Default: agente generico
        return SecurityAgent(language)