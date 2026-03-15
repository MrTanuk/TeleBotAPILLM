from telegram import Message
from telegram.ext import filters


class _TargetedOrPrivateFilter(filters.MessageFilter):
    """
    Custom filter for PTB v20+.

    Allows the command execution if:
    1. It is a private chat.
    2. It is a group AND the command explicitly mentions the bot (e.g., /start@botname).
    """

    def filter(self, message: Message) -> bool:
        """
        Determines if the message should be processed based on chat type and command format.
        Returns True if the message passes the filter, False otherwise.
        """
        if not message or not message.text:
            return False

        if message.chat.type == "private":
            return True

        command_part = message.text.split()[0]
        return "@" in command_part


TARGETED_OR_PRIVATE = _TargetedOrPrivateFilter()
