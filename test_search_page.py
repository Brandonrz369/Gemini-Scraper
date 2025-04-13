# test_search_page.py
import os
import sys
import logging
from dotenv import load_dotenv

# --- Setup Paths and Environment ---
# Assume this script is run from the gemini-scraper directory
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_dir) # Add backend directory to path

# Load environment variables from backend/.env
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f"Loaded environment variables from {dotenv_path}")
else:
    logging.warning(f".env file not found at {dotenv_path}. API keys might be missing.")

# Configure basic logging (DEBUG level to see the new logs) - Keep for module logs if they work
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

# Use print for direct script output confirmation
print("Attempting module imports...")
try:
    # Import necessary components AFTER setting path and loading env
    from modules.request_handler import RequestHandler
    from modules.content_analyzer import ContentAnalyzer
    from config.settings import OXYLABS_CONFIG, SEARCH_CONFIG # Import necessary configs
    print("Modules imported successfully.")
except ImportError as e:
    print(f"CRITICAL: Error importing modules: {e}")
    print("Ensure you are running this script from the 'gemini-scraper' directory")
    sys.exit(1)

# --- Test Parameters ---
test_city_code = "losangeles" # Use the correct code
test_category = "cpg"
test_url = f"https://{test_city_code}.craigslist.org/search/{test_category}"

# --- Main Test Logic ---
def run_test():
    print("Initializing Request Handler and Content Analyzer...")
    request_handler = RequestHandler(OXYLABS_CONFIG)
    # Pass SEARCH_CONFIG to ContentAnalyzer if its __init__ expects it
    content_analyzer = ContentAnalyzer({'SEARCH_CONFIG': SEARCH_CONFIG})
    print("Handlers Initialized.")

    print(f"Fetching search page: {test_url}")
    html_content = request_handler.get_page(test_url)

    if not html_content:
        print(f"ERROR: Failed to fetch HTML content for {test_url}. Exiting test.")
        return

    print(f"Parsing search page for city '{test_city_code}'...")
    # Call the parse_search_page method
    # No need to limit leads for this test, we want to see everything parsed on page 1
    potential_leads, next_page = content_analyzer.parse_search_page(html_content, test_city_code)

    print("-" * 30)
    print(f"Parsing complete. Found {len(potential_leads)} potential leads on the first page.")
    print("Extracted Lead URLs:")
    if potential_leads:
        for i, lead in enumerate(potential_leads):
            print(f"  {i+1}: {lead.get('url', 'N/A')} (Title: {lead.get('title', 'N/A')})")
    else:
        print("  No leads extracted.")
    print("-" * 30)

    # Optionally, check if the specific lead was found
    target_lead_url_part = "7841430579.html" # From the Wordpress/Elementor lead
    found_target = any(target_lead_url_part in lead.get('url', '') for lead in potential_leads)

    if found_target:
        print(f"SUCCESS: The target lead containing '{target_lead_url_part}' WAS found by the parser on page 1.")
    else:
        print(f"WARNING: The target lead containing '{target_lead_url_part}' was NOT found by the parser on page 1.")


if __name__ == "__main__":
    print("--- test_search_page.py script started ---")
    run_test()
    print("--- test_search_page.py script finished ---")
