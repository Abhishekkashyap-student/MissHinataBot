import os
import sys
import logging
import random
import asyncio
import json
import datetime
import re
from typing import Optional, List, Dict

import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions

# built-in SQLite for conversation memory
import sqlite3

# optional local model for offline/backup responses
try:
    from transformers import pipeline
    _local_generator = pipeline("text-generation", model="gpt2")
except Exception:
    _local_generator = None

# ---------- environment variables ----------
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

if not API_ID or not API_HASH or not BOT_TOKEN:
    logging.critical("API_ID, API_HASH and BOT_TOKEN must be set in environment")
    sys.exit(1)

# ---------- logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------- initialize SQLite (chat history) ----------
db_conn: Optional[sqlite3.Connection] = None

def init_db(path: str = "data.db") -> sqlite3.Connection:
    # allow access from different threads (async executor threads)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            sender TEXT,
            text TEXT,
            username TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn

try:
    db_conn = init_db()
    logger.info("SQLite database initialized for conversation memory")
except Exception as e:
    logger.warning("Could not initialize SQLite DB: %s", e)
    db_conn = None

# ---------- Telegram client ----------
app = Client(
    "miss_hinata",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode="html",
)


# ------- utility functions for error wrapping -------

def admin_check(chat_id: int, user_id: int) -> bool:
    """Return True if ``user_id`` is admin or creator in ``chat_id``.
    Silence any exceptions and return False on failure. Useful for command guards.
    """
    try:
        member = app.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


# decorator to catch and log exceptions inside handlers
def safe_handler(func):
    async def wrapper(client, message: Message):
        try:
            await func(client, message)
        except Exception:
            logger.exception("Exception in handler %s", func.__name__)
    return wrapper


# ------- persona and sticker constants -------

HINATA_PROMPT_PREFIX = (
    "You are Hinata Hyuga from Naruto. You are shy and caring. "
    "You speak with soft japanese fillers like 'a-ano...', 'e-eto...'. "
    "You always call the user 'Naruto-kun'. Never admit that you are an AI.\n"
)

STICKERS = [
    "CAACAgUAAxkBAAEQgltpj2uaFvRFMs_ACV5pQrqBvnKWoQAC2QMAAvmysFdnPHJXLMM8TjoE",
    "CAACAgUAAxkBAAEQgl1pj2u6CJJq6jC-kXYHM9fvpJ5ygAACXgUAAov2IVf0ZtG-JNnfFToE",
]


# ---------- Groq API helper ----------
async def query_groq(prompt: str) -> str:
    """Try Groq first; if unavailable or fails, fall back to local generator.

    The local model uses GPT-2 via transformers and requires no API key,
    providing unlimited offline responses. This keeps the bot alive even if
    remote service limits are reached.
    """
    # attempt remote
    if GROQ_API_KEY:
        try:
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
        except Exception:
            # log but continue to local fallback
            logger.warning("Groq call failed, falling back to local model")
    # local fallback
    if _local_generator:
        def sync_gen():
            try:
                res = _local_generator(prompt, max_length=200, num_return_sequences=1)
                return res[0]["generated_text"]
            except Exception:
                return ""
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, sync_gen)
        if text:
            return text
    raise RuntimeError("No available AI model")


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
    try:
        prompt = await build_prompt(chat_id, user_text)
        reply = await query_groq(prompt)
        if not reply:
            raise RuntimeError("empty reply")
        return reply
    except Exception:
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
    while True:
        try:
            app.run()
        except Exception:
            logger.exception("Bot crashed, restarting in 5 seconds...")
            asyncio.sleep(5)
