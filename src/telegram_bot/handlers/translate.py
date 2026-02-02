import logging
from telegram import Update, constants
from telegram.ext import ContextTypes
from ..services import llm_api
from .. import config

logger = logging.getLogger(__name__)


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles translation commands: /es_en (Spanish->English) and /en_es (English->Spanish).
    Supports direct arguments or replies to messages.
    """
    # Clean command (/es_en@BotName -> es_en)
    command = update.message.text.split()[0].replace("/", "").split("@")[0]

    text_to_translate = ""

    # 1. Direct arguments (/es_en Hello)
    if context.args:
        text_to_translate = " ".join(context.args)

    # 2. Reply to message (/es_en replying to someone)
    elif update.message.reply_to_message:
        original = update.message.reply_to_message
        text_to_translate = original.text or original.caption or ""

    if not text_to_translate:
        await update.message.reply_text(
            "Please provide text or reply to a message to translate."
        )
        return

    # Define languages
    lang_map = {"es_en": "Spanish to English", "en_es": "English to Spanish"}
    direction = lang_map.get(command, "Spanish to English")

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )

    prompt = f"Translate the following text from {direction}. Output ONLY the translation:\n\n{text_to_translate}"

    messages = [
        {"role": "system", "content": "You are a professional translator."},
        {"role": "user", "content": prompt},
    ]

    try:
        # Asynchronous API Call
        translation = await llm_api.get_api_llm(
            messages,
            config.API_TOKEN,
            config.API_URL,
            config.LLM_MODEL,
            config.PROVIDER,
            MAX_OUTPUT_TOKENS=800,
        )
        await update.message.reply_text(translation)

    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")
