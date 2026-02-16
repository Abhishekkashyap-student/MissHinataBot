import os
import logging
import requests
import random
import time
import sys
import psutil
import asyncio
import io
import re
from threading import Thread
from flask import Flask
from colorama import Fore, init
from gtts import gTTS
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from motor.motor_asyncio import AsyncIOMotorClient

# --- SETUP ---
init(autoreset=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION (ENV VARS) ---
TOKEN = os.getenv("BOT_TOKEN")
# Tumhara Database Direct Laga Diya (Backup ke liye)
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://axlbot:pass1234@alexamusiccluster.jxblrni.mongodb.net/alexamusic")
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")
HINATA_VOICE_ID = os.getenv("HINATA_VOICE_ID", "xz3UpnFf1JhWWawf9xUy") 
OWNER_ID = 8430369957
START_TIME = time.time()

if not TOKEN:
    print(Fore.RED + "❌ FATAL: BOT_TOKEN missing!")
    sys.exit(1)

# --- MONGODB CONNECTION ---
db_available = False
chat_collection = None
user_prefs = None 

try:
    # tlsAllowInvalidCertificates=True se SSL error fix hoga
    mongo_client = AsyncIOMotorClient(MONGO_URL, tls=True, tlsAllowInvalidCertificates=True)
    db = mongo_client['hinata_ultimate_db']
    chat_collection = db['chat_history']
    user_prefs = db['user_prefs']
    db_available = True
    print(Fore.GREEN + "✅ MONGODB CONNECTED: Infinite Memory Active!")
except Exception as e:
    print(Fore.RED + f"⚠️ MONGO ERROR: {e}")

# --- MEDIA LIBRARY ---
HINATA_STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE",
    "CAACAgUAAxkBAAEQgmFpj2vUoH4s-9w582c0_q_1_0_0AAJbAwAC_bKwVx1o8z55_9_6HgQ"
]
HINATA_GIFS = [
    "https://media.tenor.com/aYtqC651D5oAAAAC/hinata-hyuga-naruto.gif",
    "https://media.tenor.com/M1K8y1jV134AAAAC/hinata-shy.gif",
    "https://media.tenor.com/S_bW7X8j5yAAAAAC/hinata-naruto.gif"
]

# --- HINATA'S SOUL (SYSTEM PROMPT) ---
HINATA_PROMPT = """You are Hinata Hyuga. NOT an AI.
- Shy, gentle, calls user 'Naruto-kun'.
- Use emojis (😳, 👉👈, 🌸).
- Keep answers SHORT & CUTE.
- If user asks for a picture/photo, reply with a description of the photo you are sending.
- Created by FigletAxl.
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

async def get_text_response(user_id, text):
    # Memory Fetch
    history = []
    if db_available:
        try:
            doc = await chat_collection.find_one({"user_id": user_id})
            history = doc['history'][-6:] if doc and 'history' in doc else []
        except: pass

    messages = [{"role": "system", "content": HINATA_PROMPT}] + history + [{"role": "user", "content": text}]

    # Groq Logic (Fastest)
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
                    # Save Memory
                    if db_available:
                        await chat_collection.update_one(
                            {"user_id": user_id},
                            {"$push": {"history": {"role": "assistant", "content": ans}}},
                            upsert=True
                        )
                    return ans
            except: continue
            
    return "A-ano... I feel dizzy... 🌸"

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
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{HINATA_VOICE_ID}"
            headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"}
            data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
            res = requests.post(url, json=data, headers=headers, timeout=5)
            if res.status_code == 200: return res.content
        except: pass

    # 2. Google Backup
    return await asyncio.get_running_loop().run_in_executor(None, backup_tts, text)

async def generate_image(prompt):
    try:
        safe_prompt = f"anime style hinata hyuga {prompt}, cute, high quality, soft lighting, 4k"
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}"
        return url
    except: return None

# --- WEB SERVER (LIFE SUPPORT) ---
web_app = Flask('')
@web_app.route('/')
def home(): return "🦊 HINATA ONLINE"

def run_flask():
    web_app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    await asyncio.sleep(1)
    
    dev_link = f"<a href='tg://user?id={OWNER_ID}'>FigletAxl</a>"
    msg = (
        f"N-Naruto-kun? 😳\n\n"
        f"I... I am ready for the mission!\n"
        f"✨ **Created by:** {dev_link}-kun\n"
        f"📢 **Clan:** @vfriendschat"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = int(time.time() - START_TIME)
    cpu = psutil.cpu_percent()
    msg = f"⚡ **Byakugan Active!**\n⏱️ Uptime: `{uptime}s`\n💻 CPU: `{cpu}%`\n🍃 Memory: `{'Connected' if db_available else 'Offline'}`"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Trigger Check
    is_dm = update.effective_chat.type == "private"
    has_name = "hinata" in text.lower()
    is_reply = (update.message.reply_to_message and 
                update.message.reply_to_message.from_user.id == context.bot.id)

    if not (is_dm or has_name or is_reply): return

    lower_text = text.lower()
    
    # 1. IMAGE GEN
    if "pic" in lower_text or "photo" in lower_text or "image" in lower_text:
        await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
        prompt = text.replace("hinata", "").replace("bhejo", "").replace("pic", "").strip()
        img_url = await generate_image(prompt or "smiling")
        if img_url:
            await update.message.reply_photo(img_url, caption="Ye lijiye... 👉👈")
        return

    # 2. VOICE MODE
    if "voice chat" in lower_text:
        await set_mode(user_id, "voice")
        await update.message.reply_text("Theek hai! Ab main bolungi. 🎤🌸")
        return
    if "text chat" in lower_text:
        await set_mode(user_id, "text")
        await update.message.reply_text("Wapas text par aa gayi! 📝")
        return

    # 3. RESPONSE LOGIC
    mode = await get_mode(user_id)
    
    if mode == "voice":
        await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
        ai_text = await get_text_response(user_id, text)
        audio = await generate_voice(ai_text)
        if audio:
            await update.message.reply_voice(audio, caption="🌸")
        else:
            await update.message.reply_text(ai_text)
    else:
        # REALISTIC CHAT (Double Texting Logic)
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        ai_text = await get_text_response(user_id, text)
        
        # Agar text bada hai ya Hinata excited hai, toh kabhi kabhi 2 parts mein bhejegi
        if len(ai_text) > 100 and random.random() > 0.7:
            parts = ai_text.split(". ", 1)
            if len(parts) > 1:
                await update.message.reply_text(parts[0] + ".")
                await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
                await asyncio.sleep(1.5) # Human pause
                await update.message.reply_text(parts[1])
            else:
                await update.message.reply_text(ai_text)
        else:
            await update.message.reply_text(ai_text)

        # 4. RANDOM MEDIA (GIF/STICKER)
        if random.random() > 0.85:
            try:
                await asyncio.sleep(1)
                if random.choice([True, False]):
                    await context.bot.send_sticker(chat_id, random.choice(HINATA_STICKERS))
                else:
                    await context.bot.send_animation(chat_id, random.choice(HINATA_GIFS))
            except: pass

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    keep_alive() # Fake Server
    
    # PTB V20+ Setup
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('ping', ping))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    
    print(Fore.YELLOW + "🚀 HINATA ULTIMATE IS LIVE!")
    application.run_polling()
