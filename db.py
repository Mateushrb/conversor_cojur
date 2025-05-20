# db.py
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("conversoes.db")

def registrar_conversao(qtd_arquivos: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS conversoes (id INTEGER PRIMARY KEY AUTOINCREMENT, conversao_n INTEGER, qtd_arq_convertidos INTEGER, data TEXT)")
    cur.execute("SELECT MAX(conversao_n) FROM conversoes")
    ultimo = cur.fetchone()[0] or 0
    nova_conversao = ultimo + 1

    cur.execute("INSERT INTO conversoes (conversao_n, qtd_arq_convertidos, data) VALUES (?, ?, ?)",
                (nova_conversao, qtd_arquivos, datetime.now().isoformat()))

    conn.commit()
    conn.close()

    return nova_conversao

def obter_estatisticas():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Garante a tabela
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversao_n INTEGER,
            qtd_arq_convertidos INTEGER,
            data TEXT
        )
    """)

    # Busca os 10 últimos registros
    cur.execute("""
        SELECT conversao_n, qtd_arq_convertidos, data
        FROM conversoes
        ORDER BY id DESC
        LIMIT 10
    """)
    ultimas = [
        {"conversao_n": cn, "qtd_arquivos": qtd, "data": dt}
        for cn, qtd, dt in cur.fetchall()
    ]

    # Busca totais
    cur.execute("SELECT COUNT(*) FROM conversoes")
    total_conversoes = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM(qtd_arq_convertidos) FROM conversoes")
    total_arquivos = cur.fetchone()[0] or 0

    conn.close()

    return {
        "total_conversoes": total_conversoes,
        "total_arquivos_convertidos": total_arquivos,
        "ultimas_conversoes": ultimas
    }
