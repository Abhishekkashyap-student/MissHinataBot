import os
import logging
import requests
import random
import time
import sys
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from motor.motor_asyncio import AsyncIOMotorClient

# --- LIVE CONSOLE SETUP ---
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION (ENV VARS) ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://axlbot:pass1234@alexamusiccluster.jxblrni.mongodb.net/alexamusic") # Backup agar env fail ho
OWNER_ID = int(os.getenv("OWNER_ID", "0")) # Yahan apni Telegram ID dalo (Environment mein)
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN:
    print("❌ FATAL ERROR: BOT_TOKEN is missing!")
    sys.exit(1)

# --- MONGODB CONNECTION (LONG TERM MEMORY) ---
try:
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client['hinata_db']
    chat_collection = db['chat_history']
    print("✅ MONGODB CONNECTED: Infinite Memory Active!")
except Exception as e:
    print(f"❌ MONGO ERROR: {e}")

# --- MEDIA COLLECTION ---
HINATA_STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE"
]

# --- AI ENGINE (MEMORY & CONTEXT) ---
async def get_history(user_id):
    # Pichle 10 messages nikalo database se
    doc = await chat_collection.find_one({"user_id": user_id})
    return doc['history'][-10:] if doc and 'history' in doc else []

async def save_history(user_id, role, content):
    # Naya message save karo
    await chat_collection.update_one(
        {"user_id": user_id},
        {"$push": {"history": {"role": role, "content": content}}},
        upsert=True
    )

async def get_ai_response(user_id, text, context_msg=None, is_owner=False):
    # 1. Memory Fetch
    history = await get_history(user_id)
    
    # 2. Dynamic System Prompt
    user_name = "Naruto-kun" if is_owner else "User-san"
    
    system_prompt = f"""You are Hinata Hyuga (Naruto anime).
    - You are a REAL girl, shy and caring.
    - The user talking to you is '{user_name}'.
    - If '{user_name}' is Naruto-kun, be extra shy and loving.
    - If replying to a forwarded message, explain or react to THAT message.
    - No robotic talk. Use emojis (😳, 👉👈, 🌸). Keep it short."""

    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": text}]
    
    # Agar kisi aur ke message par reply kar rahe hain (Context)
    if context_msg:
        messages.append({"role": "system", "content": f"Context Message to reply to: {context_msg}"})

    # 3. GROQ ENGINE (Priority)
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
                    await save_history(user_id, "user", text)
                    await save_history(user_id, "assistant", ans)
                    return ans
            except: continue

    # 4. OPENROUTER BACKUP
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
                await save_history(user_id, "user", text)
                await save_history(user_id, "assistant", ans)
                return ans
        except: pass

    return "Gomen... chakkar aa raha hai... 🌸"

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🦊 HINATA WITH MONGODB IS LIVE"
def run_flask(): app.run(host='0.0.0.0', port=8000)
def keep_alive(): Thread(target=run_flask).start()

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    is_owner = update.effective_user.id == OWNER_ID
    msg = "N-Naruto-kun? 😳❤️\nMain wapas aa gayi!" if is_owner else "Hello! I am Hinata. 🌸"
    await update.message.reply_text(msg)

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    is_owner = user_id == OWNER_ID
    
    # 1. STICKER REPLY LOGIC
    if update.message.sticker:
        # Agar Owner ne sticker bheja ya reply mein sticker aaya
        is_reply = (update.message.reply_to_message and 
                    update.message.reply_to_message.from_user.id == context.bot.id)
        if update.effective_chat.type == "private" or is_reply:
            if random.random() > 0.3: # 70% chance to reply with sticker
                try:
                    await context.bot.send_sticker(chat_id, random.choice(HINATA_STICKERS))
                except: pass
        return

    # 2. TEXT REPLY LOGIC
    if update.message.text:
        text = update.message.text
        lower_text = text.lower()
        
        # Check Context (Reply to another user)
        context_text = None
        if update.message.reply_to_message:
            # Agar bot ko reply kiya hai -> Normal Chat
            if update.message.reply_to_message.from_user.id == context.bot.id:
                pass 
            # Agar kisi aur user ko reply karke Hinata ko bola -> Smart Reply
            elif "hinata" in lower_text:
                context_text = f"User said: {update.message.reply_to_message.text}"
        
        # Trigger Conditions
        is_dm = update.effective_chat.type == "private"
        has_name = "hinata" in lower_text
        is_reply_to_bot = (update.message.reply_to_message and 
                           update.message.reply_to_message.from_user.id == context.bot.id)

        if is_dm or has_name or is_reply_to_bot or context_text:
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
            
            # AI Call with all details
            reply = await get_ai_response(user_id, text, context_text, is_owner)
            await update.message.reply_text(reply)

# --- MAIN ---
if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.ALL, chat)) # All types (Text + Sticker)
    
    print("🚀 BARYON MODE V2: MONGODB & CONTEXT ACTIVE!")
    application.run_polling()
