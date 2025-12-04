# 🚀 Async AI & Media Telegram Bot

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688?logo=fastapi)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-2CA5E0?logo=telegram)
![Poetry](https://img.shields.io/badge/Poetry-Dependency%20Manager-blueviolet?logo=poetry)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)

A high-performance, asynchronous Telegram bot built with **FastAPI** and **Python-Telegram-Bot (v20+)**. 

This bot features concurrent processing for heavy tasks (video downloading, audio transcription) and seamless integration with multiple LLM providers (Google Gemini, OpenAI, DeepSeek).

## ✨ Key Features

- **⚡ Asynchronous & Concurrent:**
  - Built on `FastAPI` (ASGI) for high-throughput webhook handling.
  - Heavy tasks (video downloads, speech-to-text) run in non-blocking threads, keeping the bot responsive.
  
- **🧠 Advanced AI Integration:**
  - Supports **Google Gemini**, **OpenAI**, and **DeepSeek**.
  - **Context Aware:** Remembers conversation history per chat.
  - **Smart Replies:** Can analyze replied messages (e.g., reply to a long text with `/ask Summarize this`).

- **🎬 Multimedia Downloader:**
  - Downloads videos from **Instagram**, **TikTok**, **Facebook**, and **YouTube**.
  - Uses `yt-dlp` with cookie support (via Supabase) for age-restricted/private content.
  - Automatic video compression for Telegram limits.

- **🗣️ Speech-to-Text:**
  - Transcribes voice notes into text automatically.
  - Users can talk to the AI using voice messages.

- **🛡️ Smart Group Management:**
  - **Anti-Spam Filter:** In groups, the bot ignores generic commands (`/help`). It only responds to direct mentions (`/help@MyBot`) or private chats.

## 🛠️ Tech Stack

- **Framework:** FastAPI + Uvicorn
- **Bot Library:** python-telegram-bot (v20+ Async)
- **Dependency Manager:** Poetry
- **HTTP Client:** HTTPX (Async)
- **Database:** Supabase (for Cookie storage)
- **Media Processing:** yt-dlp, FFmpeg, SpeechRecognition

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- [Poetry](https://python-poetry.org/) installed
- FFmpeg installed on your system
- A Telegram Bot Token
- An API Key for your LLM provider (Google/OpenAI)

### 1. Installation

Clone the repository and install dependencies using Poetry:

```
git clone https://github.com/MrTanuk/TeleBotAPILLM.git
cd TeleBotAPILLM

# Install dependencies
poetry install

# Activate the virtual environment
poetry env activate
```

### 2. Configuration

Create a .env file in the root directory:

```
cp .env.example .env
```

Fill in your credentials:

```bash
    
# --- Bot Configuration ---
BOT_TOKEN=your_telegram_bot_token_here

# --- LLM Configuration ---
# Options provider: google, openai, deepseek
PROVIDER=
API_TOKEN=
LLM_MODEL=
# Google Base URL: https://generativelanguage.googleapis.com/v1beta/models
API_URL=
SYSTEM_MESSAGE="You are a helpful and sarcastic AI assistant."
MAX_OUTPUT_TOKENS=800

# --- Supabase (Optional, for Cookies) ---
SUPABASE_URL=
SUPABASE_KEY=

# --- Hosting ---
# 'development' (Polling) or 'production' (Webhook)
HOSTING=development
WEBHOOK_URL= 
PORT=
```

### 3. Running the Bot

**Development Mode (Polling):**  
Ideal for local testing. No webhook/domain required.

```bash
poetry run python -m src.telegram_bot.main
```

**Production Mode (Webhook):**  
Runs the FastAPI server. Requires HOSTING=production in .env.

```bash
uvicorn src.telegram_bot.main:app --host 0.0.0.0 --port 8080
```

## 🐳 Docker Deployment

The project includes an optimized Dockerfile.

1. **Build the image:**

```
docker build -t telegram-ai-bot .
```

2. **Run the container:**

``` 
docker run -d \
  --env-file .env \
  -p 8080:8080 \
  --name my-bot \
  telegram-ai-bot
  ```

## 🤖 Commands


| Command  | Usage             | Description                                      |
| -------- | ----------------- | ------------------------------------------------ |
| `/start` | `/start`          | Check if the bot is alive.                       |
| `/help`  | `/help`           | Show all commands and their functions            |
| `/ask`   | `/ask [question]` | Ask the AI. Supports replying to other messages. |
| `/dl`    | `/dl [question]`  | Download video from Insta/TikTok/FB/YouTube.     |
| `/es_en` | `/es_en`          | Translate Spanish to English.                    |
| `/en_es` | `/en_es`          | Translate English to Spanish.                    |
| `/clear` | `/clear`          | Reset AI conversation history.                   |
| Voice    | *Send audio*      | Transcribes audio and sends it to AI.            |

> **Note:** In groups, append the bot username (e.g., /ask@MyBotName) for the command to work.

## 📂 Project Structure

```
├── src/telegram_bot/
│   ├── handlers/        # Command logic (AI, Video, Audio)
│   ├── services/        # External API logic (LLM, yt-dlp)
│   ├── config.py        # Environment & Setup
│   ├── custom_filters.py# Group vs Private logic
│   └── main.py          # Entry point (FastAPI + Bot App)
├── scripts/             # Utilities (Cookie updater)
├── Dockerfile           # Production container
├── pyproject.toml       # Poetry dependencies
└── README.md            # Documentation
```

## 🍪 Cookie Management

To download **private** or **age-restricted** content (especially from Instagram and some YouTube videos), the bot needs valid browser cookies.

### 1. Export Cookies
You need to export cookies in the **Netscape HTTP Cookie File** format.
1. Install a browser extension like **"Get cookies.txt LOCALLY"** ([Chrome](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflccgomilekfcg) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/get-cookies-txt-locally/)).
2. Log in to Instagram/YouTube in your browser.
3. Open the extension and export the cookies.
4. Save the file as `cookies.txt`.

### 2. Upload to Database
We use a smart script to upload these cookies to Supab1ase.

**Option A: Automatic Search (Easiest)**
The script automatically looks for `cookies.txt` in your **Downloads folder**, the project root, or the `scripts/` folder.

```
python scripts/update_cookies.py
```

**Option B: Specific File**
If your file has a different name or location:

```
python scripts/update_cookies.py --file /path/to/my-cookies.txt
 ```

**Option C: CI/CD (No confirmation)**  
To skip the "Are you sure?" prompt (useful for automated pipelines):

```
python scripts/update_cookies.py
```

> **Note:** The script validates the file format before uploading to ensure yt-dlp compatibility.

## 📄 License

This project is licensed under the MIT License.
