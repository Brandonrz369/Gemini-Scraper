import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define database path relative to the script location
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, 'backend', 'data', 'leads.db')

logging.info(f"Attempting to connect to database: {db_path}")

if not os.path.exists(db_path):
    logging.error(f"Database file not found at {db_path}")
    exit()

conn = None
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    logging.info("Connected to database.")

    # Query to check the last completed city checkpoint
    checkpoint_query = "SELECT value FROM progress WHERE key = 'last_completed_city';"
    logging.info(f"Executing checkpoint query: {checkpoint_query}")
    cursor.execute(checkpoint_query)
    checkpoint_result = cursor.fetchone()

    if checkpoint_result:
        last_city = checkpoint_result[0]
        print(f"\n--- Checkpoint Status ---")
        print(f"Last successfully completed city: {last_city}")
        print(f"-------------------------\n")
    else:
        print("\n--- Checkpoint Status ---")
        print("No checkpoint found (last_completed_city key not set in progress table).")
        print("-------------------------\n")

except sqlite3.Error as e:
    logging.error(f"Database error during checkpoint check: {e}", exc_info=True)
except Exception as e:
    logging.error(f"An unexpected error occurred: {e}", exc_info=True)
finally:
    if conn:
        conn.close()
        logging.info("Database connection closed.")
