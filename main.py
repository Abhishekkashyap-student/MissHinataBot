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
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_KEYS = os.getenv("GROQ_API_KEY", "").split(",")

app = Client("miss_hinata", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- WEB SERVER ---
async def web_server():
    async def handle(request): return web.Response(text="ALIVE")
    web_app = web.Application()
    web_app.router.add_get("/", handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8000).start()
    logger.info("✅ Web Server started")

# --- AI LOGIC ---
async def get_groq_response(text):
    if not GROQ_KEYS or not GROQ_KEYS[0]: return "Keys missing!"
    
    # Simple Prompt for Testing
    messages = [{"role": "user", "content": text}]

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
    return "Network Error"

# --- DEBUG HANDLER (SAB KUCH PAKDEGA) ---
@app.on_message()
async def debug_handler(client, message):
    # 1. Log to Console (Koyeb Logs mein dikhega)
    logger.info(f"📩 RECEIVED: {message.text} | FROM: {message.chat.id}")

    # 2. Typing Action (Proof ki bot zinda hai)
    await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)

    # 3. Simple Reply Logic
    if message.text:
        # Check Commands
        if message.text.startswith("/start"):
            await message.reply_text("✨ I am Alive Naruto-kun!")
        elif message.text.startswith("/ping"):
            await message.reply_text("⚡ Pong!")
        else:
            # AI Reply
            reply = await get_groq_response(message.text)
            await message.reply_text(reply)

# --- MAIN ---
async def main():
    await web_server()
    await app.start()
    logger.info("🚀 BOT STARTED - WAITING FOR MESSAGES")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
