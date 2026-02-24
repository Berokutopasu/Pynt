# config.py

class Config:
    DEBUG = True
    # [SECURITY] Hardcoded Secret: Chiave segreta Flask esposta
    SECRET_KEY = "super-secret-key-12345"
    
    # [SECURITY] Credenziali AWS Hardcoded (Pattern p/secrets)
    AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
    AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    
    # [BEST PRACTICE] Variabile non usata
    UNUSED_VAR = "Non mi usa nessuno"