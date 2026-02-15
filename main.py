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
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from motor.motor_asyncio import AsyncIOMotorClient

# --- LIVE CONSOLE & LOGGING ---
init(autoreset=True)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OWNER_ID = 8430369957  # Tera User ID
START_TIME = time.time()

if not TOKEN:
    print(Fore.RED + "❌ FATAL ERROR: BOT_TOKEN is missing!")
    sys.exit(1)

# --- MONGODB CONNECTION ---
db_available = False
chat_collection = None
if MONGO_URL:
    try:
        mongo_client = AsyncIOMotorClient(MONGO_URL, tls=True, tlsAllowInvalidCertificates=True)
        db = mongo_client['hinata_db']
        chat_collection = db['chat_history']
        db_available = True
        print(Fore.GREEN + "✅ MONGODB CONNECTED: Infinite Memory Active!")
    except Exception as e:
        print(Fore.RED + f"⚠️ MONGO ERROR: {e}")

# --- MEDIA LIBRARY (ADVANCED) ---
# Default Stickers (Start ke liye)
HINATA_STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE"
]

# Random GIFs (Direct Links)
HINATA_GIFS = [
    "https://media.tenor.com/aYtqC651D5oAAAAC/hinata-hyuga-naruto.gif",
    "https://media.tenor.com/M1K8y1jV134AAAAC/hinata-shy.gif",
    "https://media.tenor.com/S_bW7X8j5yAAAAAC/hinata-naruto.gif",
    "https://media.tenor.com/E50_a9_5_6AAAAAC/hinata-hyuga.gif"
]

# --- AI LOGIC ---
HINATA_PROMPT = """You are Hinata Hyuga. NOT an AI. Real girl.
- Shy, caring, calls user 'Naruto-kun'.
- Use emojis (😳, 👉👈, 🌸).
- No roleplay asterisks.
- Created by FigletAxl.
"""

async def get_ai_response(user_id, text):
    # Memory Fetch
    history = []
    if db_available:
        try:
            doc = await chat_collection.find_one({"user_id": user_id})
            history = doc['history'][-6:] if doc and 'history' in doc else []
        except: pass

    messages = [{"role": "system", "content": HINATA_PROMPT}] + history + [{"role": "user", "content": text}]

    # Groq Engine
    if GROQ_KEYS:
        for key in GROQ_KEYS:
            try:
                res = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 200},
                    timeout=5
                )
                if res.status_code == 200:
                    ans = res.json()['choices'][0]['message']['content']
                    # Save History
                    if db_available:
                        await chat_collection.update_one(
                            {"user_id": user_id},
                            {"$push": {"history": {"role": "assistant", "content": ans}}},
                            upsert=True
                        )
                    return ans
            except: continue
    
    return "Gomen... network error. 🌸"

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🦊 HINATA LIVE"
def run_flask(): app.run(host='0.0.0.0', port=8000)
def keep_alive(): Thread(target=run_flask).start()

# --- COMMAND HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    
    # Advanced Developer Link
    dev_link = f"<a href='tg://user?id={OWNER_ID}'>FigletAxl</a>"
    
    msg = (
        f"N-Naruto-kun? 😳\n"
        f"I am ready! Created by {dev_link}-kun. 🌸\n"
        f"Join my clan: @vfriendschat"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = int(time.time() - START_TIME)
    ram = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    msg = f"⚡ **STATUS**\n🌸 **Ping:** Pong!\n💻 **CPU:** `{cpu}%`\n🧠 **RAM:** `{ram}%`\n⏱️ **Uptime:** `{uptime}s`"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# --- SMART CHAT HANDLER ---
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # 1. STICKER REACTION (NEW JUTSU) 🖼️
    if update.message.sticker:
        # Agar private chat hai ya bot ko reply kiya hai
        is_dm = update.effective_chat.type == "private"
        is_reply = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
        
        if is_dm or is_reply:
            # 80% Chance to reply with a sticker
            if random.random() > 0.2:
                await context.bot.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
                time.sleep(1) # Human feel
                # Agar us sticker set se aur stickers mil sakein toh wo bhejo (Advanced), nahi toh default
                try:
                    await context.bot.send_sticker(chat_id, random.choice(HINATA_STICKERS))
                except: pass
        return

    # 2. TEXT & GIF LOGIC 💬
    if update.message.text:
        text = update.message.text.lower()
        is_dm = update.effective_chat.type == "private"
        has_name = "hinata" in text
        is_reply = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id

        if is_dm or has_name or is_reply:
            # Typing...
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
            
            # AI Reply
            reply = await get_ai_response(user_id, update.message.text)
            await update.message.reply_text(reply)

            # Random GIF Injection (10% Chance)
            if random.random() > 0.90:
                try:
                    await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_VIDEO)
                    await context.bot.send_animation(chat_id, random.choice(HINATA_GIFS))
                except: pass

# --- MAIN ---
if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('ping', ping))
    application.add_handler(MessageHandler(filters.ALL, chat)) # Stickers bhi pakdega
    
    print(Fore.YELLOW + "🚀 HINATA ULTIMATE VERSION STARTED!")
    application.run_polling()
