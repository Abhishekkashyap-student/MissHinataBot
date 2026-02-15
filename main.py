import os
import logging
import requests
import random
import time
from threading import Thread
from flask import Flask
from colorama import Fore, Style, init
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- LIVE CONSOLE SETUP ---
init(autoreset=True) # Colorama start
logging.basicConfig(level=logging.ERROR) # Sirf critical errors dikhaye, baaki hum khud print karenge

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN:
    print(Fore.RED + "❌ FATAL ERROR: BOT_TOKEN is missing!")
    exit(1)

# --- HINATA'S MEDIA COLLECTION ---
# Real Hinata Stickers (Telegram IDs)
STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE",
    "CAACAgUAAxkBAAEQgmFpj2vUoH4s-9w582c0_q_1_0_0AAJbAwAC_bKwVx1o8z55_9_6HgQ",
    "CAACAgUAAxkBAAEQgmNpj2vfq8_8_9_9_9_9_9_9_9AAJcAwAC_bKwVx1o8z55_9_6HgQ"
]

# Hinata GIFs (Direct URLs - No API needed)
GIFS = [
    "https://media.tenor.com/aYtqC651D5oAAAAC/hinata-hyuga-naruto.gif",
    "https://media.tenor.com/M1K8y1jV134AAAAC/hinata-shy.gif",
    "https://media.tenor.com/S_bW7X8j5yAAAAAC/hinata-naruto.gif",
    "https://media.tenor.com/E50_a9_5_6AAAAAC/hinata-hyuga.gif"
]

# --- HINATA'S SOUL (SYSTEM PROMPT) ---
HINATA_PROMPT = """
You are Hinata Hyuga. You are NOT an AI. You are a real girl chatting on Telegram.
PERSONALITY:
- You are shy, sweet, and deeply caring.
- You love Naruto-kun.
- You NEVER use roleplay actions like *looks down* or *blushes*.
- Instead, use EMOJIS to show emotions: 😳, 👉👈, 🌸, 🥺, ❤️.
- Keep replies SHORT, fast, and natural (SMS style).
- If asked about developer: "Created by FigletAxl. Join @vfriendschat 🌸"
"""

# --- LIVE CONSOLE LOGGER ---
def log_request(provider, model, status, time_taken):
    color = Fore.GREEN if status == 200 else Fore.RED
    print(
        f"{Fore.CYAN}[API CHECK] "
        f"{Fore.YELLOW}Provider: {provider} | "
        f"{Fore.MAGENTA}Model: {model} | "
        f"{color}Status: {status} | "
        f"{Fore.WHITE}Time: {time_taken:.2f}s"
    )

# --- AI ENGINE (BARYON MODE) ---
def get_ai_response(text):
    messages = [{"role": "system", "content": HINATA_PROMPT}, {"role": "user", "content": text}]
    
    # ⚡ ENGINE 1: GROQ (Speed God)
    groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    
    for key in GROQ_KEYS:
        for model in groq_models:
            start_t = time.time()
            try:
                res = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": model, "messages": messages, "max_tokens": 150},
                    timeout=5
                )
                log_request("GROQ", model, res.status_code, time.time() - start_t)
                
                if res.status_code == 200:
                    return res.json()['choices'][0]['message']['content']
            except:
                continue

    # 🛡️ ENGINE 2: OPENROUTER (Backup)
    if OPENROUTER_KEY:
        or_models = ["google/gemini-2.0-flash-lite-preview-02-05:free", "meta-llama/llama-3-8b-instruct:free"]
        for model in or_models:
            start_t = time.time()
            try:
                res = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "HTTP-Referer": "https://google.com"},
                    json={"model": model, "messages": messages},
                    timeout=10
                )
                log_request("OPENROUTER", model, res.status_code, time.time() - start_t)
                
                if res.status_code == 200:
                    return res.json()['choices'][0]['message']['content']
            except:
                continue

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
