from telegram.ext import filters

class _TargetedOrPrivateFilter(filters.MessageFilter):
    """
    Custom filter for PTB v20+.
    
    Allows the command execution if:
    1. It is a private chat.
    2. It is a group AND the command explicitly mentions the bot (e.g., /start@botname).
    """
    def filter(self, message):
        """
        Determines if the message should be processed based on chat type and command format.
        """
        # Safety check if message has no text
        if not message or not message.text:
            return False

        # 1. In Private chats, always allow commands
        if message.chat.type == 'private':
            return True
            
        # 2. In Groups, verify if there is an explicit mention
        # Get the first word (the command itself)
        command_part = message.text.split()[0]
        
        # If it contains '@', return True.
        return '@' in command_part

# Instantiate the class to export it as a ready-to-use filter object
TARGETED_OR_PRIVATE = _TargetedOrPrivateFilter()
