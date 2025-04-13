import requests
from bs4 import BeautifulSoup
import json

def scrape_craigslist_cities():
    print("--- scrape_craigslist_cities.py script started ---")
    try:
        url = "https://www.craigslist.org/about/sites"
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        cities = []
        for section in soup.select("section.body ul"):
            for li in section.find_all("li"):
                a = li.find("a")
                if a and a.has_attr("href"):
                    href = a["href"]
                    # Extract the subdomain (city code) from the URL
                    if href.startswith("https://") and ".craigslist.org" in href:
                        code = href.split("//")[1].split(".")[0]
                        name = a.text.strip()
                        cities.append({"code": code, "name": name})

        # Save as JSON
        with open("craigslist_cities_scraped.json", "w", encoding="utf-8") as f:
            json.dump(cities, f, indent=2, ensure_ascii=False)

        print(f"Scraped {len(cities)} Craigslist city codes. Saved to craigslist_cities_scraped.json.")
    except Exception as e:
        print(f"ERROR: {e}")
    print("--- scrape_craigslist_cities.py script finished ---")

if __name__ == "__main__":
    scrape_craigslist_cities()
