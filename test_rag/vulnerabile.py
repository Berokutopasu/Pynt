import os

# --- 1. SECURITY PROBLEM (Per l'agente Security) ---
# Hardcoded password (p/secrets)
API_KEY = "12345-abcde" 

def calcola_cose(lista=[]):
    # --- 2. BEST PRACTICE PROBLEM (Per l'agente Best Practices) ---
    # Mutable Default Argument: In Python è il male assoluto!
    # La lista mantiene i valori tra chiamate diverse della funzione.
    
    # Confronto con True (Anti-pattern: si usa 'if x:')
    if True == True: 
        print("Sempre vero")

    # --- 3. FAULT DETECTION PROBLEM (Per l'agente Fault) ---
    # Confronto impossibile: Stringa vs Intero
    # Questo codice non crasherà, ma è un bug logico perché è sempre False.
    if "100" == 100:
        print("Impossibile")
        
    # Variabile usata prima dell'assegnazione (o shadowing errato)
    # Semgrep spesso rileva 'Redundant assignment' o 'Variable defined but not used'
    x = 10
    x = 20 # Assegnazione inutile (Fault/Correctness)
    
    # Esecuzione insicura (Security again)
    eval("print('hello')")

    return x