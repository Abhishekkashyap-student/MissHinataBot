import os
import logging
import requests
import json
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- LOGGING ON (Jasoosi Mode) ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN:
    logger.critical("❌ BOT_TOKEN missing!")
    exit(1)

# --- AI LOGIC (DUAL ENGINE) ---
def get_ai_response(text):
    # Hinata Persona
    messages = [
        {"role": "system", "content": "You are Hinata Hyuga from Naruto. Real girl, shy, caring. Call user 'Naruto-kun'. Keep answers short/cute. NO AI talk."},
        {"role": "user", "content": text}
    ]

    # 🔥 ENGINE 1: GROQ (Speed)
    if GROQ_KEYS:
        # Models: Latest Llama 3.3 -> Old Llama 3.1 -> Mixtral
        groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
        
        for key in GROQ_KEYS:
            for model in groq_models:
                try:
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                    data = {"model": model, "messages": messages, "max_tokens": 200}
                    
                    response = requests.post(url, headers=headers, json=data, timeout=8)
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Success with Groq ({model})")
                        return response.json()['choices'][0]['message']['content']
                    else:
                        logger.warning(f"⚠️ Groq {model} Failed: {response.status_code}")
                except Exception as e:
                    logger.error(f"❌ Groq Error: {e}")
                    continue

    # 🔥 ENGINE 2: OPENROUTER (Backup)
    if OPENROUTER_KEY:
        logger.info("🔄 Switching to OpenRouter Backup...")
        # Free Models on OpenRouter
        or_models = [
            "google/gemini-2.0-flash-lite-preview-02-05:free",
            "meta-llama/llama-3-8b-instruct:free",
            "mistralai/mistral-7b-instruct:free"
        ]
        
        for model in or_models:
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://telegram.org", 
                }
                data = {"model": model, "messages": messages}
                
                response = requests.post(url, headers=headers, json=data, timeout=15)
                
                if response.status_code == 200:
                    logger.info(f"✅ Success with OpenRouter ({model})")
                    return response.json()['choices'][0]['message']['content']
                else:
                    logger.warning(f"⚠️ OpenRouter {model} Failed: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"❌ OpenRouter Error: {e}")
                continue

    return "Gomen nasai... my chakra is completely drained. (Check Logs) 🌸"

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

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    text = update.message.text.lower()
    is_private = update.effective_chat.type == "private"
    has_name = "hinata" in text
    is_reply = (update.message.reply_to_message and 
                update.message.reply_to_message.from_user.id == context.bot.id)

    if is_private or has_name or is_reply:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        # Running AI logic in a way that doesn't block the bot
        reply = get_ai_response(update.message.text)
        await update.message.reply_text(reply)

# --- MAIN ---
if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    
    print("🚀 BOT STARTED SUCCESSFULLY!")
    application.run_polling()
