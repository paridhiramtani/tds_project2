import os

# API Keys
# --- FIX: Add .strip() to remove accidental spaces/newlines ---
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN", "").strip() or None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip() or None

# If using AIProxy, set the base URL
OPENAI_BASE_URL = "https://aiproxy.sanand.workers.dev/openai/v1" if AIPROXY_TOKEN else "https://api.openai.com/v1"

# Application Settings
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8000))

# Timeout settings
BROWSER_TIMEOUT = 60000 
SUBMISSION_TIMEOUT = 180
