# Environment Variables Guide

This document explains how to set up the variables the bot needs, in a simple way.

Imagine the bot is a little robot that needs a few keys to start working. These keys are called "environment variables" and we give them to the robot before it wakes up.

## What you need to give the bot

| Variable | What it tells the bot | Example (do not use) |
|----------|-----------------------|----------------------|
| `API_ID` | Your Telegram application ID (from my.telegram.org). Even though you
|          | are running a bot, Pyrogram still acts as a Telegram client and needs to
|          | identify itself with these credentials. | `123456` |
| `API_HASH` | Your Telegram application hash (from my.telegram.org). Used with
|          | the API ID to authenticate requests to Telegram. | `abcdef123456` |
| `BOT_TOKEN` | The token you get when you create a bot with @BotFather | `1234:ABCD...` |
| `GROQ_API_KEY` | A secret key used to ask the Groq AI model to chat | `sk-xxxx` |



> **Note:** Do not put these values in the code. They must stay secret, just like a password.

## How to set them (Linux / macOS)

Open a terminal and type these lines, replacing the words after `=` with your own keys:

```bash
export API_ID="your_api_id_here"
export API_HASH="your_api_hash_here"
export BOT_TOKEN="your_bot_token_here"
export GROQ_API_KEY="your_groq_key_here"
# optional memory:
# export FIREBASE_JSON='{"type": "service_account", ...}'
# or
# export FIREBASE_CRED_PATH="/path/to/your/firebase.json"
```

After exporting them, you can start the bot:

```bash
pip install -r requirements.txt
python main.py
```

## How to set them (Windows PowerShell)

```powershell
$env:API_ID="your_api_id_here"
$env:API_HASH="your_api_hash_here"
$env:BOT_TOKEN="your_bot_token_here"
$env:GROQ_API_KEY="your_groq_key_here"
# optional memory:
# $env:FIREBASE_JSON='{"type": "service_account", ...}'
# or
# $env:FIREBASE_CRED_PATH="C:\path\to\firebase.json"
python main.py
```

## Quick tips for kids

1. Think of `export` or `$env:` as giving a label to your robot before it starts. You only need to do it once per terminal session.
2. If you are using a hosting service (like Koyeb or Heroku), they will usually have a place in the dashboard where you can paste these names and values instead of using `export`.
3. Keep your keys private! Do not share them with friends or put them on GitHub.

The bot will automatically create and use a file called `data.db` in the same folder for remembering chats. No extra setup is required.

That's it! Once the variables are set, the bot will wake up and can chat with you as Miss Hinata.