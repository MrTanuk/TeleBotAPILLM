# --- Helper Functions ---
import telebot
from ..config import BOT_NAME


def is_valid_command(message):
    """Differentiates commands intended for this bot from others in a group."""
    command = telebot.util.extract_command(message.text)
    if not command:
        return False

    user_command = message.text.partition(" ")[0].replace("/", "")
    complete_command = f"{command}@{BOT_NAME}"
    is_group = message.chat.type in ["group", "supergroup"]

    if is_group:
        return user_command == complete_command
    else:  # Private chat
        return user_command in (command, complete_command)


def extract_arguments(message):
    """Extracts arguments from a command or the full text if it's not a command."""
    if message.text.startswith("/"):
        return telebot.util.extract_arguments(message.text)
    else:
        return message.text.strip()
