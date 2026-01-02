import sqlite3
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, ConversationHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from config import TOKEN

# Stati conversazione
OPPONENT, WINLOSS, SCORE, CONFIRM = range(4)
H2H_OPPONENT = 10

DB_PATH = "mytennis.db"

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        name TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        opponent TEXT,
        winloss TEXT,
        score TEXT,
        sets_won INTEGER,
        sets_lost INTEGER,
        games_won INTEGER,
        games_lost INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(player_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT OR IGNORE INTO users (telegram_id, username, name)
    VALUES (?, ?, ?)
    """, (user.id, user.username, user.first_name))
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("➕ Nuova partita", callback_data="new_match"),
         InlineKeyboardButton("🤝 Head to Head", callback_data="h2h")], 
        [InlineKeyboardButton("📊 Visualizza Statistiche", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎾 Benvenuto in MyTennisBot!\nCosa vuoi fare?",
        reply_markup=reply_markup
    )

# --- NUOVA PARTITA ---
async def new_match_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📋 Inserisci il nome del tuo avversario:")
    return OPPONENT

async def new_match_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['opponent'] = update.message.text

    keyboard = [
        [InlineKeyboardButton("Win", callback_data="win"),
         InlineKeyboardButton("Loss", callback_data="loss")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏆 Seleziona Win o Loss:", reply_markup=reply_markup)
    return WINLOSS

async def new_match_winloss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['winloss'] = query.data
    await query.message.reply_text("✏ Inserisci il punteggio (es. 6-3 4-6 7-5):")
    return SCORE

async def new_match_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['score'] = update.message.text

    opponent = context.user_data['opponent']
    winloss = context.user_data['winloss']
    score = context.user_data['score']

    keyboard = [
        [InlineKeyboardButton("✅ SI", callback_data="confirm"),
         InlineKeyboardButton("❌ NO", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Confermi il risultato?\nAvversario: {opponent}\nWin/Loss: {winloss}\nPunteggio: {score}",
        reply_markup=reply_markup
    )
    return CONFIRM

def parse_score(score_text):
    sets_won = sets_lost = games_won = games_lost = 0
    sets = score_text.split()
    for s in sets:
        if "-" in s:
            p1, p2 = map(int, s.split("-"))
            games_won += p1
            games_lost += p2
            if p1 > p2:
                sets_won += 1
            else:
                sets_lost += 1
    return sets_won, sets_lost, games_won, games_lost

async def new_match_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "confirm":
        user_id = query.from_user.id
        opponent = context.user_data['opponent']
        winloss = context.user_data['winloss']
        score = context.user_data['score']

        sets_won, sets_lost, games_won, games_lost = parse_score(score)

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
        player = c.fetchone()
        player_id = player[0] if player else None

        c.execute("""
        INSERT INTO matches (player_id, opponent, winloss, score, sets_won, sets_lost, games_won, games_lost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (player_id, opponent, winloss, score, sets_won, sets_lost, games_won, games_lost))
        conn.commit()
        conn.close()

        #await query.message.reply_text("🎾 Risultato registrato!")

        # Messaggio conferma
        keyboard = [
            [InlineKeyboardButton("➕ Nuova partita", callback_data="new_match")],
            [InlineKeyboardButton("📊 Visualizza statistiche", callback_data="stats")]
        ]

        await query.message.reply_text(
            "✅ Partita registrata!\nVuoi registrare un'altra partita o vedere le statistiche?",            
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        

        # Pulizia dati temporanei
        context.user_data.clear()

    return ConversationHandler.END

async def new_match_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Registrazione partita annullata.")
    return ConversationHandler.END

# --- STATISTICHE ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        message = update.callback_query.message
    else:
        message = update.message

    user_id = update.effective_user.id

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
    player = c.fetchone()

    if not player:
        await message.reply_text("❌ Utente non trovato. Usa /start prima.")
        return

    player_id = player[0]

    c.execute("""
        SELECT COUNT(*), SUM(CASE WHEN winloss='win' THEN 1 ELSE 0 END),
               SUM(sets_won), SUM(sets_lost), SUM(games_won), SUM(games_lost)
        FROM matches WHERE player_id = ?
    """, (player_id,))

    total, wins, sets_won, sets_lost, games_won, games_lost = c.fetchone()
    conn.close()

    total = total or 0
    wins = wins or 0
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0

    text = (
            f"🎾 Le tue statistiche:\n\n"
            f"Partite giocate: {total}\n"
            f"Vittorie: {wins}\n"
            f"Sconfitte: {losses}\n"
            f"Win rate: {win_rate:.1f}%\n"
            f"Set vinti: {sets_won}\nSet persi: {sets_lost}\n"
            f"Games vinti: {games_won}\nGames persi: {games_lost}"
        )

    # Tastiera con torna al menu
    keyboard = [
        [InlineKeyboardButton("🏠 Torna al menù", callback_data="menu")]
    ]

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )



    conn.close()

# --- HEAD TO HEAD ---
async def h2h_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "🤝 Inserisci il nome dell'avversario:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Torna al menù", callback_data="menu")]
        ])
    )
    return H2H_OPPONENT

