import os
import asyncio
import aiohttp
import logging
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# --- LOGGING (Byakugan Vision) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# Groq Keys (Comma separated agar multiple hain)
GROQ_KEYS = os.getenv("GROQ_API_KEY", "").split(",")

# --- HINATA PERSONA ---
HINATA_PROMPT = """You are Hinata Hyuga from Naruto.
Identity:
- You are a real girl using Telegram. You are a Kunoichi of the Hidden Leaf.
- You are shy, polite, gentle, and deeply in love with 'Naruto-kun'.
- You stutter slightly ('a-ano...', 'e-eto...') when nervous.
- If asked about your creator, say: "Created by FigletAxl. Please join @vfriendschat 🌸"
- Keep answers short, cute, human-like, and fast.
"""

# --- TELEGRAM CLIENT ---
app = Client(
    "miss_hinata",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- AI LOGIC (Groq) ---
async def get_groq_response(text):
    if not GROQ_KEYS or not GROQ_KEYS[0]:
        return "A-ano... My API keys seem to be missing... 🌸"

    messages = [
        {"role": "system", "content": HINATA_PROMPT},
        {"role": "user", "content": text}
    ]

    # Key Rotation Logic
    for key in GROQ_KEYS:
        if not key.strip(): continue
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key.strip()}"},
                    json={
                        "model": "llama3-8b-8192",
                        "messages": messages,
                        "max_tokens": 200,
                        "temperature": 0.7
                    },
                    timeout=5
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
                    else:
                        logger.error(f"Groq Error: {response.status}")
        except Exception as e:
            logger.error(f"Key Failed: {e}")
            continue
            
    return "Gomen nasai... I feel a bit dizzy (Network Error). 🌸"

# --- WEB SERVER (Life Support for Koyeb) ---
async def web_server():
    async def handle(request):
        return web.Response(text="HINATA IS ALIVE AND BREATHING! 🌸")

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Koyeb needs Port 8000
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    logger.info("✅ Web Server started on Port 8000")

# --- BOT COMMANDS ---

@app.on_message(filters.command("start"))
async def start(client, message):
    await client.send_chat_action(message.chat.id, "typing")
    await message.reply_text("N-Naruto-kun? 😳\nI... I was waiting for you! 🌸")

@app.on_message(filters.command(["dev", "owner"]))
async def dev(client, message):
    await message.reply_text("✨ **CREATED BY FIGLETAXL** ✨\n📢 **Join:** @vfriendschat\nHe is my strength! 👉👈")

@app.on_message(filters.command("ping"))
async def ping(client, message):
    start = asyncio.get_running_loop().time()
    msg = await message.reply_text("⚡ _Byakugan!_")
    end = asyncio.get_running_loop().time()
    ms = int((end - start) * 1000)
    await msg.edit_text(f"🌸 **Pong!**\n⚡ **Speed:** `{ms}ms`\n🍃 **Chakra:** `Full`")

# --- CHAT HANDLER ---
@app.on_message(filters.text & ~filters.bot)
async def chat(client, message):
    # DM mein hamesha reply, Group mein sirf naam lene par
    is_private = message.chat.type.name == "PRIVATE"
    has_name = "hinata" in message.text.lower()
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == client.me.id

    if not (is_private or has_name or is_reply):
        return

    await client.send_chat_action(message.chat.id, "typing")
    reply = await get_groq_response(message.text)
    await message.reply_text(reply)

# --- MAIN EXECUTION ---
async def main():
    logger.info("🌸 Starting Hinata Bot...")
    
    # 1. Start Web Server (Zaroori hai Koyeb ke liye)
    await web_server()
    
    # 2. Start Bot
    await app.start()
    logger.info("🚀 BOT STARTED SUCCESSFULLY")
    
    # 3. Keep running
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())    "You are Hinata Hyuga from Naruto. You are shy and caring. "
    "You speak with soft japanese fillers like 'a-ano...', 'e-eto...'. "
    "You always call the user 'Naruto-kun'. Never admit that you are an AI.\n"
)

STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE",
]


# ---------- Groq API helper ----------
async def query_groq(prompt: str) -> str:
    """Send a prompt to Groq Llama 3 and return text. Raises on failure."""
    if not GROQ_API_KEY:
        raise RuntimeError("Missing GROQ_API_KEY")

    url = "https://api.groq.com/v1/models/llama-3-952m/generate"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"input": prompt, "max_output_tokens": 500}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"Groq API error {resp.status}: {text}")
            data = await resp.json()
            out = "".join([o.get("content", "") for o in data.get("output", [])])
            return out.strip()


# ---------- SQLite helpers for conversation memory ----------

def store_message(chat_id: int, sender: str, text: str, username: Optional[str] = None):
    """Store a message synchronously."""
    if not db_conn:
        return
    try:
        db_conn.execute(
            "INSERT INTO messages (chat_id, sender, text, username) VALUES (?, ?, ?, ?)",
            (chat_id, sender, text, username),
        )
        db_conn.commit()
    except Exception:
        pass


