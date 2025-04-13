# test_ads_lead.py
import os
import sys
from dotenv import load_dotenv

# Setup paths and environment
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_dir)
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

try:
    from modules.ai_handler import AIHandler
    from config.settings import AI_CONFIG
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Test data: ad setup lead
test_title = "Help needed to set up Google Ads for my business"
test_snippet = "Looking for someone to set up and manage Google Ads campaigns. Must have experience with PPC and digital marketing."
test_description = """
I need help setting up Google Ads for my small business. Tasks include:
- Creating new ad campaigns
- Keyword research
- Setting up conversion tracking
- Ongoing optimization and reporting
Experience with AdWords, PPC, and digital marketing required.
"""

def run_test():
    ai_handler = AIHandler({'AI_CONFIG': AI_CONFIG})
    print(f"AI Handler active_service: {ai_handler.active_service}")

    # Step 1: Pre-filter (using the current prompt)
    print(f"\nTesting pre_filter_lead with title: '{test_title}'")
    is_relevant = ai_handler.pre_filter_lead(test_title, test_snippet)
    print(f"Pre-filter result: {is_relevant}")

    # Step 2: Full AI grading (if passed)
    if is_relevant:
        print("\nTesting grade_lead with title and description...")
        grade_result = ai_handler.grade_lead(test_title, test_description)
        print("AI Grading Result:")
        print(f"  Is Junk: {grade_result.get('is_junk', 'N/A')}")
        print(f"  Score: {grade_result.get('profitability_score', 'N/A')}")
        print(f"  Reasoning: {grade_result.get('reasoning', 'N/A')}")
    else:
        print("Lead did not pass pre-filter, skipping full AI grading.")

if __name__ == "__main__":
    run_test()
