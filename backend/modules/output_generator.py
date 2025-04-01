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
        self.json_output_path = os.path.join(self.frontend_public_dir, 'graded_leads.json') # Save JSON to frontend/public

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

    def generate_html_dashboard(self, leads_data):
        """Generates a simple HTML dashboard for viewing leads (saved in backend/data)."""
        # This remains largely unchanged, still saves to backend/data
        if not leads_data:
            logging.warning("No leads data provided for HTML dashboard generation.")
            return

        logging.info(f"Generating internal HTML dashboard at: {self.html_output_path}")
        # (HTML generation code remains the same as before, including AI fields)
        # Basic HTML structure with a table
        html_start = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Craigslist Leads Dashboard (Internal)</title>
    <!-- DataTables CSS -->
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <!-- Custom Styles -->
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }} /* Escape braces */
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .description {{ max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .reasoning {{ max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    </style>
</head>
<body>
    <h1>Craigslist Leads Dashboard (Internal)</h1>
    <p>Generated on: {generation_time}</p>
    <p>Total Leads in DB: {lead_count}</p>
    <table id="leadsTable" class="display" style="width:100%">
        <thead>
            <tr>
                <th>Scraped</th>
                <th>Date Posted</th>
                <th>City</th>
                <th>Title</th>
                <th>Description</th>
                <th>Value</th>
                <th>Contact Method</th>
                <th>Category</th>
                <th>Contacted</th>
                <th>Follow Up</th>
                <th>AI Score</th>
                <th>AI Junk?</th>
                <th>AI Reason</th>
            </tr>
        </thead>
        <tbody>
"""
        html_end = """
        </tbody>
    </table>
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
    <!-- DataTables JS -->
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script>
        $(document).ready(function() {{ // Escape braces
            $('#leadsTable').DataTable({{ // Escape braces
                "order": [[ 0, "desc" ]]
            }});
        }});
    </script>
</body>
</html>
"""
        table_rows = []
        for lead in leads_data:
            scraped_dt_str = lead.get('scraped_timestamp', 'N/A')
            posted_dt_str = lead.get('date_posted_iso', 'N/A')
            try:
                if scraped_dt_str and scraped_dt_str != 'N/A': scraped_dt_str = datetime.fromisoformat(scraped_dt_str).strftime('%Y-%m-%d %H:%M')
            except ValueError: pass
            try:
                if posted_dt_str and posted_dt_str != 'N/A': posted_dt_str = datetime.fromisoformat(posted_dt_str).strftime('%Y-%m-%d %H:%M')
            except ValueError: pass

            desc_tooltip = lead.get('description', '').replace('"', '"')
            ai_grade = lead.get('ai_grade')
            ai_reasoning = ai_grade.get('reasoning', 'N/A') if isinstance(ai_grade, dict) else 'N/A'
            ai_reasoning_tooltip = ai_reasoning.replace('"', '"')
            ai_score = ai_grade.get('profitability_score', 'N/A') if isinstance(ai_grade, dict) else 'N/A'
            ai_is_junk = ai_grade.get('is_junk', False) if isinstance(ai_grade, dict) else False

            row = f"""
            <tr>
                <td>{scraped_dt_str}</td>
                <td>{posted_dt_str}</td>
                <td>{lead.get('city', 'N/A')}</td>
                <td><a href="{lead.get('url', '#')}" target="_blank">{lead.get('title', 'N/A')}</a></td>
                <td class="description" title="{desc_tooltip}">{lead.get('description', 'N/A')}</td>
                <td>{lead.get('estimated_value', 'N/A')}</td>
                <td>{lead.get('contact_method', 'N/A')}</td>
                <td>{lead.get('category', 'N/A')}</td>
                <td>{'Yes' if lead.get('has_been_contacted') else 'No'}</td>
                <td>{lead.get('follow_up_date', 'N/A')}</td>
                <td>{ai_score}</td>
                <td>{'Yes' if ai_is_junk else 'No'}</td>
                <td class="reasoning" title="{ai_reasoning_tooltip}">{ai_reasoning[:50]}{'...' if len(ai_reasoning) > 50 else ''}</td>
            </tr>
"""
            table_rows.append(row)

        full_html = html_start.format(
            generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            lead_count=len(leads_data)
        ) + "".join(table_rows) + html_end

        try:
            with open(self.html_output_path, 'w', encoding='utf-8') as f:
                f.write(full_html)
            logging.info(f"Successfully generated internal HTML dashboard.")
        except Exception as e:
            logging.error(f"Error generating internal HTML dashboard: {e}", exc_info=True)

    def generate_graded_json(self, leads_data):
        """Generates a JSON file containing leads with AI grading to the frontend public directory."""
        if not leads_data:
            logging.warning("No leads data provided for JSON generation.")
            return

        filepath = self.json_output_path
        logging.info(f"Generating graded JSON output for frontend at: {filepath}")

        try:
            serializable_leads = []
            for lead in leads_data:
                serializable_lead = lead.copy()
                for key, value in serializable_lead.items():
                    if isinstance(value, datetime):
                        serializable_lead[key] = value.isoformat()
                serializable_leads.append(serializable_lead)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(serializable_leads, f, indent=4, ensure_ascii=False)
            logging.info(f"Successfully generated graded JSON file with {len(serializable_leads)} leads.")
        except TypeError as e:
             logging.error(f"TypeError generating JSON report: {e}. Check for non-serializable data types.", exc_info=True)
        except Exception as e:
            logging.error(f"Error generating JSON report: {e}", exc_info=True)

    # Placeholder for weekly summary/trend analysis
    def generate_weekly_summary(self, leads_data):
        """Generates a weekly summary report (placeholder)."""
        logging.info("Weekly summary generation not yet implemented.")
        pass
