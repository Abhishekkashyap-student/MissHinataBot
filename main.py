import os
import logging
import requests
import random
import time
import sys
import psutil
import asyncio
from threading import Thread
from flask import Flask
from colorama import Fore, Style, init
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from motor.motor_asyncio import AsyncIOMotorClient

# --- LIVE CONSOLE SETUP ---
init(autoreset=True)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
# Agar Mongo URL nahi hai toh crash mat hona, bas memory disable karna
MONGO_URL = os.getenv("MONGO_URL") 
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
START_TIME = time.time()

if not TOKEN:
    print(Fore.RED + "❌ FATAL ERROR: BOT_TOKEN is missing!")
    sys.exit(1)

# --- MONGODB CONNECTION (SSL BYPASS FIX) ---
db_available = False
chat_collection = None

if MONGO_URL:
    try:
        # tlsAllowInvalidCertificates=True : Ye hai wo JUTSU jo SSL error theek karega
        mongo_client = AsyncIOMotorClient(MONGO_URL, tls=True, tlsAllowInvalidCertificates=True)
        db = mongo_client['hinata_db']
        chat_collection = db['chat_history']
        db_available = True
        print(Fore.GREEN + "✅ MONGODB CONNECTED: Infinite Memory Active!")
    except Exception as e:
        print(Fore.RED + f"⚠️ MONGO ERROR: {e} (Bot will run without memory)")
else:
    print(Fore.YELLOW + "⚠️ MONGO_URL missing. Running in Amnesia Mode.")

# --- MEDIA ---
HINATA_STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE"
]

# --- HINATA'S SOUL ---
HINATA_PROMPT = """
You are Hinata Hyuga (Naruto anime). You are NOT an AI. You are a real girl.
RULES:
1. DETECT LANGUAGE: Reply in the same language as the user (Hindi/English).
2. NO ACTIONS: No asterisks (*blushes*). Use emojis (😳, 👉👈, 🌸).
3. CREATOR: Created by FigletAxl. Join @vfriendschat.
4. LENGTH: Keep replies short, cute, and fast.
"""

# --- MEMORY FUNCTIONS (SAFE MODE) ---
async def save_history(user_id, role, content):
    if not db_available: return
    try:
        await chat_collection.update_one(
            {"user_id": user_id},
            {"$push": {"history": {"role": role, "content": content}}},
            upsert=True
        )
    except: pass

async def get_history(user_id):
    if not db_available: return []
    try:
        doc = await chat_collection.find_one({"user_id": user_id})
        return doc['history'][-6:] if doc and 'history' in doc else []
    except: return []

# --- AI ENGINE (UNLIMITED ROTATION) ---
async def get_ai_response(user_id, text):
    # 1. Memory Fetch
    history = await get_history(user_id)
    messages = [{"role": "system", "content": HINATA_PROMPT}] + history + [{"role": "user", "content": text}]

    # 2. GROQ ENGINE (Priority)
    groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    if GROQ_KEYS:
        for key in GROQ_KEYS:
            for model in groq_models:
                try:
                    res = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": model, "messages": messages, "max_tokens": 200},
                        timeout=5
                    )
                    if res.status_code == 200:
                        ans = res.json()['choices'][0]['message']['content']
                        print(f"{Fore.GREEN}🟢 GROQ ({model}): Success")
                        await save_history(user_id, "user", text)
                        await save_history(user_id, "assistant", ans)
                        return ans
                except: continue

    # 3. OPENROUTER BACKUP
    if OPENROUTER_KEY:
        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "HTTP-Referer": "https://google.com"},
                json={"model": "google/gemini-2.0-flash-lite-preview-02-05:free", "messages": messages},
                timeout=10
            )
            if res.status_code == 200:
                ans = res.json()['choices'][0]['message']['content']
                print(f"{Fore.CYAN}🔵 OPENROUTER: Success")
                await save_history(user_id, "user", text)
                await save_history(user_id, "assistant", ans)
                return ans
        except: pass

    return "Gomen nasai... network is down. 🌸"

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🦊 HINATA LIVE"
def run_flask(): app.run(host='0.0.0.0', port=8000)
def keep_alive(): Thread(target=run_flask).start()

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    await update.message.reply_text("N-Naruto-kun? 😳\nI am ready! 🌸")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # System Stats Calculation
    uptime = int(time.time() - START_TIME)
    ram = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    
    msg = f"""
⚡ **BARYON MODE STATUS** ⚡

🌸 **Ping:** `Pong!`
💻 **CPU:** `{cpu}%`
🧠 **RAM:** `{ram}%`
⏱️ **Uptime:** `{uptime}s`
🍃 **Memory (DB):** `{'Online ✅' if db_available else 'Offline ❌'}`
    """
    await update.message.reply_text(msg, parse_mode="Markdown")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_msg = update.message.text
    user_id = update.effective_user.id
    
    is_dm = update.effective_chat.type == "private"
    has_name = "hinata" in user_msg.lower()
    is_reply = (update.message.reply_to_message and 
                update.message.reply_to_message.from_user.id == context.bot.id)

    if is_dm or has_name or is_reply:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
        
        # Non-blocking AI call
        reply = await get_ai_response(user_id, user_msg)
        await update.message.reply_text(reply)
        
        if random.randint(1, 100) > 85:
            try: await context.bot.send_sticker(update.effective_chat.id, random.choice(HINATA_STICKERS))
            except: pass

# --- MAIN ---
if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('ping', ping))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    
    print(Fore.YELLOW + "🚀 HINATA BOT STARTED WITH SSL FIX!")
    application.run_polling()
