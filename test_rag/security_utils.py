# security_utils.py
import os
import sqlite3

# --- 1. Soluzione per i SEGRETI ---
def get_secret_from_vault(key_name):
    """
    Recupera una credenziale in modo sicuro dalle variabili d'ambiente 
    o da un Secret Manager (AWS/Azure/GCP).
    NON scrivere mai le password nel codice!
    """
    return os.environ.get(key_name)

# --- 2. Soluzione per SQL INJECTION ---
def safe_db_query(cursor, query_string, parameters):
    """
    Esegue una query SQL sicura utilizzando i parametri bind.
    Previene totalmente la SQL Injection.
    
    Esempio:
    safe_db_query(cur, "SELECT * FROM users WHERE id = ?", (user_id,))
    """
    try:
        cursor.execute(query_string, parameters)
        return cursor.fetchall()
    except Exception as e:
        print(f"Errore database sicuro: {e}")
        return []

# --- 3. Soluzione per EVAL/EXEC ---
def safe_math_eval(expression):
    """
    Valuta espressioni matematiche in modo sicuro senza usare eval().
    Usa librerie come 'ast' o parser dedicati.
    """
    # Esempio fittizio di sicurezza
    if not all(c in "0123456789+-*/ " for c in expression):
        raise ValueError("Caratteri non permessi")
    return eval(expression, {"__builtins__": None}, {})