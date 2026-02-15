import os
import asyncio
import aiohttp
import logging
from aiohttp import web
from pyrogram import Client, filters, idle, enums

# --- LOGGING ON (Sab kuch dikhega) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- VARIABLES ---
try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GROQ_KEYS = os.getenv("GROQ_API_KEY", "").split(",")
    print(f"✅ Variables Loaded: API_ID={API_ID}, Token=...{BOT_TOKEN[-5:]}")
except Exception as e:
    print(f"❌ Variable Error: {e}")
    exit(1)

# --- CLIENT ---
app = Client("miss_hinata", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- AI LOGIC ---
async def get_groq_response(text):
    if not GROQ_KEYS: return "No API Keys found!"
    
    messages = [
        {"role": "system", "content": "You are Hinata Hyuga. Reply shortly and cutely."},
        {"role": "user", "content": text}
    ]

    for key in GROQ_KEYS:
        if not key.strip(): continue
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key.strip()}"},
                    json={"model": "llama3-8b-8192", "messages": messages, "max_tokens": 100},
                    timeout=5
                ) as response:
                    if response.status == 200:
                        return (await response.json())['choices'][0]['message']['content']
        except: continue
    return "Network Error 🌸"

# --- WEB SERVER (Koyeb Fix) ---
async def web_server():
    async def handle(request): return web.Response(text="ALIVE")
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8000).start()
    print("✅ Web Server started on Port 8000")

# --- HANDLERS (SIMPLE) ---

@app.on_message(filters.command("start"))
async def start(c, m):
    print(f"📩 START COMMAND RECEIVED from {m.from_user.first_name}")
    await m.reply_text(f"N-Naruto-kun? I am connected! 🌸\nID: `{m.chat.id}`")

@app.on_message(filters.command("ping"))
async def ping(c, m):
    print("📩 PING COMMAND RECEIVED")
    await m.reply_text("⚡ Pong! Baryon Mode Active.")

# Catch-All Handler (Har text message par chalega)
@app.on_message(filters.text)
async def chat(c, m):
    print(f"📩 TEXT RECEIVED: {m.text} | Type: {m.chat.type}")
    
    # Typing dikhao
    await c.send_chat_action(m.chat.id, enums.ChatAction.TYPING)
    
    # Reply karo
    reply = await get_groq_response(m.text)
    await m.reply_text(reply)

# --- MAIN ---
async def main():
    await web_server()
    print("🔄 Starting Bot Client...")
    await app.start()
    print("🚀 BOT STARTED SUCCESSFULLY! GO CHECK TELEGRAM.")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
