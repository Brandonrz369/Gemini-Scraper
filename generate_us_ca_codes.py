import json
import os
import requests
from bs4 import BeautifulSoup

# File containing the full scraped list
SCRAPED_FILE = "craigslist_cities_scraped.json"
# Output file for US/CA codes
OUTPUT_FILE = "us_canada_city_codes.txt"

def get_us_canada_sections():
    """Fetches the Craigslist site map and identifies US/CA sections."""
    url = "https://www.craigslist.org/about/sites"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        us_sections = soup.find_all('div', class_='colmask') # US states are in these divs
        canada_sections = soup.find_all('h4', string='canada') # Find the Canada header
        
        us_cities = set()
        for section in us_sections:
             # Find all links within the US sections
             for a in section.find_all('a', href=True):
                 if a['href'].startswith("https://") and ".craigslist.org" in a['href']:
                     code = a['href'].split("//")[1].split(".")[0]
                     us_cities.add(code)

        canada_cities = set()
        if canada_sections:
            # Find the next sibling `ul` list after the 'canada' h4 tag
            ul_canada = canada_sections[0].find_next_sibling('ul')
            if ul_canada:
                for a in ul_canada.find_all('a', href=True):
                     if a['href'].startswith("https://") and ".craigslist.org" in a['href']:
                         code = a['href'].split("//")[1].split(".")[0]
                         canada_cities.add(code)
        
        print(f"Identified {len(us_cities)} US city codes and {len(canada_cities)} Canadian city codes from site map structure.")
        return us_cities.union(canada_cities)

    except Exception as e:
        print(f"Error fetching or parsing Craigslist site map: {e}")
        return None

def main():
    print("Identifying US and Canadian city codes from Craigslist site map...")
    us_ca_codes = get_us_canada_sections()

    if us_ca_codes is None:
        print("Could not determine US/CA cities from site map. Aborting.")
        return

    if not os.path.exists(SCRAPED_FILE):
        print(f"ERROR: {SCRAPED_FILE} not found. Please run scrape_craigslist_cities.py first.")
        return

    with open(SCRAPED_FILE, "r", encoding="utf-8") as f:
        all_cities = json.load(f)

    # Filter the scraped list based on the identified US/CA codes
    filtered_codes = []
    for entry in all_cities:
        if entry["code"] in us_ca_codes:
            filtered_codes.append(entry["code"])

    # Remove potential duplicates and sort
    final_codes = sorted(list(set(filtered_codes)))
    code_str = ",".join(final_codes)

    print(f"Filtered down to {len(final_codes)} US & Canadian city codes.")
    print("Sample:", code_str[:200] + "..." if len(code_str) > 200 else code_str)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(code_str)
    print(f"Full list saved to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
