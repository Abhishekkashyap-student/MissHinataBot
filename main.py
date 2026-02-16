import os
import logging
import requests
import random
import time
import sys
import psutil
import asyncio
import io
import urllib.parse
from threading import Thread
from flask import Flask
from colorama import Fore, init
from gtts import gTTS
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp

# --- SETUP ---
init(autoreset=True)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
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
    print(Fore.RED + "❌ FATAL ERROR: BOT_TOKEN missing!")
    sys.exit(1)

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

# --- MEDIA COLLECTION ---
HINATA_STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE"
]
HINATA_GIFS = [
    "https://media.tenor.com/aYtqC651D5oAAAAC/hinata-hyuga-naruto.gif",
    "https://media.tenor.com/S_bW7X8j5yAAAAAC/hinata-naruto.gif"
]

# --- HINATA'S SOUL ---
HINATA_PROMPT = """You are Hinata Hyuga.
- You are a real girl, not an AI.
- You are shy, polite, and deeply caring.
- Call the user 'Naruto-kun' if they are the owner, else '-san'.
- Use emojis (😳, 👉👈, 🌸).
- Keep answers SHORT & CUTE.
- Never show technical errors.
"""

# --- UTILS ---
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

# --- AI ENGINE ---
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
        async with aiohttp.ClientSession() as session:
            for key in GROQ_KEYS:
                try:
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 150},
                        timeout=8
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
        # Google TTS (Free Backup)
        fp = io.BytesIO()
        tts = gTTS(text=text, lang='en', tld='co.in', slow=False) 
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception as e:
        logger.error(f"GTTS Error: {e}")
        return None

async def generate_voice(text):
    # 1. ElevenLabs (Real Voice)
    if ELEVENLABS_KEY:
        try:
            logger.info("🎙️ Trying ElevenLabs...")
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{HINATA_VOICE_ID}"
            headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"}
            data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=5) as res:
                    if res.status == 200:
                        return io.BytesIO(await res.read()) # Return as BytesIO
                    else:
                        logger.warning(f"ElevenLabs Limit/Error: {res.status}")
        except: pass
    
    # 2. Google Backup (Unlimited)
    logger.info("🔄 Switching to Google TTS Backup...")
    return await asyncio.get_running_loop().run_in_executor(None, backup_tts, text)

async def generate_image_bytes(prompt):
    try:
        # URL Safe Encode
        safe_prompt = urllib.parse.quote(f"anime style hinata hyuga {prompt}, cute, high quality, 4k")
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}"
        
        # Download Image FIRST (To avoid Telegram URL error)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return io.BytesIO(await resp.read())
    except Exception as e:
        logger.error(f"Image Gen Error: {e}")
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
    dev_link = f"<a href='tg://user?id={OWNER_ID}'>FigletAxl</a>"
    await update.message.reply_text(f"N-Naruto-kun? 😳\nI am ready! Created by {dev_link}-kun. 🌸", parse_mode=ParseMode.HTML)

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check Logic
    is_dm = update.effective_chat.type == "private"
    has_name = "hinata" in text.lower()
    is_reply = (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)

    if not (is_dm or has_name or is_reply): return

    lower_text = text.lower()
    
    # 1. IMAGE GEN (FIXED)
    if any(x in lower_text for x in ["pic", "photo", "image", "bhejo"]):
        await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
        prompt = text.replace("hinata", "").replace("bhejo", "").replace("pic", "").replace("photo", "").strip()
        img_bytes = await generate_image_bytes(prompt or "smiling")
        
        if img_bytes:
            await update.message.reply_photo(img_bytes, caption="Ye lijiye... 👉👈")
        else:
            await update.message.reply_text("Gomen... camera kharab hai. 🌸")
        return

    # 2. MODE SWITCHING
    if "voice chat" in lower_text:
        await set_mode(user_id, "voice")
        await update.message.reply_text("Theek hai! Ab main bol kar jawab dungi. 🎤🌸")
        return
    if "text chat" in lower_text:
        await set_mode(user_id, "text")
        await update.message.reply_text("Wapas text par aa gayi! 📝")
        return

    # 3. REPLY LOGIC
    mode = await get_mode(user_id)
    ai_text = await get_text_response(user_id, text)
    
    if mode == "voice":
        await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
        audio_file = await generate_voice(ai_text)
        
        if audio_file:
            await update.message.reply_voice(audio_file, caption="🌸")
        else:
            # Agar voice fail ho gayi toh text bhejo
            await update.message.reply_text(f"{ai_text}\n(Gala kharab hai aaj... 😣)")
            
    else:
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        
        # Double Texting Logic
        if len(ai_text) > 80 and random.random() > 0.6:
            parts = ai_text.split(". ", 1)
            await update.message.reply_text(parts[0] + ".")
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(1.5)
            await update.message.reply_text(parts[1] if len(parts) > 1 else "👉👈")
        else:
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
    print(Fore.YELLOW + "🚀 OTSUTSUKI HINATA STARTED!")
    application.run_polling()
