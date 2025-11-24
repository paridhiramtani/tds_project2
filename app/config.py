import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# Server Config
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Security
USER_SECRET = os.getenv("USER_SECRET", "default_secret")

# Limits
MAX_RETRIES = 3
GLOBAL_TIMEOUT_SECONDS = 300  # 5 minutes
TOKEN_BUDGET_LIMIT = 2.0      # $2.00

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
