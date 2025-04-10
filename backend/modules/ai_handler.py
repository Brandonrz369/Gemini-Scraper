# modules/ai_handler.py
import logging
import time
import json # Added for parsing AI response
from openai import OpenAI, RateLimitError, APIError, APITimeoutError

class AIHandler:
    def __init__(self, config):
        ai_config = config.get('AI_CONFIG', {})
        self.api_key = ai_config.get('API_KEY')
        self.base_url = ai_config.get('BASE_URL')
        self.model_name = ai_config.get('MODEL_NAME')

        if not all([self.api_key, self.base_url, self.model_name]):
            logging.error("AI configuration (API_KEY, BASE_URL, MODEL_NAME) is incomplete. AI filtering disabled.")
            self.client = None
        else:
            try:
                # Initialize OpenAI client configured for OpenRouter
                self.client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                )
                logging.info(f"AI Handler initialized for model: {self.model_name}")
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client for OpenRouter: {e}", exc_info=True)
                self.client = None

    def grade_lead(self, title, description, max_retries=2, initial_delay=5):
        """
        Uses the configured AI model via OpenRouter to grade a lead's potential profitability
        and identify junk.
        Returns a dictionary: {'is_junk': bool, 'profitability_score': int|None, 'reasoning': str}
        Returns None if the AI call fails definitively after retries.
        """
        if not self.client:
            logging.warning("AI client not initialized. Skipping lead grading.")
            # Default to not junk, no score if AI is disabled
            return {"is_junk": False, "profitability_score": None, "reasoning": "AI client not initialized"}

        # Limit description length to avoid excessive token usage
        description_snippet = description[:2000]

        system_prompt = """You are an expert lead evaluator for a web/graphic design agency specializing in website development, graphic design, branding, and Photoshop services. Your task is to analyze Craigslist posts to identify potential clients *seeking these specific services*.

Respond ONLY with a valid JSON object containing the following keys:
- "is_junk": boolean. Set to `true` if the post is spam, selling unrelated items/services (like art pieces, supplies, classes), offering jobs *at* other companies, or is *not* clearly a request *for* web design, graphic design, or Photoshop services. Set to `false` ONLY if the post appears to be a genuine request *seeking* the agency's services.
- "profitability_score": integer (1-10, higher means more profitable potential) or null (if is_junk is true). Base the score on factors like: clarity of the service request, mention of budget, direct relevance to the agency's core services (web design, graphic design, Photoshop), specificity of needs, and perceived professionalism of the poster. Posts just selling items, even related ones, should generally be junk or have a very low score.
- "reasoning": string (a brief explanation for the score and junk status, specifically mentioning *why* it is or isn't a relevant service request for the agency)."""

        user_prompt = f"""Please evaluate the following Craigslist post based *strictly* on whether it represents a potential client seeking web design, graphic design, or Photoshop services:

Title: {title}
Description: {description_snippet}

Provide your evaluation in the specified JSON format."""

        retries = 0
        delay = initial_delay
        last_error = "Unknown error" # Initialize last_error
        while retries <= max_retries:
            try:
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3, # Slightly higher temp for more nuanced reasoning
                    max_tokens=150, # Increased tokens for JSON output + reasoning
                    response_format={"type": "json_object"}, # Request JSON output if model supports it
                )

                response_content = completion.choices[0].message.content.strip()
                logging.debug(f"AI grading raw response for '{title}': {response_content}")

                try:
                    # Parse the JSON response
                    grade_data = json.loads(response_content)

                    # Validate required keys
                    if not all(k in grade_data for k in ["is_junk", "profitability_score", "reasoning"]):
                        logging.warning(f"AI grading response missing required keys for '{title}'. Response: {response_content}")
                        # Attempt to salvage if possible, otherwise treat as failure for this attempt
                        grade_data = {"is_junk": True, "profitability_score": None, "reasoning": "AI response format error (missing keys)"} # Default to junk on format error

                    # Validate types and score range
                    if not isinstance(grade_data.get("is_junk"), bool):
                         grade_data["is_junk"] = True # Default to junk if type is wrong
                         grade_data["reasoning"] += " | Invalid type for is_junk."
                    if grade_data["is_junk"]:
                        grade_data["profitability_score"] = None # Ensure score is null if junk
                    elif not (isinstance(grade_data.get("profitability_score"), int) and 1 <= grade_data["profitability_score"] <= 10):
                         logging.warning(f"AI grading returned invalid score for '{title}'. Score: {grade_data.get('profitability_score')}")
                         # Allow null score if AI returns it, even if not junk
                         if grade_data.get("profitability_score") is not None:
                             grade_data["profitability_score"] = None # Nullify invalid scores
                             grade_data["reasoning"] += " | Invalid profitability score (must be 1-10 or null)."
                    if not isinstance(grade_data.get("reasoning"), str):
                         grade_data["reasoning"] = str(grade_data.get("reasoning", "")) + " | Invalid type for reasoning."


                    logging.info(f"AI grading successful for '{title}'. Score: {grade_data.get('profitability_score')}, Junk: {grade_data.get('is_junk')}")
                    return grade_data

                except json.JSONDecodeError:
                    logging.warning(f"AI grading response was not valid JSON for '{title}'. Response: {response_content}")
                    # Treat as failure for this attempt, retry
                    last_error = f"Invalid JSON response from AI: {response_content}"
                    # Fall through to retry logic below

            except RateLimitError as e:
                last_error = f"AI API rate limit hit (attempt {retries + 1}/{max_retries + 1}). Retrying in {delay}s. Error: {e}"
                logging.warning(last_error)
            except APITimeoutError as e:
                 last_error = f"AI API timeout (attempt {retries + 1}/{max_retries + 1}). Retrying in {delay}s. Error: {e}"
                 logging.warning(last_error)
            except APIError as e:
                # Includes errors like invalid request, model errors etc.
                last_error = f"AI API error during grading for '{title}' (attempt {retries + 1}/{max_retries + 1}): {e}"
                logging.error(last_error, exc_info=False) # Log API errors as ERROR
                # Check if it's a potentially recoverable error before retrying
                if "invalid_request_error" in str(e).lower(): # e.g., prompt issues
                     logging.error("Potential prompt issue detected. Aborting retries for this lead.")
                     return None # Abort retries for likely unrecoverable API errors like bad prompts
            except Exception as e:
                last_error = f"Unexpected error during AI grading for '{title}' (attempt {retries + 1}/{max_retries + 1}): {e}"
                logging.error(last_error, exc_info=True)

            # If we are here, an error occurred or JSON parsing failed. Retry.
            retries += 1
            if retries <= max_retries:
                logging.info(f"Waiting {delay:.1f} seconds before retry {retries}/{max_retries}...")
                time.sleep(delay)
                delay *= 2 # Exponential backoff
            else:
                # If loop finishes, all retries failed
                logging.error(f"AI grading failed after {max_retries + 1} attempts for '{title}'. Last error: {last_error}")
                return None # Indicate failure after retries

        # This part should ideally not be reached if the loop logic is correct
        logging.error(f"AI grading loop finished unexpectedly for '{title}'.")
        return None

    def pre_filter_lead(self, title, snippet, max_retries=1, initial_delay=2):
        """
        Uses the configured AI model for a quick pre-filter based on title/snippet.
        Returns True if potentially relevant, False if definitely junk/unrelated.
        Defaults to True if the AI call fails, to avoid discarding good leads.
        """
        if not self.client:
            logging.warning("AI client not initialized. Skipping pre-filtering, assuming relevant.")
            return True # Default to potentially relevant if AI is disabled

        # Use snippet if available, otherwise just title
        content_to_analyze = f"Title: {title}"
        if snippet:
            # Limit snippet length for pre-filter efficiency
            content_to_analyze += f"\nSnippet: {snippet[:300]}"

        system_prompt = """You are a rapid lead pre-filter for a web/graphic design agency. Your task is to quickly determine if a Craigslist post *might* be relevant based ONLY on its title and snippet.

Focus: Identify if the post is *definitely* junk (spam, selling unrelated items like art/furniture/supplies, offering jobs at other companies, user research studies, seeking dating advice, etc.) or if it *could possibly* be someone seeking web design, graphic design, or Photoshop services. Err on the side of caution; if unsure, mark as potentially relevant.

Respond ONLY with a valid JSON object containing a single key:
- "is_potentially_relevant": boolean (true if it *might* be relevant, false if it's *definitely* junk/unrelated)"""

        user_prompt = f"""Quickly evaluate if the following post title/snippet could possibly be relevant to a web/graphic design agency seeking clients. Is it definitely junk/unrelated?

{content_to_analyze}

Provide your evaluation in the specified JSON format."""

        retries = 0
        delay = initial_delay
        last_error = "Unknown error"
        while retries <= max_retries:
            try:
                completion = self.client.chat.completions.create(
                    model=self.model_name, # Consider using a faster/cheaper model if available for pre-filtering
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1, # Low temperature for more deterministic filtering
                    max_tokens=50, # Smaller max tokens for faster response
                    response_format={"type": "json_object"},
                )

                response_content = completion.choices[0].message.content.strip()
                logging.debug(f"AI pre-filter raw response for '{title}': {response_content}")

                try:
                    # Parse the JSON response
                    filter_data = json.loads(response_content)

                    if "is_potentially_relevant" in filter_data and isinstance(filter_data["is_potentially_relevant"], bool):
                        logging.debug(f"AI pre-filter successful for '{title}'. Potentially Relevant: {filter_data['is_potentially_relevant']}")
                        return filter_data["is_potentially_relevant"]
                    else:
                        logging.warning(f"AI pre-filter response missing/invalid key for '{title}'. Response: {response_content}")
                        last_error = "Invalid JSON response format from pre-filter AI"
                        # Fall through to retry logic

                except json.JSONDecodeError:
                    logging.warning(f"AI pre-filter response was not valid JSON for '{title}'. Response: {response_content}")
                    last_error = f"Invalid JSON response from pre-filter AI: {response_content}"
                    # Fall through to retry logic

            except RateLimitError as e:
                last_error = f"AI API rate limit hit during pre-filter (attempt {retries + 1}/{max_retries + 1}). Retrying in {delay}s. Error: {e}"
                logging.warning(last_error)
            except APITimeoutError as e:
                 last_error = f"AI API timeout during pre-filter (attempt {retries + 1}/{max_retries + 1}). Retrying in {delay}s. Error: {e}"
                 logging.warning(last_error)
            except APIError as e:
                last_error = f"AI API error during pre-filter for '{title}' (attempt {retries + 1}/{max_retries + 1}): {e}"
                logging.error(last_error, exc_info=False)
                if "invalid_request_error" in str(e).lower():
                     logging.error("Potential pre-filter prompt issue detected. Aborting retries.")
                     return True # Default to relevant on unrecoverable error
            except Exception as e:
                last_error = f"Unexpected error during AI pre-filter for '{title}' (attempt {retries + 1}/{max_retries + 1}): {e}"
                logging.error(last_error, exc_info=True)

            # Retry logic
            retries += 1
            if retries <= max_retries:
                logging.info(f"Waiting {delay:.1f} seconds before pre-filter retry {retries}/{max_retries}...")
                time.sleep(delay)
                delay *= 2
            else:
                logging.error(f"AI pre-filter failed after {max_retries + 1} attempts for '{title}'. Last error: {last_error}")
                return True # Default to potentially relevant if pre-filter fails

        logging.error(f"AI pre-filter loop finished unexpectedly for '{title}'.")
        return True # Default to potentially relevant
