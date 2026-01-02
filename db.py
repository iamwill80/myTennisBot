import sqlite3

conn = sqlite3.connect("mytennis.db")
c = conn.cursor()

# Tabella utenti
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    username TEXT,
    name TEXT
)
""")

# Tabella partite con tutte le colonne necessarie
c.execute("""
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER,
    opponent TEXT,
    winloss TEXT,
    score TEXT,
    sets_won INTEGER DEFAULT 0,
    sets_lost INTEGER DEFAULT 0,
    games_won INTEGER DEFAULT 0,
    games_lost INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()
