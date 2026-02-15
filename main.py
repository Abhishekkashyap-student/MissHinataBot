import os
import logging
import requests
import json
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- LOGGING ON (Error pakdne ke liye) ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
# Keys ko safai se split karenge
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]

if not TOKEN:
    logger.critical("❌ BOT_TOKEN missing!")
    exit(1)

# --- AI LOGIC (MULTI-MODEL JUTSU) ---
def get_groq_response(text):
    if not GROQ_KEYS: return "No API Keys found! 🌸"
    
    # Hinata Persona
    messages = [
        {"role": "system", "content": "You are Hinata Hyuga from Naruto. You are a real girl, shy, caring, and polite. You call the user 'Naruto-kun'. Keep answers short and human-like. Do not sound like an AI."},
        {"role": "user", "content": text}
    ]

    # Models List (Agar ek fail ho toh dusra try kare)
    models = [
        "llama-3.3-70b-versatile",  # Newest & Smartest
        "llama-3.1-8b-instant",     # Fastest
        "mixtral-8x7b-32768"        # Reliable Backup
    ]

    for key in GROQ_KEYS:
        # Har key ke saath har model try karenge
        for model in models:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": 200,
                    "temperature": 0.7
                }
                
                # Timeout badha diya taaki connection drop na ho
                response = requests.post(url, headers=headers, json=data, timeout=10)
                
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
                else:
                    # Log error to Koyeb Console (Tujhe dikhega kya galti hai)
                    logger.error(f"⚠️ Key failed on {model}: {response.status_code} - {response.text}")
                    continue

            except Exception as e:
                logger.error(f"❌ Connection Error: {e}")
                continue

    return "Gomen nasai... I can't connect right now. (Check Logs) 🌸"

# --- WEB SERVER (Life Support) ---
app = Flask('')
@app.route('/')
def home(): return "🦊 BARYON MODE ONLINE"

def run_flask():
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.message.reply_text("N-Naruto-kun? 😳\nI am ready! 🌸")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ Pong!")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    text = update.message.text.lower()
    is_private = update.effective_chat.type == "private"
    has_name = "hinata" in text
    is_reply = (update.message.reply_to_message and 
                update.message.reply_to_message.from_user.id == context.bot.id)

    if is_private or has_name or is_reply:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        # Run AI in thread to avoid blocking
        reply = get_groq_response(update.message.text)
        await update.message.reply_text(reply)

# --- MAIN ---
if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('ping', ping))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    
    print("🚀 BOT STARTED SUCCESSFULLY!")
    application.run_polling()
