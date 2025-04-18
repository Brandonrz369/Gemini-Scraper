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
        next_page_link = None # Initialize next_page_link
        if not html_content:
            logging.warning("parse_search_page received empty html_content.")
            return leads, next_page_link # Return two values (empty list, None)

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

                    # --- ADDED LOGGING ---
                    logging.debug(f"Parser found potential lead: Title='{title}', URL='{url}'")
                    # --- END ADDED LOGGING ---

                    leads.append({'url': url, 'title': title})
                    count += 1 # Increment counter after successfully adding a lead
                else:
                    logging.debug("Could not find title link element in result item.")

        except Exception as e:
            logging.error(f"Error parsing search page HTML: {e}", exc_info=True)
            # Return empty list and None in case of error during parsing
            return [], None # Return two values

        # Find the next page link after processing leads
        next_page_link = self.find_next_page_link(html_content)

        logging.info(f"Extracted {len(leads)} basic leads from search page. Next page link: {next_page_link}")
        return leads, next_page_link # Return both leads and the link (already correct here)

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
            # --- Extract Contact Email (if available) ---
            full_details['contact_email'] = None # Initialize
            reply_info_section = soup.find('div', class_='reply-info') # Often contains the email spans
            # Define reply_button_area earlier to ensure it exists for phone fallback logic
            reply_button_area = soup.find('div', class_='reply-button-row') # Or similar container

            if reply_info_section:
                local_part_span = reply_info_section.find('span', class_='reply-email-localpart')
                if local_part_span:
                    # The domain part is usually in the next sibling span
                    domain_part_span = local_part_span.find_next_sibling('span')
                    if domain_part_span:
                        local_part = local_part_span.get_text(strip=True)
                        domain_part = domain_part_span.get_text(strip=True)
                        if local_part and domain_part:
                            full_details['contact_email'] = f"{local_part}{domain_part}"
                            logging.debug(f"Extracted contact email for {basic_lead_info.get('url')}")
                        else:
                             logging.debug(f"Found email spans but one was empty for {basic_lead_info.get('url')}")
                    else:
                         logging.debug(f"Found local part span but no sibling domain span for {basic_lead_info.get('url')}")
                else:
                     logging.debug(f"Could not find span.reply-email-localpart within reply-info for {basic_lead_info.get('url')}")
            elif reply_button_area: # Use elif since reply_button_area is now defined earlier
                 # Fallback: Check if the spans exist directly under the reply button area if no div.reply-info
                 local_part_span = reply_button_area.find('span', class_='reply-email-localpart')
                 if local_part_span:
                           domain_part_span = local_part_span.find_next_sibling('span')
                           if domain_part_span:
                               local_part = local_part_span.get_text(strip=True)
                               domain_part = domain_part_span.get_text(strip=True)
                               if local_part and domain_part:
                                   full_details['contact_email'] = f"{local_part}{domain_part}"
                                   logging.debug(f"Extracted contact email (fallback) for {basic_lead_info.get('url')}")

            # --- Extract Contact Phone (if available) ---
            full_details['contact_phone'] = None # Initialize
            # Phone numbers are often in tel: links within the reply info or button area
            phone_link = None
            if reply_info_section:
                 phone_link = reply_info_section.find('a', href=lambda href: href and href.startswith('tel:'))
            if not phone_link and reply_button_area: # Check fallback area if not found in reply_info
                 phone_link = reply_button_area.find('a', href=lambda href: href and href.startswith('tel:'))

            if phone_link:
                phone_number = phone_link.get_text(strip=True)
                if phone_number:
                    full_details['contact_phone'] = phone_number
                    logging.debug(f"Extracted contact phone for {basic_lead_info.get('url')}")
                else:
                    logging.debug(f"Found phone link but text was empty for {basic_lead_info.get('url')}")
            else:
                 logging.debug(f"Could not find phone link for {basic_lead_info.get('url')}")


            # --- (Placeholder) Extract Other Details ---
            # Example: Look for reply button info (already done above implicitly)
            reply_button = soup.find('button', class_='reply-button')
            if reply_button:
                 full_details['contact_method'] = 'Reply Button' # Keep this for context

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
