import sqlite3
from flask import Flask, request

app = Flask(__name__)

def funzione_inutile():
    return "Ignorami"

# TARGET: Questa funzione DEVE essere rilevata come SQL Injection
def get_user_data():
    db = sqlite3.connect("database.db")
    cursor = db.cursor()
    user_id = request.args.get("id")
    
    # Vulnerabilità palese: concatenazione stringhe in query SQL
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()

def altra_funzione():
    return "Non toccare"