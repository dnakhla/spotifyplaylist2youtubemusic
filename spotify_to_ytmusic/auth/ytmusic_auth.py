import os
from ytmusicapi import YTMusic, setup_oauth

# Define the path for the OAuth credentials file.
# This file will store the authentication tokens after successful authorization.
YT_OAUTH_FILE = 'oauth.json'

def setup_ytmusic_oauth():
    """
    Initiates the YouTube Music OAuth setup process.

    This function uses ytmusicapi.setup_oauth to guide the user through
    the authentication flow. It will print a device code and verification URL
    to the console. The user needs to visit the URL, enter the code, and
    authorize the application.

    The resulting authentication credentials will be saved to the file
    specified by YT_OAUTH_FILE.
    """
    if os.path.exists(YT_OAUTH_FILE):
        print(f"OAuth credentials file '{YT_OAUTH_FILE}' already exists. "
              f"Setup is likely complete. Delete the file to re-run setup.")
        return

    print("Starting YouTube Music OAuth setup...")
    try:
        # This function handles the interactive OAuth setup process.
        # It will print instructions to the console for the user to follow.
        setup_oauth(filepath=YT_OAUTH_FILE)
        print(f"YouTube Music OAuth setup successful. Credentials saved to '{YT_OAUTH_FILE}'.")
    except Exception as e:
        print(f"An error occurred during YouTube Music OAuth setup: {e}")
        # Optionally, clean up if the file was partially created or invalid
        if os.path.exists(YT_OAUTH_FILE):
            try:
                os.remove(YT_OAUTH_FILE)
                print(f"Removed potentially incomplete OAuth file: '{YT_OAUTH_FILE}'.")
            except OSError as remove_err:
                print(f"Error removing OAuth file: {remove_err}")

def get_ytmusic_client():
    """
    Creates and returns an authenticated YouTube Music client using OAuth credentials.

    Checks if the OAuth credentials file (specified by YT_OAUTH_FILE) exists.
    If it exists, it initializes the YTMusic client with the credentials.
    If it doesn't exist, it indicates that the setup process needs to be run.

    Raises:
        FileNotFoundError: If the OAuth credentials file does not exist,
                           prompting the user to run the setup function.

    Returns:
        ytmusicapi.YTMusic: An authenticated YTMusic client instance.
    """
    if not os.path.exists(YT_OAUTH_FILE):
        raise FileNotFoundError(
            f"YouTube Music OAuth credentials file '{YT_OAUTH_FILE}' not found. "
            f"Please run the setup function (e.g., by calling setup_ytmusic_oauth()) "
            f"to authenticate first."
        )

    # Initialize the YTMusic client using the saved OAuth credentials.
    ytmusic_client = YTMusic(YT_OAUTH_FILE)
    return ytmusic_client
