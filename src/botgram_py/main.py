import argparse
import logging
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from cachetools import TTLCache
from fastapi import FastAPI, Request, Response
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters,
)

from . import config
from .custom_filters import TARGETED_OR_PRIVATE
from .handlers import ai, audio, translate

# We import the HTTP clients to close them on shutdown
from .services.llm_api import http_client as llm_client
from .services.speech_to_text import http_client as groq_client
from .services.video_api import http_client as video_client

config.setup_logging()
logger = logging.getLogger(__name__)

processed_updates: TTLCache[int, bool] = TTLCache(maxsize=1000, ttl=300)
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")


# --- 1. Define Basic Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    if not update.message or not update.effective_user:
        return
    user = update.effective_user.first_name
    await update.message.reply_text(f"Hello {user}! What can I do for you?")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the welcome and help message with detailed instructions."""
    if not update.message or not update.effective_user:
        return
    
    user = update.effective_user.first_name
    bot_username = context.bot.username

    help_text = (
        f"👋 Hello, *{user}*! I am your multifunctional AI assistant.\n\n"
        
        "🧠 *Artificial Intelligence*\n"
        "• `/ask [text]` — Ask me a direct question.\n"
        "• `/ask` — *Replying to a message:* I analyze and answer the message you quote.\n"
        "• `/clear` — Reset my memory and forget our current conversation.\n\n"
        
        "🗣️ *Audio & Voice*\n"
        "• *Voice Note:* Send me a voice note in private chat to talk to the AI.\n"
        "• `/transcribe` — Convert audio to text (reply to any audio file).\n\n"
        
        "🌍 *Translation*\n"
        "• `/es_en` — Translate Spanish to English.\n"
        "• `/en_es` — Translate English to Spanish.\n"
        "• _You can use these by replying to a message or by typing text after the command._\n\n"
        
        "👥 *Group Usage*\n"
        "To get my attention in groups, you must mention me:\n"
        f"`/ask@{bot_username} question` or `@{bot_username} hello`"
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


# --- 2. Helper Function to Register Everything (AVOIDS DUPLICATION) ---
def register_handlers(application: Application) -> None:
    """
    Registers all commands for both Webhook and Polling modes.
    Follows DRY principle.
    """
    # 1. General Commands
    # filters=TARGETED_OR_PRIVATE performs the magic of filtering group spam
    application.add_handler(
        CommandHandler("start", start_command, filters=TARGETED_OR_PRIVATE)
    )
    application.add_handler(
        CommandHandler("help", help_command, filters=TARGETED_OR_PRIVATE)
    )
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.Entity("mention"), ai.handle_group_mention
        )
    )

    # 2. AI
    application.add_handler(
        CommandHandler("ask", ai.ask_command, filters=TARGETED_OR_PRIVATE)
    )
    application.add_handler(
        CommandHandler("clear", ai.clear_command, filters=TARGETED_OR_PRIVATE)
    )

    # 3. Video (Commented out by default)
    # application.add_handler(
    #     CommandHandler("dl", video.dl_command, filters=TARGETED_OR_PRIVATE)
    # )

    # 4. Translation
    application.add_handler(
        CommandHandler(
            ["es_en", "en_es", "translate"],
            translate.translate_command,
            filters=TARGETED_OR_PRIVATE,
        )
    )

    # 5. Audio / Voice
    application.add_handler(
        CommandHandler(
            "transcribe", audio.transcribe_command, filters=TARGETED_OR_PRIVATE
        )
    )
    application.add_handler(
        MessageHandler(filters.VOICE & filters.ChatType.PRIVATE, audio.handle_voice)
    )

    # 6. Private Text for AI
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            ai.handle_private_text,
        )
    )


# --- 3.  Constants and global Configurations ---


BOT_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("help", "Show all commands"),
    BotCommand("ask", "Ask anything to the AI (or reply to a message)"),
    BotCommand("transcribe", "Transcribe a voice note or audio replying it"),
    BotCommand("es_en", "Translate from Spanish to English"),
    BotCommand("en_es", "Translate from English to Spanish"),
    BotCommand("clear", "Clear chat history"),
    # BotCommand("dl", "Download video from URL"),
]


async def setup_commands(application: Application) -> None:
    """
    Configure the bot commands on Telegram.
    It runs automatically after initialization.
    """
    logger.info("Setting bot commands...")
    await application.bot.set_my_commands(BOT_COMMANDS)


# --- 4. Lifespan Logic (for FastAPI) ---


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    storage_data = PicklePersistence(filepath="bot_data.pickle")

    # --- STARTUP ---
    logger.info("🚀 Starting Bot Application...")
    ptb_app = (
        ApplicationBuilder()
        .token(config.BOT_TOKEN)
        .persistence(storage_data)
        .post_init(setup_commands)
        .build()
    )

    register_handlers(ptb_app)

    await ptb_app.initialize()
    await ptb_app.start()

    if config.HOSTING == "production":
        webhook_url = f"{config.WEBHOOK_URL}/webhook"
        logger.info(f"Configuring Webhook at: {webhook_url}")
        await ptb_app.bot.set_webhook(url=webhook_url)
    else:
        await ptb_app.bot.delete_webhook()

    app.state.ptb_bot = ptb_app

    yield

    logger.info("🛑 Stopping Bot and closing connections...")
    await app.state.ptb_bot.stop()
    await app.state.ptb_bot.shutdown()

    await llm_client.aclose()
    await groq_client.aclose()
    await video_client.aclose()


# --- 5. Initialize FastAPI ---
app = FastAPI(lifespan=lifespan)


@app.api_route("/", methods=["GET", "HEAD"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "bot": "active"}


@app.post("/webhook")
async def telegram_webhook(request: Request) -> Response:
    ptb_bot: Application = request.app.state.ptb_bot

    data: dict[str, Any] = await request.json()
    update = Update.de_json(data, ptb_bot.bot)

    if not update:
        return Response(status_code=400, content="Bad Request: Invalid Update")

    if update.update_id in processed_updates:
        logger.warning(f"⚠️ Update {update.update_id} duplicated.")
        return Response(status_code=200)

    processed_updates[update.update_id] = True
    await ptb_bot.process_update(update)
    return Response(status_code=200)


# --- 6. Entry Point for Polling (Classic Local Development) ---
def run_polling() -> None:
    """
    Runs WITHOUT FastAPI, directly with the Telegram library.
    Ideal for local testing without configuring ngrok or ports.
    """
    storage_data = PicklePersistence(filepath="bot_data.pickle")

    logger.info("Polling Mode: Starting...")

    # Create a LOCAL instance
    app_bot = (
        ApplicationBuilder()
        .token(config.BOT_TOKEN)
        .persistence(storage_data)
        .post_init(setup_commands)
        .build()
    )

    # Use the SAME registration function
    register_handlers(app_bot)

    logger.info("🤖 Bot listening... (Ctrl+C to stop)")
    app_bot.run_polling()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute Telegram Bot")
    parser.add_argument(
        "--mode",
        choices=["polling", "webhook"],
        default="polling",
        help="Execution mode: 'polling' for local, 'webhook' for production",
    )
    args = parser.parse_args()

    if args.mode == "webhook":
        logger.info("⚠️ Running in WEBHOOK mode via Uvicorn...")
        uvicorn.run(
            "src.botgram_py.main:app", host="0.0.0.0", port=config.PORT, reload=False
        )
    else:
        logger.info("🧑‍💻 Running in POLLING mode...")
        run_polling()
