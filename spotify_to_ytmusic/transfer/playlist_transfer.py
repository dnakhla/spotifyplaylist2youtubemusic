import spotipy
import logging
import json
import os
import time
import ytmusicapi

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the default filename for storing fetched Spotify playlist data
SPOTIFY_DATA_FILE = 'spotify_playlists.json'

def fetch_spotify_playlists(sp: spotipy.Spotify):
    """
    Fetches all current user's playlists and their tracks from Spotify.

    Handles pagination for both playlists and tracks within each playlist.
    Extracts playlist name, track name, first artist name, and album name.

    Args:
        sp: An authenticated spotipy.Spotify client instance.

    Returns:
        list: A list of dictionaries, where each dictionary represents a playlist
              and contains 'name' (playlist name) and 'tracks' (a list of track
              dictionaries with 'name', 'artist', and 'album').
              Returns an empty list if no playlists are found or in case of an error.
    """
    all_playlists_data = []
    playlists_offset = 0
    playlists_limit = 50  # Max limit for playlists is 50

    logging.info("Starting to fetch Spotify playlists...")

    try:
        while True:
            # Fetch a batch of playlists
            logging.info(f"Fetching playlists batch: offset={playlists_offset}, limit={playlists_limit}")
            playlists_batch = sp.current_user_playlists(limit=playlists_limit, offset=playlists_offset)

            if not playlists_batch or not playlists_batch.get('items'):
                logging.warning("No playlists found or empty batch received.")
                break  # Exit if no items are returned

            for playlist in playlists_batch['items']:
                playlist_name = playlist.get('name', 'Unknown Playlist')
                playlist_id = playlist.get('id')

                if not playlist_id:
                    logging.warning(f"Skipping playlist '{playlist_name}' due to missing ID.")
                    continue

                logging.info(f"Fetching tracks for playlist: '{playlist_name}' (ID: {playlist_id})")
                tracks_data = []
                tracks_offset = 0
                tracks_limit = 100 # Max limit for tracks is 100

                while True:
                    # Fetch a batch of tracks for the current playlist
                    # Request only necessary fields to optimize the API call
                    logging.debug(f"Fetching tracks batch for '{playlist_name}': offset={tracks_offset}, limit={tracks_limit}")
                    try:
                        tracks_batch = sp.playlist_items(
                            playlist_id,
                            limit=tracks_limit,
                            offset=tracks_offset,
                            fields='items(track(name, id, artists(name), album(name))),next', # Added 'next' to fields
                            additional_types=['track']
                        )
                    except spotipy.exceptions.SpotifyException as e:
                         logging.error(f"Error fetching tracks for playlist '{playlist_name}' (ID: {playlist_id}): {e}")
                         # Decide whether to skip the playlist or stop entirely
                         # For now, we'll skip this playlist and continue with others
                         tracks_data = [] # Clear potentially partial data
                         break # Break inner loop for this playlist


                    if not tracks_batch or not tracks_batch.get('items'):
                        logging.debug(f"No more tracks found for playlist '{playlist_name}'.")
                        break # Exit if no track items are returned in the batch

                    for item in tracks_batch['items']:
                        track_info = item.get('track')

                        # Skip if item is not a track or track info is missing
                        if not track_info:
                            logging.warning(f"Skipping item in '{playlist_name}' - missing track data.")
                            continue

                        track_name = track_info.get('name', 'Unknown Track')
                        album_name = track_info.get('album', {}).get('name', 'Unknown Album')

                        # Get the first artist's name, handle missing artists list
                        artists = track_info.get('artists')
                        artist_name = artists[0].get('name', 'Unknown Artist') if artists else 'Unknown Artist'

                        tracks_data.append({
                            'name': track_name,
                            'artist': artist_name,
                            'album': album_name
                        })
                        logging.debug(f"  Added track: {track_name} - {artist_name} - {album_name}")

                    # Check if there are more tracks to fetch for the current playlist
                    if tracks_batch.get('next') is None:
                        logging.debug(f"No more pages of tracks for playlist '{playlist_name}'.")
                        break  # Exit the inner loop if no more pages
                    else:
                        tracks_offset += tracks_limit # Increment offset for the next batch of tracks

                # Add the playlist and its tracks to the main list
                if tracks_data: # Only add playlist if it has tracks fetched successfully
                    all_playlists_data.append({
                        'name': playlist_name,
                        'id': playlist_id, # Also storing id for potential future use
                        'tracks': tracks_data
                    })
                    logging.info(f"Finished fetching {len(tracks_data)} tracks for playlist '{playlist_name}'.")
                else:
                    logging.info(f"No tracks fetched or added for playlist '{playlist_name}'.")


            # Check if there are more playlists to fetch
            if playlists_batch.get('next') is None:
                logging.info("No more pages of playlists.")
                break # Exit the outer loop if no more pages
            else:
                playlists_offset += playlists_limit # Increment offset for the next batch of playlists

    except spotipy.exceptions.SpotifyException as e:
        logging.error(f"A Spotify API error occurred during playlist fetching: {e}")
        # Depending on the error, you might want to return partial data or raise the exception
        # For now, return whatever was collected before the error
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        # Handle other potential errors

    logging.info(f"Finished fetching all playlists. Total playlists processed: {len(all_playlists_data)}")
    return all_playlists_data


