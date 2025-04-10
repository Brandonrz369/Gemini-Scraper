# main.py (in backend/)
import time
import sys
import os
import random
import logging
import multiprocessing
import shutil
import subprocess
import argparse
import concurrent.futures # Added for ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urljoin

# --- Project Root Definition ---
project_root = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(project_root)

# --- Configure Logging ---
log_file = os.path.join(project_root, 'run.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.info("Logging configured.")

logging.info("Attempting module imports...")
try:
    # Import PRE_FILTER_CONFIG as well
    from config.settings import OXYLABS_CONFIG, SEARCH_CONFIG, STATE_CONFIG, AI_CONFIG, PRE_FILTER_CONFIG
    from modules.city_manager import CityManager
    from modules.request_handler import RequestHandler
    from modules.content_analyzer import ContentAnalyzer
    from modules.state_manager import StateManager
    from modules.output_generator import OutputGenerator
    from modules.ai_handler import AIHandler
    logging.info("Module imports successful.")
except ImportError as e:
    logging.critical(f"Error importing modules: {e}", exc_info=True)
    logging.critical("Ensure you are running this script from the 'Gemini-Scraper/backend' directory")
    logging.critical("or that the necessary modules/config are in the correct subdirectories.")
    sys.exit(1)

# --- Lead Processing Helper Function (for ThreadPoolExecutor) ---
def process_single_lead(basic_lead_info, worker_request_handler, worker_content_analyzer, worker_ai_handler, worker_name):
    """Fetches details grades and prepares a single lead dictionary."""
    lead_url = basic_lead_info.get('url')
    if not lead_url:
        logging.warning(f"[{worker_name}] Skipping potential lead: Missing URL.")
        return None, None # Indicate failure/skip

    # Use different log prefix for threaded operations
    log_prefix = f"[{worker_name}-Thread]"

    # --- Add City Domain Check ---
    # Extract city code from the worker_args passed to scrape_city_worker
    # This requires modifying scrape_city_worker to pass city_code down or accessing it differently.
    # Let's modify process_single_lead signature for simplicity here.
    # We need city_code in this function scope. Let's pass it in worker_args and extract it.
    # RETHINK: Modifying scrape_city_worker args is better. Let's assume city_code is passed down.
    # We'll modify the call signature later. For now, assume city_code is available.
    # --- This approach is complex. Let's check the URL domain directly ---
    from urllib.parse import urlparse
    parsed_url = urlparse(lead_url)
    expected_domain = f"{basic_lead_info.get('city_code', 'unknown')}.craigslist.org" # Assume city_code is added to basic_lead_info
    if parsed_url.netloc != expected_domain:
        logging.warning(f"{log_prefix} Skipping lead from different city: {lead_url} (Expected domain: {expected_domain})")
        return None, None # Indicate skip

    logging.info(f"{log_prefix} Fetching lead details: {basic_lead_info.get('title', 'Untitled')} ({lead_url})")
    lead_page_html = worker_request_handler.get_page(lead_url)

    if not lead_page_html:
        logging.warning(f"{log_prefix} Failed to fetch lead detail page: {lead_url}. Skipping lead.")
        return None, None # Indicate failure/skip

    full_lead_details = worker_content_analyzer.analyze_lead_details(lead_page_html, basic_lead_info)

    # AI Grading Step
    ai_grade_result = None
    if worker_ai_handler and worker_ai_handler.client:
        logging.debug(f"{log_prefix} Sending lead to AI for grading: {lead_url}")
        ai_grade_result = worker_ai_handler.grade_lead(
            full_lead_details.get('title', ''),
            full_lead_details.get('description', '')
        )
        full_lead_details['ai_grade'] = ai_grade_result
    else:
        full_lead_details['ai_grade'] = {"is_junk": False, "profitability_score": None, "reasoning": "AI disabled"}

    # Return processed details (including grade) and the grade result separately for filtering logic
    return full_lead_details, ai_grade_result

# --- Worker Function for Parallel Processing (Refactored for Threading) ---
def scrape_city_worker(worker_args):
    """
    Worker function to scrape categories (with pagination) for a single city.
    Uses ThreadPoolExecutor to process leads found on each page in parallel.
    """
    # Unpack args (added limit_leads_per_page and search_scope)
    city_info, config, limit_pages, limit_categories, limit_leads_per_page, num_threads, search_scope = worker_args
    city_code = city_info.get('code')
    city_name = city_info.get('name', city_code)
    worker_name = multiprocessing.current_process().name
    logging.info(f"[{worker_name}] Starting worker for city: {city_name} ({city_code})")

    worker_state_manager = None
    worker_ai_handler = None
    city_leads_found_total = 0
    try:
        worker_state_manager = StateManager(config)
        worker_request_handler = RequestHandler(config['OXYLABS_CONFIG'])
        worker_content_analyzer = ContentAnalyzer(config)
        worker_ai_handler = AIHandler(config)

        if not city_code:
            logging.warning(f"[{worker_name}] Skipping city: Missing 'code' in city_info {city_info}")
            return (city_code, 0)

        # Determine categories to process
        all_categories = config['SEARCH_CONFIG'].get('CATEGORIES', [])
        categories_to_process = all_categories[:limit_categories] if limit_categories is not None else all_categories
        if limit_categories is not None:
             logging.warning(f"[{worker_name}] Limiting to first {len(categories_to_process)} categories based on --limit-categories argument.")

        for category_code in categories_to_process:
            current_page = 1
            next_page_url = f"https://{city_code}.craigslist.org/search/{category_code}"
            processed_category_leads = 0
            max_pages_to_scrape = limit_pages # Use the passed limit

            while next_page_url and current_page <= max_pages_to_scrape:
                logging.info(f"[{worker_name}] Fetching category: {category_code} (Page {current_page}/{max_pages_to_scrape}) -> {next_page_url}")
                search_page_html = worker_request_handler.get_page(next_page_url)
                if not search_page_html:
                    logging.warning(f"[{worker_name}] Failed to fetch search page {current_page} for {city_code}/{category_code}. Skipping rest of category.")
                    break

                logging.info(f"[{worker_name}] Parsing search results page {current_page} for {city_code}/{category_code}...")
                potential_leads_count_page = 0
                processed_leads_count_page = 0
                # Pass limit_leads_per_page to the parser
                leads_on_page_basic = worker_content_analyzer.parse_search_page(search_page_html, city_code, limit_leads_per_page)

                # Add city_code to each basic lead info dict for domain checking later
                leads_on_page = []
                for lead in leads_on_page_basic:
                    lead['city_code'] = city_code
                    leads_on_page.append(lead)


                # --- Pre-filter leads based on title/blacklist before AI pre-filter ---
                pre_filtered_leads_basic = []
                blacklist = config.get('PRE_FILTER_CONFIG', {}).get('BLACKLIST_TERMS', [])
                if leads_on_page:
                    potential_leads_count_page = len(leads_on_page)
                    logging.info(f"[{worker_name}] Basic Pre-filtering {potential_leads_count_page} leads from page...")
                    for lead_info in leads_on_page:
                        title = lead_info.get('title', '').lower()
                        # Basic blacklist check
                        if any(term in title for term in blacklist):
                            logging.info(f"[{worker_name}] Basic pre-filtered out (blacklist term): {lead_info.get('url')}")
                            continue # Skip this lead entirely
                        pre_filtered_leads_basic.append(lead_info)
                    logging.info(f"[{worker_name}] {len(pre_filtered_leads_basic)} leads passed basic pre-filtering.")
                else:
                    pre_filtered_leads_basic = []

                # --- AI Pre-filter remaining leads ---
                pre_filtered_leads_ai = []
                if pre_filtered_leads_basic:
                    logging.info(f"[{worker_name}] AI Pre-filtering {len(pre_filtered_leads_basic)} leads...")
                    for lead_info in pre_filtered_leads_basic:
                        title = lead_info.get('title', '')
                        # Using None for snippet as parse_search_page doesn't extract it yet
                        is_potentially_relevant = worker_ai_handler.pre_filter_lead(title, None)
                        if is_potentially_relevant:
                            pre_filtered_leads_ai.append(lead_info)
                        else:
                            logging.info(f"[{worker_name}] AI pre-filtered out (junk/unrelated): {lead_info.get('url')}")
                    logging.info(f"[{worker_name}] {len(pre_filtered_leads_ai)} leads passed AI pre-filtering.")
                else:
                     pre_filtered_leads_ai = []


                # --- Process AI-pre-filtered leads on this page in parallel using threads ---
                if pre_filtered_leads_ai:
                    logging.info(f"[{worker_name}] Processing {len(pre_filtered_leads_ai)} AI pre-filtered leads using {num_threads} threads...")
                    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                        future_to_lead = {
                            executor.submit(process_single_lead, lead_info, worker_request_handler, worker_content_analyzer, worker_ai_handler, worker_name): lead_info
                            for lead_info in pre_filtered_leads_ai # Use pre_filtered_leads_ai here
                        }
                        for future in concurrent.futures.as_completed(future_to_lead):
                            original_lead_info = future_to_lead[future]
                            try:
                                full_lead_details, ai_grade_result = future.result()
                                if full_lead_details is None: continue # Skip if processing failed

                                # Add the category code to the details before saving
                                full_lead_details['category'] = category_code

                                # Add lead to DB (still done sequentially by main worker thread after thread finishes)
                                # Pass search_scope to add_lead
                                if ai_grade_result is not None and not ai_grade_result.get('is_junk', True):
                                    if worker_state_manager.add_lead(full_lead_details, search_scope=search_scope):
                                        city_leads_found_total += 1
                                        processed_leads_count_page += 1
                                        score = ai_grade_result.get('profitability_score', 'N/A')
                                        logging.info(f"[{worker_name}] Added graded lead (Score: {score}): {full_lead_details.get('url')}")
                                elif ai_grade_result and ai_grade_result.get('is_junk'):
                                    score = ai_grade_result.get('profitability_score', 'N/A')
                                    reason = ai_grade_result.get('reasoning', 'No reason provided')
                                    logging.info(f"[{worker_name}] Skipping junk lead (AI Filter Score: {score}, Reason: {reason}): {full_lead_details.get('url')}")
                                elif ai_grade_result is None and worker_ai_handler and worker_ai_handler.client:
                                     logging.error(f"[{worker_name}] Skipping lead due to AI grading failure: {full_lead_details.get('url')}")
                                elif not worker_ai_handler or not worker_ai_handler.client:
                                     # Ensure category is added even if AI is disabled
                                     full_lead_details['category'] = category_code
                                     # Pass search_scope to add_lead
                                     if worker_state_manager.add_lead(full_lead_details, search_scope=search_scope):
                                        city_leads_found_total += 1
                                        processed_leads_count_page += 1
                                        logging.info(f"[{worker_name}] Added lead (AI Disabled): {full_lead_details.get('url')}")
                            except Exception as exc:
                                lead_url = original_lead_info.get('url', 'unknown URL')
                                logging.error(f'[{worker_name}] Lead {lead_url} generated an exception during threaded processing: {exc}', exc_info=True)
                # --- End of parallel processing block ---

                logging.info(f"[{worker_name}] Page {current_page}: Parsed {potential_leads_count_page} potential leads, added {processed_leads_count_page} new graded leads for {city_code}/{category_code}.")
                processed_category_leads += processed_leads_count_page

                # Find next page link (Placeholder)
                next_page_relative = None
                if current_page < max_pages_to_scrape: pass # Keep next_page_relative as None

                if next_page_relative and current_page < max_pages_to_scrape:
                    next_page_url = urljoin(next_page_url, next_page_relative)
                    current_page += 1
                    time.sleep(random.uniform(1.0, 2.5))
                else:
                    if current_page >= max_pages_to_scrape: logging.info(f"[{worker_name}] Reached page limit ({max_pages_to_scrape}) for {city_code}/{category_code}.")
                    elif not next_page_relative and current_page < max_pages_to_scrape: logging.info(f"[{worker_name}] No next page link found for {city_code}/{category_code}.")
                    next_page_url = None # Stop pagination

            logging.info(f"[{worker_name}] Finished category {category_code} for {city_code}. Added {processed_category_leads} leads.")
            time.sleep(random.uniform(0.5, 1.5))

        logging.info(f"[{worker_name}] Finished processing {city_name}. Found {city_leads_found_total} new relevant leads in total.")
        return (city_code, city_leads_found_total)

    except Exception as e:
        logging.error(f"[{worker_name}] Error processing city {city_code}: {e}", exc_info=True)
        return (city_code, 0)
    finally:
        if worker_state_manager and worker_state_manager.conn:
            worker_state_manager.close_db()
            logging.info(f"[{worker_name}] Closed DB connection for city {city_code}.")

# --- GitHub Deployment Function ---
def deploy_to_github():
    """Adds all changes, commits, and pushes to the GitHub remote."""
    # (Deployment logic remains the same - uses environment variable)
    github_pat = os.environ.get('GITHUB_PAT')
    if not github_pat:
        logging.error("GITHUB_PAT environment variable not set. Skipping deployment.")
        return
    github_username = "Brandonrz369"
    repo_name = "Gemini-Scraper"
    logging.info(f"Attempting to commit and push changes to GitHub repo: {github_username}/{repo_name}")
    try:
        logging.info(f"Running Git commands in: {repo_root}")
        status_result = subprocess.run(['git', 'status', '--porcelain'], check=True, cwd=repo_root, capture_output=True, text=True)
        if not status_result.stdout and "graded_leads.json" not in status_result.stdout: # Check if only JSON changed potentially
             # Double check if graded_leads.json exists and was modified recently
             json_path = os.path.join(repo_root, 'frontend', 'public', 'graded_leads.json')
             if not os.path.exists(json_path):
                 logging.info("No changes detected and no JSON file found to commit.")
                 return
             # If only JSON changed git status might be empty if .gitignore ignores it, force add
             logging.info("Staging potential JSON update...")
             subprocess.run(['git', 'add', os.path.join('frontend', 'public', 'graded_leads.json')], check=True, cwd=repo_root, capture_output=True, text=True)
             # Check status again
             status_result = subprocess.run(['git', 'status', '--porcelain'], check=True, cwd=repo_root, capture_output=True, text=True)
             if not status_result.stdout:
                 logging.info("No changes detected to commit after attempting to stage JSON.")
                 return

        logging.info("Staging all changes...")
        subprocess.run(['git', 'add', '.'], check=True, cwd=repo_root, capture_output=True, text=True)
        commit_message = f"Update leads dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        logging.info(f"Committing changes with message: '{commit_message}'")
        subprocess.run(['git', 'commit', '-m', commit_message], check=True, cwd=repo_root, capture_output=True, text=True)
        logging.info("Pushing changes to remote 'origin'...")
        push_env = os.environ.copy()
        push_env['GITHUB_PAT'] = github_pat
        try:
            subprocess.run(['git', 'push', 'origin'], check=True, cwd=repo_root, capture_output=True, text=True, env=push_env)
            logging.info("Changes pushed to GitHub successfully via origin.")
        except subprocess.CalledProcessError as e_push:
             logging.warning(f"Push to origin failed (maybe auth issue?): {e_push.stderr}. Trying fallback push with PAT in URL (less secure)...")
             try:
                 authenticated_repo_url = f"https://{github_pat}@github.com/{github_username}/{repo_name}.git"
                 branch_result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], check=True, cwd=repo_root, capture_output=True, text=True)
                 current_branch = branch_result.stdout.strip()
                 subprocess.run(['git', 'push', authenticated_repo_url, current_branch], check=True, cwd=repo_root, capture_output=True, text=True)
                 logging.info("Changes pushed to GitHub successfully via authenticated URL.")
             except subprocess.CalledProcessError as e_fallback:
                  logging.error(f"Fallback Git push failed! Stderr: {e_fallback.stderr}")
             except Exception as e_fallback_unexpected:
                  logging.error(f"An unexpected error occurred during fallback GitHub push: {e_fallback_unexpected}", exc_info=True)
    except FileNotFoundError: logging.error("Git command not found. Ensure Git is installed and in PATH.")
    except subprocess.CalledProcessError as e: logging.error(f"Git operation failed! Stderr: {e.stderr}")
    except Exception as e: logging.error(f"An unexpected error during GitHub deployment: {e}", exc_info=True)

