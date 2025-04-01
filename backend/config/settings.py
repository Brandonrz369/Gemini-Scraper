"""Configuration settings for the Craigslist Lead Generator"""

# Oxylabs credentials
OXYLABS_CONFIG = {
    'OXYLABS_USERNAME': 'brandonrz_J8EYk', # Corrected username based on successful curl test
    'OXYLABS_PASSWORD': '+p0wer24fromJah',
    # Do not commit this file to version control!
}

# AI Filtering Configuration (Using OpenRouter)
AI_CONFIG = {
    'API_KEY': "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", # Keep existing key
    'BASE_URL': "https://openrouter.ai/api/v1",
    'MODEL_NAME': "anthropic/claude-3-haiku" # Try simpler model ID for OpenRouter
    # Do not commit API keys to version control!
}

# Census API Key (Removed as dynamic fetching is disabled for now)
# CENSUS_API_KEY = "a2d7b3e482533611f6840b0af121066656909d84"

# Search parameters
SEARCH_CONFIG = {
    'BASE_TERMS': [
        "website", "website needed", "web developer", "web design",
        "web designer", "graphic design", "graphic designer",
        "logo design", "WordPress", "Shopify", "ecommerce",
        "landing page", "UX/UI", "branding", "business cards",
        "marketing materials"
    ],
    'MAX_AGE_DAYS': 7,
    # Expanded categories: web, gigs, creative, computer, services, software, marketing, business, writing
    'CATEGORIES': ['web', 'gig', 'crg', 'cpg', 'sad', 'sof', 'mar', 'bus', 'wri'],
}

# State management settings
STATE_CONFIG = {
    # Paths are relative to the backend directory now
    'DATABASE_FILE': 'data/leads.db', # Path to the SQLite database file
    # 'CHECKPOINT_FREQUENCY': 10, # Removed, saving is more granular now
}
