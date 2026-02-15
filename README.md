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

For deployment on platforms like Koyeb, wrap the application in a Docker container.

---

## Firebase Conversation Memory

To retain past conversations and give the bot context, the project can use Firebase Firestore.
1. Create a Firebase project at https://console.firebase.google.com/
2. Add a service account (Settings ➜ Service accounts) and generate a JSON key.
3. Provide that JSON either via the `FIREBASE_JSON` environment variable (entire file contents) or set `FIREBASE_CRED_PATH` to a path inside your container.
4. The bot will automatically record every message it sees and replay the last ~20 entries to the AI model.

If `firebase-admin` is not installed or credentials are missing, the bot will simply operate without memory.

## GIF Support

The bot randomly sends Naruto/Hinata/Kakashi GIFs using a small built-in list of free URLs. No API key or setup is required – the feature works out of the box.
## Environment Variables Recap

- `API_ID`, `API_HASH` (from my.telegram.org)
- `BOT_TOKEN` (Telegram bot token)
- `GROQ_API_KEY` (for Llama 3)
- `FIREBASE_JSON` or `FIREBASE_CRED_PATH` (optional, for memory)

---



