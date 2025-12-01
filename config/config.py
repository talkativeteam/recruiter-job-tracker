"""
System Configuration
Central configuration for the Recruiter ICP Job Tracker Agent
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
TMP_DIR = BASE_DIR / ".tmp"
LOGS_DIR = BASE_DIR / "logs"
DIRECTIVES_DIR = BASE_DIR / "directives"
EXECUTION_DIR = BASE_DIR / "execution"

# Ensure directories exist
TMP_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
(TMP_DIR / "scraped_jobs").mkdir(exist_ok=True)
(TMP_DIR / "filtered_companies").mkdir(exist_ok=True)
(TMP_DIR / "decision_makers").mkdir(exist_ok=True)
(TMP_DIR / "final_output").mkdir(exist_ok=True)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APIFY_API_KEY = os.getenv("APIFY_API_KEY")
EXA_API_KEY = os.getenv("EXA_API_KEY")
BRIGHT_DATA_API_KEY = os.getenv("BRIGHT_DATA_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Agent configuration
AGENT_NAME = "recruiter-job-tracker"
DEFAULT_MAX_JOBS = 100
MAX_JOBS_LIMIT = 400

# AI Models
MODEL_CHEAP = "gpt-4o-mini"  # For most tasks
MODEL_PREMIUM = "gpt-4-turbo-preview"  # For client-facing content - fast, solid

# API Timeouts (seconds)
TIMEOUT_HTTP = 30
TIMEOUT_PLAYWRIGHT = 90
TIMEOUT_AI_API = 60
TIMEOUT_APIFY = 120

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds (exponential backoff base)

# Company filtering
MAX_COMPANY_SIZE = 100  # employees

# LinkedIn search parameters
LINKEDIN_BASE_URL = "https://www.linkedin.com/jobs/search/"
LINKEDIN_TIME_FILTER_24H = "r86400"  # Last 24 hours (default - fresher results)
LINKEDIN_TIME_FILTER_7D = "r604800"  # Last 7 days (fallback if 24h has insufficient results)
LINKEDIN_JOB_TYPE = "F"  # Full-time

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Cost tracking (approximate)
COST_OPENAI_GPT4_MINI = 0.00015  # per 1K input tokens
COST_OPENAI_GPT4_TURBO = 0.01  # per 1K input tokens
COST_APIFY_PER_RUN = 0.05  # approximate
COST_EXA_PER_SEARCH = 0.001
COST_BRIGHT_DATA_PER_REQUEST = 0.01  # approximate

# Validation
def validate_config():
    """Validate that all required configuration is present"""
    required_keys = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "APIFY_API_KEY": APIFY_API_KEY,
        "EXA_API_KEY": EXA_API_KEY,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
    }
    
    missing = [key for key, value in required_keys.items() if not value]
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    return True

if __name__ == "__main__":
    try:
        validate_config()
        print("✅ Configuration validated successfully")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
