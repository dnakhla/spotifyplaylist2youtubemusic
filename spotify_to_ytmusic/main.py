import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
import threading
import queue
import os # Needed for checking YT OAuth file

# Import project functions
try:
    from auth.spotify_auth import get_spotify_client
    from auth.ytmusic_auth import setup_ytmusic_oauth, get_ytmusic_client, YT_OAUTH_FILE
    from transfer.playlist_transfer import (
        fetch_spotify_playlists,
        save_playlists_to_json,
        transfer_playlists_to_ytmusic,
        SPOTIFY_DATA_FILE,
    )
except ImportError as e:
    # Handle cases where the script might be run directly without the package structure
    # This is a basic fallback, ideally run as a module
    print(f"Error importing modules: {e}. Make sure you run this script from the project root "
          f"or install the package.")
    # Attempt relative imports if run as script within the directory (less ideal)
    try:
        from .auth.spotify_auth import get_spotify_client
        from .auth.ytmusic_auth import setup_ytmusic_oauth, get_ytmusic_client, YT_OAUTH_FILE
        from .transfer.playlist_transfer import (
            fetch_spotify_playlists,
            save_playlists_to_json,
            transfer_playlists_to_ytmusic,
            SPOTIFY_DATA_FILE,
        )
    except ImportError:
        messagebox.showerror("Import Error", "Could not import required modules. Ensure the script is run correctly.")
        exit()


# --- Logging Setup ---

# Queue for thread-safe logging updates to the GUI
log_queue = queue.Queue()

class TextHandler(logging.Handler):
    """A logging handler that puts messages into a queue for the Tkinter UI."""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        log_entry = self.format(record)
        self.queue.put(log_entry)

# --- Main Application Class ---

class PlaylistTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spotify to YouTube Music Transfer")
        self.root.geometry("700x550") # Adjusted size

        # Client instances
        self.sp_client = None
        self.yt_client = None

        # Main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # --- UI Elements ---
        # Instructions Label
        instructions = (
            "Instructions:\n"
            "1. Ensure Spotify environment variables are set:\n"
            "   SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI (e.g., http://localhost:8888/callback)\n"
            "2. Click 'Login to Spotify'. You might be prompted to authorize in your browser.\n"
            "3. Click 'Login/Setup YouTube Music'. Follow console instructions for the first-time setup.\n"
            "4. Once both are logged in, click 'Transfer Playlists'."
        )
        self.info_label = ttk.Label(self.main_frame, text=instructions, justify=tk.LEFT)
        self.info_label.pack(pady=(0, 10), anchor='w')

        # Buttons Frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=5)

        self.spotify_button = ttk.Button(self.button_frame, text="1. Login to Spotify", command=self._spotify_login)
        self.spotify_button.pack(side=tk.LEFT, padx=5)

        self.ytmusic_button = ttk.Button(self.button_frame, text="2. Login/Setup YouTube Music", command=self._ytmusic_login, state=tk.DISABLED)
        self.ytmusic_button.pack(side=tk.LEFT, padx=5)

        self.transfer_button = ttk.Button(self.button_frame, text="3. Transfer Playlists", command=self._start_transfer, state=tk.DISABLED)
        self.transfer_button.pack(side=tk.LEFT, padx=5)

        # Log Area
        self.log_area = scrolledtext.ScrolledText(self.main_frame, height=20, state=tk.DISABLED, wrap=tk.WORD)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # --- Logging Configuration ---
        self.log_handler = TextHandler(log_queue)
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.log_handler.setFormatter(log_format)

        # Configure root logger and project-specific loggers
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO) # Set overall level
        root_logger.addHandler(self.log_handler)

        # Ensure project loggers also use this handler if they exist
        logging.getLogger('auth').addHandler(self.log_handler)
        logging.getLogger('transfer').addHandler(self.log_handler)
        # Set levels for project loggers if needed (optional)
        # logging.getLogger('auth').setLevel(logging.DEBUG)
        # logging.getLogger('transfer').setLevel(logging.INFO)


        # Start processing the log queue
        self._process_log_queue()

        self._log("Application started. Please follow the steps.")

    def _log(self, message, level=logging.INFO):
        """Logs a message using the logging framework."""
        # Use the root logger or a specific logger
        logger = logging.getLogger(__name__) # Or logging.getLogger()
        logger.log(level, message)


    def _update_log_area(self, message):
        """Appends a message to the ScrolledText widget in a thread-safe way."""
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + '\n')
        self.log_area.configure(state=tk.DISABLED)
        self.log_area.see(tk.END) # Scroll to the end

    def _process_log_queue(self):
        """Processes messages from the log queue and updates the GUI."""
        try:
            while True:
                message = log_queue.get_nowait()
                self._update_log_area(message)
        except queue.Empty:
            pass # No messages in the queue
        # Schedule the next check
        self.root.after(100, self._process_log_queue)

    def _run_in_thread(self, target_func, callback=None, args=()):
        """Runs a target function in a separate thread."""
        thread = threading.Thread(target=self._thread_wrapper, args=(target_func, callback, args), daemon=True)
        thread.start()
        return thread # Might be useful for tracking later

    def _thread_wrapper(self, target_func, callback, args):
        """Wrapper to execute the target function and handle result/error."""
        try:
            result = target_func(*args)
            if callback:
                # Schedule callback in the main thread
                self.root.after(0, callback, True, result) # Success = True
        except Exception as e:
            logging.error(f"Error in thread ({target_func.__name__}): {e}", exc_info=False) # Log basic error
            # Log full traceback to console/main log file if needed
            # logging.exception(f"Full traceback for {target_func.__name__}")
            if callback:
                # Schedule callback in the main thread with error info
                self.root.after(0, callback, False, e) # Success = False

    # --- Button Actions ---

    def _spotify_login(self):
        self._log("Attempting Spotify login...")
        self.spotify_button.config(state=tk.DISABLED) # Disable while logging in
        self._run_in_thread(get_spotify_client, self._spotify_login_callback)

    def _spotify_login_callback(self, success, result):
        self.spotify_button.config(state=tk.NORMAL) # Re-enable button
        if success:
            self.sp_client = result
            self._log("Spotify login successful!")
            self.ytmusic_button.config(state=tk.NORMAL) # Enable next step
            # Maybe disable Spotify button after success? Optional.
            # self.spotify_button.config(state=tk.DISABLED)
        else:
            self._log(f"Spotify login failed: {result}", level=logging.ERROR)
            messagebox.showerror("Spotify Login Error", f"Could not log in to Spotify.\nError: {result}\n\nPlease ensure environment variables are set correctly and try again.")
            self.sp_client = None
            self.ytmusic_button.config(state=tk.DISABLED)
            self.transfer_button.config(state=tk.DISABLED)

    def _ytmusic_login(self):
        self._log("Attempting YouTube Music login/setup...")
        self.ytmusic_button.config(state=tk.DISABLED) # Disable while processing

        # Check if setup file exists
        if not os.path.exists(YT_OAUTH_FILE):
            self._log(f"'{YT_OAUTH_FILE}' not found. Starting first-time setup.")
            self._log("Please follow the instructions printed in the CONSOLE/TERMINAL "
                      "where you ran this application to authorize access.", level=logging.WARNING)
            # Run setup in thread because it blocks waiting for console input
            self._run_in_thread(setup_ytmusic_oauth, self._ytmusic_setup_callback)
        else:
            self._log(f"Found '{YT_OAUTH_FILE}'. Attempting to get client.")
            # File exists, try getting the client directly
            self._run_in_thread(get_ytmusic_client, self._ytmusic_login_callback)

    def _ytmusic_setup_callback(self, success, result):
        if success:
            self._log("YouTube Music setup process completed.")
            # Now try to get the client again
            self._run_in_thread(get_ytmusic_client, self._ytmusic_login_callback)
        else:
            self._log(f"YouTube Music setup failed: {result}", level=logging.ERROR)
            messagebox.showerror("YouTube Music Setup Error", f"Setup failed.\nError: {result}\nPlease check the console output and try again.")
            self.ytmusic_button.config(state=tk.NORMAL) # Re-enable to allow retry
            self.yt_client = None
            self.transfer_button.config(state=tk.DISABLED)

    def _ytmusic_login_callback(self, success, result):
        self.ytmusic_button.config(state=tk.NORMAL) # Re-enable button
        if success:
            self.yt_client = result
            self._log("YouTube Music login successful!")
            if self.sp_client: # Only enable transfer if Spotify is also ready
                self.transfer_button.config(state=tk.NORMAL)
            # Maybe disable YT button after success? Optional.
            # self.ytmusic_button.config(state=tk.DISABLED)
        else:
            self._log(f"YouTube Music login failed: {result}", level=logging.ERROR)
            # Specific check for FileNotFoundError after setup attempt
            if isinstance(result, FileNotFoundError):
                 messagebox.showerror("YouTube Music Login Error", f"Login failed.\nError: {result}\n\nDid the setup process complete successfully? Check console output.")
            else:
                 messagebox.showerror("YouTube Music Login Error", f"Could not log in to YouTube Music.\nError: {result}")
            self.yt_client = None
            self.transfer_button.config(state=tk.DISABLED)


    def _start_transfer(self):
        if not self.sp_client:
            messagebox.showwarning("Missing Client", "Please log in to Spotify first.")
            return
        if not self.yt_client:
            messagebox.showwarning("Missing Client", "Please log in to YouTube Music first.")
            return

        self._log("Starting playlist transfer process...")
        self.transfer_button.config(state=tk.DISABLED) # Disable during transfer
        # Disable other buttons too?
        self.spotify_button.config(state=tk.DISABLED)
        self.ytmusic_button.config(state=tk.DISABLED)

        # Run the whole transfer sequence in a thread
        self._run_in_thread(self._transfer_sequence, self._transfer_callback)

    def _transfer_sequence(self):
        """The actual sequence of fetching, saving, and transferring."""
        # 1. Fetch from Spotify
        self._log("Step 1/3: Fetching playlists from Spotify...")
        spotify_playlists = fetch_spotify_playlists(self.sp_client)
        if not spotify_playlists:
            # fetch_spotify_playlists logs errors internally
            raise RuntimeError("Failed to fetch any playlists from Spotify. Check logs.")
        self._log(f"Fetched {len(spotify_playlists)} playlists from Spotify.")

        # 2. Save to JSON (optional but good practice)
        self._log(f"Step 2/3: Saving Spotify data to '{SPOTIFY_DATA_FILE}'...")
        save_playlists_to_json(spotify_playlists, SPOTIFY_DATA_FILE)
        self._log("Spotify data saved.")

        # 3. Transfer to YouTube Music
        self._log("Step 3/3: Transferring playlists to YouTube Music...")
        transfer_success = transfer_playlists_to_ytmusic(self.yt_client, SPOTIFY_DATA_FILE)
        if not transfer_success:
            # transfer_playlists_to_ytmusic logs errors internally
             raise RuntimeError("Playlist transfer process reported an issue. Check logs.")

        # If we reach here, all steps initiated correctly (individual track errors are logged within transfer)
        return "Transfer process completed. Check logs for details on individual playlists and tracks."


    def _transfer_callback(self, success, result):
        # Re-enable buttons regardless of outcome
        self.transfer_button.config(state=tk.NORMAL)
        self.spotify_button.config(state=tk.NORMAL) # Or keep disabled if successful login?
        self.ytmusic_button.config(state=tk.NORMAL) # Or keep disabled if successful login?

        if success:
            self._log(f"Transfer Sequence Result: {result}", level=logging.INFO)
            messagebox.showinfo("Transfer Complete", result)
        else:
            self._log(f"Transfer Sequence Error: {result}", level=logging.ERROR)
            messagebox.showerror("Transfer Error", f"The transfer process failed.\nError: {result}\n\nPlease check the log window for more details.")

# --- Main Execution ---

if __name__ == "__main__":
    root = tk.Tk()
    app = PlaylistTransferApp(root)
    root.mainloop()
