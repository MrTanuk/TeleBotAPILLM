import logging
from datetime import datetime, timezone
from typing import cast

from telegram import Update, constants
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from .. import config
from ..services import llm_api

logger = logging.getLogger(__name__)

# --- Helper Functions ---


def get_user_keys(user_id: int) -> tuple[str, str]:
    """Generates unique keys for storage in chat_data based on the user’s ID."""
    return f"conversation_{user_id}", f"last_active_{user_id}"


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the conversation history."""
    if not update.effective_user or not update.message:
        return

    if context.chat_data is None:
        return

    user_id = update.effective_user.id
    history_key, time_key = get_user_keys(user_id)

    context.chat_data[history_key] = []
    context.chat_data[time_key] = None

    await update.message.reply_text("♻️ Your conversation history has been cleared.")


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /ask command, supporting replies to other messages."""
    if not update.message:
        return

    user_instruction = " ".join(context.args) if context.args else ""
    reply_content = ""

    if update.message.reply_to_message:
        if update.message.reply_to_message.text:
            reply_content = update.message.reply_to_message.text
        elif update.message.reply_to_message.caption:
            reply_content = update.message.reply_to_message.caption

    final_prompt = ""

    if reply_content and user_instruction:
        final_prompt = f"Original message context: '{reply_content}'\n\nMy instruction: {user_instruction}"
    elif reply_content and not user_instruction:
        final_prompt = f"Analyze and respond to this message: '{reply_content}'"
    elif user_instruction:
        final_prompt = user_instruction
    else:
        await update.message.reply_text(
            "Please write a question or reply to a message with `/ask`."
        )
        return

    await process_ai_interaction(update, context, final_prompt)


async def handle_private_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles text messages in private chats without commands."""
    if not update.message or not update.message.text:
        return

    if update.message.text.startswith("/"):
        return
    await process_ai_interaction(update, context, update.message.text)


async def handle_group_mention(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Detect if the bot was mentioned in a group, strip the '@BotName', and send the rest to the AI.
    """
    message = update.message
    if not message or not message.text:
        return

    bot_username = context.bot.username
    text = message.text

    if f"@{bot_username}" in text:
        clean_text = text.replace(f"@{bot_username}", "").strip()

        if not clean_text:
            await message.reply_text("👋 Hello! How can I help you?")
            return
        await process_ai_interaction(update, context, clean_text)


# --- Core Logic ---


async def process_ai_interaction(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str
) -> None:
    """
    Main function to manage AI interaction: history, API call, and response.
    """
    if not update.effective_chat or not update.effective_user or not update.message:
        logger.warning("Update missing critical data (chat/user/message), ignoring.")
        return

    if context.chat_data is None:
        logger.error("chat_data is None, cannot process interaction.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    history_key, time_key = get_user_keys(user_id)

    await context.bot.send_chat_action(
        chat_id=chat_id, action=constants.ChatAction.TYPING
    )

    if history_key not in context.chat_data:
        context.chat_data[history_key] = []

    last_active = context.chat_data.get(time_key)
    current_time = datetime.now(timezone.utc)

    if last_active and (current_time - last_active).total_seconds() > 3600:
        context.chat_data[history_key] = []
        await update.message.reply_text("🕒 Your chat history reset due to inactivity.")

    context.chat_data[time_key] = current_time

    conversation = cast(list[dict[str, str]], context.chat_data[history_key])
    conversation.append({"role": "user", "content": user_text})

    if len(conversation) > 20:
        context.chat_data[history_key] = conversation[-20:]
        conversation = cast(list[dict[str, str]], context.chat_data[history_key])

    api_token = config.API_TOKEN or ""
    llm_model = config.LLM_MODEL or ""
    api_url = config.API_URL
    ai_response = ""

    try:
        ai_response = await llm_api.get_api_llm(
            conversation,
            api_token,
            api_url,
            llm_model,
            config.PROVIDER or "",
            MAX_OUTPUT_TOKENS=config.MAX_OUTPUT_TOKENS,
            system_message=config.SYSTEM_MESSAGE,
        )

        conversation.append({"role": "assistant", "content": ai_response})
        await update.message.reply_text(ai_response, parse_mode="Markdown")

    except BadRequest as e:
        logger.warning(f"Markdown failed, sending plain text. Error: {e}")
        try:
            if ai_response:
                await update.message.reply_text(ai_response)
            else:
                await update.message.reply_text("🚨 Received an empty response.")
        except Exception as e2:
            logger.error(f"Error sending the answer: {e2}")
            await update.message.reply_text("🚨 Error sending the answer")

    except Exception as e:
        logger.error("Error in AI handler: %s", e, exc_info=True)
        try:
            await update.message.reply_text("🚨 Sorry, technical problem")
        except Exception:
            pass