async def h2h_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    opponent_name = message.text
    user_id = update.effective_user.id

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
    player = c.fetchone()
    if not player:
        await message.reply_text("❌ Utente non trovato. Usa /start.")
        conn.close()
        return ConversationHandler.END

    player_id = player[0]

    c.execute("""
        SELECT COUNT(*),
               SUM(CASE WHEN winloss='win' THEN 1 ELSE 0 END),
               SUM(sets_won), SUM(sets_lost),
               SUM(games_won), SUM(games_lost)
        FROM matches
        WHERE player_id = ?
          AND LOWER(opponent) = LOWER(?)
    """, (player_id, opponent_name))

    total, wins, sets_won, sets_lost, games_won, games_lost = c.fetchone()
    conn.close()

    total = total or 0
    wins = wins or 0
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0

    if total == 0:
        text = f"🎾 Nessuna partita registrata contro {opponent_name}."
    else:
        text = (
            f"🎾 Head-to-Head vs {opponent_name}\n\n"
            f"Partite: {total}\n"
            f"Vittorie: {wins}\n"
            f"Sconfitte: {losses}\n"
            f"Win rate: {win_rate:.1f}%\n\n"
            f"Set vinti: {sets_won}\n"
            f"Set persi: {sets_lost}\n"
            f"Games vinti: {games_won}\n"
            f"Games persi: {games_lost}"
        )

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Torna al menù", callback_data="menu")]
        ])
    )

    return ConversationHandler.END


# --- BACK TO MENU---
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Menu principale
    keyboard = [
        [InlineKeyboardButton("➕ Nuova partita", callback_data="new_match")],
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("🤝 Head to Head", callback_data="h2h")]
    ]
    await query.message.reply_text(
        "🎾 Torniamo al menu principale:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- AVVIO BOT ---
if __name__ == "__main__":
    init_db()
    app = Application.builder().token(TOKEN).build()

    # /start
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
    app.add_handler(CommandHandler("h2h", h2h_start))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^menu$"))


    # Conversazione nuova partita
    match_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(new_match_start, pattern="new_match")],
        states={
            OPPONENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_match_opponent)],
            WINLOSS: [CallbackQueryHandler(new_match_winloss, pattern="^(win|loss)$")],
            SCORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_match_score)],
            CONFIRM: [CallbackQueryHandler(new_match_confirm, pattern="^(confirm|cancel)$")]
        },
        fallbacks=[CommandHandler('cancel', new_match_cancel)],
        per_message=False
    )
    app.add_handler(match_conv)

    # Conversazione H2H
    h2h_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(h2h_start, pattern="^h2h$")],
        states={
            H2H_OPPONENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, h2h_opponent)
            ]
        },
        fallbacks=[CallbackQueryHandler(back_to_menu, pattern="^menu$")],

        per_message=False
    )
    app.add_handler(h2h_conv)

    print("🤖 Bot avviato...")
    app.run_polling()
