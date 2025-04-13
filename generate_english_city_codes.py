import json
import os
import requests
from bs4 import BeautifulSoup

# File containing the full scraped list
SCRAPED_FILE = "craigslist_cities_scraped.json"
# Output file for English-speaking codes
OUTPUT_FILE = "english_speaking_codes.txt"

# Headers for sections on craigslist.org/about/sites that are English-speaking
ENGLISH_SECTION_HEADERS = [
    "US", # Implicitly includes all states listed in colmask divs
    "canada",
    "europe", # UK, Ireland are under Europe
    "asia", # Philippines, Singapore are under Asia
    "oceania", # Australia, New Zealand are under Oceania
    "africa", # South Africa is under Africa
    # Add other regions if needed, e.g., "latin america" for Caribbean islands
]

# Specific English-speaking countries/cities listed under broader regions
# (Handles cases like Ireland/UK under Europe)
ENGLISH_SUBREGIONS = [
    "dublin", "ireland", # Ireland
    "aberdeen", "bath", "belfast", "birmingham", "brighton", "bristol", # UK Cities
    "cambridge", "cardiff", "coventry", "derby", "devon", "dundee", # UK Cities
    "norwich", "eastmids", "edinburgh", "essex", "glasgow", "hampshire", # UK Cities
    "kent", "leeds", "liverpool", "london", "manchester", "newcastle", # UK Cities
    "nottingham", "oxford", "sheffield", # UK Cities
    "philippines", "bacolod", "naga", "cdo", "cebu", "davaocity", "iloilo", "manila", "pampanga", "zamboanga", # Philippines
    "singapore", # Singapore
    "australia", "adelaide", "brisbane", "cairns", "canberra", "darwin", "goldcoast", "melbourne", "ntl", "perth", "sydney", "hobart", "wollongong", # Australia
    "new zealand", "auckland", "christchurch", "dunedin", "wellington", # New Zealand
    "south africa", "capetown", "durban", "johannesburg", "pretoria" # South Africa
]

def get_english_speaking_codes_from_site_map():
    """Fetches the Craigslist site map and extracts codes from English-speaking sections."""
    url = "https://www.craigslist.org/about/sites"
    english_codes = set()
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        # Get all US codes first (they are in divs with class 'colmask')
        us_sections = soup.find_all('div', class_='colmask')
        for section in us_sections:
            for a in section.find_all('a', href=True):
                if a['href'].startswith("https://") and ".craigslist.org" in a['href']:
                    code = a['href'].split("//")[1].split(".")[0]
                    english_codes.add(code)
        print(f"Found {len(english_codes)} US codes.")

        # Find headers for other English-speaking regions
        for header_text in ENGLISH_SECTION_HEADERS:
            if header_text == "US": continue # Already handled

            headers = soup.find_all('h4', string=lambda t: t and header_text in t.lower())
            if not headers:
                print(f"Warning: Could not find section header for '{header_text}'")
                continue

            for header in headers:
                 # Find the next sibling `ul` list
                 ul_section = header.find_next_sibling('ul')
                 if ul_section:
                     section_codes = set()
                     for a in ul_section.find_all('a', href=True):
                         if a['href'].startswith("https://") and ".craigslist.org" in a['href']:
                             code = a['href'].split("//")[1].split(".")[0]
                             name = a.text.strip().lower()
                             # Check if this specific city/subregion is English-speaking
                             if header_text != "europe" or any(subregion in name or subregion == code for subregion in ENGLISH_SUBREGIONS):
                                 section_codes.add(code)
                     print(f"Found {len(section_codes)} codes under '{header_text}' section.")
                     english_codes.update(section_codes)
                 else:
                      print(f"Warning: Could not find 'ul' list after header '{header_text}'")

        print(f"Total English-speaking codes identified from site map: {len(english_codes)}")
        return english_codes

    except Exception as e:
        print(f"Error fetching or parsing Craigslist site map: {e}")
        return None

def main():
    print("Identifying English-speaking city codes from Craigslist site map...")
    target_codes = get_english_speaking_codes_from_site_map()

    if target_codes is None:
        print("Could not determine English-speaking cities from site map. Aborting.")
        return

    if not os.path.exists(SCRAPED_FILE):
        print(f"ERROR: {SCRAPED_FILE} not found. Please run scrape_craigslist_cities.py first.")
        return

    with open(SCRAPED_FILE, "r", encoding="utf-8") as f:
        all_cities = json.load(f)

    # Filter the scraped list based on the identified English-speaking codes
    filtered_codes = []
    for entry in all_cities:
        if entry["code"] in target_codes:
            filtered_codes.append(entry["code"])

    # Remove potential duplicates and sort
    final_codes = sorted(list(set(filtered_codes)))
    code_str = ",".join(final_codes)

    print(f"Filtered down to {len(final_codes)} English-speaking city codes.")
    print("Sample:", code_str[:200] + "..." if len(code_str) > 200 else code_str)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(code_str)
    print(f"Full list saved to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