def save_playlists_to_json(playlists_data: list, filename: str = SPOTIFY_DATA_FILE):
    """
    Saves the fetched Spotify playlist data to a JSON file.

    Args:
        playlists_data: The list of playlist dictionaries to save.
        filename: The name of the file to save the data to.
                  Defaults to SPOTIFY_DATA_FILE.
    """
    logging.info(f"Attempting to save playlist data to {filename}...")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(playlists_data, f, ensure_ascii=False, indent=4)
        logging.info(f"Successfully saved {len(playlists_data)} playlists to {filename}")
    except IOError as e:
        logging.error(f"Error writing to file {filename}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while saving to JSON: {e}")


def load_playlists_from_json(filename: str = SPOTIFY_DATA_FILE) -> list:
    """
    Loads Spotify playlist data from a JSON file.

    Args:
        filename: The name of the file to load the data from.
                  Defaults to SPOTIFY_DATA_FILE.

    Returns:
        A list of playlist dictionaries loaded from the file.
        Returns an empty list if the file doesn't exist or if an error occurs during loading.
    """
    logging.info(f"Attempting to load playlist data from {filename}...")
    if not os.path.exists(filename):
        logging.warning(f"File {filename} not found. Returning empty list.")
        return []

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            playlists_data = json.load(f)
        logging.info(f"Successfully loaded {len(playlists_data)} playlists from {filename}")
        return playlists_data
    except IOError as e:
        logging.error(f"Error reading file {filename}: {e}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from file {filename}: {e}")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading from JSON: {e}")
        return []


