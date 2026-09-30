"""
app.py
-------
Unified Entry Point for Secure File Vault.
- Ensures all required directories exist.
- Starts the Flask Web Server in a background thread (http://127.0.0.1:5000).
- Launches the upgraded Cyberpunk-Glass Desktop GUI.
- Automatically opens the 3D Glass Web Application in the browser.
"""

import os
import sys
import time
import logging
import threading
import webbrowser

from gui import SecureFileVaultApp


def start_background_web_server():
    """Starts the Flask web server in a daemon thread."""
    try:
        # Suppress werkzeug info logs to keep terminal clean
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        from web.server import app as flask_app
        flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[Web Server] Notice: {e}")


def main():
    # Make sure required folders exist
    for folder in ("encrypted_files", "decrypted_files", "logs"):
        os.makedirs(folder, exist_ok=True)

    # 1. Start the full-stack Web Server in the background
    web_thread = threading.Thread(target=start_background_web_server, daemon=True)
    web_thread.start()

    print("\n" + "=" * 60)
    print("  ◈ SECURE FILE VAULT — SYSTEM ACTIVE")
    print("  • Desktop GUI: Launched with Cyberpunk-Glass Dark Theme")
    print("  • Web Application: Active at http://127.0.0.1:5000")
    print("  • Features: 3D Parallax Tilt, Live Blurs, PBKDF2 Key Derivation")
    print("=" * 60 + "\n")

    # 2. Auto-open the 3D Glass Web Application in the browser after a brief delay
    def open_browser():
        time.sleep(1.0)
        webbrowser.open("http://127.0.0.1:5000")

    threading.Thread(target=open_browser, daemon=True).start()

    # 3. Create and launch the modernized desktop GUI
    app = SecureFileVaultApp()
    app.mainloop()


if __name__ == "__main__":
    main()
