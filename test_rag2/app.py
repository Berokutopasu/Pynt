# app.py
from flask import Flask, request, send_file
from database import get_user_by_name
from utils import system_ping, log_activity
from auth import hash_password

app = Flask(__name__)

@app.route('/profile')
def profile():
    username = request.args.get('username')
    # Chiama la funzione SQL Injection in un altro file
    user = get_user_by_name(username)
    return f"Hello {user}"

@app.route('/admin/tools')
def admin_tools():
    target = request.args.get('target')
    # Chiama la Command Injection in un altro file
    system_ping(target)
    return "Ping eseguito"

@app.route('/download')
def download_report():
    filename = request.args.get('file')
    # [SECURITY] Path Traversal
    # Permette di scaricare /etc/passwd se file=../../../../etc/passwd
    return send_file(filename)

@app.route('/register', methods=['POST'])
def register():
    password = request.form.get('password')
    # Usa hashing debole
    p_hash = hash_password(password)
    
    # Bug logico: Mutable default argument
    log_activity("New user registered")
    
    return f"User registered with hash {p_hash}"

if __name__ == '__main__':
    # [SECURITY] Debug=True in produzione (preso da Config in teoria)
    app.run(debug=True)