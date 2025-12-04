import logging
import asyncio
from telegram import Update, constants
from telegram.ext import ContextTypes

from ..services.speech_to_text import speech
from .ai import process_ai_interaction

logger = logging.getLogger(__name__)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles voice notes, transcribes them, and sends the text to the AI."""
    
    # Visual feedback
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    try:
        # 1. Get file information
        voice = update.message.voice
        file_id = voice.file_id
        
        # If too large (>20MB), better ignore to not block RAM
        if voice.file_size > 20 * 1024 * 1024:
            await update.message.reply_text("⚠️ Voice note too large.")
            return

        # 2. Download file to memory (Async)
        new_file = await context.bot.get_file(file_id)
        file_byte_array = await new_file.download_as_bytearray()

        # 3. Transcribe in a THREAD (Blocking -> Non-blocking)
        transcribed_text = await asyncio.to_thread(speech, file_byte_array)

        if not transcribed_text:
            await update.message.reply_text("😓 I couldn't understand the audio.")
            return

        # Confirm to user what the bot understood
        await update.message.reply_text(f"🎤 *Transcription:* _{transcribed_text}_", parse_mode="HTML")

        # 4. Send to AI
        # Reusing the function you already wrote in ai.py
        await process_ai_interaction(update, context, transcribed_text)

    except Exception as e:
        logger.error(f"Error handling voice: {e}", exc_info=True)
        await update.message.reply_text("🚨 Error processing audio.")
