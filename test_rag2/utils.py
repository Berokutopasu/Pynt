# utils.py
import os
import pickle
import subprocess

# [FAULT DETECTION] Mutable Default Argument
def log_activity(msg, history=[]):
    history.append(msg)
    print(f"Log: {history}")
    return history

def system_ping(hostname):
    # [SECURITY] Command Injection: Input non sanitizzato in shell
    # Semgrep rule: python.lang.security.audit.system-wildcard-detected
    command = "ping -c 1 " + hostname
    os.system(command)

def unsafe_load(data):
    # [SECURITY] Insecure Deserialization
    # Semgrep rule: python.lang.security.audit.pickle-loads
    return pickle.loads(data)

def check_status(is_admin):
    # [FAULT DETECTION] Confronto inutile
    if is_admin == True:
        return "Admin"
    
    # [FAULT DETECTION] Codice irraggiungibile (se ci fosse logica complessa)
    x = 10
    x = 10 # Assegnazione ridondante
    return "User"