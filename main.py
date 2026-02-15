import os
import asyncio
import aiohttp
import logging
from aiohttp import web
from pyrogram import Client, filters, idle, enums

# --- LOGGING ON ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GROQ_KEYS = os.getenv("GROQ_API_KEY", "").split(",")
except:
    logger.error("❌ VARS MISSING")
    exit(1)

app = Client("miss_hinata", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- AI LOGIC ---
async def get_groq_response(text):
    if not GROQ_KEYS: return "No keys! 🌸"
    
    messages = [{"role": "user", "content": text}] # Simple prompt for speed

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
                        data = await response.json()
                        return data['choices'][0]['message']['content']
        except: continue
    return "Error 🌸"

# --- WEB SERVER ---
async def web_server():
    async def handle(request): return web.Response(text="ALIVE")
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8000).start()
    logger.info("✅ Web Server started")

# --- ULTIMATE HANDLER (BINA FILTER KE) ---
# Ye handler har tarah ke message ko pakdega
@app.on_message() 
async def chat(c, m):
    # Agar message text nahi hai (photo/video), toh ignore karo
    if not m.text: return

    # Console mein print karo taaki pata chale message aaya
    logger.info(f"📩 MSG from {m.chat.title or m.chat.first_name}: {m.text}")

    # Logic: 
    # 1. Agar Private chat hai
    # 2. Agar Group mein 'Hinata' bola gaya
    # 3. Agar Message '/start' ya '/ping' se shuru hota hai
    
    text = m.text.lower()
    is_private = m.chat.type == enums.ChatType.PRIVATE
    is_call = "hinata" in text
    is_command = text.startswith("/") or text.startswith(".")

    if is_private or is_call or is_command:
        # Typing dikhao (Proof ki bot ne suna)
        await c.send_chat_action(m.chat.id, enums.ChatAction.TYPING)
        
        # Jawab do
        if is_command:
            await m.reply_text("N-Naruto-kun! I am here! ⚡")
        else:
            reply = await get_groq_response(m.text)
            await m.reply_text(reply)

# --- MAIN ---
async def main():
    await web_server()
    await app.start()
    logger.info("🚀 BOT STARTED - WAITING FOR MESSAGES")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
