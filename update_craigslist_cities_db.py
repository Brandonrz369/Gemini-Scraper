import json
import os
from datetime import datetime

SCRAPED_FILE = "craigslist_cities_scraped.json"
DB_FILE = "craigslist_cities_db.json"

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def update_cities_db():
    scraped = load_json(SCRAPED_FILE)
    db = load_json(DB_FILE)
    now = datetime.now().isoformat()

    # Convert db to dict for fast lookup
    db_dict = {entry["code"]: entry for entry in db}

    changes = []
    for city in scraped:
        code = city["code"]
        name = city["name"]
        if code in db_dict:
            entry = db_dict[code]
            # Update name if changed
            if entry["name"] != name:
                changes.append(f"Name changed for {code}: '{entry['name']}' -> '{name}'")
                entry["name"] = name
            # Update last_seen
            entry["last_seen"] = now
        else:
            # New city
            db_dict[code] = {
                "code": code,
                "name": name,
                "first_seen": now,
                "last_seen": now
            }
            changes.append(f"New city added: {code} ({name})")

    # Optionally, mark cities not seen in this scrape as "inactive"
    for code, entry in db_dict.items():
        if entry.get("last_seen") != now:
            entry["inactive_since"] = now
            changes.append(f"City marked inactive: {code} ({entry['name']})")

    # Save updated db
    save_json(DB_FILE, list(db_dict.values()))

    print(f"Updated {DB_FILE} with {len(scraped)} cities. {len(changes)} changes.")
    if changes:
        print("Recent changes:")
        for c in changes[:20]:
            print(" -", c)
        if len(changes) > 20:
            print(f"...and {len(changes)-20} more.")

if __name__ == "__main__":
    update_cities_db()
