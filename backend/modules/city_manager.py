# modules/city_manager.py (Recreated)
import json
import logging
import os

class CityManager:
    def __init__(self, config, state_manager):
        self.config = config
        self.state_manager = state_manager
        self.backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.backend_dir, 'data')
        logging.info("CityManager initialized (Recreated Version).")

    def get_cities_by_population(self, list_size='small'):
        """
        Reads city data from the specified JSON file (small, medium, large) and returns it.
        Defaults to 'small'.
        Placeholder: Currently does not actually sort by population.
        """
        filename_map = {
            'small': 'cities_small.json',
            'medium': 'cities_medium.json',
            'large': 'cities_large.json'
        }
        # Default to small if invalid size is given
        filename = filename_map.get(list_size, 'cities_small.json')
        cities_file_path = os.path.join(self.data_dir, filename)

        logging.info(f"Loading city list: {filename}")

        cities = []
        try:
            if not os.path.exists(cities_file_path):
                 logging.error(f"Cities file not found at {cities_file_path}")
                 return []

            with open(cities_file_path, 'r', encoding='utf-8') as f:
                cities = json.load(f)

            # Basic validation
            if not isinstance(cities, list):
                logging.error(f"{self.cities_file_path} does not contain a valid JSON list.")
                return []

            valid_cities = []
            for city in cities:
                if isinstance(city, dict) and 'code' in city and 'name' in city:
                    valid_cities.append(city)
                else:
                    logging.warning(f"Skipping invalid city entry in {self.cities_file_path}: {city}")

            # Placeholder for sorting logic if population data exists in the file
            # e.g., valid_cities.sort(key=lambda x: x.get('population', 0), reverse=True)
            logging.info(f"Loaded {len(valid_cities)} valid cities from {cities_file_path}.")
            return valid_cities

        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {cities_file_path}: {e}", exc_info=True)
            return []
        except Exception as e:
            logging.error(f"Error reading or processing cities file {cities_file_path}: {e}", exc_info=True)
            return []
