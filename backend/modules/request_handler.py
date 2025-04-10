# modules/request_handler.py
import requests
import time
import random
import logging # Import logging
# from fake_useragent import UserAgent # Note: fake-useragent might not be needed if Oxylabs handles it (Removed import)

class RequestHandler:
    def __init__(self, config):
        self.config = config
        # self.ua = UserAgent() # Oxylabs handles user agent via 'user_agent_type'
        self.username = config.get('OXYLABS_USERNAME') # Get from config dict
        self.password = config.get('OXYLABS_PASSWORD') # Get from config dict
        self.base_url = 'https://realtime.oxylabs.io/v1/queries'

        if not self.username or not self.password:
             raise ValueError("Oxylabs username and password must be provided in the configuration.")

        # Stats tracking for adaptive behavior
        self.success_count = 0
        self.failure_count = 0
        self.blocked_count = 0 # Tracks failures after all retries

    def get_page(self, url, retry_count=3, backoff_factor=2):
        """Fetch a page using Oxylabs Web Scraper API with intelligent retries"""
        last_error = None
        for attempt in range(retry_count):
            try:
                # Build request payload for Oxylabs API
                payload = {
                    "source": "universal",
                    "url": url,
                    "user_agent_type": "desktop", # Let Oxylabs manage the user agent
                    "render": "html",  # Get rendered HTML with JavaScript processed
                    # Consider adding 'geo_location' if needed for specific cities
                }

                # Add randomized delay before the request
                # Adjust delay based on Oxylabs recommendations if available
                time.sleep(random.uniform(1, 3)) # Reduced delay as Oxylabs manages infrastructure

                logging.info(f"Attempt {attempt + 1}/{retry_count}: Fetching {url} via Oxylabs...")

                # Make request to Oxylabs API
                response = requests.post(
                    self.base_url,
                    auth=(self.username, self.password),
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=60 # Set a reasonable timeout for the API call
                )

                # Check for successful response from Oxylabs
                if response.status_code == 200:
                    data = response.json()
                    # Oxylabs successful response structure check
                    if ('results' in data and
                        len(data['results']) > 0 and
                        'content' in data['results'][0] and
                        data['results'][0].get('status_code') == 200): # Check status_code within Oxylabs result

                        logging.info(f"Success fetching {url}")
                        self.success_count += 1
                        return data['results'][0]['content'] # Return the HTML content
                    else:
                        # Log Oxylabs specific failure reason if available
                        failure_reason = data.get('_error', 'Unknown Oxylabs issue')
                        status_code_in_result = data['results'][0].get('status_code', 'N/A') if 'results' in data and data['results'] else 'N/A'
                        last_error = f"Oxylabs returned 200 OK but failed for {url}. Reason: {failure_reason}. Internal Status: {status_code_in_result}"
                        logging.warning(last_error) # Use warning level for internal API failures
                        # Treat this as a failure for retry logic
                        self.failure_count += 1

                elif response.status_code == 401:
                     last_error = f"Oxylabs Authentication Failed (401). Check credentials for user '{self.username}'."
                     logging.error(last_error) # Use error level for auth failures
                     # No point retrying on auth failure
                     self.failure_count += (retry_count - attempt) # Count remaining attempts as failures
                     break
                elif response.status_code == 403:
                     last_error = f"Oxylabs Forbidden (403). Check subscription or permissions for {url}."
                     logging.error(last_error) # Use error level for permission issues
                     # May not be worth retrying if it's a permission issue
                     self.failure_count += 1 # Count this attempt as failure
                     # Consider breaking if 403 persists
                elif response.status_code == 429:
                     last_error = f"Oxylabs Rate Limited (429) for {url}."
                     logging.warning(last_error) # Use warning for rate limiting
                     self.failure_count += 1 # Count this attempt as failure
                     # Exponential backoff will handle waiting
                else:
                    # General HTTP error from Oxylabs endpoint
                    last_error = f"Oxylabs API request failed for {url}. Status: {response.status_code}, Body: {response.text[:200]}"
                    logging.warning(last_error) # Use warning for general API errors
                    self.failure_count += 1

                # Implement exponential backoff if request failed (and not auth error)
                if response.status_code != 401:
                    wait_time = backoff_factor ** attempt + random.uniform(0, 1) # Add jitter
                    logging.info(f"Waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)

            except requests.exceptions.Timeout:
                last_error = f"Request timed out after 60s for {url} on attempt {attempt + 1}"
                logging.warning(last_error)
                self.failure_count += 1
                # Apply backoff before retrying
                wait_time = backoff_factor ** attempt + random.uniform(0, 1)
                logging.info(f"Waiting {wait_time:.2f} seconds before retry...")
                time.sleep(wait_time)
            except requests.exceptions.RequestException as e:
                last_error = f"Network exception during request for {url} on attempt {attempt + 1}: {str(e)}"
                logging.warning(last_error, exc_info=True) # Log exception info
                self.failure_count += 1
                # Apply backoff before retrying
                wait_time = backoff_factor ** attempt + random.uniform(0, 1)
                logging.info(f"Waiting {wait_time:.2f} seconds before retry...")
                time.sleep(wait_time)
            except Exception as e:
                # Catch unexpected errors during the process
                last_error = f"Unexpected exception during request for {url} on attempt {attempt + 1}: {str(e)}"
                logging.error(last_error, exc_info=True) # Log unexpected errors as ERROR
                self.failure_count += 1
                # Apply backoff before retrying
                wait_time = backoff_factor ** attempt + random.uniform(0, 1)
                logging.info(f"Waiting {wait_time:.2f} seconds before retry...")
                time.sleep(wait_time)


        # If we exhausted all retries
        logging.error(f"Failed to fetch {url} after {retry_count} attempts. Last error: {last_error}")
        self.blocked_count += 1 # Increment blocked count after all retries fail
        return None

    def get_stats(self):
        """Returns the current request statistics."""
        total_attempts = self.success_count + self.failure_count
        success_rate = self.success_count / total_attempts if total_attempts > 0 else 0
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count, # Failures during retry attempts
            "blocked_count": self.blocked_count, # URLs that failed after all retries
            "total_attempts": total_attempts,
            "success_rate": success_rate
        }

    def is_healthy(self, threshold=0.8):
        """Check if the request handler is working properly based on success rate."""
        stats = self.get_stats()
        # Consider recent performance if stats become large
        return stats["success_rate"] >= threshold if stats["total_attempts"] > 10 else True # Assume healthy if few attempts

    def get_raw_page_for_debug(self, url):
        """Fetches a page using Oxylabs and returns raw content for debugging, minimal retries."""
        logging.debug(f"Attempting to fetch raw HTML for {url}") # Use debug level
        try:
            payload = {
                "source": "universal",
                "url": url,
                "user_agent_type": "desktop",
                "render": "html",
            }
            response = requests.post(
                self.base_url,
                auth=(self.username, self.password),
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            if response.status_code == 200:
                data = response.json()
                if ('results' in data and
                    len(data['results']) > 0 and
                    'content' in data['results'][0] and
                    data['results'][0].get('status_code') == 200):
                    logging.debug(f"Successfully fetched raw HTML.")
                    return data['results'][0]['content']
                else:
                    logging.warning(f"DEBUG: Oxylabs returned 200 OK but failed internally. Response: {data}")
                    return None
            else:
                logging.warning(f"DEBUG: Oxylabs API request failed. Status: {response.status_code}, Body: {response.text[:200]}")
                return None
        except Exception as e:
            logging.error(f"DEBUG: Exception during raw fetch: {str(e)}", exc_info=True)
            return None
