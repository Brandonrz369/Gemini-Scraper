"""Configuration settings for the Craigslist Lead Generator"""

# Oxylabs credentials
OXYLABS_CONFIG = {
    'OXYLABS_USERNAME': 'brandonrz_FPQP5', # Updated username again as per user request
    'OXYLABS_PASSWORD': '+p0wer24fromJah',
    # Do not commit this file to version control!
}

# AI Filtering Configuration (Using OpenRouter)
AI_CONFIG = {
    'API_KEY': "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", # Updated API Key
    'BASE_URL': "https://openrouter.ai/api/v1",
    'MODEL_NAME': "anthropic/claude-3-haiku" # Try simpler model ID for OpenRouter
    # Do not commit API keys to version control!
}

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
