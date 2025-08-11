# zellobridgewatchdog
Zello Bridge Watchdog

This script monitors the status of the Zello Bridge service and generates new connection token(s) when the Zello Bridge disconnects, then it forces it to reconnect with the new token(s).

# Functionality Explained

The script operates in an infinite loop, performing the following key tasks:

**Endpoint Polling**: It continuously sends GET requests to a local endpoint http://127.0.0.1:8810/status to retrieve the current status of the Zello Bridge.

**Error Detection**: It parses the JSON response from the status endpoint. The script iterates through the connectors and looks for ones of type 'zello-channel-api'. If a connector of this type has a last_error code of 3001 or 3002, it flags a connection error.

**Token Generation**: If a connection error is found, the script calls the update_connector_tokens function. This function reads a specified JSON configuration file, identifies the relevant connectors, and generates a new JWT token for them. This token is created using a private key and an issuer ID, which are expected to be in separate files named {username}.pem and {username}.txt.

**Bridge Restart**: After generating and saving the new token to the configuration file, the script sends a PUT request to http://127.0.0.1:8810/restart to restart the Zello Bridge application, allowing it to use the new token and re-establish a connection.

**Logging and Timeouts**: The script includes extensive logging to track its actions and any errors. It uses a 1-second delay between status checks and a 1-minute delay after a restart to give the bridge time to initialize.


# Installation and Setup

**Download the Script**: Download the ZelloBridgeWatchdog.py file and place it in a location where you can easily run it.

**Install Required Libraries**: Open a command prompt or terminal and run the following command to install the necessary Python libraries:

    pip install PyJWT cryptography

**Back up Your Configuration**: Before you proceed, make a copy of your ZelloBridge.json file. This is a critical step because the script will modify this file to insert new tokens.

**Prepare the ZelloBridge.json File**: Open ZelloBridge.json and delete the existing developer token(s). This ensures the script will generate new ones from scratch. As you do this, take note of the username for each connector you want the script to manage. You will need these names in the next steps.

**Place Your Private Key**: Copy the file containing your private key into the Zello Bridge installation folder (e.g., C:\Program Files\Zello Bridge). Rename this file to match the username you noted in the previous step, using a .pem extension. For example, if your username is bridgeuser, the file should be named bridgeuser.pem.

**Place Your Issuer Code**: Copy the file containing your issuer code into the same Zello Bridge installation folder. Rename this file to match the username, using a .txt extension. For example, bridgeuser.txt.

**Run the Watchdog Script**: Open a command prompt or terminal, navigate to the folder where you saved the script, and run it with the following command:

    python ZelloBridgeWatchdog.py

**Finalize and Monito**r: Go to your Zello Bridge web interface, click the Restart button, and then switch back to the script's console. You should see messages indicating that it is detecting the Zello Bridge service, generating a new token, and restarting the service. Monitor the console for any errors to confirm everything is working correctly.
