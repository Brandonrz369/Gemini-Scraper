"""Configuration settings for the Craigslist Lead Generator"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file located in the backend directory
# Assumes .env file is in the 'backend' directory, one level up from 'config'
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)


# Oxylabs credentials
OXYLABS_CONFIG = {
    'OXYLABS_USERNAME': 'brandonrz_FPQP5', # Updated username again as per user request
    'OXYLABS_PASSWORD': '+p0wer24fromJah',
    # Do not commit this file to version control!
}

# --- AI Filtering Configuration ---
# Ensure API keys are loaded from environment variables for security
# Add these to your backend/.env file
GEMINI_API_KEYS = [
    os.getenv('GEMINI_API_KEY_MARKETING'),
    os.getenv('GEMINI_API_KEY_SUPPORT'),
    os.getenv('GEMINI_API_KEY_BRANDONL'),
    os.getenv('GEMINI_API_KEY_BRANDONLB'),
]
# Filter out None values in case some keys are not set
GEMINI_API_KEYS = [key for key in GEMINI_API_KEYS if key]

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

AI_CONFIG = {
    'GEMINI_MODEL': "gemini-2.5-pro-exp-03-25", # User specified Gemini model
    'OPENROUTER_BASE_URL': "https://openrouter.ai/api/v1",
    'OPENROUTER_MODEL': "openrouter/optimus-alpha", # Default OpenRouter fallback model
    'KEY_CYCLE_COOLDOWN_MINUTES': 20, # Cooldown before retrying Gemini keys
    # API Keys are now loaded directly above and passed to the handler
}
# --- End AI Filtering Configuration ---


# Pre-filtering settings
PRE_FILTER_CONFIG = {
    'BLACKLIST_TERMS': [ # Terms indicating likely junk/unrelated posts
        'hiring', 'job', 'position', 'intern', 'internship', 'career', 'opportunity',
        'tester', 'testers', 'survey', 'study', 'research', 'participant', 'participants',
        'selling', 'sale', 'buy', 'collectible', 'antique', 'vintage', 'art piece',
        'class', 'workshop', 'course', 'instructor', 'teach', 'learn',
        'dating', 'model', 'models', 'actor', 'actress', 'casting', 'photoshoot',
        'investment', 'partner', 'funding', 'relief', 'cash machine', 'side hustle',
        'paid per location', 'commission', 'loan officer', 'recruiter', 'telemarketing',
        'assistant', 'manager', 'coordinator', 'operator', 'representative',
        'seeking roommate', 'seeking relationship', 'personal ad',
        'jailbreak', 'grapheneos', 'mobile app', 'game tester'
        # Add more terms as needed
    ]
}

# Census API Key (Removed as dynamic fetching is disabled for now)
# CENSUS_API_KEY = "a2d7b3e482533611f6840b0af121066656909d84"

# Search parameters
SEARCH_CONFIG = {
    'BASE_TERMS': [
        "website", "website needed", "web developer", "web design",
        "web designer", "graphic design", "graphic designer",
        "logo design", "WordPress", "Shopify", "ecommerce", # Added WordPress, Shopify
        "landing page", "UX/UI", "branding", "business cards",
        "marketing materials", "photoshop", "GoDaddy" # Added photoshop, GoDaddy
    ],
    'MAX_AGE_DAYS': 7,
    # Expanded categories: web, gigs, creative, computer, services, software, marketing, business, writing
    # Added 'art' (art/media/design) and reordered for testing
    'CATEGORIES': ['web', 'art', 'crg', 'cpg', 'mar', 'gig', 'sad', 'sof', 'bus', 'wri'], # Reordered for test
}

# State management settings
STATE_CONFIG = {
    # Paths are relative to the backend directory now
    'DATABASE_FILE': 'data/leads.db', # Path to the SQLite database file
    # 'CHECKPOINT_FREQUENCY': 10, # Removed, saving is more granular now
}
