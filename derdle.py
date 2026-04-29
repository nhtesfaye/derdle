
# Derdle Telegram Bot (Version 1)
# Install:
# pip install python-telegram-bot==20.6

import logging
import random
import string
import sqlite3

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8547980046:AAFyjJ4Pe3KrE2qvV0iem3AMXHKWEeo7n6k"

# -----------------------------
# DATABASE
# -----------------------------
conn = sqlite3.connect("derdle.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS challenges (
    code TEXT PRIMARY KEY,
    word TEXT NOT NULL,
    creator_id TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    user_id TEXT,
    code TEXT,
    attempts INTEGER,
    PRIMARY KEY(user_id, code)
)
""")

conn.commit()

# -----------------------------
# FIDEL HOUSE LOGIC
# -----------------------------

houses = {

    "ሀ": ["ሀ", "ሁ", "ሂ", "ሃ", "ሄ", "ህ", "ሆ"],
    "ለ": ["ለ", "ሉ", "ሊ", "ላ", "ሌ", "ል", "ሎ"],
    "ሐ": ["ሐ", "ሑ", "ሒ", "ሓ", "ሔ", "ሕ", "ሖ"],
    "መ": ["መ", "ሙ", "ሚ", "ማ", "ሜ", "ም", "ሞ"],
    "ሠ": ["ሠ", "ሡ", "ሢ", "ሣ", "ሤ", "ሥ", "ሦ"],
    "ረ": ["ረ", "ሩ", "ሪ", "ራ", "ሬ", "ር", "ሮ"],
    "ሰ": ["ሰ", "ሱ", "ሲ", "ሳ", "ሴ", "ስ", "ሶ"],
    "ሸ": ["ሸ", "ሹ", "ሺ", "ሻ", "ሼ", "ሽ", "ሾ"],
    "ቀ": ["ቀ", "ቁ", "ቂ", "ቃ", "ቄ", "ቅ", "ቆ"],
    "በ": ["በ", "ቡ", "ቢ", "ባ", "ቤ", "ብ", "ቦ"],
    "ተ": ["ተ", "ቱ", "ቲ", "ታ", "ቴ", "ት", "ቶ"],
    "ቸ": ["ቸ", "ቹ", "ቺ", "ቻ", "ቼ", "ች", "ቾ"],
    "ኀ": ["ኀ", "ኁ", "ኂ", "ኃ", "ኄ", "ኅ", "ኆ"],
    "ነ": ["ነ", "ኑ", "ኒ", "ና", "ኔ", "ን", "ኖ"],
    "ኘ": ["ኘ", "ኙ", "ኚ", "ኛ", "ኜ", "ኝ", "ኞ"],
    "አ": ["አ", "ኡ", "ኢ", "ኣ", "ኤ", "እ", "ኦ"],
    "ከ": ["ከ", "ኩ", "ኪ", "ካ", "ኬ", "ክ", "ኮ"],
    "ኸ": ["ኸ", "ኹ", "ኺ", "ኻ", "ኼ", "ኽ", "ኾ"],
    "ወ": ["ወ", "ዉ", "ዊ", "ዋ", "ዌ", "ው", "ዎ"],
    "ዐ": ["ዐ", "ዑ", "ዒ", "ዓ", "ዔ", "ዕ", "ዖ"],
    "ዘ": ["ዘ", "ዙ", "ዚ", "ዛ", "ዜ", "ዝ", "ዞ"],
    "የ": ["የ", "ዩ", "ዪ", "ያ", "ዬ", "ይ", "ዮ"],
    "ደ": ["ደ", "ዱ", "ዲ", "ዳ", "ዴ", "ድ", "ዶ"],
    "ጀ": ["ጀ", "ጁ", "ጂ", "ጃ", "ጄ", "ጅ", "ጆ"],
    "ገ": ["ገ", "ጉ", "ጊ", "ጋ", "ጌ", "ግ", "ጎ"],
    "ጠ": ["ጠ", "ጡ", "ጢ", "ጣ", "ጤ", "ጥ", "ጦ"],
    "ጨ": ["ጨ", "ጩ", "ጪ", "ጫ", "ጬ", "ጭ", "ጮ"],
    "ጰ": ["ጰ", "ጱ", "ጲ", "ጳ", "ጴ", "ጵ", "ጶ"],
    "ጸ": ["ጸ", "ጹ", "ጺ", "ጻ", "ጼ", "ጽ", "ጾ"],
    "ፀ": ["ፀ", "ፁ", "ፂ", "ፃ", "ፄ", "ፅ", "ፆ"],
    "ፈ": ["ፈ", "ፉ", "ፊ", "ፋ", "ፌ", "ፍ", "ፎ"],
    "ፐ": ["ፐ", "ፑ", "ፒ", "ፓ", "ፔ", "ፕ", "ፖ"]

}

def get_house(char):
    for group in houses:
        if char in group:
            return group
    return None

}

def get_house(char):
    for root, group in houses.items():
        if char in group:
            return root
    return None

# -----------------------------
# GAME LOGIC
# -----------------------------

def evaluate_guess(secret, guess):
    result = []

    for i in range(len(guess)):
        if i >= len(secret):
            result.append("⬜️")
            continue

        if guess[i] == secret[i]:
            result.append("🟩")
        elif guess[i] in secret:
            result.append("🟨")
        elif get_house(guess[i]) and get_house(guess[i]) == get_house(secret[i]):
            result.append("🟧")
        else:
            result.append("⬜️")

    return "".join(result)

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# -----------------------------
# BOT COMMANDS
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if args:
        code = args[0].upper()

        cur.execute("SELECT word FROM challenges WHERE code=?", (code,))
        row = cur.fetchone()

        if not row:
            await update.message.reply_text("Challenge not found.")
            return

        user_id = str(update.effective_user.id)

        cur.execute("""
        INSERT OR REPLACE INTO sessions(user_id, code, attempts)
        VALUES (?, ?, ?)
        """, (user_id, code, 6))
        conn.commit()

        await update.message.reply_text(
            f"🎯 Derdle Challenge {code}\n"
            f"You have 6 attempts.\n"
            f"Send your guess."
        )
        context.user_data["active_code"] = code
        return

    await update.message.reply_text(
        "Welcome to Derdle Bot 🇪🇹\n\n"
        "/create - Create challenge"
    )

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me your secret Amharic word.")
    context.user_data["creating"] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = str(update.effective_user.id)

    # Creating challenge
    if context.user_data.get("creating"):
        code = generate_code()

        cur.execute("""
        INSERT INTO challenges(code, word, creator_id)
        VALUES (?, ?, ?)
        """, (code, text, user_id))
        conn.commit()

        context.user_data["creating"] = False

        link = f"https://t.me/YOUR_BOT_USERNAME?start={code}"

        await update.message.reply_text(
            f"✅ Challenge created!\n"
            f"Code: {code}\n\n"
            f"Share:\n{link}"
        )
        return

    # Playing challenge
    code = context.user_data.get("active_code")

    if not code:
        await update.message.reply_text("Use /create or open a challenge link.")
        return

    cur.execute("SELECT word FROM challenges WHERE code=?", (code,))
    row = cur.fetchone()

    if not row:
        await update.message.reply_text("Challenge expired.")
        return

    secret = row[0]

    cur.execute("""
    SELECT attempts FROM sessions
    WHERE user_id=? AND code=?
    """, (user_id, code))

    session = cur.fetchone()

    if not session:
        await update.message.reply_text("Start challenge again.")
        return

    attempts = session[0]

    if attempts <= 0:
        await update.message.reply_text("No attempts left.")
        return

    result = evaluate_guess(secret, text)

    if text == secret:
        await update.message.reply_text(
            f"{result}\n🎉 Correct! You solved it."
        )
        return

    attempts -= 1

    cur.execute("""
    UPDATE sessions
    SET attempts=?
    WHERE user_id=? AND code=?
    """, (attempts, user_id, code))
    conn.commit()

    if attempts == 0:
        await update.message.reply_text(
            f"{result}\n❌ Game Over.\nAnswer was: {secret}"
        )
    else:
        await update.message.reply_text(
            f"{result}\nAttempts left: {attempts}"
        )

# -----------------------------
# MAIN
# -----------------------------

def main():
    logging.basicConfig(level=logging.INFO)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("create", create))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()