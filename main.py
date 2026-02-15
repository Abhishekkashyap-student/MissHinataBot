import os
import asyncio
import aiohttp
import logging
from aiohttp import web
from pyrogram import Client, filters, idle

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_KEYS = os.getenv("GROQ_API_KEY", "").split(",")

# --- HINATA PERSONA ---
HINATA_PROMPT = """You are Hinata Hyuga from Naruto.
Identity:
- You are a real girl using Telegram.
- You are shy, polite, gentle, and deeply caring.
- You stutter slightly ('a-ano...', 'e-eto...') when nervous.
- If asked about creator: "Created by FigletAxl. Join @vfriendschat 🌸"
- Keep answers short and cute.
"""

app = Client("miss_hinata", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- AI LOGIC ---
async def get_groq_response(text):
    if not GROQ_KEYS or not GROQ_KEYS[0]:
        return "A-ano... keys missing... 🌸"

    messages = [{"role": "system", "content": HINATA_PROMPT}, {"role": "user", "content": text}]

    for key in GROQ_KEYS:
        if not key.strip(): continue
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key.strip()}"},
                    json={"model": "llama3-8b-8192", "messages": messages, "temperature": 0.7, "max_tokens": 200},
                    timeout=5
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
        except: continue
    return "Gomen nasai... network error. 🌸"

# --- WEB SERVER (KOYEB LIFE SUPPORT) ---
async def web_server():
    async def handle(request):
        return web.Response(text="HINATA IS ALIVE!")
    
    # Port 8000 par server chalega
    web_app = web.Application()
    web_app.router.add_get("/", handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    logger.info("✅ Web Server started on Port 8000")

# --- HANDLERS ---
@app.on_message(filters.command("start"))
async def start(c, m):
    await m.reply_text("N-Naruto-kun? 😳\nI am ready! 🌸")

@app.on_message(filters.command("ping"))
async def ping(c, m):
    await m.reply_text("⚡ _Byakugan!_ Pong!")

@app.on_message(filters.text & ~filters.bot)
async def chat(c, m):
    is_private = m.chat.type.name == "PRIVATE"
    has_name = "hinata" in m.text.lower()
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == c.me.id
    
    if is_private or has_name or is_reply:
        await c.send_chat_action(m.chat.id, "typing")
        reply = await get_groq_response(m.text)
        await m.reply_text(reply)

# --- MAIN ---
async def main():
    await web_server() # Start fake server first
    await app.start()  # Then start bot
    logger.info("🚀 BOT STARTED")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
