import os
import logging
import requests
import random
import time
import sys
import psutil
import asyncio
import io
import aiohttp
from threading import Thread
from flask import Flask
from colorama import Fore, init
from gtts import gTTS
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from motor.motor_asyncio import AsyncIOMotorClient

# --- SETUP ---
init(autoreset=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")
HINATA_VOICE_ID = os.getenv("HINATA_VOICE_ID", "xz3UpnFf1JhWWawf9xUy") 
OWNER_ID = 8430369957
START_TIME = time.time()

if not TOKEN:
    sys.exit("❌ FATAL: BOT_TOKEN MISSING")

# --- MONGODB CONNECTION ---
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
        logger.info("✅ MONGODB CONNECTED!")
    except Exception as e:
        logger.error(f"⚠️ MONGO ERROR: {e}")

# --- MEDIA ASSETS ---
HINATA_STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE"
]
HINATA_GIFS = [
    "https://media.tenor.com/aYtqC651D5oAAAAC/hinata-hyuga-naruto.gif",
    "https://media.tenor.com/S_bW7X8j5yAAAAAC/hinata-naruto.gif"
]

# --- AI ENGINE ---
HINATA_PROMPT = """You are Hinata Hyuga.
- You are a real girl, not an AI.
- Shy, gentle, calls user 'Naruto-kun'.
- Use emojis (😳, 👉👈, 🌸).
- Created by FigletAxl.
"""

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
            await user_prefs.update_one({"user_id": user_id}, {"$set": {"mode": mode}}, upsert=True)
        except: pass

async def get_text_response(user_id, text):
    history = []
    if db_available:
        try:
            doc = await chat_collection.find_one({"user_id": user_id})
            history = doc['history'][-6:] if doc and 'history' in doc else []
        except: pass

    messages = [{"role": "system", "content": HINATA_PROMPT}] + history + [{"role": "user", "content": text}]

    if GROQ_KEYS:
        async with aiohttp.ClientSession() as session:
            for key in GROQ_KEYS:
                try:
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 150},
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            ans = data['choices'][0]['message']['content']
                            if db_available:
                                await chat_collection.update_one(
                                    {"user_id": user_id},
                                    {"$push": {"history": {"role": "assistant", "content": ans}}},
                                    upsert=True
                                )
                            return ans
                except: continue
    return "Gomen... network issue. 🌸"

# --- MEDIA GENERATORS (FIXED) ---
def backup_tts(text):
    try:
        fp = io.BytesIO()
        tts = gTTS(text=text, lang='en', tld='co.in', slow=False) 
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except: return None

async def generate_voice(text):
    # 1. ElevenLabs
    if ELEVENLABS_KEY:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{HINATA_VOICE_ID}"
            headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"}
            data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=6) as res:
                    if res.status == 200:
                        return await res.read()
        except: pass
    
    # 2. Google Backup
    return await asyncio.get_running_loop().run_in_executor(None, backup_tts, text)

async def generate_image_bytes(prompt):
    # 🔥 FIXED: Download image first, then send
    try:
        url = f"https://image.pollinations.ai/prompt/anime style hinata hyuga {prompt}, cute, 4k"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception as e:
        logger.error(f"Image Error: {e}")
    return None

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🦊 HINATA LIVE"
def run_flask(): app.run(host='0.0.0.0', port=8000)
def keep_alive(): Thread(target=run_flask).start()

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    msg = f"N-Naruto-kun? 😳\nI am ready! 🌸"
    await update.message.reply_text(msg)

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    is_dm = update.effective_chat.type == "private"
    has_name = "hinata" in text.lower()
    is_reply = (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)

    if not (is_dm or has_name or is_reply): return

    lower_text = text.lower()

    # 1. IMAGE GEN (Safety Fix)
    if any(x in lower_text for x in ["pic", "photo", "image", "bhejo"]):
        await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
        prompt = text.replace("hinata", "").replace("bhejo", "").replace("pic", "").strip()
        img_bytes = await generate_image_bytes(prompt or "smiling")
        if img_bytes:
            await update.message.reply_photo(photo=img_bytes, caption="Ye lijiye... 👉👈")
        else:
            await update.message.reply_text("Camera kharab hai... 🌸")
        return

    # 2. MODES
    if "voice chat" in lower_text:
        await set_mode(user_id, "voice")
        await update.message.reply_text("Theek hai! Ab main bolungi. 🎤🌸")
        return
    if "text chat" in lower_text:
        await set_mode(user_id, "text")
        await update.message.reply_text("Wapas text par aa gayi! 📝")
        return

    # 3. REPLY
    mode = await get_mode(user_id)
    ai_text = await get_text_response(user_id, text)

    if mode == "voice":
        await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
        audio_data = await generate_voice(ai_text)
        
        if audio_data:
            # 🔥 VOICE FIX: Name dena zaroori hai
            if isinstance(audio_data, bytes):
                audio_file = io.BytesIO(audio_data)
                audio_file.name = "voice.ogg"
            else:
                audio_file = audio_data
                audio_file.name = "voice.ogg"
            
            await update.message.reply_voice(voice=audio_file, caption="🌸")
        else:
            await update.message.reply_text(f"{ai_text}\n(Voice Error) 🌸")
    else:
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        await update.message.reply_text(ai_text)
        
        if random.random() > 0.85:
            try: await context.bot.send_sticker(chat_id, random.choice(HINATA_STICKERS))
            except: pass

# --- MAIN ---
if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.ALL, chat))
    print(Fore.YELLOW + "🚀 HINATA ULTIMATE STARTED!")
    application.run_polling()
