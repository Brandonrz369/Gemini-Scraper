# modules/content_analyzer.py (Recreated)
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

class ContentAnalyzer:
    def __init__(self, config):
        # Config might be used later for filtering keywords, etc.
        self.config = config
        logging.info("ContentAnalyzer initialized (Recreated Version).")

    def parse_search_page(self, html_content, city_code, limit_leads=None): # Added limit_leads parameter
        """
        Parses the HTML of a Craigslist search results page to find basic lead info.
        Returns a list of dictionaries, e.g., [{'url': '...', 'title': '...'}, ...]
        Optionally limits the number of leads returned using limit_leads.
        NOTE: Selectors used here are common guesses and might need adjustment.
        """
        leads = []
        if not html_content:
            return leads

        try:
            soup = BeautifulSoup(html_content, 'lxml') # Use lxml parser

            # Updated Selector based on provided HTML (new york web_html_info design jobs - craigslist.html)
            # Results are in <div class="cl-search-result">
            results = soup.select('div.cl-search-result')

            logging.info(f"Found {len(results)} potential result elements using 'div.cl-search-result'.")

            count = 0 # Initialize counter for limiting leads
            for result in results:
                # Apply limit if specified
                if limit_leads is not None and count >= limit_leads:
                    logging.warning(f"Reached lead limit ({limit_leads}) for this page. Stopping parse.")
                    break

                # Title and link are in <a class="posting-title">
                title_element = result.find('a', class_='posting-title')

                if title_element and title_element.has_attr('href'):
                    url = title_element['href']
                    # Title text is within a span with class 'label' inside the link
                    title_span = title_element.find('span', class_='label')
                    title = title_span.get_text(strip=True) if title_span else title_element.get_text(strip=True) # Fallback to link text

                    # Handle relative URLs if necessary (though Oxylabs might resolve them)
                    if not url.startswith('http'):
                        # Need a base URL - constructing from city_code might be fragile
                        # Assuming Oxylabs provides absolute URLs or this needs refinement
                        logging.warning(f"Found relative URL, skipping for now: {url}")
                        continue

                    leads.append({'url': url, 'title': title})
                    count += 1 # Increment counter after successfully adding a lead
                else:
                    logging.debug("Could not find title link element in result item.")

        except Exception as e:
            logging.error(f"Error parsing search page HTML: {e}", exc_info=True)

        logging.info(f"Extracted {len(leads)} basic leads from search page.")
        return leads

    def analyze_lead_details(self, html_content, basic_lead_info):
        """
        Parses the HTML of a specific lead page to extract description and other details.
        Merges details with basic_lead_info.
        NOTE: Selectors used here are common guesses and might need adjustment.
        """
        full_details = basic_lead_info.copy()
        full_details['description'] = None # Initialize description
        full_details['date_posted_iso'] = None # Initialize post date
        full_details['scraped_timestamp'] = datetime.now().isoformat() # Add scrape time

        if not html_content:
            return full_details

        try:
            soup = BeautifulSoup(html_content, 'lxml')

            # --- Extract Description ---
            # Common ID for the main post body
            description_section = soup.find('section', id='postingbody')
            if description_section:
                # Remove the "QR Code Link to This Post" part if it exists
                qr_element = description_section.find('div', class_='print-qrcode-container')
                if qr_element:
                    qr_element.decompose()
                full_details['description'] = description_section.get_text(separator='\n', strip=True)
            else:
                logging.warning(f"Could not find description section (#postingbody) for {basic_lead_info.get('url')}")

            # --- Extract Post Date ---
            # Date is often in a <time> tag with datetime attribute
            time_tag = soup.find('time', class_='date timeago')
            if time_tag and time_tag.has_attr('datetime'):
                full_details['date_posted_iso'] = time_tag['datetime']
            else:
                 logging.debug(f"Could not find time tag for post date for {basic_lead_info.get('url')}")

            # --- (Placeholder) Extract Other Details ---
            # Add logic here to extract things like contact info, compensation, etc. if needed
            # Example: Look for reply button info
            reply_button = soup.find('button', class_='reply-button')
            if reply_button:
                 full_details['contact_method'] = 'Reply Button'
                 # Further logic could try to get email/phone if revealed

        except Exception as e:
            logging.error(f"Error analyzing lead details HTML for {basic_lead_info.get('url')}: {e}", exc_info=True)

        return full_details

    # Placeholder for finding next page link - requires analyzing search page structure
    def find_next_page_link(self, html_content):
        """
        Parses search page HTML to find the link to the next page.
        Returns the relative URL or None.
        NOTE: Selectors are guesses.
        """
        if not html_content: return None
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            # Common pattern: link with class 'next' inside pagination controls
            next_link = soup.select_one('a.button.next') # Check common button class
            if next_link and next_link.has_attr('href'):
                return next_link['href']
            # Add other potential selectors if needed
        except Exception as e:
            logging.error(f"Error finding next page link: {e}", exc_info=True)
        return None