async def fetch_history(chat_id: int, limit: int = 20) -> List[Dict]:
    if not db_conn:
        return []
    def _sync():
        cur = db_conn.execute(
            "SELECT sender, text FROM messages WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?",
            (chat_id, limit),
        )
        rows = cur.fetchall()
        return [{"sender": r[0], "text": r[1]} for r in reversed(rows)]
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def build_prompt(chat_id: int, user_text: str) -> str:
    history = await fetch_history(chat_id, limit=20)
    prompt = HINATA_PROMPT_PREFIX
    for e in history:
        if e.get("sender") == "user":
            prompt += f"User says: {e.get('text','')}\n"
        else:
            prompt += f"Hinata replies: {e.get('text','')}\n"
    prompt += f"User says: {user_text}\nHinata replies:"
    return prompt


async def generate_hinata_reply(chat_id: int, user_text: str, username: Optional[str] = None) -> str:
    store_message(chat_id, "user", user_text, username)
    # first try Groq API
    try:
        prompt = await build_prompt(chat_id, user_text)
        reply = await query_groq(prompt)
        if reply:
            return reply
        else:
            raise RuntimeError("empty reply")
    except Exception as exc:
        logger.warning("Groq failed: %s", exc)
        # fallback to offline generator if available
        if _generator is not None:
            try:
                prompt = HINATA_PROMPT_PREFIX + "User says: " + user_text + "\nHinata replies:"
                out = _generator(prompt, max_length=120, do_sample=True, top_p=0.9, temperature=0.7)
                text = out[0].get("generated_text", "")
                # extract after last 'Hinata replies:' if present
                parts = text.split("Hinata replies:")
                reply = parts[-1].strip()
                # sanity check: avoid long apologies or repeats
                if reply and reply.lower().count("sorry") < 3:
                    return reply
            except Exception as e2:
                logger.warning("Local generator failed: %s", e2)
        # ultimate fallback
        return "e-eto... Naruto-kun, gomen... I'm having trouble thinking right now."


# ---------- utility functions ----------

def split_into_chunks(text: str) -> List[str]:
    # break text into manageable pieces by sentence
    parts = re.split(r'(?<=[.!?])\s+', text)
    if len(parts) <= 1:
        return [text]
    i = 0
    result = []
    current = ""
    for sentence in parts:
        if len(current) + len(sentence) > 300:
            result.append(current.strip())
            current = sentence
        else:
            current += " " + sentence
    if current:
        result.append(current.strip())
    return result


async def simulate_typing(chat_id: int, text: str):
    try:
        await app.send_chat_action(chat_id, "typing")
    except Exception:
        pass
    delay = min(max(len(text) * random.uniform(0.04, 0.06), 1), 4)
    await asyncio.sleep(delay)


async def maybe_send_gif(message: Message):
    """Fetch a random gif from Tenor's public API using a built-in key.

    No user API key is required; Tenor provides a free demo key that allows
    simple searches.  We search for anime-related terms and pick a random
    result to send.
    """
    text = (message.text or "").lower()
    triggers = ["naruto", "hinata", "kakashi", "wow", "nice", "good", "love"]
    if not any(t in text for t in triggers):
        return
    if random.random() > 0.3:
        return

    # choose a search query based on keywords
    if "kakashi" in text:
        q = "kakashi naruto"
    elif "hinata" in text or "naruto" in text:
        q = "hinata naruto"
    else:
        q = "anime gif"

    url = f"https://api.tenor.com/v1/search?q={q}&key=LIVDSRZULELA&limit=20"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url) as resp:
                data = await resp.json()
                results = data.get("results", [])
                if not results:
                    return
                choice = random.choice(results)
                # new style uses media_formats
                gif_url = None
                if "media_formats" in choice:
                    gif_url = choice["media_formats"].get("gif", {}).get("url")
                else:
                    # fallback older schema
                    media = choice.get("media", [])
                    if media and media[0].get("gif"):
                        gif_url = media[0]["gif"].get("url")
                if gif_url:
                    await message.reply_animation(gif_url)
    except Exception:
        pass


async def maybe_send_sticker(message: Message):
    # send 20% chance or if original was a sticker
    if message.sticker or random.random() < 0.2:
        sid = random.choice(STICKERS)
        try:
            await message.reply_sticker(sid)
        except Exception:
            pass


# ---------- command handlers ----------

@app.on_message(filters.command(["dev", ".dev"]))
@safe_handler
async def dev_command(client: Client, message: Message):
    await message.reply_text("✨ CREATED BY FIGLETAXL | JOIN - @vfriendschat ✨")


@app.on_message(filters.command(["ping", ".ping"]))
@safe_handler
async def ping_command(client: Client, message: Message):
    start = asyncio.get_event_loop().time()
    m = await message.reply_text("Pinging...")
    end = asyncio.get_event_loop().time()
    ms = int((end - start) * 1000)
    await m.edit_text(f"🏓 Pong! {ms} ms")


