import logging
from telegram import Update, constants
from telegram.ext import ContextTypes

from ..services.speech_to_text import transcribe
from .ai import process_ai_interaction
from ..config import API_TOKEN

logger = logging.getLogger(__name__)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles voice notes, transcribes them via Groq, and sends to AI."""

    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(
        chat_id=chat_id, action=constants.ChatAction.TYPING
    )

    try:
        voice = update.message.voice

        if voice.file_size > 25 * 1024 * 1024:
            await update.message.reply_text("⚠️ Audio too large to process.")
            return

        new_file = await context.bot.get_file(voice.file_id)
        file_byte_array = await new_file.download_as_bytearray()

        transcribed_text = await transcribe(bytes(file_byte_array), API_TOKEN)

        if not transcribed_text:
            await update.message.reply_text("😓 I couldn't hear anything in the audio.")
            return

        # Feedback visual de lo que entendió
        await update.message.reply_text(
            f"🎤 *You:* {transcribed_text}", parse_mode="Markdown"
        )

        # 3. Enviar a la IA
        await process_ai_interaction(update, context, transcribed_text)

    except Exception as e:
        logger.error(f"Error handling voice: {e}", exc_info=True)
        await update.message.reply_text("🚨 Error processing audio.")
