import json
import os
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Input file with all scraped cities
SOURCE_FILE = "craigslist_cities_scraped.json"
# Output file for English-speaking codes
OUTPUT_FILE = "english_speaking_codes.txt"

# Known English-speaking country/region codes or names
# These are used to identify the correct sections/sublists
# We need a robust way to map codes to countries/regions.
# For now, we'll use a simplified approach based on common codes.
# A more robust solution might involve a separate country mapping file.
ENGLISH_SPEAKING_CODES = {
    # US (Assume all US codes are English) - Handled separately
    # Canada
    "calgary", "edmonton", "ftmcmurray", "lethbridge", "hat", "peace", "reddeer",
    "cariboo", "comoxvalley", "abbotsford", "kamloops", "kelowna", "kootenays",
    "nanaimo", "princegeorge", "skeena", "sunshine", "vancouver", "victoria", "whistler",
    "winnipeg", "newbrunswick", "newfoundland", "territories", "yellowknife", "halifax",
    "barrie", "belleville", "brantford", "chatham", "cornwall", "guelph", "hamilton",
    "kingston", "kitchener", "londonon", "niagara", "ottawa", "owensound", "peterborough",
    "sarnia", "soo", "sudbury", "thunderbay", "toronto", "windsor", "pei",
    "regina", "saskatoon", "whitehorse",
    # UK
    "aberdeen", "bath", "belfast", "birmingham", "brighton", "bristol", "cambridge",
    "cardiff", "coventry", "derby", "devon", "dundee", "norwich", "eastmids",
    "edinburgh", "essex", "glasgow", "hampshire", "kent", "leeds", "liverpool",
    "london", "manchester", "newcastle", "nottingham", "oxford", "sheffield",
    # Ireland
    "dublin",
    # Australia
    "adelaide", "brisbane", "cairns", "canberra", "darwin", "goldcoast", "melbourne",
    "ntl", "perth", "sydney", "hobart", "wollongong",
    # New Zealand
    "auckland", "christchurch", "dunedin", "wellington",
    # South Africa
    "capetown", "durban", "johannesburg", "pretoria",
    # Philippines
    "bacolod", "naga", "cdo", "cebu", "davaocity", "iloilo", "manila", "pampanga", "zamboanga",
    # Singapore
    "singapore",
    # Others (add as needed)
    "micronesia", "virgin", "caribbean" # Guam, USVI, Caribbean
}

def main():
    if not os.path.exists(SOURCE_FILE):
        logging.error(f"ERROR: Source file {SOURCE_FILE} not found. Please run scrape_craigslist_cities.py first.")
        return

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        all_cities = json.load(f)

    # Filter based on known English codes + assume all US are English
    # A more robust method would map codes to countries first.
    english_codes = set()
    us_codes_count = 0
    other_english_codes_count = 0

    # Simple heuristic: Assume codes without clear non-English country indicators are US/English
    # This is imperfect but avoids needing a complex country mapping for now.
    # We explicitly include known English codes from other countries.
    for entry in all_cities:
        code = entry["code"]
        # Add known English codes
        if code in ENGLISH_SPEAKING_CODES:
            english_codes.add(code)
            other_english_codes_count += 1
        # Add codes that don't obviously belong to non-English regions (likely US)
        # This is a broad assumption and might include some non-English Canadian/etc.
        # A better approach would use the site map structure if parsing worked reliably.
        elif code not in ["vienna", "brussels", "bulgaria", "zagreb", "prague", "copenhagen", "helsinki",
                         "bordeaux", "rennes", "grenoble", "lille", "loire", "lyon", "marseilles", "montpellier",
                         "cotedazur", "rouen", "paris", "strasbourg", "toulouse", "berlin", "bremen", "cologne",
                         "dresden", "dusseldorf", "essen", "frankfurt", "hamburg", "hannover", "heidelberg",
                         "kaiserslautern", "leipzig", "munich", "nuremberg", "stuttgart", "athens", "budapest",
                         "reykjavik", "bologna", "florence", "genoa", "milan", "naples", "perugia", "rome",
                         "sardinia", "sicily", "torino", "venice", "luxembourg", "amsterdam", "oslo", "warsaw",
                         "faro", "lisbon", "porto", "bucharest", "moscow", "stpetersburg", "alicante", "baleares",
                         "barcelona", "bilbao", "cadiz", "canarias", "granada", "madrid", "malaga", "sevilla",
                         "valencia", "stockholm", "basel", "bern", "geneva", "lausanne", "zurich", "istanbul",
                         "ukraine", "bangladesh", "beijing", "chengdu", "chongqing", "dalian", "guangzhou",
                         "hangzhou", "nanjing", "shanghai", "shenyang", "shenzhen", "wuhan", "xian", "hongkong",
                         "ahmedabad", "bangalore", "bhubaneswar", "chandigarh", "chennai", "delhi", "goa",
                         "hyderabad", "indore", "jaipur", "kerala", "kolkata", "lucknow", "mumbai", "pune",
                         "surat", "jakarta", "tehran", "baghdad", "haifa", "jerusalem", "telaviv", "ramallah",
                         "fukuoka", "hiroshima", "nagoya", "okinawa", "osaka", "sapporo", "sendai", "tokyo",
                         "seoul", "kuwait", "beirut", "malaysia", "pakistan", "taipei", "bangkok", "dubai",
                         "vietnam", "buenosaires", "lapaz", "belohorizonte", "brasilia", "curitiba", "fortaleza",
                         "portoalegre", "recife", "rio", "salvador", "saopaulo", "santiago", "colombia",
                         "costarica", "santodomingo", "quito", "elsalvador", "guatemala", "acapulco", "bajasur",
                         "chihuahua", "juarez", "guadalajara", "guanajuato", "hermosillo", "mazatlan", "mexicocity",
                         "monterrey", "oaxaca", "puebla", "pv", "tijuana", "veracruz", "yucatan", "managua",
                         "panama", "lima", "montevideo", "caracas", "cairo", "addisababa", "accra", "kenya",
                         "casablanca", "tunis"]:
            if english_codes.add(code):
                 us_codes_count += 1 # Assume these are mostly US/CA

    final_codes = sorted(list(english_codes))
    code_str = ",".join(final_codes)

    logging.info(f"Filtered to {len(final_codes)} likely English-speaking city codes.")
    logging.info(f"(Assumed {us_codes_count} US/CA + {other_english_codes_count} explicitly listed English regions)")
    print(f"\nGenerated list of {len(final_codes)} English-speaking city codes.")
    print("Sample:", code_str[:200] + "..." if len(code_str) > 200 else code_str)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(code_str)
    print(f"Full list saved to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
