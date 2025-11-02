# 🤖 Telegram AI & Multimedia Bot

A powerful and versatile Telegram bot that integrates a multi-provider conversational AI, a comprehensive video downloader, speech-to-text transcription, and translation capabilities.

## ✨ Features

- **🧠 Conversational AI:**
  - Supports multiple LLM providers: **Google Gemini**, **OpenAI**, and **DeepSeek**.
  - Maintains conversation history (last 25 messages) for contextual responses.
  - Automatically resets conversation after 1 hour of inactivity to ensure privacy.
  - Handles direct messages and group mentions seamlessly.

- **🎬 Video & Audio Downloader:**
  - Downloads videos from  **Instagram**, **Facebook**, and **TikTok**.
  - Utilizes `yt-dlp` for efficient and reliable downloads.
  - Supports cookie-based authentication for downloading private/age-restricted content from Instagram.
  - Optimizes video format and quality for mobile devices.

- **🎤 Speech-to-Text:**
  - Transcribes voice messages into text using Google Speech Recognition.
  - Allows users to interact with the AI assistant using their voice.

- **🌐 Translation:**
  - Translates text between **English** and **Spanish** using the configured LLM.

- **👥 Group & Private Chat Support:**
  - Fully functional in both private chats and group environments.
  - Responds to commands addressed to it in groups (e.g., `/ask@YourBotName`).
  - Welcomes new members in group chats.

- **🔧 Advanced Configuration:**
  - All settings are managed via a `.env` file for easy setup.
  - Detailed logging for easy debugging.
  - Includes a script to update downloader cookies in a Supabase database.

## Features

| Feature             | Supported Platforms                               |
| ------------------- | ------------------------------------------------- |
| **Video Downloader**| Instagram, Facebook, TikTok              |
| **AI Providers**    | Google Gemini, OpenAI, DeepSeek                   |
| **Speech-to-Text**  | Google Speech Recognition                         |

## 🤖 Commands

| Command        | Description                                       | Example                                           |
| -------------- | ------------------------------------------------- | ------------------------------------------------- |
| `/start`       | Initialize the bot and show a welcome message.    | `/start`                                          |
| `/help`        | Display the list of available commands.           | `/help`                                           |
| `/ask [text]`  | Ask a question to the AI assistant.               | `/ask What is the capital of Japan?`              |
| `/clear`       | Clear the current conversation history with the AI. | `/clear`                                          |
| `/dl [url]`    | Download a video from a supported platform.       | `/dl https://www.instagram.com/watch?v=...`         |
| `/es_en [text]`| Translate text from Spanish to English.           | `/es_en Hola, ¿cómo estás?`                       |
| `/en_es [text]`| Translate text from English to Spanish.           | `/en_es Hello, how are you?`                      |

*Note: In group chats, all commands must be directed at the bot, e.g., `/ask@YourBotName ...`*

## 📋 Prerequisites

- Python 3.9+
- [FFmpeg](https://ffmpeg.org/download.html)
- An account with a supported LLM provider (Google, OpenAI, or DeepSeek).
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather).
- (Optional) A Supabase account for storing cookies.

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/TeleBotAPILLM.git
    cd TeleBotAPILLM
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

1.  **Create a `.env` file** in the root of the project by copying the example:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file** with your credentials:

    ```env
    # Telegram Bot Configuration
    BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"

    # LLM Configuration (choose one provider)
    PROVIDER="google"  # or "openai", "deepseek"
    API_TOKEN="YOUR_LLM_API_TOKEN"
    LLM_MODEL="gemini-pro" # e.g., "gpt-4", "deepseek-coder"
    API_URL="https://generativelanguage.googleapis.com/v1beta/models" # Adjust for your provider
    SYSTEM_MESSAGE="You are a helpful AI assistant."
    MAX_OUTPUT_TOKENS=700

    # Supabase Configuration (Optional, for video downloader cookies)
    SUPABASE_URL="YOUR_SUPABASE_URL"
    SUPABASE_KEY="YOUR_SUPABASE_KEY"

    # Hosting Configuration (for production)
    HOSTING="development" # "production" or "development"
    WEBHOOK_URL="https://your-domain.com" # Required for production
    ```

## 🚀 Usage

### Development Mode

For local development, the bot uses long polling.

```bash
python -m src.telegram_bot.main
```

### Production Mode

For production, the bot uses webhooks, which requires a publicly accessible URL.

1.  Set `HOSTING="production"` in your `.env` file.
2.  Make sure `WEBHOOK_URL` is set to your public domain.
3.  Run the bot using a production-ready WSGI server like Waitress (included):

    ```bash
    python -m src.telegram_bot.main
    ```

### Docker

A `Dockerfile` is included for easy containerization.

1.  **Build the image:**
    ```bash
    docker build -t telegram-bot .
    ```

2.  **Run the container:**
    ```bash
    docker run -d --env-file .env --name telegram-bot-container telegram-bot
    ```

### Updating Cookies for Video Downloader

To download private or age-restricted content from and Instagram, you need to provide cookies.

1.  Get your browser's cookies for the required sites and save them in a file named `cookies.txt` in the root of the project.
2.  Run the `update_cookies.py` script:
    ```bash
    python scripts/update_cookies.py
    ```
    This will upload the cookies to your Supabase database.

## 📦 Dependencies

Here are the main dependencies of the project:

- `pyTelegramBotAPI`: Telegram Bot API wrapper.
- `yt-dlp`: Video downloader.
- `SpeechRecognition`: Speech-to-text conversion.
- `pydub`: Audio manipulation.
- `requests`: HTTP requests for LLM APIs.
- `Flask` & `waitress`: For webhook deployment.
- `python-dotenv`: Environment variable management.
- `supabase`: Supabase client.

For a full list of dependencies, see `requirements.txt`.
