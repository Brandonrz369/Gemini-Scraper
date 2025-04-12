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
from config.settings import OPENROUTER_API_KEY, AI_CONFIG # Removed GEMINI_API_KEYS

class AIHandler:
    def __init__(self, config): # config is passed but we use imported constants now
        # Removed Gemini specific attributes
        self.openrouter_model_name = AI_CONFIG.get('OPENROUTER_MODEL', "anthropic/claude-3-haiku") # Ensure default
        self.openrouter_base_url = AI_CONFIG.get('OPENROUTER_BASE_URL', "https://openrouter.ai/api/v1")
        # self.key_cooldown = timedelta(minutes=AI_CONFIG.get('KEY_CYCLE_COOLDOWN_MINUTES', 20)) # No longer needed

        # self.gemini_keys = deque(GEMINI_API_KEYS) # Removed Gemini keys
        self.openrouter_key = OPENROUTER_API_KEY

        # self.gemini_unavailable_until = None # Removed Gemini state
        self.active_service = 'openrouter' if self.openrouter_key else 'disabled' # Default to OpenRouter if key exists

        if not self.openrouter_key:
            logging.error("No OpenRouter API key found in config/env. AI filtering disabled.")
            self.active_service = 'disabled'

        logging.info(f"AI Handler initialized. Primary Service: {self.active_service.upper()}. OpenRouter Key: {'Yes' if self.openrouter_key else 'No'}")

    def _get_llm_client(self, temperature=None): # Keep temperature parameter for potential use with OpenRouter models
        """Gets the appropriate Langchain LLM client based on current state."""
        now = datetime.now()

        # Simplified logic: only use OpenRouter if available
        if self.active_service == 'openrouter' and self.openrouter_key:
            try:
                logging.debug("Initializing OpenRouter client.")
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
                return None
        else:
            logging.error("No active AI service or keys available.")
            return None

    def _call_llm_with_cycling(self, system_prompt, user_prompt, max_tokens, temperature, json_mode=True, max_retries=2, initial_delay=5):
        """
        Handles the LLM call, retries. Now primarily uses OpenRouter.
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
                return None # Cannot proceed without a client

            current_service = self.active_service # Should always be 'openrouter' if active
            model_name = self.openrouter_model_name
            logging.debug(f"Attempt {retries + 1}/{max_retries + 1} using {current_service.upper()} model: {model_name}")

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            invoke_kwargs = {}

            # Set parameters for OpenRouter (using ChatOpenAI structure)
            if isinstance(llm_client, ChatOpenAI):
                # Temperature handled at init
                invoke_kwargs["max_tokens"] = max_tokens
                if json_mode:
                    invoke_kwargs["response_format"] = {"type": "json_object"}
            else:
                 # This case should ideally not happen if only OpenRouter is configured
                 logging.warning("LLM client is not ChatOpenAI, cannot set specific parameters like response_format.")
                 invoke_kwargs["temperature"] = temperature # Pass temp directly if not ChatOpenAI
                 invoke_kwargs["max_tokens"] = max_tokens


            try:
                # Use **invoke_kwargs
                response = llm_client.invoke(messages, **invoke_kwargs)
                response_content = response.content.strip()
                logging.debug(f"Raw response from {current_service.upper()}: {response_content}")
                return response_content # Success

            # Removed specific Gemini error handling
            except (OpenAIRateLimitError, OpenAIAPIError, OpenAPITimeoutError) as e:
                 # Handle OpenRouter specific errors
                 logging.warning(f"OpenRouter API Error (Attempt {retries + 1}): {e}")
                 last_error = e
                 # No fallback, just proceed to retry logic

            except OutputParserException as e:
                 logging.warning(f"Langchain Output Parser Error (Attempt {retries + 1}): {e}. Likely malformed response from LLM.")
                 last_error = e

            except Exception as e:
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
        Uses the configured AI model for a quick pre-filter based on title/snippet.
        Returns True if potentially relevant, False if definitely junk/unrelated.
        Defaults to True if the AI call fails, to avoid discarding good leads.
        """
        if self.active_service == 'disabled':
            logging.warning("AI service is disabled. Skipping pre-filtering, assuming relevant.")
            return True

        content_to_analyze = f"Title: {title}"
        if snippet: content_to_analyze += f"\nSnippet: {snippet[:300]}"

        # Updated prompt for Gemini/JSON
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
