import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file before reading config
load_dotenv()


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SCREENSHOTS_DIR = STATIC_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = BASE_DIR / "qa_assistant.db"

# Server configuration
PORT = int(os.environ.get("PORT", 5000))
HOST = os.environ.get("HOST", "0.0.0.0")
DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")

# Cryptographically secure fallback secret key
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    # Use persistent generated key or generate random bytes
    SECRET_KEY = os.environ.get("APP_SECRET", secrets.token_hex(32))

# Session Cookie Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

# Target Application URL (defaults to built-in target store)
TARGET_APP_DEFAULT_URL = f"http://127.0.0.1:{PORT}/app/target-store"

# URL Whitelist & SSRF Security Config
ALLOWED_TARGET_DOMAINS = os.environ.get("ALLOWED_DOMAINS", "localhost,127.0.0.1,0.0.0.0,192.168.").split(",")
ALLOW_EXTERNAL_TARGET_URLS = os.environ.get("ALLOW_EXTERNAL_URLS", "false").lower() in ("1", "true", "yes")

# AI Configuration (Optional Gemini / OpenAI key)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
AI_PROVIDER = os.environ.get("AI_PROVIDER", "hybrid")  # hybrid, gemini, openai, heuristic
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-3.8-flash")

# AI Fallback: when True, the Offline Heuristic Engine activates on any online provider failure.
# When False, failures surface as errors without silent substitution.
AI_FALLBACK_ENABLED = os.environ.get("AI_FALLBACK_ENABLED", "true").lower() in ("1", "true", "yes")

# Asynchronous Test Runner Configuration
DEFAULT_PER_TEST_TIMEOUT_SEC = int(os.environ.get("TEST_TIMEOUT", 15))
MAX_EXECUTION_QUEUE_WORKERS = int(os.environ.get("QUEUE_WORKERS", 2))