def transfer_playlists_to_ytmusic(yt: ytmusicapi.YTMusic, spotify_data_file: str = SPOTIFY_DATA_FILE) -> bool:
    """
    Transfers playlists and tracks from a loaded Spotify data structure to YouTube Music.

    Loads playlist data from the specified JSON file, creates corresponding playlists
    on YouTube Music, searches for each track, and adds found tracks to the new playlists.

    Args:
        yt: An authenticated ytmusicapi.YTMusic client instance.
        spotify_data_file: Path to the JSON file containing Spotify playlist data
                           (created by save_playlists_to_json). Defaults to SPOTIFY_DATA_FILE.

    Returns:
        True if the transfer process started (data was loaded), False otherwise.
    """
    logging.info(f"Starting playlist transfer to YouTube Music from file: {spotify_data_file}")

    # 1. Load Spotify data
    spotify_playlists = load_playlists_from_json(filename=spotify_data_file)
    if not spotify_playlists:
        logging.error("No Spotify playlist data loaded. Aborting transfer.")
        return False # Indicate that the process didn't start due to missing data

    logging.info(f"Loaded {len(spotify_playlists)} playlists from Spotify data file.")

    # 2. Iterate through each Spotify playlist
    for playlist in spotify_playlists:
        playlist_name = playlist.get('name', 'Unnamed Spotify Playlist')
        spotify_playlist_id = playlist.get('id', 'N/A') # Get Spotify ID for logging
        logging.info(f"Processing Spotify playlist: '{playlist_name}' (ID: {spotify_playlist_id})")

        yt_playlist_id = None # Initialize YT playlist ID for this iteration

        # 3. Create the corresponding playlist on YouTube Music
        try:
            logging.info(f"Creating YouTube Music playlist: '{playlist_name}'")
            # Create playlist with a description indicating its origin
            yt_playlist_id = yt.create_playlist(
                title=playlist_name,
                description=f"Migrated from Spotify playlist: {playlist_name} (ID: {spotify_playlist_id})"
            )
            logging.info(f"Successfully created YouTube Music playlist '{playlist_name}' with ID: {yt_playlist_id}")
            time.sleep(1) # Short delay after creating a playlist

        except Exception as e:
            # This might happen if the playlist already exists or due to API errors
            logging.error(f"Failed to create YouTube Music playlist '{playlist_name}'. Error: {e}")
            # Decide whether to try finding an existing playlist or skip
            # For simplicity, we'll skip this playlist for now if creation fails
            logging.warning(f"Skipping playlist '{playlist_name}' due to creation error.")
            time.sleep(2) # Wait a bit longer after an error
            continue # Move to the next Spotify playlist

        # 4. Find and collect track video IDs on YouTube Music
        video_ids_to_add = []
        tracks = playlist.get('tracks', [])
        logging.info(f"Searching for {len(tracks)} tracks from '{playlist_name}' on YouTube Music...")

        for i, track in enumerate(tracks):
            track_name = track.get('name')
            artist_name = track.get('artist')
            # album_name = track.get('album') # Keep album name for potential future use

            if not track_name or not artist_name:
                logging.warning(f"Skipping track {i+1} in '{playlist_name}' due to missing name or artist.")
                continue

            # Construct search query - simple name + artist is usually effective
            query = f"{track_name} {artist_name}"
            logging.debug(f"Searching YT Music for: '{query}'")

            try:
                # Search for the track primarily in 'songs'
                search_results = yt.search(query, filter='songs', limit=5) # Limit results

                found_video_id = None
                if search_results:
                    # Check the first few results for a likely match
                    for result in search_results:
                        if result.get('videoId') and result.get('resultType') == 'song':
                            found_video_id = result['videoId']
                            logging.info(f"  Found song match for '{query}': Video ID {found_video_id}")
                            break # Use the first song result

                # Fallback: If no song found, try searching videos
                if not found_video_id:
                    logging.warning(f"  No direct song match for '{query}'. Trying video search...")
                    time.sleep(0.2) # Small delay before fallback search
                    search_results_videos = yt.search(query, filter='videos', limit=5)
                    if search_results_videos:
                         for result in search_results_videos:
                            # Prioritize official music videos if possible, otherwise take first video
                            # This logic can be refined based on title matching etc.
                            if result.get('videoId') and result.get('resultType') == 'video':
                                found_video_id = result['videoId']
                                logging.info(f"  Found video match for '{query}': Video ID {found_video_id}")
                                break # Use the first video result

                if found_video_id:
                    if found_video_id not in video_ids_to_add: # Avoid duplicates within the same playlist add batch
                         video_ids_to_add.append(found_video_id)
                    else:
                         logging.debug(f"  Video ID {found_video_id} already queued for addition.")
                else:
                    logging.warning(f"  Could not find any match for track: '{query}' on YouTube Music.")

            except Exception as e:
                logging.error(f"Error searching for track '{query}': {e}")
                # Continue to the next track even if one search fails

            # Add a delay between track searches to avoid rate-limiting
            time.sleep(0.6) # Increased sleep slightly based on experience

        # 5. Add found tracks to the YouTube Music playlist
        if video_ids_to_add:
            logging.info(f"Adding {len(video_ids_to_add)} found tracks to YT Music playlist '{playlist_name}' (ID: {yt_playlist_id})...")
            try:
                # YTMusicAPI can sometimes fail if adding too many at once, though it handles batches.
                # Consider chunking video_ids_to_add if adding hundreds/thousands fails.
                status = yt.add_playlist_items(yt_playlist_id, video_ids_to_add)
                logging.info(f"API response for adding tracks to '{playlist_name}': {status}")
                if isinstance(status, dict) and 'status' in status and status['status'] == 'STATUS_SUCCEEDED':
                     logging.info(f"Successfully added tracks to playlist '{playlist_name}'.")
                else:
                     logging.warning(f"Potential issue adding tracks to '{playlist_name}'. Response: {status}")

            except Exception as e:
                logging.error(f"Failed to add tracks to YT Music playlist '{playlist_name}' (ID: {yt_playlist_id}). Error: {e}")
        else:
            logging.info(f"No tracks were found or matched to add to YT Music playlist '{playlist_name}'.")

        # 6. Log completion for the current playlist and delay before the next one
        logging.info(f"Finished processing Spotify playlist: '{playlist_name}'")
        logging.info("-" * 30) # Separator for clarity
        time.sleep(2) # Wait before processing the next playlist

    logging.info("Completed transfer process for all playlists.")
    return True # Indicate the process started and ran
