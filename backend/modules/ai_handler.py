# modules/ai_handler.py
# modules/ai_handler.py
import logging
import time
import json
from collections import deque
from datetime import datetime, timedelta

# Langchain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.exceptions import OutputParserException

# Exception handling imports
from openai import RateLimitError as OpenAIRateLimitError, APIError as OpenAIAPIError, APITimeoutError as OpenAPITimeoutError
from google.api_core.exceptions import ResourceExhausted as GoogleRateLimitError, GoogleAPIError, DeadlineExceeded as GoogleAPITimeoutError

# Import keys directly from config (which loads from .env)
# Re-added GEMINI_API_KEYS import
from config.settings import OPENROUTER_API_KEY, GEMINI_API_KEYS, AI_CONFIG

class AIHandler:
    def __init__(self, config): # config is passed but we use imported constants now
        # Re-added Gemini attributes
        self.gemini_model_name = AI_CONFIG.get('GEMINI_MODEL', "gemini-2.0-flash") # Use updated model name
        self.openrouter_model_name = AI_CONFIG.get('OPENROUTER_MODEL', "anthropic/claude-3-haiku")
        self.openrouter_base_url = AI_CONFIG.get('OPENROUTER_BASE_URL', "https://openrouter.ai/api/v1")
        self.key_cooldown = timedelta(minutes=AI_CONFIG.get('KEY_CYCLE_COOLDOWN_MINUTES', 20)) # Re-added cooldown

        self.gemini_keys = deque(GEMINI_API_KEYS) # Re-added Gemini keys
        self.openrouter_key = OPENROUTER_API_KEY

        self.gemini_unavailable_until = None # Re-added Gemini state
        # Prioritize Gemini if keys exist, otherwise OpenRouter, then disabled
        if self.gemini_keys:
            self.active_service = 'gemini'
        elif self.openrouter_key:
            self.active_service = 'openrouter'
        else:
            self.active_service = 'disabled'

        if self.active_service == 'disabled':
            logging.error("No Gemini or OpenRouter API keys found in config/env. AI filtering disabled.")
        elif not self.gemini_keys:
             logging.warning("No Gemini API keys found. Will use OpenRouter as fallback.")
        elif not self.openrouter_key:
             logging.warning("No OpenRouter API key found. Will only use Gemini (no fallback).")


        logging.info(f"AI Handler initialized. Primary Service: {self.active_service.upper()}. Gemini Keys: {len(self.gemini_keys)}. OpenRouter Key: {'Yes' if self.openrouter_key else 'No'}")

    def _get_llm_client(self, temperature=None): # Keep temperature parameter
        """Gets the appropriate Langchain LLM client based on current state."""
        now = datetime.now()

        # --- Gemini Logic ---
        if self.active_service == 'gemini':
            if self.gemini_unavailable_until and now < self.gemini_unavailable_until:
                logging.warning(f"Gemini keys are on cooldown until {self.gemini_unavailable_until}. Attempting OpenRouter fallback.")
                self.active_service = 'openrouter' # Temporarily switch to OpenRouter
                # Fall through to OpenRouter logic below
            elif not self.gemini_keys:
                 logging.warning("No Gemini keys available. Attempting OpenRouter fallback.")
                 self.active_service = 'openrouter' # Permanently switch if no keys
                 # Fall through to OpenRouter logic below
            else:
                try:
                    current_key = self.gemini_keys[0] # Peek at the next key
                    logging.debug(f"Initializing Gemini client with model {self.gemini_model_name}.")
                    # Pass temperature if provided
                    client_kwargs = {
                        "model": self.gemini_model_name,
                        "google_api_key": current_key,
                        "convert_system_message_to_human": True, # Recommended for Gemini
                        # Set max_output_tokens at initialization
                        "max_output_tokens": AI_CONFIG.get('GEMINI_MAX_TOKENS', 8192) # Use a default or get from config if added
                    }
                    if temperature is not None:
                        client_kwargs["temperature"] = temperature
                    return ChatGoogleGenerativeAI(**client_kwargs)
                except Exception as e:
                    logging.error(f"Failed to initialize Gemini client: {e}", exc_info=True)
                    # Don't cycle key here, cycle on API call failure
                    return None # Indicate failure to get client

        # --- OpenRouter Logic (Fallback or Primary) ---
        if self.active_service == 'openrouter' and self.openrouter_key:
            try:
                logging.debug(f"Initializing OpenRouter client with model {self.openrouter_model_name}.")
                # Pass temperature if provided
                client_kwargs = {
                    "model": self.openrouter_model_name,
                    "openai_api_key": self.openrouter_key,
                    "base_url": self.openrouter_base_url,
                }
                if temperature is not None:
                    client_kwargs["temperature"] = temperature

                return ChatOpenAI(**client_kwargs)
            except Exception as e:
                logging.error(f"Failed to initialize OpenRouter client: {e}", exc_info=True)
                # If OpenRouter fails to init, and we got here from Gemini cooldown, we're stuck
                if not self.gemini_keys and not (self.gemini_unavailable_until and now < self.gemini_unavailable_until):
                     logging.critical("OpenRouter client init failed and no Gemini keys available/off cooldown.")
                return None
        # --- Disabled ---
        else: # Covers disabled state or OpenRouter fallback failure
            logging.error("No active AI service or keys available/functional.")
            return None

    def _call_llm_with_cycling(self, system_prompt, user_prompt, max_tokens, temperature, json_mode=True, max_retries=2, initial_delay=5):
        """
        Handles the LLM call, retries, and cycling between Gemini keys/OpenRouter.
        Returns the raw response content string or None if all attempts fail.
        """
        if self.active_service == 'disabled':
            logging.warning("AI service is disabled. Skipping LLM call.")
            return None

        retries = 0
        delay = initial_delay
        last_error = None

        while retries <= max_retries:
            # Pass temperature to _get_llm_client
            llm_client = self._get_llm_client(temperature=temperature)
            if not llm_client:
                logging.error("Failed to get LLM client. Cannot make API call.")
                # If Gemini was on cooldown, maybe try OpenRouter one last time if available
                if self.active_service == 'gemini' and self.gemini_unavailable_until and datetime.now() < self.gemini_unavailable_until and self.openrouter_key:
                    logging.warning("Gemini client failed init during cooldown, trying OpenRouter again.")
                    self.active_service = 'openrouter'
                    continue # Retry the while loop, will attempt OpenRouter init
                return None # Cannot proceed

            current_service = self.active_service
            model_name = self.gemini_model_name if current_service == 'gemini' else self.openrouter_model_name
            logging.debug(f"Attempt {retries + 1}/{max_retries + 1} using {current_service.upper()} model: {model_name}")

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            invoke_kwargs = {}

            # Set parameters based on client type
            if isinstance(llm_client, ChatGoogleGenerativeAI):
                # Gemini specific settings (temperature handled at init)
                # Gemini specific settings (temperature and max_output_tokens handled at init)
                # We rely on the prompt asking for JSON for json_mode.
                # Safety settings could be added to client_kwargs if needed.
                pass # No specific invoke_kwargs needed here now for max_tokens
            elif isinstance(llm_client, ChatOpenAI):
                # OpenRouter specific settings (temperature handled at init)
                invoke_kwargs["max_tokens"] = max_tokens
                if json_mode:
                    # Attempt to use JSON mode for OpenRouter models that support it
                    invoke_kwargs["response_format"] = {"type": "json_object"}
            else:
                 logging.warning("Unknown LLM client type, cannot set specific parameters.")
                 # Pass generic params if possible
                 invoke_kwargs["temperature"] = temperature
                 invoke_kwargs["max_tokens"] = max_tokens


            try:
                # Use **invoke_kwargs
                response = llm_client.invoke(messages, **invoke_kwargs)
                response_content = response.content.strip()
                logging.debug(f"Raw response from {current_service.upper()}: {response_content}")

                # --- Reset Gemini cooldown on success ---
                if current_service == 'gemini' and self.gemini_unavailable_until:
                    logging.info("Successful Gemini call, resetting cooldown.")
                    self.gemini_unavailable_until = None
                # --- End Reset Cooldown ---

                return response_content # Success

            # --- Gemini Error Handling ---
            except (GoogleRateLimitError, GoogleAPIError, GoogleAPITimeoutError) as e:
                 logging.warning(f"Gemini API Error (Attempt {retries + 1}): {e}")
                 last_error = e
                 # Cycle Gemini key and potentially switch to OpenRouter
                 if self.gemini_keys:
                     failed_key = self.gemini_keys.popleft() # Remove the failed key
                     self.gemini_keys.append(failed_key) # Add it to the end
                     logging.warning(f"Rotated Gemini API key. Keys remaining: {len(self.gemini_keys)}")
                     if len(self.gemini_keys) == 1 and isinstance(e, GoogleRateLimitError): # If only one key left and it's rate limited
                          logging.warning("Last Gemini key hit rate limit. Applying cooldown.")
                          self.gemini_unavailable_until = datetime.now() + self.key_cooldown
                          if self.openrouter_key:
                              logging.info("Switching to OpenRouter due to Gemini cooldown.")
                              self.active_service = 'openrouter'
                          else:
                              logging.error("No OpenRouter key available for fallback during Gemini cooldown.")
                              # Continue retry loop, but it will likely fail again until cooldown expires
                     elif not self.gemini_keys: # Should not happen if logic above is correct, but safety check
                          logging.error("Ran out of Gemini keys during rotation.")
                          if self.openrouter_key:
                              logging.info("Switching to OpenRouter as Gemini keys exhausted.")
                              self.active_service = 'openrouter'
                          else:
                               logging.critical("No Gemini or OpenRouter keys available.")
                               # Let retry logic handle final failure
                 else: # No Gemini keys were available to begin with
                      if self.openrouter_key:
                           logging.info("Gemini error occurred but no keys were available. Switching to OpenRouter.")
                           self.active_service = 'openrouter'
                      else:
                           logging.error("Gemini error, but no Gemini keys and no OpenRouter key for fallback.")
                 # Proceed to retry logic below

            # --- OpenRouter Error Handling ---
            except (OpenAIRateLimitError, OpenAIAPIError, OpenAPITimeoutError) as e:
                 logging.warning(f"OpenRouter API Error (Attempt {retries + 1}): {e}")
                 last_error = e
                 # No fallback from OpenRouter currently, just proceed to retry logic

            except OutputParserException as e:
                 logging.warning(f"Langchain Output Parser Error (Attempt {retries + 1}): {e}. Likely malformed response from LLM.")
                 last_error = e

            except Exception as e:
                # Check if it's the specific TypeError we've seen
                if isinstance(e, TypeError) and "'NoneType' object is not iterable" in str(e):
                    logging.error(f"TypeError during LLM call (Attempt {retries + 1}): Likely malformed API response (e.g., missing 'choices'). Error: {e}", exc_info=True)
                else:
                    logging.error(f"Unexpected error during LLM call (Attempt {retries + 1}): {e}", exc_info=True)
                last_error = e

            # --- Retry Logic ---
            retries += 1
            if retries <= max_retries:
                logging.info(f"Waiting {delay:.1f} seconds before retry {retries}/{max_retries}...")
                time.sleep(delay)
                delay *= 1.5 # Exponential backoff
            else:
                logging.error(f"LLM call failed after {max_retries + 1} attempts. Last error: {last_error}")
                return None # Indicate failure after all retries

        logging.error(f"LLM call loop finished unsuccessfully.")
        return None


    def grade_lead(self, title, description, max_retries=2, initial_delay=5):
        """
        Uses the configured AI model (now primarily OpenRouter/Haiku) to grade a lead.
        Returns a dictionary: {'is_junk': bool, 'profitability_score': int|None, 'reasoning': str}
        Returns None if the AI call fails definitively after retries.
        """
        if self.active_service == 'disabled':
             return {"is_junk": False, "profitability_score": None, "reasoning": "AI service disabled"}

        description_snippet = description[:2000] # Limit description length

        # Updated prompt to explicitly ask for JSON and include Google Ads terms
        system_prompt = """You are an expert lead evaluator for a web/graphic design agency specializing in website development, graphic design, branding, Photoshop services, and Google Ads (AdWords/PPC) management. Your task is to analyze Craigslist posts to identify potential clients *seeking these specific services*.

Respond ONLY with a valid JSON object containing the following keys:
- "is_junk": boolean. Set to `true` if the post is spam, selling unrelated items/services (like art pieces, supplies, classes), offering jobs *at* other companies, or is *not* clearly a request *for* web design, graphic design, Photoshop, or Google Ads/AdWords/PPC services. Set to `false` ONLY if the post appears to be a genuine request *seeking* the agency's services.
- "profitability_score": integer (1-10, higher means more profitable potential) or null (if is_junk is true). Base the score on factors like: clarity of the service request, mention of budget, direct relevance to the agency's core services (web design, graphic design, Photoshop, Google Ads/AdWords/PPC), specificity of needs, and perceived professionalism of the poster. Posts just selling items, even related ones, should generally be junk or have a very low score.
- "reasoning": string (a brief explanation for the score and junk status, specifically mentioning *why* it is or isn't a relevant service request for the agency).

Example valid JSON output:
{"is_junk": false, "profitability_score": 7, "reasoning": "Clear request for a new business website, mentions specific features needed."}
{"is_junk": true, "profitability_score": null, "reasoning": "Post is selling used graphic design software, not seeking services."}"""

        user_prompt = f"""Please evaluate the following Craigslist post based *strictly* on whether it represents a potential client seeking web design, graphic design, Photoshop, or Google Ads/AdWords/PPC services:

Title: {title}
Description: {description_snippet}

Provide your evaluation ONLY in the specified JSON format."""

        response_content = self._call_llm_with_cycling(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=200, # Increased slightly for robust JSON
            temperature=0.3, # Keep temperature setting
            json_mode=True, # Attempt to use native JSON mode if available
            max_retries=max_retries,
            initial_delay=initial_delay
        )

        if response_content is None:
            logging.error(f"AI grading failed for '{title}' after all retries/fallbacks.")
            return None # Indicate definitive failure

        try:
            # Attempt to parse the JSON response
            # Sometimes models wrap JSON in ```json ... ```, try to strip that
            if response_content.startswith("```json"):
                response_content = response_content[7:]
                if response_content.endswith("```"):
                    response_content = response_content[:-3]
            response_content = response_content.strip()

            grade_data = json.loads(response_content)

            # --- Validation (same as before) ---
            if not all(k in grade_data for k in ["is_junk", "profitability_score", "reasoning"]):
                logging.warning(f"AI grading response missing required keys for '{title}'. Response: {response_content}")
                grade_data = {"is_junk": True, "profitability_score": None, "reasoning": "AI response format error (missing keys)"}
            if not isinstance(grade_data.get("is_junk"), bool):
                 grade_data["is_junk"] = True
                 grade_data["reasoning"] = str(grade_data.get("reasoning", "")) + " | Invalid type for is_junk."
            if grade_data["is_junk"]:
                grade_data["profitability_score"] = None
            elif not (grade_data.get("profitability_score") is None or (isinstance(grade_data.get("profitability_score"), int) and 1 <= grade_data["profitability_score"] <= 10)):
                 logging.warning(f"AI grading returned invalid score for '{title}'. Score: {grade_data.get('profitability_score')}")
                 grade_data["profitability_score"] = None
                 grade_data["reasoning"] = str(grade_data.get("reasoning", "")) + " | Invalid profitability score (must be 1-10 or null)."
            if not isinstance(grade_data.get("reasoning"), str):
                 grade_data["reasoning"] = str(grade_data.get("reasoning", "")) + " | Invalid type for reasoning."
            # --- End Validation ---

            logging.info(f"AI grading successful for '{title}'. Score: {grade_data.get('profitability_score')}, Junk: {grade_data.get('is_junk')}")
            return grade_data

        except json.JSONDecodeError:
            logging.error(f"AI grading response was not valid JSON for '{title}' after stripping ```. Response: {response_content}")
            # Return a failure indicator, as the LLM failed to follow instructions even after retries
            return {"is_junk": True, "profitability_score": None, "reasoning": "AI failed to return valid JSON"}
        except Exception as e:
             logging.error(f"Unexpected error parsing AI grade for '{title}': {e}", exc_info=True)
             return None


    def pre_filter_lead(self, title, snippet, max_retries=1, initial_delay=2):
        """
        Uses a dynamic positive keyword check (with fuzzy matching) and the AI model for a quick pre-filter based on title/snippet.
        Returns True if potentially relevant, False if definitely junk/unrelated.
        Defaults to True if the AI call fails, to avoid discarding good leads.
        """
        import re

        # Focused positive keyword list (core web/design/marketing terms)
        POSITIVE_TERMS = [
            "website", "web site", "web dev", "web design", "web designer", "web build", "site build", "site dev",
            "wordpress", "wp", "elementor", "shopify", "ecommerce", "landing page", "ux", "ui", "branding",
            "graphic design", "graphic designer", "logo", "photoshop", "psd", "illustrator", "adobe", "seo",
            "google ads", "adwords", "ppc", "marketing"
        ]
        title_lower = title.lower()
        found_positive = False
        for term in POSITIVE_TERMS:
            pattern = re.compile(rf"\b{re.escape(term).replace(' ', r'[\s/-]?')}\b", re.IGNORECASE)
            if pattern.search(title_lower):
                found_positive = True
                break

        if found_positive:
            logging.info(f"Pre-filter: Title '{title}' matched a positive keyword. Passing to AI grading.")
            return True

        if self.active_service == 'disabled':
            logging.warning("AI service is disabled. Skipping pre-filtering, assuming relevant.")
            return True

        content_to_analyze = f"Title: {title}"
        if snippet: content_to_analyze += f"\nSnippet: {snippet[:300]}"

        # AI prompt (unchanged)
        system_prompt = """You are a rapid lead pre-filter for a web/graphic design agency. Your task is to quickly determine if a Craigslist post *might* be relevant based ONLY on its title and snippet.

Focus: Identify if the post is *definitely* junk (spam, selling unrelated items like art/furniture/supplies, offering jobs at other companies, user research studies, seeking dating advice, etc.) or if it *could possibly* be someone seeking web design, graphic design, Photoshop, or Google Ads/AdWords/PPC services. Err on the side of caution; if unsure, mark as potentially relevant.

Respond ONLY with a valid JSON object containing a single key:
- "is_potentially_relevant": boolean (true if it *might* be relevant, false if it's *definitely* junk/unrelated)

Example valid JSON output:
{"is_potentially_relevant": true}
{"is_potentially_relevant": false}"""

        user_prompt = f"""Quickly evaluate if the following post title/snippet could possibly be relevant to a web/graphic design agency seeking clients. Is it definitely junk/unrelated?

{content_to_analyze}

Provide your evaluation ONLY in the specified JSON format."""

        response_content = self._call_llm_with_cycling(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=60, # Small max tokens for faster response
            temperature=0.1, # Low temp for pre-filter
            json_mode=True,
            max_retries=max_retries,
            initial_delay=initial_delay
        )

        if response_content is None:
            logging.error(f"AI pre-filter failed for '{title}' after all retries/fallbacks. Assuming relevant.")
            return True # Default to relevant on failure

        try:
            # Strip potential markdown
            if response_content.startswith("```json"):
                response_content = response_content[7:]
                if response_content.endswith("```"):
                    response_content = response_content[:-3]
            response_content = response_content.strip()

            filter_data = json.loads(response_content)

            if "is_potentially_relevant" in filter_data and isinstance(filter_data["is_potentially_relevant"], bool):
                logging.debug(f"AI pre-filter successful for '{title}'. Potentially Relevant: {filter_data['is_potentially_relevant']}")
                return filter_data["is_potentially_relevant"]
            else:
                logging.warning(f"AI pre-filter response missing/invalid key for '{title}'. Response: {response_content}. Assuming relevant.")
                return True # Default to relevant on format error

        except json.JSONDecodeError:
            logging.warning(f"AI pre-filter response was not valid JSON for '{title}'. Response: {response_content}. Assuming relevant.")
            return True # Default to relevant on JSON error
        except Exception as e:
             logging.error(f"Unexpected error parsing AI pre-filter for '{title}': {e}", exc_info=True)
             return True # Default to relevant on unexpected error
