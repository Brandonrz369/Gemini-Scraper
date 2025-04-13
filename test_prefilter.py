print("--- test_prefilter.py script started ---") # ADDED PRINT
# test_prefilter.py
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

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    # Import necessary components AFTER setting path and loading env
    from modules.ai_handler import AIHandler
    from config.settings import AI_CONFIG # Import AI_CONFIG directly
    logging.info("AIHandler imported successfully.")
except ImportError as e:
    logging.critical(f"Error importing modules: {e}", exc_info=True)
    logging.critical("Ensure you are running this script from the 'gemini-scraper' directory")
    sys.exit(1)

# --- Test Data ---
test_title = "Need Wordpress/Elementor Help to Perfect Website with Small Tweaks"
test_snippet = None # Snippet is often not available in the current script logic

# --- Main Test Logic ---
def run_test():
    logging.info("Initializing AI Handler...")
    # Pass the AI_CONFIG directly
    ai_handler = AIHandler({'AI_CONFIG': AI_CONFIG}) # Pass config dict expected by AIHandler
    logging.info(f"AI Handler Initialized. Active Service: {ai_handler.active_service}")

    print(f"AI Handler active_service: {ai_handler.active_service}")
    if ai_handler.active_service == 'disabled':
        print("AI Service is disabled (likely missing API key). Cannot run pre-filter test.")
        return

    print(f"Testing grade_lead with title: '{test_title}'")
    # Using a placeholder description as we don't have the real one
    placeholder_description = "Looking for help with WordPress and Elementor website tweaks."

    # Call the grade_lead method
    grade_result = ai_handler.grade_lead(test_title, placeholder_description)

    print("-" * 30)
    if grade_result is None:
        print("AI grading call failed definitively after retries.")
    else:
        print(f"AI Grading Result for '{test_title}':")
        print(f"  Is Junk: {grade_result.get('is_junk', 'N/A')}")
        print(f"  Score: {grade_result.get('profitability_score', 'N/A')}")
        print(f"  Reasoning: {grade_result.get('reasoning', 'N/A')}")
        if grade_result.get('is_junk'):
             print("Conclusion: The AI grading considers this lead JUNK.")
        else:
             print("Conclusion: The AI grading considers this lead RELEVANT.")

    print("-" * 30)

if __name__ == "__main__":
    run_test()
    print("--- test_prefilter.py script finished ---") # ADDED PRINT
