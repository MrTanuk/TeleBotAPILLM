import logging
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def setup_logging() -> None:
    """Configures the global logging settings."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    # Silence httpx info logs to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)


# --- Credentials ---
BOT_TOKEN = str(os.getenv("BOT_TOKEN"))
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not defined in the environment.")

# --- LLM Configuration ---
PROVIDER = os.getenv("PROVIDER")
API_TOKEN = os.getenv("API_TOKEN")
LLM_MODEL = os.getenv("LLM_MODEL")
SYSTEM_MESSAGE = os.getenv("SYSTEM_MESSAGE")

MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", 700))
_BASE_API_URL = os.getenv("API_URL")

API_URL = ""
if PROVIDER and PROVIDER.lower() == "google":
    if _BASE_API_URL and LLM_MODEL and API_TOKEN:
        API_URL = f"{_BASE_API_URL}/{LLM_MODEL}:generateContent?key={API_TOKEN}"
else:
    # For OpenAI/DeepSeek/Groq
    API_URL = _BASE_API_URL if _BASE_API_URL else ""

# --- Webhook & Hosting Configuration ---
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

PORT = int(os.environ.get("PORT", 8080))

HOSTING = os.environ.get("HOSTING", "development")
