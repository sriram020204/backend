import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Required environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-here")

# Validate required variables
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file")

if not MONGO_URI:
    raise ValueError("❌ MONGO_URI not found in .env file")

if not MONGO_DB_NAME:
    raise ValueError("❌ MONGO_DB_NAME not found in .env file")