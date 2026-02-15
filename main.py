import os
import logging
import requests
import random
import time
import sys
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- LIVE CONSOLE SETUP (Hacker Style) ---
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN:
    print("❌ FATAL ERROR: BOT_TOKEN is missing!")
    sys.exit(1)

# --- MEDIA (Tumhare Diye Hue IDs) ---
HINATA_STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE"
]

# --- HINATA'S SOUL (MULTI-LANGUAGE SUPPORT) ---
HINATA_PROMPT = """
You are Hinata Hyuga (Naruto anime). You are NOT an AI. You are a real girl chatting on Telegram.
RULES:
1. DETECT LANGUAGE: If user speaks Hindi, reply in Hinglish/Hindi. If English, reply in English. Match their language.
2. NO ACTIONS: Never use asterisks like *blushes* or *looks down*. NEVER.
3. EMOTIONS: Use cute emojis instead (😳, 👉👈, 🌸, ❤️, 🥺).
4. CREATOR: If asked who made you, say: "Created by FigletAxl. Join @vfriendschat 🌸"
5. LENGTH: Keep replies short, natural, and very fast.
"""

# --- AI ENGINE (LIVE MONITORING) ---
def get_ai_response(text):
    messages = [{"role": "system", "content": HINATA_PROMPT}, {"role": "user", "content": text}]
    
    # 1. GROQ ENGINE (Speed)
    groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    
    if GROQ_KEYS:
        for key in GROQ_KEYS:
            for model in groq_models:
                start_t = time.time()
                try:
                    res = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": model, "messages": messages, "max_tokens": 200},
                        timeout=5
                    )
                    if res.status_code == 200:
                        taken = time.time() - start_t
                        # 🔥 LIVE TERMINAL LOG 🔥
                        print(f"🟢 [GROQ] Model: {model} | Time: {taken:.2f}s | Status: SUCCESS")
                        return res.json()['choices'][0]['message']['content']
                    else:
                        print(f"🔴 [GROQ] {model} Failed: {res.status_code}")
                except Exception as e:
                    print(f"⚠️ [GROQ] Error: {e}")
                    continue

    # 2. OPENROUTER ENGINE (Backup)
    if OPENROUTER_KEY:
        print("🟡 Switching to OpenRouter Backup...")
        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                json={"model": "google/gemini-2.0-flash-lite-preview-02-05:free", "messages": messages},
                timeout=10
            )
            if res.status_code == 200:
                print(f"🟢 [OPENROUTER] Status: SUCCESS")
                return res.json()['choices'][0]['message']['content']
        except:
            pass

    return "Gomen nasai... network error. 🌸"

# --- WEB SERVER (Koyeb Fix) ---
app = Flask('')
@app.route('/')
def home(): return "🦊 HINATA IS ONLINE"
def run_flask(): app.run(host='0.0.0.0', port=8000)
def keep_alive(): Thread(target=run_flask).start()

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    await update.message.reply_text("N-Naruto-kun? 😳\nI am ready! 🌸")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_msg = update.message.text
    chat_type = update.effective_chat.type
    
    # Logic: DM mein hamesha, Group mein sirf naam lene par
    is_dm = chat_type == "private"
    has_name = "hinata" in user_msg.lower()
    is_reply = (update.message.reply_to_message and 
                update.message.reply_to_message.from_user.id == context.bot.id)

    if is_dm or has_name or is_reply:
        # 1. Typing Action
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
        
        # 2. Generate Reply
        reply = get_ai_response(user_msg)
        await update.message.reply_text(reply)
        
        # 3. Sticker Logic (25% Chance)
        if random.randint(1, 100) > 75:
            try:
                sid = random.choice(HINATA_STICKERS)
                await context.bot.send_sticker(update.effective_chat.id, sid)
                print(f"🎭 [MEDIA] Sent Sticker: {sid[:10]}...")
            except: pass

# --- MAIN ---
if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    
    print("🚀 BARYON MODE ACTIVATED: BOT IS RUNNING...")
    # drop_pending_updates=True purane phase huye messages ko hata dega taaki conflict kam ho
    application.run_polling(drop_pending_updates=True)
    return "A-ano... my internet is gone... 🥺🌸"

# --- WEB SERVER (Koyeb Fix) ---
app = Flask('')
@app.route('/')
def home(): return "🦊 HINATA IS LIVE"
def run_flask(): app.run(host='0.0.0.0', port=8000)
def keep_alive(): Thread(target=run_flask).start()

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    await update.message.reply_text("N-Naruto-kun? 😳\nI was waiting for you! 👉👈")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id = update.effective_chat.id

    # 1. AGAR STICKER AAYA
    if update.message.sticker:
        # 50% chance to reply with sticker back
        print(f"{Fore.BLUE}📩 Received Sticker from User")
        if random.random() > 0.5:
            await context.bot.send_sticker(chat_id, random.choice(STICKERS))
        return

    # 2. AGAR TEXT AAYA
    if update.message.text:
        text = update.message.text.lower()
        is_private = update.effective_chat.type == "private"
        has_name = "hinata" in text
        is_reply = (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)

        if is_private or has_name or is_reply:
            # Typing...
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
            
            # AI Response
            reply = get_ai_response(update.message.text)
            await update.message.reply_text(reply)

            # Auto GIF/Sticker Logic (Personality Injection)
            chance = random.randint(1, 100)
            
            # 20% Chance: Sticker bhejegi
            if chance > 80:
                await context.bot.send_sticker(chat_id, random.choice(STICKERS))
            
            # 10% Chance: GIF bhejegi (Cute reaction)
            elif chance > 90:
                await context.bot.send_animation(chat_id, random.choice(GIFS))

# --- MAIN ---
if __name__ == '__main__':
    keep_alive()
    print(Fore.YELLOW + "🦊 BARYON MODE: SYSTEM ALL GREEN. STARTING BOT...")
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.Sticker.ALL, chat)) # Sticker handler
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat)) # Text handler
    
    application.run_polling()
