# 🚀 Async AI & Media Telegram Bot

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688?logo=fastapi)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-2CA5E0?logo=telegram)
![Poetry](https://img.shields.io/badge/Poetry-Dependency%20Manager-blueviolet?logo=poetry)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)

A high-performance, asynchronous Telegram bot built with **FastAPI** and **Python-Telegram-Bot (v20+)**.

This bot features concurrent processing for heavy tasks and seamless integration with multiple LLM providers.

## ✨ Key Features

- **⚡ Asynchronous & Concurrent:**
  - Built on `FastAPI` (ASGI) for high-throughput webhook handling.
  - Heavy tasks run in non-blocking threads.
- **🧠 Advanced AI Integration:**
  - Supports **Google Gemini**, **OpenAI**, **DeepSeek** and **Groq**.
  - **Context Aware:** Remembers conversation history per chat.
  - **Smart Replies:** Can analyze replied messages.
  - **Group Aware:** Responds when tagged (`@MyBot Hello`).

- **🎬 Multimedia Downloader:**
  - Downloads videos from **Instagram**, **TikTok**, **Facebook**, and **YouTube**.
  - Uses `yt-dlp` for broad compatibility.
  - Automatic video compression for Telegram limits.

- **🗣️ Speech-to-Text (Groq Powered):**
  - Transcribes voice notes instantly using **Groq Whisper API**.
  - Users can talk to the AI using voice messages.

- **🛡️ Smart Group Management:**
  - **Anti-Spam Filter:** In groups, the bot ignores generic commands (`/help`). It only responds to direct mentions (`/help@botname` or `@botname help`).

## 🛠️ Tech Stack

- **Framework:** FastAPI + Uvicorn
- **Bot Library:** python-telegram-bot (v20+ Async)
- **Dependency Manager:** Poetry
- **HTTP Client:** HTTPX (Async)
- **Media Processing:** yt-dlp, FFmpeg
- **Audio AI:** Groq (Whisper-large-v3)

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- [Poetry](https://python-poetry.org/) installed
- FFmpeg installed on your system
- A Telegram Bot Token
- API Keys (LLM Provider + Groq)

### 1. Installation

Clone the repository and install dependencies using Poetry:

```bash
git clone https://github.com/MrTanuk/TeleBotAPILLM.git
cd TeleBotAPILLM

# Install dependencies
poetry install

# Activate the virtual environment
poetry env activate
```

### 2. Configuration

Create a .env file in the root directory:

```bash
cp .env.example .env
```

Fill in your credentials:

```bash
# --- Bot Configuration ---
BOT_TOKEN=your_telegram_bot_token_here

# --- LLM Configuration ---
# Options provider: google, openai, deepseek, groq
PROVIDER=google
API_TOKEN=your_llm_api_key
LLM_MODEL=gemini-1.5-flash
API_URL=https://generativelanguage.googleapis.com/v1beta/models
SYSTEM_MESSAGE="You are a helpful and sarcastic AI assistant."
MAX_OUTPUT_TOKENS=800

# --- Audio Configuration ---
GROQ_API_KEY=gsk_your_groq_key

# --- Hosting ---
HOSTING=development
WEBHOOK_URL=
PORT=8080
```

### 3. Running the Bot

**Development Mode (Polling):**

```bash
poetry run python -m src.telegram_bot.main
```

**Production Mode / Webhook (Local):**

```bash
poetry run python -m src.telegram_bot.main --mode webhook
```

## 🐳 Docker Deployment

1. **Build the image:**

```bash
docker buildx build -t telegram-ai-bot .
```

2. **Run the container:**

```bash
docker run -d \
  --env-file .env \
  -p 8080:8080 \
  --name telebot \
  telegram-ai-bot
```

**If you use it on local before to deploy on production:**

```bash
docker run --rm -it \
  --env-file .env \
  --name telebot-local \
  telegram-ai-bot \
  python -m src.telegram_bot.main --mode polling
```

## 🤖 Commands

| Command  | Usage             | Description                                      |
| -------- | ----------------- | ------------------------------------------------ |
| `/start` | `/start`          | Check if the bot is alive.                       |
| `/help`  | `/help`           | Show all commands and their functions            |
| `/ask`   | `/ask [text]`     | Ask the AI. Supports replying to other messages. |
| `/dl`    | `/dl [url]`       | Download video from Insta/TikTok/FB/YouTube.     |
| `/es_en` | `/es_en`          | Translate Spanish to English.                    |
| `/en_es` | `/en_es`          | Translate English to Spanish.                    |
| `/clear` | `/clear`          | Reset AI conversation history.                   |
| Voice    | _Send audio_      | Transcribes audio and sends it to AI.            |

> **Note:** In groups, you can simply tag the bot to ask questions: `@MyBot How are you?`

## 📄 License

This project is licensed under the MIT License.
