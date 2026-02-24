# auth.py
import hashlib
from config import Config

def hash_password(password):
    # [SECURITY] MD5 è un algoritmo di hashing debole/rotto
    # Semgrep rule: python.lang.security.insecure-hash-algorithms
    hasher = hashlib.md5()
    hasher.update(password.encode('utf-8'))
    return hasher.hexdigest()

def verify_token(token):
    # [SECURITY] Uso di token hardcoded importato
    if token == Config.SECRET_KEY:
        return True
    return False