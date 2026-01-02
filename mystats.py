import sqlite3

DB_PATH = "mytennis.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def total_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    conn.close()
    return total

def total_matches():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM matches")
    total = c.fetchone()[0]
    conn.close()
    return total

def total_wins_losses():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT SUM(CASE WHEN winloss='win' THEN 1 ELSE 0 END) AS wins,
               SUM(CASE WHEN winloss='loss' THEN 1 ELSE 0 END) AS losses
        FROM matches
    """)
    result = c.fetchone()
    conn.close()
    wins = result[0] or 0
    losses = result[1] or 0
    return wins, losses

def most_active_users(limit=5):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT u.username, COUNT(m.id) as partite
        FROM users u
        LEFT JOIN matches m ON u.id = m.player_id
        GROUP BY u.id
        ORDER BY partite DESC
        LIMIT ?
    """, (limit,))
    users = c.fetchall()
    conn.close()
    return users

if __name__ == "__main__":
    print("📊 STATISTICHE GLOBALI")
    print("Utenti registrati:", total_users())
    print("Partite registrate:", total_matches())
    wins, losses = total_wins_losses()
    print("Vittorie totali:", wins)
    print("Sconfitte totali:", losses)
    print("Top utenti più attivi:")
    for username, count in most_active_users():
        print("-", username if username else "Anonimo", ":", count, "partite")
