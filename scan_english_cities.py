import os
import subprocess

CODES_FILE = "english_speaking_codes.txt" # Updated filename

def main():
    if not os.path.exists(CODES_FILE):
        print(f"ERROR: {CODES_FILE} not found. Please run generate_english_city_codes.py first.")
        return
    with open(CODES_FILE, "r", encoding="utf-8") as f:
        code_str = f.read().strip()
    codes = code_str.split(",")
    print(f"Loaded {len(codes)} English-speaking city codes from {CODES_FILE}.")

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
    print("Running scan with command:")
    print(" ".join(command[:4]) + " [city codes omitted for brevity] " + " ".join(command[4:]))

    # Run the main scraper
    subprocess.run(command)

if __name__ == "__main__":
    main()
