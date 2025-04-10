# Project Handoff Blueprint: Craigslist Lead Scraper (US Expansion)

**Date:** 2025-04-10

## 1. Project Goal

To scrape Craigslist job/gig postings across the entire United States for leads related to web design, graphic design, and Photoshop services. The system should be resilient to interruptions and use AI for initial filtering and grading.

## 2. Current Status & Implemented Features

The project has been enhanced from its initial state to support wider scraping and better resilience:

*   **Checkpointing/Resumption:**
    *   The script now saves the `city_code` of the last successfully completed city to the `progress` table in `backend/data/leads.db`.
    *   On startup, the script reads this value and automatically skips cities that were already processed in a previous run, allowing it to resume after interruptions.
    *   Implemented in `backend/modules/state_manager.py` and `backend/main.py`.
*   **US City List Integration:**
    *   Combined existing `small`, `medium`, and `large` city lists into `backend/data/cities_us.json` (contains 181 unique cities/regions).
    *   Updated `backend/modules/city_manager.py` to load this list.
    *   Updated `backend/main.py` to accept `--list-size us` (now the default) to use this comprehensive list.
*   **Error Handling:** Reviewed existing retry logic in `backend/modules/request_handler.py`; deemed sufficient for now.
*   **A/B Testing Framework:** Basic framework for tagging leads with `search_scope` exists in `backend/modules/state_manager.py` and `backend/main.py` (used for previous Dayton vs. Dayton+Akron test).
*   **Dependencies:** Project uses a Python virtual environment (`.venv`) with dependencies listed in `backend/requirements.txt`. Key dependencies include `requests`, `beautifulsoup4`, `sqlite3`, `openai`, `python-dotenv`.

## 3. Key Files Modified

*   `backend/main.py`: Added argument parsing for `--list-size us`, integrated checkpointing logic, modified multiprocessing pool logic slightly.
*   `backend/modules/state_manager.py`: Added `get_last_completed_city` and `set_last_completed_city` methods, fixed indentation error.
*   `backend/modules/city_manager.py`: Updated to load `cities_us.json` when `list_size='us'`.
*   `backend/data/cities_us.json`: Created by combining previous city lists.

## 4. Setup & Running on New Machine

1.  **Clone Repository:**
    ```bash
    git clone https://github.com/Brandonrz369/Gemini-Scraper.git
    cd Gemini-Scraper
    ```
2.  **Set up Virtual Environment:**
    ```bash
    # Ensure Python 3 is installed
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r backend/requirements.txt
    ```
4.  **Configure API Keys:**
    *   Create a `.env` file in the `backend/` directory.
    *   Add your API keys and credentials:
        ```dotenv
        # backend/.env
        OXYLABS_USERNAME=your_oxylabs_username
        OXYLABS_PASSWORD=your_oxylabs_password
        OPENROUTER_API_KEY=your_openrouter_key
        # Optional: For GitHub deployment
        GITHUB_PAT=your_github_personal_access_token
        ```
5.  **Configure Local Perplexity MCP Server (Optional but Recommended for Research):**
    *   The Perplexity MCP server (`researcher-mcp`) was used during development for brainstorming and research. To enable it locally, you need to add its configuration to your MCP settings file.
    *   **Location:** This file is typically located at `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` (Linux) or similar paths on other OSes. **Do NOT commit this file to Git.**
    *   **Configuration:** Add the following within the `mcpServers` object in that file (create the object if it doesn't exist):
        ```json
        "perplexity-server": {
          "command": "npx",
          "args": ["mcp-perplexity-search"],
          "env": {
            "PERPLEXITY_API_KEY": "YOUR_PERPLEXITY_API_KEY_HERE", // Replace with your actual key
            "PERPLEXITY_MODEL": "sonar-pro",
            "PERPLEXITY_MODEL_CHAT": "sonar-pro",
            "PERPLEXITY_MODEL_ASK": "sonar-reasoning-pro",
            "PERPLEXITY_MODEL_CODE": "sonar-reasoning-pro"
          }
        }
        ```
    *   **Note:** Replace `"YOUR_PERPLEXITY_API_KEY_HERE"` with your actual Perplexity API key. You may need to install the server globally first if you haven't: `npm install -g mcp-perplexity-search`.
6.  **Run Test Scan (Recommended First):**
    *   This command runs the scan using the full US list but limits it to 1 page per category for a quick test. Uses 8 threads for lead processing.
    ```bash
    source .venv/bin/activate
    python backend/main.py --list-size us --limit-pages 1 --num-threads 8
    ```
    *   Check `backend/run.log` for errors.
6.  **Run Full Scan:**
    *   Adjust `--limit-pages` as desired (e.g., `--limit-pages 3` or remove for potentially more pages, though Craigslist structure might limit this). Increase `--num-threads` if appropriate for your machine.
    ```bash
    source .venv/bin/activate
    # Example: Scan 3 pages per category for all US cities
    python backend/main.py --list-size us --limit-pages 3 --num-threads 8
    ```
    *   The scan will run, saving progress. If interrupted, simply run the same command again to resume.

## 5. Future Work / Postponed Items

*   **Refine Search Terms:** Use AI (like Perplexity or Claude) to brainstorm better keywords and potentially identify less obvious Craigslist categories to target non-technical clients needing design/web services. Update `SEARCH_CONFIG` in `backend/config/settings.py`.
*   **Automate Cline API Key Cycling:** Investigate creating a separate script or MCP server to monitor Cline's API usage (if possible externally) and automatically edit the VS Code extension's configuration file (`~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` or similar) and trigger a VS Code reload. This is complex and requires external monitoring/control capabilities.
*   **Improve Next Page Logic:** The current pagination logic in `scrape_city_worker` is a placeholder (`pass`). Implement robust logic to find and follow the "next page" link on Craigslist search results pages.
*   **More Granular Checkpointing:** Consider checkpointing at the category level within a city if city-level resumption proves too coarse for very long runs or frequent interruptions.

## 6. Notes

*   The project assumes it's run from the `Gemini-Scraper` root directory after activating the virtual environment.
*   The GitHub deployment function relies on a `GITHUB_PAT` environment variable.
*   The number of workers in the multiprocessing pool (`pool_size` in `main.py`) is currently calculated based on CPU count but capped relative to the number of cities being processed. For a full US scan, it will likely use `(os.cpu_count() or 4) * 2`.
*   The number of threads *within* each worker process for fetching lead details is set by `--num-threads` (default 8).
