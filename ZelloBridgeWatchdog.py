import json
import os
import time
import requests
import logging
from datetime import datetime

# These libraries are required to securely generate a JWT token.
# To use this script, you must install them by running:
# 'pip install PyJWT cryptography' in your terminal. 
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import jwt


# Configure the logging module to output to the console with a specific format
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Define the URL of the endpoint
url_endpoint = "http://127.0.0.1:8810"

def generate_jwt_token(issuer_path, private_key_path):
    """
    Generates a secure JWT token.
    
    This function reads a private key and an issuer ID from specified files,
    creates a JWT payload, and signs the token using the RS256 algorithm.
    
    Args:
        issuer_path (str): The file path to the issuer ID.
        private_key_path (str): The file path to the private key used for signing.

    Returns:
        str: A newly generated JWT token, or None if a required file is missing
             or if an error occurs during token creation.
    """
    # Verify that the required key and issuer files exist before proceeding.
    if not os.path.exists(private_key_path):
        logging.error(f"Private key file not found at '{private_key_path}'")
        return None
    if not os.path.exists(issuer_path):
        logging.error(f"Issuer file not found at '{issuer_path}'")
        return None

    # Safely read the content of the private key and issuer files.
    try:
        # Load the private key from a text file for use in signing.
        with open(private_key_path, "r") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read().encode(),
                password=None,
                backend=default_backend()
            )
        
        # Read the issuer ID, which is a simple string in a text file.
        with open(issuer_path, "r") as issuer_file:
            issuer_content = issuer_file.read().strip()
    except Exception as e:
        logging.error(f"Failed to read key or issuer file: {e}")
        return None
    
    # Define the JWT header and payload as per the required specification.
    header = {"typ": "JWT", "alg": "RS256"}
    payload = {
        "iss": issuer_content,
        "exp": round(time.time() + 120) #New token is valid for 2 minutes
    }
    
    # Sign the token using the private key and defined algorithm.
    try:
        token = jwt.encode(payload, private_key, algorithm="RS256", headers=header)
        logging.info("Successfully generated a new token.")
        return token
    except Exception as e:
        logging.error(f"An error occurred while generating the JWT: {e}")
        return None

def update_connector_tokens(file_path):
    """
    This is the main function that reads the configuration file, finds the
    relevant connectors, and updates their tokens.
    
    Args:
        file_path (str): The path to the JSON configuration file to process.
    """
    # Check if the configuration file exists before attempting to open it.
    if not os.path.exists(file_path):
        logging.error(f"The file '{file_path}' was not found.")
        return

    # Read the JSON configuration data from the file.
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error reading the file: {e}")
        return

    changes_made = False

    # Check for the expected JSON structure with a 'links' key.
    if isinstance(data, dict) and 'links' in data and isinstance(data['links'], list):
        # The base directory is used to locate the key and issuer files.
        base_dir = os.path.dirname(file_path)
        
        # Iterate through the links and their connectors to find the correct ones.
        for link in data['links']:
            if 'connectors' in link and isinstance(link['connectors'], list):
                for connector in link['connectors']:
                    # Look for connectors of type 'zello-channel-api' to update.
                    if connector.get('type') == 'zello-channel-api':
                        username = connector.get('username')
                        if not username:
                            logging.warning("Found 'zello-channel-api' connector without a 'username'. Skipping.")
                            continue

                        # Construct the file path for the private key based on the username.
                        private_key_file = f"{username}.pem"
                        private_key_path = os.path.join(base_dir, private_key_file)
                        
                        # Construct the file path for the issuer based on the username.
                        issuer_file_name = f"{username}.txt"
                        issuer_path = os.path.join(base_dir, issuer_file_name)
                        
                        # Call the token generation function.
                        new_token = generate_jwt_token(issuer_path, private_key_path)
                        
                        # If a token was successfully generated, update the connector data.
                        if new_token:
                            connector['token'] = new_token
                            logging.info(f"Successfully generated and assigned token for connector: {connector.get('name', 'N/A')}")
                            changes_made = True
                        else:
                            logging.error(f"Could not generate a token for connector: {connector.get('name', 'N/A')}")
    else:
        logging.error("The JSON structure is not as expected. Check for a top-level 'links' key.")
        return

    # If changes were made, save the modified data back to the file.
    if changes_made:
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            logging.info(f"Successfully updated tokens and saved the file: {file_path}")
        except Exception as e:
            logging.error(f"An error occurred while writing to the file: {e}")
            logging.error("Please check file permissions and try again.")
    else:
        logging.info("No tokens were generated. The file was not modified.")


def main():
    # Use a while loop to run the script indefinitely

    # Create a requests Session object for connection pooling.
    session = requests.Session()
    
    while True:
        try:
            # Send a GET request to the URL
            response = session.get(url_endpoint+'/status', timeout=5)

            # Check if the request was successful (status code 200)
            if response.status_code == 200:
                # The response is in JSON format, so we can parse it directly
                data = response.json()

                config_path = data.get("config_file")
 
                # --- Functionality to check for specific error code ---
                found_error = False

                # Safely iterate through the links in the response
                for link in data.get("links", []):
                    # Safely iterate through the connectors in each link
                    for connector in link.get("connectors", []):
                        # Check if the connector is of the specified type
                        if connector.get('type') == 'zello-channel-api':
                            # Access the nested 'last_error' dictionary and its 'code'
                            error_code = connector.get('last_error', {}).get('code')
                            logging.info(f"Connector '{connector.get('name', 'N/A')}' error code is {error_code}.")

                            # Check if the error code matches 3001 or 3002
                            if error_code in (3001, 3002):
                                found_error = True

                if found_error:
                    logging.info("Connection error found. Generating new tokens...")
                    update_connector_tokens(config_path)

                    logging.info("Restarting ZelloBridge")
                    try:
                        # Send a PUT request to the restart endpoint
                        restart_response = session.put(url_endpoint+'/restart', timeout=5)
                        logging.info(f"Restart request sent. Status code: {restart_response.status_code}")
                    except requests.exceptions.RequestException as e:
                        logging.error(f"Failed to send restart request: {e}")

                    # Wait for 1 minute so the Bridge has time to initialize
                    logging.info("Sleep for 1 minute\n")
                    time.sleep(60)                                

            else:
                # If the status code is not 200, print the status code and a message
                logging.error(f"Request failed with status code: {response.status_code}")
                logging.error(f"Response content: {response.text}")

        except requests.exceptions.RequestException as e:
            # This block handles any errors that might occur during the request,
            # such as a connection timeout or the server being down.
            logging.error(f"An error occurred: {e}")

        # Wait for 1 second before the next iteration
        time.sleep(1)    


# This is the entry point of the script, which calls the main function.
if __name__ == '__main__':
    main()

