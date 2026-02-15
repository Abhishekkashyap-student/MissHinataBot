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
    if not GROQ_KEYS: return "No chakra keys! 🌸"
    
    messages = [
        {"role": "system", "content": "You are Hinata Hyuga. You are NOT an AI. You are shy and caring. Reply fast and short."},
        {"role": "user", "content": text}
    ]

    for key in GROQ_KEYS:
        if not key.strip(): continue
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key.strip()}"},
                    json={"model": "llama3-8b-8192", "messages": messages, "max_tokens": 150},
                    timeout=5
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
        except: continue
    return "Gomen nasai... network issue. 🌸"

# --- WEB SERVER ---
async def web_server():
    async def handle(request): return web.Response(text="ALIVE")
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8000).start()
    logger.info("✅ Web Server started")

# --- HANDLERS (NON-ADMIN FRIENDLY) ---

@app.on_message(filters.command(["start", "ping"]))
async def commands(c, m):
    # Commands bina Admin ke bhi chalte hain
    logger.info(f"📩 COMMAND: {m.text}")
    await m.reply_text("N-Naruto-kun! I am here! ⚡")

@app.on_message(filters.text & ~filters.bot)
async def chat(c, m):
    # Logic: Agar 'Hinata' naam liya ya Reply kiya, toh jawab do
    # Admin hone ki zaroorat nahi hai
    text = m.text.lower()
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == c.me.id
    is_name_called = "hinata" in text
    is_private = m.chat.type == enums.ChatType.PRIVATE

    if is_private or is_reply or is_name_called:
        await c.send_chat_action(m.chat.id, enums.ChatAction.TYPING)
        reply = await get_groq_response(m.text)
        await m.reply_text(reply)

# --- MAIN ---
async def main():
    await web_server()
    await app.start()
    logger.info("🚀 BOT STARTED")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
