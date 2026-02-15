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
# Hinata Voice ID (ElevenLabs se milegi). Agar nahi hai toh default female ID use hogi.
HINATA_VOICE_ID = os.getenv("HINATA_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") 
OWNER_ID = 8430369957
START_TIME = time.time()

if not TOKEN:
    print(Fore.RED + "❌ FATAL ERROR: BOT_TOKEN missing!")
    sys.exit(1)

# --- MONGODB (MEMORY FIX) ---
db_available = False
chat_collection = None
user_prefs = None # Voice/Text mode store karne ke liye

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
    # Check if user wants Voice or Text
    if db_available:
        doc = await user_prefs.find_one({"user_id": user_id})
        return doc.get("mode", "text") if doc else "text"
    return "text"

async def set_mode(user_id, mode):
    if db_available:
        await user_prefs.update_one(
            {"user_id": user_id}, {"$set": {"mode": mode}}, upsert=True
        )

# --- AI GENERATION ---
async def get_text_response(user_id, text):
    # Memory Fetch
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
                    # Save Memory
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
    # ElevenLabs TTS
    if not ELEVENLABS_KEY: return None
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{HINATA_VOICE_ID}"
        headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"}
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
        res = requests.post(url, json=data, headers=headers)
        if res.status_code == 200:
            return res.content
    except: pass
    return None

async def generate_image(prompt):
    # Pollinations AI (Free & Unlimited)
    try:
        safe_prompt = f"anime style hinata hyuga {prompt}, high quality, cute, soft lighting"
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}"
        return url
    except: return None

# --- WEB SERVER ---
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
    
    # Check Trigger (DM or Mention)
    is_dm = update.effective_chat.type == "private"
    has_name = "hinata" in text.lower()
    is_reply = (update.message.reply_to_message and 
                update.message.reply_to_message.from_user.id == context.bot.id)

    if not (is_dm or has_name or is_reply): return

    # --- SPECIAL COMMANDS (Natural Language) ---
    lower_text = text.lower()
    
    # 1. Voice Mode Switch
    if "voice chat" in lower_text and "baat" in lower_text:
        await set_mode(user_id, "voice")
        await update.message.reply_text("Theek hai Naruto-kun! Ab main bol kar jawab dungi. 🎤🌸")
        return
    
    # 2. Text Mode Switch
    if "text chat" in lower_text and "baat" in lower_text:
        await set_mode(user_id, "text")
        await update.message.reply_text("Okay! Wapas text par aa gayi. 📝🌸")
        return
        
    # 3. Image Generation (Selfie Logic)
    if "pic" in lower_text or "photo" in lower_text or "image" in lower_text:
        await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
        prompt = text.replace("hinata", "").replace("bhejo", "").replace("pic", "").strip()
        img_url = await generate_image(prompt or "smiling")
        if img_url:
            await update.message.reply_photo(img_url, caption="Ye lijiye... 👉👈")
            return

    # --- MAIN REPLY LOGIC ---
    mode = await get_mode(user_id)
    
    if mode == "voice":
        await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
        ai_text = await get_text_response(user_id, text)
        audio = await generate_voice(ai_text)
        if audio:
            await update.message.reply_voice(audio, caption="🌸")
        else:
            await update.message.reply_text(ai_text) # Fallback to text
    else:
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        ai_text = await get_text_response(user_id, text)
        await update.message.reply_text(ai_text)
        
        # Random GIF/Sticker
        if random.random() > 0.85:
            try:
                if random.choice([True, False]):
                    await context.bot.send_sticker(chat_id, random.choice(HINATA_STICKERS))
                else:
                    await context.bot.send_animation(chat_id, random.choice(HINATA_GIFS))
            except: pass

if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.ALL, chat))
    print(Fore.YELLOW + "🚀 HINATA ULTIMATE (VOICE + IMAGE) ACTIVE!")
    application.run_polling()def home(): return "🦊 HINATA LIVE"
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
