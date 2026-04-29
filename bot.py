import os
import base64
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
    # Check for Deep Linking (e.g., /start c2VsYW0=)
    if context.args:
        try:
            encoded_word = context.args[0]
            # Decode the shared word
            target = base64.b64decode(encoded_word).decode('utf-8')
            context.user_data['target'] = target
            context.user_data['attempts'] = 0
            await update.message.reply_text(f"🎮 Challenge Accepted!\nGuess the 3-letter Amharic word. You have 8 tries.")
        except Exception:
            await update.message.reply_text("❌ Invalid challenge link.")
    else:
        await update.message.reply_text("👋 Welcome to Derdle Bot!\n\nTo challenge a friend, type:\n`/create [3-letter-word]`")

async def create_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args[0]) != 3:
        await update.message.reply_text("⚠️ Use: `/create ሰላም` (must be 3 characters)")
        return
    
    word = context.args[0]
    # Encode word into Base64 for the URL
    encoded = base64.b64encode(word.encode('utf-8')).decode('utf-8')
    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={encoded}"
    
    await update.message.reply_text(f"✅ Challenge Ready!\nShare this link with your friend:\n`{link}`", parse_mode="Markdown")

async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = context.user_data.get('target')
    if not target:
        await update.message.reply_text("Start a game by using a challenge link or creating your own!")
        return

    guess = update.message.text.strip()
    if len(guess) != 3:
        await update.message.reply_text("❌ Words must be exactly 3 characters.")
        return

    context.user_data['attempts'] = context.user_data.get('attempts', 0) + 1
    attempts = context.user_data['attempts']
    
    feedback = get_feedback(guess, target)
    response = f"Attempt {attempts}/8: {guess}\nResult: {feedback}"
    
    await update.message.reply_text(response)

    if guess == target:
        await update.message.reply_text("🎉 በሪሁ! (Brilliant!) You guessed it!")
        context.user_data['target'] = None
    elif attempts >= 8:
        await update.message.reply_text(f"💀 Game Over. The word was: {target}")
        context.user_data['target'] = None

# --- APP START ---
if __name__ == "__main__":
    # Your actual token placed directly here
    TOKEN = "8547980046:AAFyjJ4Pe3KrE2qvV0iem3AMXHKWEeo7n6k"
    
    # Initialize the Application
    app = Application.builder().token(TOKEN).build()
    
    # Add Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("create", create_challenge))
    
    # This handler manages the Amharic word guesses
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
    
    # Log status and start the bot
    print("Bot is starting...")
    print("Status: Connected to Telegram successfully.")
    
    # This keeps the bot running on Railway
    app.run_polling()
