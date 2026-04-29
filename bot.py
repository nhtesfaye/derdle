import os
import base64
import threading
import asyncio
from flask import Flask
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. THE DECOY WEB SERVER (To keep Render happy)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running!"

def run_flask():
    # Render provides a PORT variable automatically
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- AMHARIC GAME LOGIC ---

def get_family_id(char):
    """
    Returns the 'Family' ID for an Amharic character.
    In Unicode (U+1200 - U+137F), characters are grouped in blocks of 8.
    The first character in each block is the 1st Order (Geez).
    """
    code = ord(char)
    if 0x1200 <= code <= 0x137F:
        # Subtract start of block and divide by 8 to get the 'Family' index
        return (code - 0x1200) // 8
    return None

def get_feedback(guess, target):
    """Generates the 4-color feedback string."""
    if len(guess) != len(target):
        return "Please guess a 3-letter word."
    
    result = ["⬛"] * len(target)
    target_list = list(target)
    guess_list = list(guess)

    # 1. Check for Green (Exact Match)
    for i in range(len(guess_list)):
        if guess_list[i] == target_list[i]:
            result[i] = "🟩"
            target_list[i] = None # Mark as used
            guess_list[i] = None

    # 2. Check for Orange (Same Family)
    for i in range(len(guess_list)):
        if guess_list[i] is not None:
            g_fam = get_family_id(guess_list[i])
            t_fam = get_family_id(target[i]) # Compare to target at same position
            if g_fam is not None and g_fam == t_fam:
                result[i] = "🟧"
                guess_list[i] = None

    # 3. Check for Yellow (Misplaced)
    for i in range(len(guess_list)):
        if guess_list[i] is not None and guess_list[i] in target_list:
            result[i] = "🟨"
            target_list[target_list.index(guess_list[i])] = None
            
    return "".join(result)

# --- TELEGRAM HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This is the intro for someone just opening the bot (The Creator)
    creator_intro = (
        "👋 **Welcome to the Derdle By Nahom Creator!**\n\n"
        "Want to test your friends? Here is how:\n"
        "1️⃣ Type `/create` followed by a 3-letter word.\n"
        "   _Example: /create ሰላም_\n"
        "2️⃣ I'll give you a secret link.\n"
        "3️⃣ Send that link to your friend!\n\n"
        "**Rules you're setting:**\n"
        "🟩 = Perfect match\n"
        "🟧 = Correct family, wrong vowel\n"
        "🟨 = Wrong spot\n"
        "⬛ = Not in word"
    )

    # This is the intro for someone clicking a friend's link (The Challenger)
    challenger_intro = (
        "🎮 **Challenge Accepted!**\n\n"
        "A friend has challenged you to guess their **3-letter Amharic word**.\n\n"
        "**How to play:**\n"
        "Type any 3-letter word to start. You have **8 tries**.\n\n"
        "**Hints:**\n"
        "🟩 = Right letter, right spot\n"
        "🟧 = Same family (e.g., you guessed 'ሁ' but it's 'ሃ')\n"
        "🟨 = Letter is in the word, wrong spot\n"
        "⬛ = Letter is not in the word at all\n\n"
        "👉 **Go ahead, make your first guess!**"
    )

    # Check if they used a link (context.args contains the encoded word)
    if context.args:
        try:
            encoded_word = context.args[0]
            target = base64.b64decode(encoded_word).decode('utf-8')
            context.user_data['target'] = target
            context.user_data['attempts'] = 0
            
            await update.message.reply_text(challenger_intro, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("❌ Oops! That challenge link seems broken.")
    else:
        # No link? Show them the "How to Create" intro
        await update.message.reply_text(creator_intro, parse_mode="Markdown")
async def create_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args[0]) != 3:
        await update.message.reply_text("⚠️ Use: `/create ሰላም` (must be 3 characters)")
        return
    
    word = context.args[0]
    encoded = base64.b64encode(word.encode('utf-8')).decode('utf-8')
    bot_info = await context.bot.get_me()
    
    # Generate the link
    link = f"https://t.me/{bot_info.username}?start={encoded}"
    
    # Create a clickable text link
    # NOTE: In MarkdownV2, we must escape certain characters or use simple Markdown
    text_message = (
        "✅ **Challenge Created!**\n\n"
        f"Send this link to your friend:\n"
        f"[Click here to start the Challenge]({link})"
    )
    
    await update.message.reply_text(text_message, parse_mode="Markdown")
async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = context.user_data.get('target')
    
    # Check if a game is actually active
    if not target:
        await update.message.reply_text("👋 No active game! Use a challenge link or type /create to start.")
        return

    guess = update.message.text.strip()

    # --- THE 3-CHARACTER LIMITATION ---
    if len(guess) < 3:
        await update.message.reply_text("⚠️ Too short! Your guess must be exactly 3 characters.")
        return
    if len(guess) > 3:
        await update.message.reply_text("⚠️ Too long! Your guess must be exactly 3 characters.")
        return
    # ----------------------------------

    context.user_data['attempts'] = context.user_data.get('attempts', 0) + 1
    attempts = context.user_data['attempts']
    
    feedback = get_feedback(guess, target)
    response = f"Attempt {attempts}/8: {guess}\nResult: {feedback}"
    
    await update.message.reply_text(response)

    if guess == target:
        await update.message.reply_text("🎉 ፀዴ! (Brilliant!) You guessed it!")
        context.user_data['target'] = None
    elif attempts >= 8:
        await update.message.reply_text(f"💀 Game Over. The word was: {target}")
        context.user_data['target'] = None

# --- APP START ---
if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    # Start the decoy web server in the background
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start the Telegram Bot
    async def main():
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
        
        print("Bot is starting on Render...")
        async with application:
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            while True:
                await asyncio.sleep(3600)

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
