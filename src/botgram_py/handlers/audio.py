import logging

from telegram import Update, constants
from telegram.ext import ContextTypes

from .. import config
from ..services.speech_to_text import transcribe
from .ai import process_ai_interaction

logger = logging.getLogger(__name__)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles voice notes, transcribes them via Groq, and sends to AI."""
    if not update.message or not update.message.voice or not update.effective_chat:
        return

    if not config.GROQ_API_KEY:
        await update.message.reply_text(
            "⚠️ Voice transcription is not configured (missing GROQ_API_KEY)."
        )
        return

    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(
        chat_id=chat_id, action=constants.ChatAction.TYPING
    )

    try:
        voice = update.message.voice

        if voice.file_size and voice.file_size > 25 * 1024 * 1024:
            await update.message.reply_text("⚠️ Audio too large to process.")
            return

        new_file = await context.bot.get_file(voice.file_id)
        file_byte_array = await new_file.download_as_bytearray()

        transcribed_text = await transcribe(bytes(file_byte_array), config.GROQ_API_KEY)

        if not transcribed_text:
            await update.message.reply_text("😓 I couldn't hear anything in the audio.")
            return

        await update.message.reply_text(
            f"🎤 *You:* {transcribed_text}", parse_mode="Markdown"
        )

        await process_ai_interaction(update, context, transcribed_text)

    except Exception as e:
        logger.error(f"Error handling voice: {e}", exc_info=True)
        if update.message:
            await update.message.reply_text("🚨 Error processing audio.")


async def transcribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Transcribes a voice note or audio file when replied with /transcribe."""

    if not update.message or not update.effective_chat:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a voice note or audio file with `/transcribe`.")
        return

    replied_msg = update.message.reply_to_message
    audio_obj = None

    # Detect if it's a voice note or a general audio file
    if replied_msg.voice:
        audio_obj = replied_msg.voice
    elif replied_msg.audio:
        audio_obj = replied_msg.audio

    if not audio_obj:
        await update.message.reply_text("The message you replied to does not contain any audio.")
        return

    # Configuration check
    if not config.GROQ_API_KEY:
        await update.message.reply_text("⚠️ GROQ_API_KEY is missing in configuration.")
        return

    chat_id = update.effective_chat.id
    status_msg = await update.message.reply_text("⏳ Transcribing audio...")
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)

    try:
        # Download file
        new_file = await context.bot.get_file(audio_obj.file_id)
        file_byte_array = await new_file.download_as_bytearray()

        # Call Groq Service
        transcribed_text = await transcribe(bytes(file_byte_array), config.GROQ_API_KEY)

        if not transcribed_text:
            await status_msg.edit_text("😓 I couldn't extract any text from this audio.")
            return

        # Reply with the result
        final_text = f"*Transcription:*\n\n{transcribed_text}"
        await status_msg.edit_text(final_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in transcribe_command: {e}", exc_info=True)
        await status_msg.edit_text("🚨 Error processing the transcription.")
