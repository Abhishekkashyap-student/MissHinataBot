import os
import logging
import requests
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- LOGGING ON ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# Sirf Token chahiye, koi API ID/Hash nahi!
TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEYS = os.getenv("GROQ_API_KEY", "").split(",")

if not TOKEN:
    print("❌ Error: BOT_TOKEN missing in Koyeb!")
    exit(1)

# --- AI LOGIC (GROQ) ---
def get_groq_response(text):
    if not GROQ_KEYS or not GROQ_KEYS[0]: return "No API Keys! 🌸"
    
    messages = [
        {"role": "system", "content": "You are Hinata Hyuga. Shy, caring, real girl. Reply fast."},
        {"role": "user", "content": text}
    ]

    for key in GROQ_KEYS:
        if not key.strip(): continue
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key.strip()}"},
                json={"model": "llama3-8b-8192", "messages": messages, "max_tokens": 150},
                timeout=5
            )
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content']
        except: continue
    return "Gomen nasai... network error. 🌸"

# --- WEB SERVER (Koyeb Life Support) ---
app = Flask('')
@app.route('/')
def home(): return "I AM ALIVE! 🦊"

def run_flask():
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.message.reply_text("N-Naruto-kun? 😳\nI am ready! 🌸")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ Pong!")

# --- CHAT HANDLER ---
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Message text check
    if not update.message or not update.message.text: return
    
    text = update.message.text.lower()
    is_private = update.effective_chat.type == "private"
    has_name = "hinata" in text
    is_reply = (update.message.reply_to_message and 
                update.message.reply_to_message.from_user.id == context.bot.id)

    # Logic: Private mein hamesha, Group mein sirf naam lene par ya reply par
    if is_private or has_name or is_reply:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        reply = get_groq_response(update.message.text)
        await update.message.reply_text(reply)

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    keep_alive() # Fake Server Start
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('ping', ping))
    # Ye line har text message ko sunegi (Groups included)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    
    print("🚀 BOT STARTED SUCCESSFULLY!")
    application.run_polling()