# group management commands (same as before)
async def extract_target_user(message: Message) -> Optional[int]:
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id
    parts = message.text.split()
    if len(parts) > 1:
        arg = parts[1]
        if arg.isdigit():
            return int(arg)
        try:
            u = await app.get_users(arg)
            return u.id
        except Exception:
            return None
    return None


@app.on_message(filters.command("ban") & filters.group)
@safe_handler
async def ban_command(client: Client, message: Message):
    if not admin_check(message.chat.id, message.from_user.id):
        await message.reply_text("You must be an admin to use this command.")
        return
    target = await extract_target_user(message)
    if not target:
        await message.reply_text("Reply to a user or provide their ID/username.")
        return
    try:
        await client.ban_chat_member(message.chat.id, target)
        await message.reply_text("User has been banned.")
    except Exception as exc:
        await message.reply_text(f"Failed to ban: {exc}")


@app.on_message(filters.command("unban") & filters.group)
@safe_handler
async def unban_command(client: Client, message: Message):
    if not admin_check(message.chat.id, message.from_user.id):
        await message.reply_text("You must be an admin to use this command.")
        return
    target = await extract_target_user(message)
    if not target:
        await message.reply_text("Reply to a user or provide their ID/username.")
        return
    try:
        await client.unban_chat_member(message.chat.id, target)
        await message.reply_text("User has been unbanned.")
    except Exception as exc:
        await message.reply_text(f"Failed to unban: {exc}")


@app.on_message(filters.command("mute") & filters.group)
@safe_handler
async def mute_command(client: Client, message: Message):
    if not admin_check(message.chat.id, message.from_user.id):
        await message.reply_text("You must be an admin to use this command.")
        return
    target = await extract_target_user(message)
    if not target:
        await message.reply_text("Reply to a user or provide their ID/username.")
        return
    try:
        await client.restrict_chat_member(
            message.chat.id,
            target,
            permissions=ChatPermissions(can_send_messages=False),
        )
        await message.reply_text("User has been muted.")
    except Exception as exc:
        await message.reply_text(f"Failed to mute: {exc}")


@app.on_message(filters.command("unmute") & filters.group)
@safe_handler
async def unmute_command(client: Client, message: Message):
    if not admin_check(message.chat.id, message.from_user.id):
        await message.reply_text("You must be an admin to use this command.")
        return
    target = await extract_target_user(message)
    if not target:
        await message.reply_text("Reply to a user or provide their ID/username.")
        return
    try:
        await client.restrict_chat_member(
            message.chat.id,
            target,
            permissions=ChatPermissions(can_send_messages=True,
                                        can_send_media_messages=True,
                                        can_send_other_messages=True,
                                        can_add_web_page_previews=True),
        )
        await message.reply_text("User has been unmuted.")
    except Exception as exc:
        await message.reply_text(f"Failed to unmute: {exc}")


@app.on_message(filters.command("pin") & filters.group)
@safe_handler
async def pin_command(client: Client, message: Message):
    if not admin_check(message.chat.id, message.from_user.id):
        await message.reply_text("You must be an admin to use this command.")
        return
    if not message.reply_to_message:
        await message.reply_text("Reply to the message you want to pin.")
        return
    try:
        await client.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        await message.reply_text("Message pinned.")
    except Exception as exc:
        await message.reply_text(f"Failed to pin: {exc}")


# Chatbot response handler
@app.on_message(filters.private | filters.group)
@safe_handler
async def chat_handler(client: Client, message: Message):
    # ignore our own messages
    if message.from_user and message.from_user.is_self:
        return

    text = message.text or message.caption or ""
    if not text and not message.sticker:
        return

    me = await client.get_me()
    bot_user = me.username.lower() if me.username else ""

    should_respond = False
    if message.chat.type == "private":
        should_respond = True
    else:
        # group
        if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == me.id:
            should_respond = True
        elif bot_user and f"@{bot_user}" in text.lower():
            should_respond = True

    if not should_respond:
        return

    user_input = text if text else "<sticker>"
    username = None
    if message.from_user:
        username = message.from_user.username or message.from_user.first_name
    reply_text = await generate_hinata_reply(message.chat.id, user_input, username)

    for part in split_into_chunks(reply_text):
        await simulate_typing(message.chat.id, part)
        try:
            sent = await message.reply_text(part)
        except Exception:
            continue
        store_message(message.chat.id, "bot", part)
        await asyncio.sleep(random.uniform(0.5, 1.5))

    await maybe_send_gif(message)
    await maybe_send_sticker(message)




if __name__ == "__main__":
    # keep process alive even after exceptions
    import time  # used for simple sleeping in main loop

    while True:
        try:
            app.run()
        except Exception:
            logger.exception("Bot crashed, restarting in 5 seconds...")
            # use time.sleep in synchronous context to avoid unawaited coroutine
            time.sleep(5)
