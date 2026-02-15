# Miss Hinata Bot

This repository contains a production-ready asynchronous Telegram bot implementation using Pyrogram. The bot embodies the persona of Hinata Hyuga from *Naruto* and provides AI-generated responses via the Groq API.

## Features

- **AI Chatbot** in private and group chats with a shy Hinata personality
- **Group management commands**: `/ban`, `/unban`, `/mute`, `/unmute`, `/pin` (admins only)
- `/dev` and `/ping` system commands
- Global error handling to prevent crashes
- Optional MongoDB support via `MONGO_URL`

## Environment Variables

Set the following variables before running:

- `API_ID`, `API_HASH` (from my.telegram.org)
- `BOT_TOKEN` (Telegram bot token)
- `GROQ_API_KEY` (for Llama 3 model)
- `MONGO_URL` (optional, for MongoDB connection)

## Running the Bot

```bash
pip install -r requirements.txt
python main.py
```

For deployment on platforms like Koyeb or other container hosts, a `Dockerfile` is included. Build and test locally with:

```bash
docker build -t miss-hinata-bot .
docker run --rm -e API_ID=... -e API_HASH=... -e BOT_TOKEN=... -e GROQ_API_KEY=... miss-hinata-bot
```

Koyeb automatically builds from your repository if a `Dockerfile` is present. Be sure to add your environment variables through the Koyeb dashboard or CLI so the container can start successfully.

---

## Conversation Memory (SQLite)

The bot now stores chat history in a local SQLite database (`data.db` in the working directory).
It records every message it processes along with the sender and username, and uses the last ~20 entries
as context when querying the AI model. No external services or credentials are required – the database is
created automatically when the bot starts.

You can inspect the database with tools like `sqlite3 data.db` or mount it in your container to preserve
history between restarts.

## Environment Variables Recap

- `API_ID`, `API_HASH` (from my.telegram.org; required by Pyrogram even for bots)
- `BOT_TOKEN` (Telegram bot token)
- `GROQ_API_KEY` (for Llama 3)

---

## Offline fallback model

If the Groq service is unavailable or you run out of quota, the bot automatically
uses a small local language model (distilgpt2) that ships with the code. This
model requires **no API key**, can run completely offline, and responds to
an unlimited number of messages. Responses are simpler than Groq's but still
maintain the Hinata persona. If the local model also misbehaves the bot falls
back to a cute canned reply so it never crashes or behaves like a generic bot.



## GIF Support

The bot randomly sends Naruto/Hinata/Kakashi GIFs using a small built-in list of free URLs. No API key or setup is required – the feature works out of the box.
## Environment Variables Recap

- `API_ID`, `API_HASH` (from my.telegram.org)
- `BOT_TOKEN` (Telegram bot token)
- `GROQ_API_KEY` (for Llama 3)
- `FIREBASE_JSON` or `FIREBASE_CRED_PATH` (optional, for memory)

---



