import json
import os
import subprocess
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Input file with all scraped cities
SOURCE_FILE = "craigslist_cities_scraped.json"

def main():
    if not os.path.exists(SOURCE_FILE):
        logging.error(f"ERROR: Source file {SOURCE_FILE} not found. Please run scrape_craigslist_cities.py first.")
        return

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        all_cities = json.load(f)

    # Extract all city codes
    codes = [entry["code"] for entry in all_cities if "code" in entry]
    codes = sorted(list(set(codes))) # Ensure unique and sorted
    code_str = ",".join(codes)

    logging.info(f"Loaded {len(codes)} city codes from {SOURCE_FILE}.")

    # Build the command to run the main scraper
    pool_size = 16
    num_threads = 32
    main_py = os.path.join("backend", "main.py")
    command = [
        "python", main_py,
        "--target-cities", code_str,
        "--num-threads", str(num_threads),
        "--pool-size", str(pool_size)
    ]
    logging.info("Running full global scan with command:")
    # Log command safely, omitting potentially huge city list
    logging.info(" ".join(command[:4]) + " [city codes omitted for brevity] " + " ".join(command[4:]))

    # Run the main scraper
    try:
        # Use Popen for potentially long-running process, stream output if possible
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        
        # Stream output
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip()) # Print live output
        
        rc = process.poll()
        logging.info(f"Scan process finished with return code {rc}")

    except Exception as e:
        logging.error(f"Error running subprocess: {e}", exc_info=True)


if __name__ == "__main__":
    main()
