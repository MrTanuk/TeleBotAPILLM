import logging
import warnings
from contextlib import asynccontextmanager
from cachetools import TTLCache
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from . import config

# Import handlers
from .handlers import ai, video, audio, translate
from .custom_filters import TARGETED_OR_PRIVATE

# Logger setup
config.setup_logging()
logger = logging.getLogger(__name__)

processed_updates = TTLCache(maxsize=1000, ttl=300)

# Filter syntax warnings from pydub due to Python version strictness
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")


# --- 1. Define Basic Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user.first_name
    await update.message.reply_text(f"Hello {user}! What can I do for you?")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el mensaje de bienvenida y ayuda."""
    user = update.effective_user.first_name
    help_text = (
        f"👋 Hello {user}!\n\n"
        "🤖 **Available Commands:**\n\n"
        "✨ /ask `[text]` - Ask the AI (or reply to a message)\n"
        "🧹 /clear - Reset conversation history\n"
        "🎬 /dl `[url]` - Download video (Insta/TikTok/FB)\n"
        r"🇪🇸 /es\_en - Translate to English\n"
        r"🇬🇧 /en\_es - Translate to Spanish\n"
        "🎤 **Voice Note** - I will transcribe and answer via audio\n\n"
        "ℹ️ *In groups, remember to mention me:* `/ask@MyBot ...`"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# --- 2. Helper Function to Register Everything (AVOIDS DUPLICATION) ---
def register_handlers(application: Application):
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

    # 2. AI
    application.add_handler(
        CommandHandler("ask", ai.ask_command, filters=TARGETED_OR_PRIVATE)
    )
    application.add_handler(
        CommandHandler("clear", ai.clear_command, filters=TARGETED_OR_PRIVATE)
    )

    # 3. Video
    application.add_handler(
        CommandHandler("dl", video.dl_command, filters=TARGETED_OR_PRIVATE)
    )

    # 4. Translation
    application.add_handler(
        CommandHandler(
            ["es_en", "en_es"], translate.translate_command, filters=TARGETED_OR_PRIVATE
        )
    )

    # 5. Audio (Voice Notes) - This is not a text command, but a message type
    application.add_handler(
        MessageHandler(filters.VOICE & filters.ChatType.PRIVATE, audio.handle_voice)
    )

    # 6. Private Text for AI (This stays the same, already restricted to PRIVATE)
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            ai.handle_private_text,
        )
    )


# --- 3. Lifespan Logic (for FastAPI) ---
ptb_application: Application = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ptb_application

    # --- STARTUP ---
    logger.info("🚀 Starting Bot Application (Webhook Mode)...")
    ptb_application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # Use the helper function
    register_handlers(ptb_application)

    await ptb_application.initialize()
    await ptb_application.start()

    if config.HOSTING == "production":
        webhook_url = f"{config.WEBHOOK_URL}/webhook"
        logger.info(f"Configuring Webhook at: {webhook_url}")
        await ptb_application.bot.set_webhook(url=webhook_url)
    else:
        # In development with FastAPI + Ngrok, for example
        await ptb_application.bot.delete_webhook()

    yield  # FastAPI runs here

    # --- SHUTDOWN ---
    logger.info("🛑 Stopping Bot...")
    if ptb_application:
        await ptb_application.stop()
        await ptb_application.shutdown()


# --- 4. Initialize FastAPI ---
app = FastAPI(lifespan=lifespan)


@app.api_route("/", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok", "bot": "active"}


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, ptb_application.bot)

    if update.update_id in processed_updates:
        logger.warning(f"⚠️ Update {update.update_id} duplicated (Telegram retry).")
        return Response(status_code=200)

    processed_updates[update.update_id] = True
    await ptb_application.process_update(update)
    return Response(status_code=200)


# --- 5. Entry Point for Polling (Classic Local Development) ---
def run_polling():
    """
    Runs WITHOUT FastAPI, directly with the Telegram library.
    Ideal for local testing without configuring ngrok or ports.
    """
    logger.info("Polling Mode: Starting...")

    # Create a LOCAL instance, do not use the global ptb_application
    app_bot = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # Use the SAME registration function
    register_handlers(app_bot)

    logger.info("🤖 Bot listening... (Ctrl+C to stop)")
    app_bot.run_polling()


if __name__ == "__main__":
    if config.HOSTING == "production":
        # If production, start the web server
        import uvicorn

        logger.info("⚠️ Running production mode locally via Python script...")
        uvicorn.run(
            "src.telegram_bot.main:app", host="0.0.0.0", port=config.PORT, reload=True
        )
    else:
        # If in dev and no webhook configured, use direct Polling
        logger.info("🧑‍💻 Running development mode...")
        run_polling()
