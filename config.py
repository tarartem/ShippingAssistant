import os
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER", "amyfreecat@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "ftbocmxttnxeymql")
GMAIL_IMAP_SERVER = os.getenv("GMAIL_IMAP_SERVER", "imap.gmail.com")
GMAIL_IMAP_PORT = int(os.getenv("GMAIL_IMAP_PORT", "993"))

PORT = os.getenv("PORT", "3000")
WHATSAPP_BRIDGE_URL = f"http://127.0.0.1:{PORT}"
WHATSAPP_TARGET_GROUP = os.getenv("WHATSAPP_TARGET_GROUP", "")

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
DEBUG = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
