import logging

from telegram import Update, constants
from telegram.ext import ContextTypes

from .. import config
from ..services import llm_api
from .ai import send_safe_reply

logger = logging.getLogger(__name__)

# Supported target languages: code -> display name
SUPPORTED_LANGUAGES: dict[str, str] = {
    "es": "Spanish",
    "en": "English",
    "fr": "French",
    "it": "Italian",
    "de": "German",
    "pt": "Portuguese",
    "ja": "Japanese",
    "zh": "Chinese",
    "ar": "Arabic",
    "ru": "Russian",
}

_LANG_LIST = "\n".join(
    f"  `{code}` — {name}" for code, name in SUPPORTED_LANGUAGES.items()
)
USAGE_MESSAGE = (
    "📖 *Usage:* `/translate [lang\\_code] [text]`\n\n"
    "*Supported languages:*\n"
    f"{_LANG_LIST}\n\n"
    "_You can also reply to a message instead of writing the text._\n\n"
    "*Example:* `/translate fr Hello, how are you?`"
)


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Translates text to the given target language.

    Usage:
        /translate [lang_code] [text]
        /translate [lang_code]   (replying to a message)

    Supported lang codes: es, en, fr, it, de, pt, ja, zh, ar, ru
    """
    if not update.message or not update.effective_chat:
        return

    args = context.args or []

    if not args:
        await update.message.reply_text(USAGE_MESSAGE, parse_mode="Markdown")
        return

    lang_code = args[0].lower()

    if lang_code not in SUPPORTED_LANGUAGES:
        await update.message.reply_text(
            f"❌ Unsupported language code: `{lang_code}`\n\n{USAGE_MESSAGE}",
            parse_mode="Markdown",
        )
        return

    target_language = SUPPORTED_LANGUAGES[lang_code]

    # Prefer inline text, fall back to replied message
    text_to_translate = ""
    if len(args) > 1:
        text_to_translate = " ".join(args[1:])
    elif update.message.reply_to_message:
        original = update.message.reply_to_message
        text_to_translate = original.text or original.caption or ""

    if not text_to_translate:
        await update.message.reply_text(
            "⚠️ Please provide text to translate or reply to a message.\n\n" + USAGE_MESSAGE,
            parse_mode="Markdown",
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )

    prompt = (
        f"Translate the following text to {target_language}. "
        f"Output ONLY the translation, with no explanations or extra text:\n\n"
        f"{text_to_translate}"
    )

    try:
        translation = await llm_api.get_api_llm(
            messages=[{"role": "user", "content": prompt}],
            API_TOKEN=config.API_TOKEN or "",
            API_URL=config.API_URL,
            LLM_MODEL=config.LLM_MODEL or "",
            PROVIDER=config.PROVIDER or "",
            MAX_OUTPUT_TOKENS=config.MAX_OUTPUT_TOKENS,
            system_message="You are a professional translator. Translate text accurately and naturally.",
        )
        await send_safe_reply(update, translation)

    except Exception as e:
        logger.error("Translation error: %s", e)
        await update.message.reply_text(f"🚨 Error: {e}")
