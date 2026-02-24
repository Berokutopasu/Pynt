import requests
import json
import sys
import time

# CONFIGURAZIONE
SERVER_URL = "http://localhost:8000"
ENDPOINT = "/analyze/security"

# CODICE VULNERABILE DI TEST
CODE_SNIPPET = """
import os
from flask import request

def handle_request():
    username = request.args.get('username')
    # VULNERABILITÀ: Command Injection
    os.system("echo Hello " + username)
"""

# Colori per il terminale
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def test_backend():
    print(f"{Colors.HEADER}🚀 AVVIO TEST BACKEND PYNT...{Colors.ENDC}")
    print(f"📡 Target: {SERVER_URL}{ENDPOINT}")
    
    payload = {
        "code": CODE_SNIPPET,
        "language": "python",
        "filename": "test_vuln.py"
    }

    start_time = time.time()

    try:
        # 1. Chiamata al Server
        response = requests.post(SERVER_URL + ENDPOINT, json=payload)
        response.raise_for_status() # Lancia eccezione se status != 200
        
        data = response.json()
        duration = time.time() - start_time

        print(f"\n{Colors.GREEN}✅ CONNESSIONE RIUSCITA! (Tempo: {duration:.2f}s){Colors.ENDC}")
        
        findings = data.get("findings", [])
        print(f"🔎 Trovati {len(findings)} problemi.\n")

        if not findings:
            print(f"{Colors.WARNING}⚠️ Nessun finding trovato. Semgrep sta funzionando?{Colors.ENDC}")
            return

        # 2. Stampa Formattata della Risposta
        for i, finding in enumerate(findings, 1):
            print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
            print(f"{Colors.FAIL}🚩 FINDING #{i}: {finding.get('message')}{Colors.ENDC}")
            print(f"   Regola ID: {finding.get('ruleId')}")
            print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")

            # SEZIONE SPIEGAZIONE
            print(f"\n{Colors.BLUE}📚 [LLM] EXPLANATION:{Colors.ENDC}")
            print(finding.get('educationalExplanation', 'N/A').strip())

            # SEZIONE FIX
            print(f"\n{Colors.BLUE}🛠️ [LLM] SUGGESTED FIX:{Colors.ENDC}")
            print(finding.get('suggestedFix', 'N/A').strip())

            # SEZIONE CODICE
            print(f"\n{Colors.BLUE}💻 [LLM] CODE EXAMPLE:{Colors.ENDC}")
            print(finding.get('codeExample', 'N/A').strip())

            # SEZIONE REFERENZE
            refs = finding.get('references', [])
            if refs:
                print(f"\n{Colors.BLUE}🔗 [LLM] REFERENCES:{Colors.ENDC}")
                for ref in refs:
                    print(f" - {ref}")
            
            print(f"\n{Colors.BOLD}{'-'*60}{Colors.ENDC}\n")

    except requests.exceptions.ConnectionError:
        print(f"\n{Colors.FAIL}❌ ERRORE: Impossibile connettersi al server.{Colors.ENDC}")
        print("Assicurati che il backend sia avviato su", SERVER_URL)
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ ERRORE:{Colors.ENDC} {e}")
        if 'response' in locals():
            print("Risposta Server:", response.text)

if __name__ == "__main__":
    test_backend()