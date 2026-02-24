# database.py
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('bank.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_name(username):
    conn = get_db_connection()
    # [SECURITY] SQL Injection: Concatenazione diretta di stringhe
    # Semgrep rule: python.lang.security.audit.formatted-sql-query
    query = f"SELECT * FROM users WHERE username = '{username}'"
    
    print(f"DEBUG Executing: {query}") # [BEST PRACTICE] Print in produzione
    
    cursor = conn.execute(query)
    user = cursor.fetchone()
    conn.close()
    return user