import os
import sqlite3
from flask import Flask, request

app = Flask(__name__)

@app.route('/login')
def login():
    # 1. Input utente non controllato (Source)
    username = request.args.get('username')
    
    # 2. Hardcoded Secret (Security)
    # Semgrep dovrebbe rilevarlo come credenziale esposta
    aws_key = "AKIAIOSFODNN7EXAMPLE" 

    # 3. SQL Injection (Security)
    # Concatenazione diretta di stringhe
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE user = '" + username + "'"
    cursor.execute(query)

    # 4. Command Injection (Security)
    # Passaggio diretto dell'input alla shell
    os.system("echo " + username)
    
    return "Done"