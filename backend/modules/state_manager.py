# brandonrz_pHeAj# modules/state_manager.py (Recreated)
import sqlite3
import logging
import os
import json # For handling potential JSON in DB later if needed
from datetime import datetime

class StateManager:
    def __init__(self, config):
        self.db_path = config.get('STATE_CONFIG', {}).get('DATABASE_FILE', 'data/leads.db')
        # Ensure the path is relative to the backend directory
        self.backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(self.backend_dir, self.db_path)

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.conn = None
        self.cursor = None
        self._connect_db()
        self._initialize_schema()

    def _connect_db(self):
        """Establishes connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            # Use Row factory for dictionary-like access
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logging.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logging.error(f"Error connecting to database {self.db_path}: {e}", exc_info=True)
            raise # Re-raise the exception

    def _initialize_schema(self):
        """Creates necessary tables if they don't exist."""
        if not self.conn: return
        try:
            # Leads table - adjust columns as needed based on full_lead_details structure
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT,
                    description TEXT,
                    city TEXT,
                    category TEXT,
                    date_posted_iso TEXT,
                    scraped_timestamp TEXT,
                    estimated_value TEXT,
                    contact_method TEXT,
                    contact_info TEXT, -- For email
                    contact_phone TEXT, -- Added for phone number
                    has_been_contacted BOOLEAN DEFAULT 0,
                    follow_up_date TEXT,
                    ai_is_junk BOOLEAN,
                    ai_profitability_score INTEGER,
                    ai_reasoning TEXT,
                    search_scope TEXT  -- Added for A/B testing
                )
            ''')
            # Progress table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS progress (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            self.conn.commit()
            logging.info("Database schema initialized/verified.")

            # --- Add migration logic for existing databases ---
            # Check if the search_scope column exists
            self.cursor.execute("PRAGMA table_info(leads)")
            columns = [column[1] for column in self.cursor.fetchall()]
            if 'search_scope' not in columns:
                logging.info("Adding 'search_scope' column to existing 'leads' table...")
                self.cursor.execute("ALTER TABLE leads ADD COLUMN search_scope TEXT")
                self.conn.commit()
                logging.info("'search_scope' column added successfully.")

            # Check if the contact_phone column exists
            if 'contact_phone' not in columns:
                logging.info("Adding 'contact_phone' column to existing 'leads' table...")
                self.cursor.execute("ALTER TABLE leads ADD COLUMN contact_phone TEXT")
                self.conn.commit()
                logging.info("'contact_phone' column added successfully.")
            # --- End migration logic ---

        except sqlite3.Error as e:
            logging.error(f"Error initializing/migrating database schema: {e}", exc_info=True)

    def get_last_completed_city(self):
        """Retrieves the code of the last successfully completed city."""
        if not self.conn: return None
        try:
            self.cursor.execute("SELECT value FROM progress WHERE key = 'last_completed_city'")
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logging.error(f"Error getting last completed city: {e}", exc_info=True)
            return None

    def set_last_completed_city(self, city_code):
        """Sets the code of the last successfully completed city."""
        self._set_progress_value('last_completed_city', city_code)

    # --- City-Specific Category Checkpointing ---

    def get_last_completed_category_for_city(self, city_code):
        """Retrieves the last completed category code for a specific city."""
        if not city_code: return None
        return self._get_progress_value(f'last_completed_category_for_city_{city_code}')

    def set_last_completed_category_for_city(self, city_code, category_code):
        """Sets the last completed category code for a specific city."""
        if not city_code or not category_code: return
        self._set_progress_value(f'last_completed_category_for_city_{city_code}', category_code)

    def clear_last_completed_category_for_city(self, city_code):
        """Removes the category checkpoint for a specific city."""
        if not city_code: return
        self._delete_progress_key(f'last_completed_category_for_city_{city_code}')

    # --- End City-Specific Category Checkpointing ---

    def add_lead(self, lead_details, search_scope="unknown"): # Added search_scope parameter
        """Adds a lead to the database if the URL is unique."""
        if not self.conn:
            logging.error("Database not connected. Cannot add lead.")
            return False

        url = lead_details.get('url')
        if not url:
            logging.warning("Skipping lead: Missing URL.")
            return False

        # Flatten AI grade details
        ai_grade = lead_details.get('ai_grade', {})
        ai_is_junk = ai_grade.get('is_junk') if isinstance(ai_grade, dict) else None
        ai_score = ai_grade.get('profitability_score') if isinstance(ai_grade, dict) else None
        ai_reasoning = ai_grade.get('reasoning') if isinstance(ai_grade, dict) else None

        # Prepare data for insertion, ensuring keys match table columns
        # Use .get() with default None for safety
        data_to_insert = {
            'url': url,
            'title': lead_details.get('title'),
            'description': lead_details.get('description'),
            'city': lead_details.get('city'),
            'category': lead_details.get('category'),
            'date_posted_iso': lead_details.get('date_posted_iso'),
            'scraped_timestamp': lead_details.get('scraped_timestamp', datetime.now().isoformat()),
            'estimated_value': lead_details.get('estimated_value'),
            'contact_method': lead_details.get('contact_method'),
            # Use 'contact_email' from lead_details, store in 'contact_info' column
            'contact_info': lead_details.get('contact_email'),
            'contact_phone': lead_details.get('contact_phone'), # Add phone number
            'has_been_contacted': lead_details.get('has_been_contacted', False),
            'follow_up_date': lead_details.get('follow_up_date'),
            'ai_is_junk': ai_is_junk,
            'ai_profitability_score': ai_score,
            'ai_reasoning': ai_reasoning,
            'search_scope': search_scope # Include search_scope
        }

        # Define columns explicitly for the INSERT statement
        columns = list(data_to_insert.keys())
        placeholders = ', '.join('?' * len(columns))
        sql = f"INSERT OR IGNORE INTO leads ({', '.join(columns)}) VALUES ({placeholders})"
        values = tuple(data_to_insert[col] for col in columns)

        try:
            self.cursor.execute(sql, values)
            self.conn.commit()
            # Check if a row was actually inserted (IGNORE means 0 changes if duplicate)
            if self.cursor.rowcount > 0:
                logging.debug(f"Lead added to DB: {url}")
                return True
            else:
                logging.debug(f"Lead already exists (duplicate URL): {url}")
                return False
        except sqlite3.Error as e:
            logging.error(f"Error adding lead {url} to database: {e}", exc_info=True)
            return False

    def get_leads(self):
        """Retrieves all leads from the database."""
        if not self.conn: return []
        try:
            self.cursor.execute("SELECT * FROM leads ORDER BY scraped_timestamp DESC")
            rows = self.cursor.fetchall()
            # Convert sqlite3.Row objects to dictionaries
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Error retrieving leads: {e}", exc_info=True)
            return []

    def _get_total_leads_count(self):
        """Gets the total number of leads in the database."""
        if not self.conn: return 0
        try:
            self.cursor.execute("SELECT COUNT(*) FROM leads")
            count = self.cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logging.error(f"Error getting lead count: {e}", exc_info=True)
            return 0

    # --- Internal Progress Helpers ---

    def _get_progress_value(self, key):
        """Retrieves a progress value by key."""
        if not self.conn or not key: return None
        try:
            self.cursor.execute("SELECT value FROM progress WHERE key = ?", (key,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logging.error(f"Error getting progress value for key '{key}': {e}", exc_info=True)
            return None

    def _set_progress_value(self, key, value):
        """Sets or replaces a progress key-value pair."""
        if not self.conn or not key: return
        try:
            # Ensure value is stored as string, handle None explicitly if needed
            value_str = str(value) if value is not None else None
            if value_str is None:
                 logging.warning(f"Attempted to set None value for progress key '{key}'. Deleting instead.")
                 self._delete_progress_key(key)
                 return

            sql = "INSERT OR REPLACE INTO progress (key, value) VALUES (?, ?)"
            self.cursor.execute(sql, (key, value_str))
            self.conn.commit()
            logging.debug(f"Progress value set: {key} = {value_str}")
        except sqlite3.Error as e:
            logging.error(f"Error setting progress value for key '{key}': {e}", exc_info=True)

    def _delete_progress_key(self, key):
        """Deletes a progress key."""
        if not self.conn or not key: return
        try:
            sql = "DELETE FROM progress WHERE key = ?"
            self.cursor.execute(sql, (key,))
            self.conn.commit()
            logging.debug(f"Progress key deleted: {key}")
        except sqlite3.Error as e:
            logging.error(f"Error deleting progress key '{key}': {e}", exc_info=True)

    # --- End Internal Progress Helpers ---
