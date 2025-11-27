import os

# API Keys
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# If using AIProxy, we might need to set the base URL
OPENAI_BASE_URL = "https://aiproxy.sanand.workers.dev/openai/v1" if AIPROXY_TOKEN else "https://api.openai.com/v1"

# Application Settings
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8000))

# Timeout settings
BROWSER_TIMEOUT = 60000  # 60 seconds
SUBMISSION_TIMEOUT = 180  # 3 minutes total for the task
