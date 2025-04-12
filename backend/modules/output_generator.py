# modules/output_generator.py
import csv
import json
import logging
import os # Added for path joining
from datetime import datetime

class OutputGenerator:
    def __init__(self, config):
        self.config = config
        # Define output paths relative to the backend script location
        self.backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Assumes this file is in modules/
        self.data_dir = os.path.join(self.backend_dir, 'data')
        self.frontend_public_dir = os.path.join(self.backend_dir, '..', 'frontend', 'public') # Path to frontend/public

        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.frontend_public_dir, exist_ok=True)

        self.csv_output_path_template = os.path.join(self.data_dir, 'daily_leads_{date}.csv')
        self.html_output_path = os.path.join(self.data_dir, 'leads_dashboard.html') # Keep internal dashboard in data/
        self.json_output_path = os.path.join(self.frontend_public_dir, 'graded_leads.json') # Uncommented for frontend use
        self.frontend_html_path = os.path.join(self.backend_dir, '..', 'frontend', 'index.html') # Path to frontend index.html

    def generate_csv(self, leads_data):
        """Generates a CSV report from the leads data."""
        if not leads_data:
            logging.warning("No leads data provided for CSV generation.")
            return

        today_date = datetime.now().strftime('%Y-%m-%d')
        filepath = self.csv_output_path_template.format(date=today_date)
        logging.info(f"Generating CSV report at: {filepath}")

        if not leads_data:
             logging.warning("Cannot generate CSV header: No leads found.")
             return

        # Define the header for the CSV file
        header = [
            'id', 'city', 'title', 'url', 'date_posted_iso', 'category',
            'description', 'estimated_value', 'contact_method',
            'contact_info', 'has_been_contacted', 'follow_up_date',
            'scraped_timestamp',
            'ai_is_junk', 'ai_profitability_score', 'ai_reasoning'
        ]
        processed_leads_for_csv = []
        for lead in leads_data:
            processed_lead = lead.copy()
            ai_grade = processed_lead.pop('ai_grade', None)
            processed_lead['ai_is_junk'] = ai_grade.get('is_junk') if isinstance(ai_grade, dict) else None
            processed_lead['ai_profitability_score'] = ai_grade.get('profitability_score') if isinstance(ai_grade, dict) else None
            processed_lead['ai_reasoning'] = ai_grade.get('reasoning') if isinstance(ai_grade, dict) else None
            for key in header:
                processed_lead.setdefault(key, None)
            processed_leads_for_csv.append(processed_lead)

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=header, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(processed_leads_for_csv)
            logging.info(f"Successfully generated CSV report with {len(processed_leads_for_csv)} leads.")
        except Exception as e:
            logging.error(f"Error generating CSV report: {e}", exc_info=True)

    def generate_graded_json(self, leads_data):
        """Generates a JSON file containing leads formatted for the React frontend."""
        if not leads_data:
            logging.warning("No leads data provided for JSON generation.")
            return

        filepath = self.json_output_path
        logging.info(f"Generating graded JSON output for frontend at: {filepath}")

        formatted_leads = []
        for lead in leads_data:
            ai_grade = lead.get('ai_grade', {})
            if not isinstance(ai_grade, dict): # Handle cases where ai_grade might not be a dict
                ai_grade = {}

            # Format dates - handle potential None or invalid values gracefully
            scraped_ts = lead.get('scraped_timestamp')
            posted_ts = lead.get('date_posted_iso')
            follow_up_dt = lead.get('follow_up_date')

            scraped_formatted = "N/A"
            if isinstance(scraped_ts, datetime):
                scraped_formatted = scraped_ts.strftime('%Y-%m-%d %H:%M')
            elif isinstance(scraped_ts, str): # Attempt to parse if it's already a string
                 try: scraped_formatted = datetime.fromisoformat(scraped_ts).strftime('%Y-%m-%d %H:%M')
                 except ValueError: pass # Keep "N/A" if parsing fails

            posted_formatted = "N/A"
            if isinstance(posted_ts, datetime):
                posted_formatted = posted_ts.strftime('%Y-%m-%d %H:%M')
            elif isinstance(posted_ts, str):
                 try: posted_formatted = datetime.fromisoformat(posted_ts).strftime('%Y-%m-%d %H:%M')
                 except ValueError: pass

            follow_up_formatted = None # Keep as None if not set
            if isinstance(follow_up_dt, datetime):
                follow_up_formatted = follow_up_dt.strftime('%Y-%m-%d')
            elif isinstance(follow_up_dt, str):
                 try: follow_up_formatted = datetime.fromisoformat(follow_up_dt).strftime('%Y-%m-%d')
                 except ValueError: pass # Keep None if parsing fails


            formatted_lead = {
                "id": lead.get('id'),
                "scraped": scraped_formatted,
                "datePosted": posted_formatted,
                "city": lead.get('city'),
                "title": lead.get('title'),
                "url": lead.get('url'),
                "description": lead.get('description'),
                "value": lead.get('estimated_value'), # Assumes this maps to 'value'
                "contactMethod": lead.get('contact_method'),
                "category": lead.get('category'),
                "contacted": "Yes" if lead.get('has_been_contacted') else "No", # Convert boolean to Yes/No
                "followUp": follow_up_formatted, # Use formatted date or None
                "aiScore": ai_grade.get('profitability_score', "N/A"), # Use "N/A" if missing
                "isJunk": "Yes" if ai_grade.get('is_junk', False) else "No", # Convert boolean to Yes/No
                "aiReason": ai_grade.get('reasoning', "N/A") # Use "N/A" if missing
            }
            formatted_leads.append(formatted_lead)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(formatted_leads, f, indent=2, ensure_ascii=False) # Use indent=2 for consistency with many JS formatters
            logging.info(f"Successfully generated formatted JSON file for frontend with {len(formatted_leads)} leads.")
        except TypeError as e:
             logging.error(f"TypeError generating formatted JSON report: {e}. Check for non-serializable data types.", exc_info=True)
        except Exception as e:
            logging.error(f"Error generating JSON report: {e}", exc_info=True)

    # Placeholder for weekly summary/trend analysis
    def generate_weekly_summary(self, leads_data):
        """Generates a weekly summary report (placeholder)."""
        logging.info("Weekly summary generation not yet implemented.")
        pass
