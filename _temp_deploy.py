import sys
import os
import logging

# Add backend directory to path to allow imports
project_root = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(project_root, 'backend')
sys.path.insert(0, backend_dir)

# Configure basic logging for the deployment function's messages
log_file = os.path.join(backend_dir, 'run.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a', encoding='utf-8'), # Append to existing log
        logging.StreamHandler()
    ]
)

try:
    # Import only the deployment function
    from main import deploy_to_github
    logging.info("Attempting deployment via temporary script...")
    deploy_to_github()
    logging.info("Deployment function called successfully.")
except ImportError as e:
    logging.critical(f"Failed to import deploy_to_github from backend.main: {e}")
except Exception as e:
    logging.critical(f"An error occurred during deployment script execution: {e}")
