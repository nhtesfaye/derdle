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
    # Rules message
    rules_text = (
        "👋 **Welcome to Derdle!**\n\n"
        "The goal is to guess the 3-letter Amharic word in 8 tries.\n\n"
        "**Rules:**\n"
        "🟩 = Correct character & spot\n"
        "🟧 = Same 'Family' (Bet), wrong vowel\n"
        "🟨 = Character is in the word, wrong spot\n"
        "⬛ = Character not in the word\n\n"
    )

    if context.args:
        try:
            encoded_word = context.args[0]
            target = base64.b64decode(encoded_word).decode('utf-8')
            context.user_data['target'] = target
            context.user_data['attempts'] = 0
            await update.message.reply_text(
                f"{rules_text}🎮 **Challenge Accepted!**\nStart guessing the 3-letter word.",
                parse_mode="Markdown"
            )
        except Exception:
            await update.message.reply_text("❌ Invalid challenge link.")
    else:
        await update.message.reply_text(
            f"{rules_text}To challenge a friend, type:\n`/create [word]`",
            parse_mode="Markdown"
        )
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
    TOKEN = "8547980046:AAFyjJ4Pe3KrE2qvV0iem3AMXHKWEeo7n6k"
    
    # We build the application differently to bypass the Updater bug
    application = Application.builder().token(TOKEN).build()
    
    # Add your handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create_challenge))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
    
    print("Bot is starting...")
    
    # Run the bot
    application.run_polling(drop_pending_updates=True)
