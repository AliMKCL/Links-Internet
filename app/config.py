import os
from dotenv import load_dotenv

load_dotenv()

# Reddit API credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

# OpenAI API keys
OPENAI_KEY = os.getenv("OPENAI_KEY")
OPENAI_KEY_DB = os.getenv("OPENAI_KEY_DB")