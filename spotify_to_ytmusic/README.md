# Spotify to YouTube Music Playlist Transfer

A simple GUI application built with Python and Tkinter to transfer your playlists and saved tracks from Spotify to YouTube Music.

## Features

*   **Spotify Authentication:** Securely connects to your Spotify account using OAuth 2.0.
*   **YouTube Music Authentication:** Connects to your YouTube Music account using `ytmusicapi` (requires initial OAuth setup via device code).
*   **Fetch Spotify Playlists:** Retrieves all your public and private playlists from Spotify.
*   **Playlist Transfer:** Creates corresponding playlists in YouTube Music and attempts to find and add matching tracks.
*   **GUI Interface:** Provides a basic graphical interface for managing the login and transfer process.
*   **Logging:** Displays progress and errors in the GUI's log area.

## Setup

Follow these steps to set up and run the application:

**1. Prerequisites:**
    *   Python 3.9 or higher is recommended.

**2. Clone the Repository:**
    ```bash
    git clone <repository-url> # Replace <repository-url> with the actual URL
    cd spotify-to-ytmusic-transfer # Or your repository directory name
    ```

**3. Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate the virtual environment
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

**4. Install Dependencies:**
    Make sure you are in the project's root directory (`spotify_to_ytmusic/`) where `requirements.txt` is located.
    ```bash
    pip install -r requirements.txt
    ```

**5. Spotify Setup:**
    *   Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
    *   Log in with your Spotify account.
    *   Click "Create App" (or similar).
    *   Give your application a name (e.g., `PlaylistTransferApp`) and description.
    *   Agree to the terms.
    *   Once created, you will see your **Client ID** and you can reveal your **Client Secret**. **Copy these somewhere safe.**
    *   Go to the app's "Settings".
    *   Under "Redirect URIs", add the URI you will use. For local use, `http://localhost:8888/callback` is common. Make sure this matches the one you set in the environment variable later. Click "Save".

**6. Environment Variables:**
    This application requires Spotify API credentials to be set as environment variables. You need to set the following:
    *   `SPOTIPY_CLIENT_ID`: Your Spotify application's Client ID (from step 5).
    *   `SPOTIPY_CLIENT_SECRET`: Your Spotify application's Client Secret (from step 5).
    *   `SPOTIPY_REDIRECT_URI`: The Redirect URI you added in the Spotify Developer Dashboard settings (e.g., `http://localhost:8888/callback`).

    *How to set environment variables depends on your operating system:*
        *   **Windows:** You can set them temporarily in Command Prompt (`set VARNAME=value`) or PowerShell (`$env:VARNAME="value"`) for the current session, or permanently via System Properties.
        *   **macOS/Linux:** You can set them temporarily in your terminal (`export VARNAME=value`) for the current session, or permanently by adding the `export` commands to your shell's profile file (like `.bashrc`, `.zshrc`, or `.profile`).

## Running the Application

1.  Ensure your virtual environment is activated (if you created one).
2.  Make sure you have set the required Spotify environment variables.
3.  Navigate to the project's root directory (`spotify_to_ytmusic/`) in your terminal.
4.  Run the main script:
    ```bash
    python main.py
    ```
5.  The GUI window will appear. Follow the steps in the UI:
    *   **Click "1. Login to Spotify"**: This will use your environment variables. If it's the first time or your token expired, Spotify might open a browser window asking you to authorize the application. After authorization, you'll be redirected to your specified `SPOTIPY_REDIRECT_URI` (the page might show an error, but the authentication token is captured).
    *   **Click "2. Login/Setup YouTube Music"**:
        *   **First time:** If the `oauth.json` file doesn't exist, the application will prompt you (in the *terminal* where you ran `python main.py`) to visit a URL (like `google.com/device`) and enter a code. Follow those instructions to authorize access for YouTube Music.
        *   **Subsequent times:** If `oauth.json` exists, it will attempt to log in using the saved credentials.
    *   **Click "3. Transfer Playlists"**: Once both Spotify and YouTube Music are logged in, this button becomes active. Clicking it starts the process:
        *   Fetching playlists from Spotify.
        *   (Saving data locally to `spotify_playlists.json`).
        *   Creating new playlists on YouTube Music.
        *   Searching for each track on YouTube Music and adding found matches to the corresponding new playlist.
        *   Progress and any errors will be displayed in the log area of the GUI.

## How it Works

1.  **Authentication:** Uses `spotipy` for Spotify OAuth and `ytmusicapi` for YouTube Music OAuth (device flow).
2.  **Fetch Data:** Retrieves the user's playlists and track details (name, artist, album) from Spotify using the `spotipy` client.
3.  **Save Data (Intermediate):** Saves the fetched Spotify data into a local `spotify_playlists.json` file. This acts as a cache and allows resuming or retrying the YouTube Music transfer part without re-fetching from Spotify.
4.  **Create YT Playlists:** Iterates through the loaded Spotify playlists and creates corresponding new, empty playlists on YouTube Music using the `ytmusicapi` client.
5.  **Search & Add Tracks:** For each track in a Spotify playlist, it constructs a search query (usually "track name artist name") and searches YouTube Music using `ytmusicapi`.
    *   It prioritizes results marked as 'songs'.
    *   If no 'song' match is found, it falls back to searching for 'videos'.
    *   The `videoId` of the best match found is collected.
6.  **Populate YT Playlists:** Adds the collected `videoId`s to the previously created YouTube Music playlist in batches.

## Limitations

*   **Track Matching:** Finding the exact same track on YouTube Music can be unreliable. The search relies on matching track/artist names. Remixes, covers, live versions, region-restricted tracks, or slightly different metadata can lead to incorrect matches or tracks not being found.
*   **Unofficial API:** `ytmusicapi` interacts with internal YouTube Music APIs that are not officially documented or supported by Google. Changes by YouTube Music could break the functionality of this tool without warning.
*   **Rate Limiting:** Both Spotify and YouTube Music have API rate limits. The application includes small delays between some operations (searching tracks, creating playlists) to mitigate this, but heavy usage might still encounter temporary blocks.
*   **Error Handling:** While basic error handling is included, unexpected API responses or edge cases might cause parts of the transfer to fail. Check the logs in the GUI for details.

## Disclaimer

This application uses unofficial APIs (primarily for YouTube Music). It is provided "as is" without warranty of any kind. The developers are not responsible for any issues that arise from its use, including potential problems with your Spotify or YouTube Music accounts (though issues are unlikely if used reasonably). Use at your own risk. Functionality may cease if Spotify or YouTube Music change their APIs or authentication methods.
