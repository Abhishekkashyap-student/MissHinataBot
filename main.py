import os
import logging
import requests
import random
import time
import sys
import psutil
import asyncio
import io
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
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://axlbot:pass1234@alexamusiccluster.jxblrni.mongodb.net/alexamusic")
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")
HINATA_VOICE_ID = os.getenv("HINATA_VOICE_ID", "xz3UpnFf1JhWWawf9xUy") 
OWNER_ID = 8430369957
START_TIME = time.time()

# --- MONGODB CONNECTION ---
db_available = False
chat_collection = None
user_prefs = None 

try:
    mongo_client = AsyncIOMotorClient(MONGO_URL, tls=True, tlsAllowInvalidCertificates=True)
    db = mongo_client['hinata_db']
    chat_collection = db['chat_history']
    user_prefs = db['user_prefs']
    db_available = True
    logger.info("✅ MONGODB CONNECTED!")
except Exception as e:
    logger.error(f"❌ MONGO ERROR: {e}")

# --- MEDIA ---
HINATA_STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE"
]
HINATA_GIFS = [
    "https://media.tenor.com/aYtqC651D5oAAAAC/hinata-hyuga-naruto.gif",
    "https://media.tenor.com/S_bW7X8j5yAAAAAC/hinata-naruto.gif"
]

HINATA_PROMPT = """You are Hinata Hyuga. NOT an AI.
- Shy, gentle, calls user 'Naruto-kun'.
- Use emojis (😳, 👉👈, 🌸).
- Keep answers SHORT & CUTE.
- Created by FigletAxl.
"""

# --- AI ENGINE (NEW ROBUST LOGIC) ---
async def get_text_response(user_id, text):
    history = []
    if db_available:
        try:
            doc = await chat_collection.find_one({"user_id": user_id})
            history = doc['history'][-6:] if doc and 'history' in doc else []
        except: pass

    messages = [{"role": "system", "content": HINATA_PROMPT}] + history + [{"role": "user", "content": text}]

    # 1. TRY GROQ FIRST
    if GROQ_KEYS:
        async with aiohttp.ClientSession() as session:
            for i, key in enumerate(GROQ_KEYS):
                try:
                    logger.info(f"🔄 Trying Groq Key #{i+1}...")
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 150},
                        timeout=12 # Timeout badha diya
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            ans = data['choices'][0]['message']['content']
                            if db_available:
                                await chat_collection.update_one({"user_id": user_id}, {"$push": {"history": {"role": "assistant", "content": ans}}}, upsert=True)
                            return ans
                        else:
                            error_data = await response.text()
                            logger.error(f"❌ Groq Key #{i+1} Failed ({response.status}): {error_data}")
                except Exception as e:
                    logger.error(f"⚠️ Error with Groq Key #{i+1}: {e}")
                    continue

    # 2. TRY OPENROUTER AS BACKUP (IMPORTANT!)
    if OPENROUTER_KEY:
        logger.info("🔄 Groq failed. Trying OpenRouter Backup...")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                    json={"model": "google/gemini-2.0-flash-lite-preview-02-05:free", "messages": messages},
                    timeout=15
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        ans = data['choices'][0]['message']['content']
                        return ans
            except Exception as e:
                logger.error(f"❌ OpenRouter also failed: {e}")

    return "Gomen... network issue. 🌸"

# --- MEDIA GENERATORS ---
def backup_tts(text):
    try:
        fp = io.BytesIO()
        tts = gTTS(text=text, lang='en', tld='co.in', slow=False) 
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except: return None

async def generate_voice(text):
    if ELEVENLABS_KEY:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{HINATA_VOICE_ID}"
            headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"}
            data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=10) as res:
                    if res.status == 200:
                        return await res.read()
        except: pass
    return await asyncio.get_running_loop().run_in_executor(None, backup_tts, text)

async def generate_image(prompt):
    try:
        url = f"https://image.pollinations.ai/prompt/anime style hinata hyuga {prompt}, cute, 4k"
        return url
    except: return None

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🦊 HINATA LIVE"
def run_flask(): app.run(host='0.0.0.0', port=8000)
def keep_alive(): Thread(target=run_flask).start()

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dev_link = f"<a href='tg://user?id={OWNER_ID}'>FigletAxl</a>"
    await update.message.reply_text(f"N-Naruto-kun? 😳\nI am ready! Created by {dev_link}-kun. 🌸", parse_mode=ParseMode.HTML)

async def get_mode(user_id):
    if db_available:
        doc = await user_prefs.find_one({"user_id": user_id})
        return doc.get("mode", "text") if doc else "text"
    return "text"

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
    
    if "pic" in lower_text or "photo" in lower_text:
        await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
        img_url = await generate_image(text.replace("hinata", ""))
        await update.message.reply_photo(img_url, caption="Ye lijiye... 👉👈")
        return

    if "voice chat" in lower_text:
        if db_available: await user_prefs.update_one({"user_id": user_id}, {"$set": {"mode": "voice"}}, upsert=True)
        await update.message.reply_text("Ab main bol kar jawab dungi. 🎤🌸")
        return
    if "text chat" in lower_text:
        if db_available: await user_prefs.update_one({"user_id": user_id}, {"$set": {"mode": "text"}}, upsert=True)
        await update.message.reply_text("Wapas text par aa gayi! 📝")
        return

    mode = await get_mode(user_id)
    await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE if mode == "voice" else ChatAction.TYPING)
    
    ai_text = await get_text_response(user_id, text)
    
    if mode == "voice":
        audio = await generate_voice(ai_text)
        await update.message.reply_voice(audio, caption="🌸")
    else:
        # Double texting logic
        if len(ai_text) > 100 and random.random() > 0.7:
            parts = ai_text.split(". ", 1)
            await update.message.reply_text(parts[0] + ".")
            await asyncio.sleep(1)
            await update.message.reply_text(parts[1] if len(parts) > 1 else "👉👈")
        else:
            await update.message.reply_text(ai_text)

# --- MAIN ---
if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.ALL, chat))
    print("🚀 HINATA ULTIMATE STARTED!")
    application.run_polling()
