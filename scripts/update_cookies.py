import os
import sys
import logging
import argparse
from pathlib import Path

# ========== Setup Environment ==========
# Add 'src' to python path to import config
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root / 'src'))

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("CookieUpdater")

try:
    from telegram_bot.config import supabase
except ImportError:
    logger.error("❌ ERROR: Could not import 'config.py'.")
    logger.error("Make sure you are running this from the project root or 'scripts/' folder.")
    sys.exit(1)

# ========== Constants ==========
TABLE_NAME = "cookies"
ID_COLUMN = "name_media"
ID_VALUE = "Youtube/Instagram" # Unique Key
DATA_COLUMN = "cookies_data"
DEFAULT_FILENAME = "cookies.txt"

def parse_arguments():
    """Defines command line arguments."""
    parser = argparse.ArgumentParser(description="Upload cookies.txt to Supabase for yt-dlp.")
    parser.add_argument("-f", "--file", type=str, help="Specific path to the cookies.txt file", default=None)
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    return parser.parse_args()

def find_cookie_file(user_path=None):
    """
    Smart search for the cookie file in common locations.
    """
    search_paths = []

    # 1. User provided path
    if user_path:
        search_paths.append(Path(user_path))

    # 2. Current Working Directory
    search_paths.append(Path.cwd() / DEFAULT_FILENAME)

    # 3. Project Root
    search_paths.append(project_root / DEFAULT_FILENAME)

    # 4. Scripts Directory
    search_paths.append(current_dir / DEFAULT_FILENAME)

    # 5. User Downloads Folder (Common export location)
    home = Path.home()

    search_paths.append(home / "Downloads" / DEFAULT_FILENAME)

    logger.info("🔍 Searching for cookie file...")
    
    for path in search_paths:
        if path.exists() and path.is_file():
            return path
            
    return None

def validate_netscape_format(content: str) -> bool:
    """
    Basic validation to check if it looks like a Netscape cookie file.
    yt-dlp requires Netscape format (tab separated).
    """
    lines = content.splitlines()
    if not lines:
        return False

    # Check 1: Common Header
    if "# Netscape HTTP Cookie File" in lines[0] or "# Netscape HTTP Cookie File" in lines[1]:
        return True

    # Check 2: Heuristic - Look for 7 tab-separated columns in non-comment lines
    valid_lines = 0
    for line in lines:
        if line.strip().startswith("#") or not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) >= 7:
            valid_lines += 1
            
    return valid_lines > 0

def update_cookies():
    args = parse_arguments()

    # 1. Check Supabase
    if not supabase:
        logger.error("❌ Supabase client is not configured. Check your .env file.")
        return

    # 2. Find File
    cookie_path = find_cookie_file(args.file)
    
    if not cookie_path:
        logger.error("❌ Cookie file not found.")
        logger.info(f"   Please place '{DEFAULT_FILENAME}' in the project root, scripts folder, or Downloads.")
        logger.info("   Or use: python scripts/update_cookies.py --file /path/to/cookies.txt")
        return

    logger.info(f"✅ Found file at: {cookie_path}")

    # 3. Read and Validate
    try:
        content = cookie_path.read_text(encoding="utf-8")
        
        if not validate_netscape_format(content):
            logger.warning("⚠️  WARNING: The file d
