import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Define the scopes required for accessing Spotify playlist data.
# 'playlist-read-private': Allows reading user's private playlists.
# 'playlist-read-collaborative': Allows reading user's collaborative playlists.
SCOPES = "playlist-read-private playlist-read-collaborative"

def get_spotify_client():
    """
    Authenticates with Spotify using credentials from environment variables
    and returns an authenticated Spotipy client instance.

    Requires the following environment variables to be set:
    - SPOTIPY_CLIENT_ID: Your Spotify application's client ID.
    - SPOTIPY_CLIENT_SECRET: Your Spotify application's client secret.
    - SPOTIPY_REDIRECT_URI: The redirect URI configured in your Spotify application.
                           This URI must be accessible by the machine running this script
                           to handle the OAuth callback (e.g., http://localhost:8888/callback).

    Raises:
        ValueError: If any of the required environment variables are not set.

    Returns:
        spotipy.Spotify: An authenticated Spotipy client instance.
    """
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        raise ValueError(
            "Missing Spotify credentials. Please set SPOTIPY_CLIENT_ID, "
            "SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI environment variables."
        )

    # The SpotifyOAuth object handles the OAuth 2.0 flow.
    # It will automatically prompt the user for authorization if needed
    # and cache the access token for future use.
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPES,
        # Default cache path is .cache-<username>, which is fine for most cases.
        # cache_path="path/to/your/cache/file" # Optional: specify a custom cache path
    )

    # The spotipy.Spotify client uses the auth_manager to handle authentication.
    spotify_client = spotipy.Spotify(auth_manager=auth_manager)

    return spotify_client
