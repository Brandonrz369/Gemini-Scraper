import os
import sys
import logging

# Add backend directory to sys.path to allow imports
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# Configure logging minimally to avoid errors if StateManager logs something
logging.basicConfig(level=logging.INFO)

try:
    from modules.state_manager import StateManager
    from config.settings import STATE_CONFIG, AI_CONFIG, SEARCH_CONFIG, OXYLABS_CONFIG, PRE_FILTER_CONFIG # Import all configs StateManager might need directly or indirectly

    # Combine configs as StateManager might expect a single dict
    config = {
        'STATE_CONFIG': STATE_CONFIG,
        'AI_CONFIG': AI_CONFIG,
        'SEARCH_CONFIG': SEARCH_CONFIG,
        'OXYLABS_CONFIG': OXYLABS_CONFIG,
        'PRE_FILTER_CONFIG': PRE_FILTER_CONFIG
    }

    # Ensure the data directory exists
    data_dir = os.path.join(backend_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    state_manager = StateManager(config)
    last_city = state_manager.get_last_completed_city()
    if last_city:
        print(f"LAST_COMPLETED_CITY:{last_city}")
    else:
        print("LAST_COMPLETED_CITY:None")
    # Removed state_manager.close_db() call as the method doesn't exist
except ImportError as e:
    print(f"ImportError: {e}. Make sure modules are accessible and requirements are installed.")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)
