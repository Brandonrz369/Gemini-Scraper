import json
import os
import requests
from bs4 import BeautifulSoup
import logging
import re # Import regex

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Output file for English-speaking codes
OUTPUT_FILE = "english_speaking_codes.txt"

# Known English-speaking country/region codes or names used on the site map
# These are used to identify the correct sections/sublists
ENGLISH_REGIONS_IDENTIFIERS = [
    "US", # Handled separately by 'colmask'
    "canada",
    "united kingdom", "uk", "ireland", # Europe sub-sections
    "australia", "new zealand", # Oceania
    "philippines", "singapore", # Asia sub-sections
    "south africa", # Africa sub-section
    "caribbean", "virgin islands" # Latin America sub-sections
]

def get_english_speaking_codes_from_site_map():
    """Fetches the Craigslist site map and extracts codes from English-speaking sections."""
    url = "https://www.craigslist.org/about/sites"
    english_codes = set()
    try:
        logging.info(f"Fetching Craigslist site map from {url}...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        logging.info("Successfully fetched and parsed site map.")

        # 1. Get all US codes (they are in divs with class 'colmask')
        us_sections = soup.find_all('div', class_='colmask')
        us_count = 0
        for section in us_sections:
            # Check if it's likely a US state section (contains state names)
            h4_tag = section.find('h4')
            if h4_tag: # US sections have h4 state names
                 for a in section.find_all('a', href=True):
                     if a['href'].startswith("https://") and ".craigslist.org" in a['href']:
                         code = a['href'].split("//")[1].split(".")[0]
                         english_codes.add(code)
                         us_count += 1
        logging.info(f"Found {us_count} US codes.")

        # 2. Process other regions (Canada, Europe, Asia, Oceania, Africa, Latin America)
        # Find all region boxes (usually divs with class 'box')
        region_boxes = soup.find_all('div', class_='box')
        processed_regions = set(['US']) # Keep track

        for box in region_boxes:
            h4_header = box.find('h4')
            if not h4_header: continue

            region_name = h4_header.text.strip().lower()
            # Initialize count here, inside the loop for each box
            region_added_count = 0

            # Check if this region is one we target
            target_region = None
            for identifier in ENGLISH_REGIONS_IDENTIFIERS:
                 # Use regex for flexible matching (e.g., "united kingdom / UK")
                 if re.search(rf'\b{re.escape(identifier)}\b', region_name, re.IGNORECASE):
                     target_region = identifier # Store the matched identifier
                     break

            # Check if this region is one we target
            target_region = None
            for identifier in ENGLISH_REGIONS_IDENTIFIERS:
                 if re.search(rf'\b{re.escape(identifier)}\b', region_name, re.IGNORECASE):
                     target_region = identifier
                     break

            if target_region and target_region not in processed_regions:
                 # Initialize count here, ONLY when processing a matched region
                 region_added_count = 0
                 logging.info(f"Processing section matching '{target_region}' (Header: '{h4_header.text.strip()}')")
                 ul_list = box.find('ul')
                 if ul_list:
                     for a in ul_list.find_all('a', href=True):
                         if a['href'].startswith("https://") and ".craigslist.org" in a['href']:
                             code = a['href'].split("//")[1].split(".")[0]
                             # Add all codes found under these explicitly English sections
                             if english_codes.add(code):
                                 section_added_count += 1
                     logging.info(f"Added {section_added_count} codes from '{target_region}' section.")
                     processed_regions.add(target_region) # Mark as processed
                 else:
                     logging.warning(f"Could not find 'ul' list within box for '{target_region}'")

        logging.info(f"Total English-speaking codes identified: {len(english_codes)}")
        return english_codes

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Craigslist site map: {e}")
        return None
    except Exception as e:
        logging.error(f"Error parsing Craigslist site map: {e}", exc_info=True)
        return None

def main():
    target_codes = get_english_speaking_codes_from_site_map()

    if target_codes is None:
        logging.error("Could not generate city code list. Aborting.")
        return

    # Sort and save the final list
    final_codes = sorted(list(target_codes))
    code_str = ",".join(final_codes)

    print(f"\nGenerated list of {len(final_codes)} English-speaking city codes.")
    print("Sample:", code_str[:200] + "..." if len(code_str) > 200 else code_str)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(code_str)
    print(f"Full list saved to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
