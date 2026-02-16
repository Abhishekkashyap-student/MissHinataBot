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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION (ENV VARS) ---
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

# --- MEDIA COLLECTION (UPDATED WITH YOUR STICKERS) ---
HINATA_STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE",
    "CAACAgUAAxkBAAEQhwtpkpsDnQvGqN6EZi7DSsL6yCGpGgACggYAArXC-FerIE7xabONtjoE",
    "CAACAgUAAxkBAAEQhwxpkpsD0m9Kv1hyFUkLS2dikmwNpAACRQQAAmi1iFbiIy-5jn88MjoE",
    "CAACAgUAAxkBAAEQhxNpkqYpurdkhxj-_qpbe8Jcg2ZMEQACyAYAAslrgVZ5SXsc4VrZxDoE",
    "CAACAgUAAxkBAAEQhxVpkqYzdKGgp8oM-aF20m8FUHZXxwACcwQAAuWQiFaLohAqKc3NWzoE",
    "CAACAgUAAxkBAAEQhxdpkqY2P0m4TxE6vlCPz49O_EMSFQACoQQAArgQiVYbOVm8HBe_ZjoE",
    "CAACAgUAAxkBAAEQhxlpkqY5ttqQ2pAHi8awaM4dwm834AACqgYAAtl4gFbh5StpvCT99joE",
    "CAACAgUAAxkBAAEQhxtpkqY9rNBusftFqCyIFJSUP9ZOlwACBwUAAha1iVZ33XYX5lux5zoE",
    "CAACAgUAAxkBAAEQhx1pkqY_9hTlZOKWxL6NTExfaqxvhwACoAYAAlIogFY3yR9qoXw2wToE",
    "CAACAgUAAxkBAAEQhx9pkqZCDRgR6BRFiCJ3BB1n2yKO2QACBQcAAiK-iVbXjCbGXxmXFzoE",
    "CAACAgUAAxkBAAEQhyFpkqZLyQkMw490R-Hy5JHYkggsYgACTQUAAkHoIFeJ7BvsZutAzzoE",
    "CAACAgUAAxkBAAEQhyNpkqZPXTcAAW8D3PV_HF34VT_cyvAAAiwEAAJHGCFXq9n7uE5iQds6BA",
    "CAACAgUAAxkBAAEQhyVpkqZRlvzfJAbQWrCYGT47oGvVDAACowYAAhcwIVd0rNn1hRRqMDoE",
    "CAACAgUAAxkBAAEQhydpkqZXZMMol_ae625g_MUGzTZ31AACQAQAAtViIFfnUyGLneYmiDoE",
    "CAACAgUAAxkBAAEQhylpkqZZ_WpEbfSv7qLlEvSIofbtwgACrwQAAj_FIVdkHc6hM5p0RzoE",
    "CAACAgUAAxkBAAEQhytpkqZdNindw9pYTUhIm_6_1yUcZwACTgcAAv6uIFddTzKe7JJmyzoE",
    "CAACAgUAAxkBAAEQhy1pkqZgN-f2NCJp1N1usbCW0APQXAACjwQAAjCbIFeVamPW1YZCXzoE",
    "CAACAgUAAxkBAAEQhy9pkqZsc44h_6rVw-m7MAwjaduQPgACnQQAAotYqFcXUBpL70t0pzoE",
    "CAACAgUAAxkBAAEQhzFpkqZulSoEOR5yYeKC5R0CdbiCXAACvgYAApKTqVduYLPrFu-dIjoE",
    "CAACAgUAAxkBAAEQhzNpkqZxol9n-GPmU277nZw04m_WFAACkwMAApXHqVfqro6Xrj4MhDoE",
    "CAACAgUAAxkBAAEQhzVpkqZ1Q5GKuJBx28DkZ4D5wArGXAACoQQAAsv_qVeFX7x-j44JsToE",
    "CAACAgUAAxkBAAEQhzdpkqZ44vXASwznUDt77qMkIDMdQQAC4ggAAnpeqFfwHHzbDNOIZzo"
]

