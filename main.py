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
from colorama import Fore, init
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from motor.motor_asyncio import AsyncIOMotorClient

# --- SETUP ---
init(autoreset=True)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION (ENV VARS) ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")
# Tera Naya Voice ID yahan hai
HINATA_VOICE_ID = os.getenv("HINATA_VOICE_ID", "xz3UpnFf1JhWWawf9xUy") 
OWNER_ID = 8430369957
START_TIME = time.time()

if not TOKEN:
    print(Fore.RED + "❌ FATAL ERROR: BOT_TOKEN missing!")
    sys.exit(1)

# --- MONGODB (MEMORY) ---
db_available = False
chat_collection = None
user_prefs = None 

if MONGO_URL:
    try:
        mongo_client = AsyncIOMotorClient(MONGO_URL, tls=True, tlsAllowInvalidCertificates=True)
        db = mongo_client['hinata_db']
        chat_collection = db['chat_history']
        user_prefs = db['user_prefs']
        db_available = True
        print(Fore.GREEN + "✅ MONGODB CONNECTED!")
    except Exception as e:
        print(Fore.RED + f"⚠️ MONGO ERROR: {e}")

# --- MEDIA ---
HINATA_STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE"
]
HINATA_GIFS = [
    "https://media.tenor.com/aYtqC651D5oAAAAC/hinata-hyuga-naruto.gif",
    "https://media.tenor.com/S_bW7X8j5yAAAAAC/hinata-naruto.gif"
]

# --- HINATA'S BRAIN ---
HINATA_PROMPT = """You are Hinata Hyuga. NOT an AI.
- Shy, gentle, calls user 'Naruto-kun'.
- Use emojis (😳, 👉👈, 🌸).
- Keep answers SHORT & CUTE.
- Created by FigletAxl.
"""

# --- HELPER FUNCTIONS ---
async def get_mode(user_id):
    if db_available:
        try:
            doc = await user_prefs.find_one({"user_id": user_id})
            return doc.get("mode", "text") if doc else "text"
        except: pass
    return "text"

async def set_mode(user_id, mode):
    if db_available:
        try:
            await user_prefs.update_one(
                {"user_id": user_id}, {"$set": {"mode": mode}}, upsert=True
            )
        except: pass

# --- AI GENERATION ---
async def get_text_response(user_id, text):
    history = []
    if db_available:
        try:
            doc = await chat_collection.find_one({"user_id": user_id})
            history = doc['history'][-6:] if doc and 'history' in doc else []
        except: pass

    messages = [{"role": "system", "content": HINATA_PROMPT}] + history + [{"role": "user", "content": text}]

    # Groq Logic
    if GROQ_KEYS:
        for key in GROQ_KEYS:
            try:
                res = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 150},
                    timeout=5
                )
                if res.status_code == 200:
                    ans = res.json()['choices'][0]['message']['content']
                    if db_available:
                        await chat_collection.update_one(
                            {"user_id": user_id},
                            {"$push": {"history": {"role": "assistant", "content": ans}}},
                            upsert=True
                        )
                    return ans
            except: continue
            
    return "Gomen... network issue. 🌸"

async def generate_voice(text):
    if not ELEVENLABS_KEY: return None
    try:
        # ElevenLabs v2 Multilingual Model (Best for Hindi/English)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{HINATA_VOICE_ID}"
        headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"}
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2", 
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
        res = requests.post(url, json=data, headers=headers)
        if res.status_code == 200:
            return res.content
        else:
            print(f"Voice Error: {res.text}")
    except: pass
    return None

async def generate_image(prompt):
    try:
        # Pollinations AI - Unlimited & Free
        safe_prompt = f"anime style hinata hyuga {prompt}, high quality, cute, soft lighting, 4k"
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}"
        return url
    except: return None

# --- WEB SERVER (LIFE SUPPORT) ---
app = Flask('')
@app.route('/')
def home(): return "🦊 HINATA ONLINE"
def run_flask(): app.run(host='0.0.0.0', port=8000)
def keep_alive(): Thread(target=run_flask).start()

# --- HANDLERS ---

@app.on_message(filters.command("start"))
async def start(update, context):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    dev_link = f"<a href='tg://user?id={OWNER_ID}'>FigletAxl</a>"
    msg = f"N-Naruto-kun? 😳\nI am ready! Created by {dev_link}-kun. 🌸"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

@app.on_message(filters.text & ~filters.bot)
async def chat(update, context):
    if not update.message: return
    text = update.message.text
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check Trigger
    is_dm = update.effective_chat.type == "private"
    has_name = "hinata" in text.lower()
    is_reply = (update.message.reply_to_message and 
                update.message.reply_to_message.from_user.id == context.bot.id)

    if not (is_dm or has_name or is_reply): return

    lower_text = text.lower()
    
    # 1. MODE SWITCHING
    if "voice chat" in lower_text:
        await set_mode(user_id, "voice")
        await update.message.reply_text("Theek hai! Ab main bol kar jawab dungi. 🎤🌸")
        return
    
    if "text chat" in lower_text:
        await set_mode(user_id, "text")
        await update.message.reply_text("Okay! Wapas text par aa gayi. 📝🌸")
        return
        
    # 2. IMAGE GENERATION
    if "pic" in lower_text or "photo" in lower_text or "image" in lower_text:
        await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
        # Prompt cleaning
        clean_prompt = text.replace("hinata", "").replace("bhejo", "").replace("pic", "").replace("photo", "").strip()
        img_url = await generate_image(clean_prompt or "smiling")
        if img_url:
            await update.message.reply_photo(img_url, caption="Ye lijiye... 👉👈")
            return

    # 3. CHAT LOGIC
    mode = await get_mode(user_id)
    
    if mode == "voice":
        await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
        ai_text = await get_text_response(user_id, text)
        audio = await generate_voice(ai_text)
        if audio:
            await update.message.reply_voice(audio, caption="🌸")
        else:
            await update.message.reply_text(ai_text) # Fallback if quota over
    else:
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        ai_text = await get_text_response(user_id, text)
        await update.message.reply_text(ai_text)
        
        # Sticker/GIF Random Injection
        if random.random() > 0.85:
            try:
                if random.choice([True, False]):
                    await context.bot.send_sticker(chat_id, random.choice(HINATA_STICKERS))
                else:
                    await context.bot.send_animation(chat_id, random.choice(HINATA_GIFS))
            except: pass

# --- MAIN ---
if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.ALL, chat))
    print(Fore.YELLOW + "🚀 HINATA ULTIMATE ACTIVE!")
    application.run_polling()