# --- Main Execution ---
def main(args):
    logging.info(f"--- Craigslist Lead Generation Agent Started (List Size: {args.list_size}) ---")
    os.chdir(project_root)
    logging.info(f"Working directory set to: {os.getcwd()}")
    # Include PRE_FILTER_CONFIG in the main config dict
    config = {
        'OXYLABS_CONFIG': OXYLABS_CONFIG,
        'SEARCH_CONFIG': SEARCH_CONFIG,
        'STATE_CONFIG': STATE_CONFIG,
        'AI_CONFIG': AI_CONFIG,
        'PRE_FILTER_CONFIG': PRE_FILTER_CONFIG
    }
    state_manager = None
    try:
        logging.info("Initializing main manager instances...")
        os.makedirs(os.path.join(project_root, 'data'), exist_ok=True)
        state_manager = StateManager(config)
        city_manager = CityManager(config, state_manager)
        output_generator = OutputGenerator(config)
        logging.info("Main manager instances initialized.")

        logging.info("Testing connection to Oxylabs...")
        # (Oxylabs check remains the same)
        temp_request_handler = RequestHandler(config['OXYLABS_CONFIG'])
        test_url = "https://newyork.craigslist.org/search/web"
        try:
            content = temp_request_handler.get_page(test_url, retry_count=1)
            if content and "craigslist" in content.lower(): logging.info("✅ Oxylabs connection successful.")
            else: logging.error("❌ Oxylabs connection failed during pre-check."); sys.exit(1)
        except Exception as e: logging.critical(f"Oxylabs connection pre-check error: {e}", exc_info=True); sys.exit(1)
        del temp_request_handler

        logging.info("--- System Status & Setup ---")
        # Determine which city list to load
        list_to_load = 'large' if args.target_cities else args.list_size
        logging.info(f"Loading city list: {list_to_load}.json")
        cities_to_process_full = city_manager.get_cities_by_population(list_to_load)
        total_cities_in_list = len(cities_to_process_full)
        logging.info(f"Loaded {total_cities_in_list} cities from {list_to_load}.json.")

        target_city_codes = None
        if args.target_cities:
            target_city_codes = [code.strip() for code in args.target_cities.split(',') if code.strip()]
            logging.info(f"Processing specific target cities based on --target-cities: {target_city_codes}")
            # Filter the full list based on the provided codes
            cities_to_process = [city for city in cities_to_process_full if city.get('code') in target_city_codes]
            # Verify all requested cities were found
            found_codes = {city.get('code') for city in cities_to_process}
            missing_codes = set(target_city_codes) - found_codes
            if missing_codes:
                logging.warning(f"Could not find the following target cities in the configured list: {missing_codes}")
        else:
            # Fallback to using the list_size if no target cities specified
            logging.info(f"No specific target cities provided. Using list size: '{args.list_size}'.")
            cities_to_process = cities_to_process_full

        total_cities_to_process = len(cities_to_process)
        logging.info(f"Will process {total_cities_to_process} cities.")
        logging.info(f"Total leads currently in database: {state_manager._get_total_leads_count()}")

        # --- Checkpoint/Resumption Logic ---
        last_completed_city = state_manager.get_last_completed_city()
        if last_completed_city:
            logging.warning(f"Resuming run. Last successfully completed city: {last_completed_city}")
            try:
                # Find the index of the last completed city + 1 to resume
                resume_index = [i for i, city in enumerate(cities_to_process) if city.get('code') == last_completed_city][0] + 1
                if resume_index < len(cities_to_process):
                    logging.info(f"Skipping {resume_index} already processed cities.")
                    cities_to_process = cities_to_process[resume_index:]
                else:
                    logging.info("All cities from the list were already processed in the previous run.")
                    cities_to_process = [] # No cities left to process
            except IndexError:
                logging.warning(f"Last completed city '{last_completed_city}' not found in the current list. Processing all cities.")
                # Optionally clear the invalid checkpoint: state_manager.set_last_completed_city(None)
        else:
            logging.info("Starting fresh run (no previous completed city found).")
        # --- End Checkpoint Logic ---

        total_cities_to_process = len(cities_to_process) # Recalculate after potential filtering
        logging.info(f"Will process {total_cities_to_process} cities in this run.")
        if not cities_to_process: logging.warning("No cities left to process for this run. Exiting."); sys.exit(0)

        # Determine max pages per category based on argument or default (3)
        max_pages = args.limit_pages if args.limit_pages is not None and args.limit_pages > 0 else 3
        logging.info(f"Scraping up to {max_pages} pages per category.")

        logging.info("--- Starting Parallel Scrape ---")
        # Pool size still based on number of cities to process
        pool_size = min((os.cpu_count() or 4) * 2, total_cities_to_process) if total_cities_to_process > 0 else 1
        logging.info(f"Initializing multiprocessing pool with {pool_size} workers.")

        # Determine search scope for tagging
        if args.target_cities:
            search_scope = 'single_city' if len(target_city_codes) == 1 else 'small_region'
        else:
            # If not targeting specific cities, scope depends on how many are processed from the list size
            # For simplicity, let's default to 'list_size_run' if not specifically targeted
            search_scope = f"{args.list_size}_list" # Or determine based on len(cities_to_process) if needed

        logging.info(f"Setting search_scope tag for this run: '{search_scope}'")

        # Pass limits, leads_per_page limit, thread count, and search_scope to each worker
        worker_args_list = [(city_info, config, max_pages, args.limit_categories, args.limit_leads_per_page, args.num_threads, search_scope) for city_info in cities_to_process]
        total_leads_found_this_session = 0
        processed_cities_count = 0

        with multiprocessing.Pool(processes=pool_size) as pool:
            logging.info(f"Distributing {len(worker_args_list)} cities/tasks to workers...")
            try:
                for result in pool.imap_unordered(scrape_city_worker, worker_args_list):
                    processed_cities_count += 1
                    city_code, leads_found = result
                    if leads_found > 0: total_leads_found_this_session += leads_found
                    logging.info(f"Worker finished for {city_code}. Found {leads_found} leads. ({processed_cities_count}/{total_cities_to_process} cities complete)")
                    # --- Save progress after successful city completion ---
                    if city_code: # Ensure city_code is valid before saving progress
                         state_manager.set_last_completed_city(city_code)
                         logging.debug(f"Checkpoint saved: Last completed city set to {city_code}")
                    # --- End save progress ---
                logging.info("All workers finished.")
            except KeyboardInterrupt: logging.warning("KeyboardInterrupt received. Terminating pool..."); pool.terminate(); pool.join(); logging.warning("Pool terminated."); sys.exit(1)
            except Exception as e: logging.error(f"Error during pool execution: {e}", exc_info=True); pool.terminate(); pool.join(); sys.exit(1)

        logging.info("--- Scrape Finished ---")
        state_manager._set_progress_value("last_full_run_completed", datetime.now().isoformat())
        logging.info(f"Processed {processed_cities_count} cities.")
        logging.info(f"Found approx {total_leads_found_this_session} new leads this session.")

        all_leads = state_manager.get_leads()
        if all_leads:
            logging.info(f"Generating final reports for {len(all_leads)} total leads...")
            output_generator.generate_csv(all_leads)
            output_generator.generate_html_dashboard(all_leads)
            output_generator.generate_graded_json(all_leads)
        else:
            logging.info("No leads found in database to generate reports.")

        logging.info("--- Attempting GitHub Deployment ---")
        deploy_to_github()
        logging.info("--- Agent Finished ---")

    except Exception as e:
        logging.critical(f"An unexpected error occurred in main execution: {e}", exc_info=True)
    finally:
        if state_manager and hasattr(state_manager, 'conn') and state_manager.conn:
            logging.info("Closing main database connection...")
            state_manager.close_db()
        else:
            logging.info("Main StateManager not initialized or connection already closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Craigslist Lead Generation Agent")
    parser.add_argument('--list-size', type=str, choices=['small', 'medium', 'large', 'us'], default='us', help="Size of the city list to use (ignored if --target-cities is set). Default: us") # Added 'us', changed default
    # parser.add_argument('--limit-cities', type=int, default=None, metavar='N', help="Limit run to first N cities.") # Replaced by --target-cities
    parser.add_argument('--target-cities', type=str, default=None, metavar='city1,city2,...', help="Specify exact city codes to process (comma-separated). Overrides --list-size.")
    parser.add_argument('--limit-pages', type=int, default=None, metavar='P', help="Limit scraping to first P pages per category. Default: 3")
    parser.add_argument('--limit-categories', type=int, default=None, metavar='C', help="Limit run to first C categories per city.")
    parser.add_argument('--limit-leads-per-page', type=int, default=None, metavar='L', help="Limit processing to first L leads per search page (for testing).") # Added limit-leads-per-page
    parser.add_argument('--num-threads', type=int, default=8, metavar='T', help="Number of threads for internal lead processing. Default: 8") # Added num-threads
    args = parser.parse_args()

    logging.info("Executing main block...")
    main(args)
