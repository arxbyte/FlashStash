# FlashStash 🚀
A local micro-service for instant file and text exchange within a single Wi-Fi / LAN network.

![FlashStash](screenshots/main_screen.png)

![FlashStash](screenshots/main_screen.png)

## 📦 How to download and launch the portable version:
1. Download the latest release archive.
2. Unzip the archive into any convenient folder.
3. Run **run.bat**.
4. The script will automatically verify dependencies, start the server, and **open the app in your browser**.
   * *If the page is already open, the script will detect the active WebSocket connection and skip opening a duplicate tab.*
5. To connect a smartphone or another PC, simply enter the IP address shown in the console (or scan the QR code directly from the UI).

## 🛠 Key Features & Recent Updates:
* **Smart Auto-Launch:** Automatically opens the browser on startup. Avoids creating duplicate tabs if the web interface is already active.
* **Built-in Media Players:** Images, videos (.mp4, .webm, etc.), and audio (.mp3, .wav, .flac) can now be previewed or streamed directly in the browser via a custom UI without downloading.
* **Archive Structure Indexing:** Added support for .zip and .rar files. Clicking on an archive displays its internal file tree and file sizes directly on the webpage (requires `rarfile`).
* **Stream vs. Download Separation:** The `[GET]` button now explicitly forces a file download, while clicking the preview item safely opens the internal media viewer.
* **Password Protection:** Set optional passwords on uploaded files to restrict access. Other local network users won't be able to download or preview locked files without the correct password.
* **Persistent Text History:** The text clipboard history is now automatically saved to a local `text_history.txt` file and survives server restarts.