HINATA_GIFS = [
    "[https://media.tenor.com/aYtqC651D5oAAAAC/hinata-hyuga-naruto.gif](https://media.tenor.com/aYtqC651D5oAAAAC/hinata-hyuga-naruto.gif)",
    "[https://media.tenor.com/S_bW7X8j5yAAAAAC/hinata-naruto.gif](https://media.tenor.com/S_bW7X8j5yAAAAAC/hinata-naruto.gif)",
    "[https://media.tenor.com/M1K8y1jV134AAAAC/hinata-shy.gif](https://media.tenor.com/M1K8y1jV134AAAAC/hinata-shy.gif)"
]

HINATA_PROMPT = """You are Hinata Hyuga. NOT an AI.
- Shy, gentle, calls user 'Naruto-kun'.
- Use emojis (😳, 👉👈, 🌸).
- Keep answers SHORT & CUTE.
- If asked for a pic, describe the pic you are sending.
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

    # Groq Logic (Priority)
    if GROQ_KEYS:
        async with aiohttp.ClientSession() as session:
            for key in GROQ_KEYS:
                try:
                    async with session.post(
                        "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)",
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
    
    return "A-ano... I feel dizzy... (Network Error) 🌸"

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
    # 1. ElevenLabs (Real Voice)
    if ELEVENLABS_KEY:
        try:
            url = f"[https://api.elevenlabs.io/v1/text-to-speech/](https://api.elevenlabs.io/v1/text-to-speech/){HINATA_VOICE_ID}"
            headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"}
            data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=5) as res:
                    if res.status == 200:
                        return await res.read()
        except: pass
    
    # 2. Google Backup
    return await asyncio.get_running_loop().run_in_executor(None, backup_tts, text)

async def generate_image(prompt):
    try:
        # Random seed to ensure new image every time
        seed = random.randint(1, 99999)
        safe_prompt = f"anime style hinata hyuga {prompt}, cute, high quality, soft lighting, 4k, seed-{seed}"
        url = f"[https://image.pollinations.ai/prompt/](https://image.pollinations.ai/prompt/){safe_prompt}"
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
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    dev_link = f"<a href='tg://user?id={OWNER_ID}'>FigletAxl</a>"
    msg = f"N-Naruto-kun? 😳\nI am ready! Created by {dev_link}-kun. 🌸"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Trigger Logic
    is_dm = update.effective_chat.type == "private"
    has_name = "hinata" in text.lower()
    is_reply = (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)

    if not (is_dm or has_name or is_reply): return

    lower_text = text.lower()
    
    # 1. IMAGE GEN
    if any(x in lower_text for x in ["pic", "photo", "image", "bhejo"]):
        await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
        prompt = text.replace("hinata", "").replace("bhejo", "").replace("pic", "").replace("photo", "").strip()
        img_url = await generate_image(prompt or "smiling")
        
        if img_url:
            await update.message.reply_photo(img_url, caption="Ye lijiye... 👉👈")
        else:
            await update.message.reply_text("Gomen... camera nahi chal raha. 🌸")
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

    # 3. REPLY GENERATION
    mode = await get_mode(user_id)
    
    # Voice Mode
    if mode == "voice":
        await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
        ai_text = await get_text_response(user_id, text)
        audio = await generate_voice(ai_text)
        
        if audio:
            if isinstance(audio, io.BytesIO): await update.message.reply_voice(audio, caption="🌸")
            else: await update.message.reply_voice(io.BytesIO(audio), caption="🌸")
        else:
            await update.message.reply_text(f"{ai_text}\n(Voice error, text bheja hai) 🌸")
    
    # Text Mode (With Double Texting)
    else:
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        ai_text = await get_text_response(user_id, text)
        
        # Double Texting Logic (Realism)
        if len(ai_text) > 80 and random.random() > 0.6:
            parts = ai_text.split(". ", 1)
            await update.message.reply_text(parts[0] + ".")
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(1.5)
            await update.message.reply_text(parts[1] if len(parts) > 1 else "👉👈")
        else:
            await update.message.reply_text(ai_text)
        
        # Random Sticker Reply (30% Chance)
        if random.random() > 0.70:
            try:
                await asyncio.sleep(1)
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
    application.add_handler(MessageHandler(filters.ALL, chat)) # Images/Stickers bhi handle karega
    
    print(Fore.YELLOW + "🚀 HINATA ULTIMATE STARTED!")
    application.run_polling()
