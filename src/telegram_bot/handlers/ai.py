import logging
from datetime import datetime, timezone
from telegram import Update, constants
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from .. import config
from ..services import llm_api

logger = logging.getLogger(__name__)

# --- Commands ---

# --- Helper Functions ---


def get_user_keys(user_id: int):
    """
    Generates unique keys for storage in chat_data based on the user’s ID.
    This allows each user to have their own context in a group.
    """
    return f"conversation_{user_id}", f"last_active_{user_id}"


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clears the conversation history."""

    # context.chat_data is a persistent dictionary in memory for this chat

    user_id = update.effective_user.id
    history_key, time_key = get_user_keys(user_id)

    context.chat_data[history_key] = []
    context.chat_data[time_key] = None

    await update.message.reply_text("♻️ Your conversation history has been cleared.")


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /ask command, supporting replies to other messages."""

    # 1. Text written by User B (who invokes the command)
    user_instruction = " ".join(context.args) if context.args else ""

    # 2. Text from User A (the replied message)
    reply_content = ""
    if update.message.reply_to_message:
        # Could be normal text or caption (text under photo/video)
        if update.message.reply_to_message.text:
            reply_content = update.message.reply_to_message.text
        elif update.message.reply_to_message.caption:
            reply_content = update.message.reply_to_message.caption

    # 3. Combination Logic
    final_prompt = ""

    if reply_content and user_instruction:
        # Case: Replying with instruction ("Summarize", "Translate", "Opinion")
        final_prompt = f"Original message context: '{reply_content}'\n\nMy instruction: {user_instruction}"
    elif reply_content and not user_instruction:
        # Case: Just /ask replying to a message
        final_prompt = f"Analyze and respond to this message: '{reply_content}'"
    elif user_instruction:
        # Case: Normal use without replying
        final_prompt = user_instruction
    else:
        # Case: No text and no reply
        await update.message.reply_text(
            "Please write a question or reply to a message with `/ask`."
        )
        return

    # Send to core logic
    await process_ai_interaction(update, context, final_prompt)


async def handle_private_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text messages in private chats without commands."""
    # Filter if it is a command (good practice even if PTB filters it)
    if update.message.text.startswith("/"):
        return
    await process_ai_interaction(update, context, update.message.text)


async def handle_group_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
):
    """
    Main function to manage AI interaction: history, API call, and response.
    """
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        history_key, time_key = get_user_keys(user_id)

        # 1. Visual Feedback (Typing...)
        await context.bot.send_chat_action(
            chat_id=chat_id, action=constants.ChatAction.TYPING
        )

        # 2. History Management using context.chat_data
        # Initialize if not exists (We start with an EMPTY list, no system message here)
        if history_key not in context.chat_data:
            context.chat_data[history_key] = []

        # Check inactivity time (1 hour)
        last_active = context.chat_data.get(time_key)
        current_time = datetime.now(timezone.utc)

        if last_active and (current_time - last_active).total_seconds() > 3600:
            context.chat_data[history_key] = []
            await update.message.reply_text(
                "🕒 Your chat history reset due to inactivity."
            )

        # 3. Update history
        context.chat_data[time_key] = current_time
        conversation = context.chat_data[history_key]

        # Append ONLY the user message to history
        conversation.append({"role": "user", "content": user_text})

        # Limit history (keep last 20 messages to save tokens)
        if len(conversation) > 20:
            context.chat_data[history_key] = conversation[-20:]
            conversation = context.chat_data[history_key]

        # 4. ASYNCHRONOUS API Call
        # We pass the SYSTEM_MESSAGE from config here.
        # This ensures updates to .env are applied immediately without clearing history.
        ai_response = await llm_api.get_api_llm(
            conversation,
            config.API_TOKEN,
            config.API_URL,
            config.LLM_MODEL,
            config.PROVIDER,
            MAX_OUTPUT_TOKENS=config.MAX_OUTPUT_TOKENS,
            system_message=config.SYSTEM_MESSAGE,
        )

        # 5. Save response and send
        conversation.append({"role": "assistant", "content": ai_response})

        await update.message.reply_text(ai_response, parse_mode="Markdown")

    except BadRequest as e:
        logger.warning(f"Markdown failed, Sending text plain. Error: {e}")
        try:
            await update.message.reply_text(ai_response)
        except Exception as e2:
            logger.error(f"Error sending the answer: {e2}")
            await update.message.reply_text("🚨 Error sending the answer")

    except Exception as e:
        logger.error("Error in AI handler: %s", e, exc_info=True)
        try:
            await update.message.reply_text("🚨 Sorry, technical problem")
        except:
            pass
