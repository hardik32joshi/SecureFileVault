"""
server.py
----------
Flask backend for the Secure File Vault WEB frontend.

RESPONSIBILITY OF THIS FILE:
This is the web equivalent of gui.py — it is a thin layer that:
  - Receives HTTP requests (file uploads, password fields)
  - Calls the SAME crypto.py / auth.py / utils.py / logger.py modules
    used by the desktop app (zero duplication of security logic)
  - Returns JSON or file responses back to the browser

WHY THIS PROVES GOOD ARCHITECTURE:
Because crypto.py and auth.py never imported anything from gui.py, we can
plug in an entirely different interface (a website) without changing a
single line of the encryption/decryption/PBKDF2 code. This is the payoff
of "separation of concerns" mentioned in the desktop app.
"""

import os
import sys
import uuid

from flask import Flask, request, jsonify, send_file, render_template

# Add the parent directory (SecureFileVault/) to the import path so we can
# reuse the exact same backend modules as the desktop app, instead of
# copy-pasting the encryption logic into the web app.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto import CryptoEngine          # noqa: E402
from auth import AuthManager              # noqa: E402
from utils import calculate_sha256, format_file_size  # noqa: E402
from logger import ActivityLogger         # noqa: E402
from cryptography.fernet import InvalidToken  # noqa: E402


# --- Flask app setup ---
app = Flask(__name__)

# Folders (relative to this file's location) for temp uploads and outputs.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads_tmp")
ENCRYPTED_DIR = os.path.join(os.path.dirname(BASE_DIR), "encrypted_files")
DECRYPTED_DIR = os.path.join(os.path.dirname(BASE_DIR), "decrypted_files")

for folder in (UPLOAD_DIR, ENCRYPTED_DIR, DECRYPTED_DIR):
    os.makedirs(folder, exist_ok=True)

# Cap uploads at 200 MB to keep the demo server well-behaved.
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

# Shared backend engine instances (stateless, safe to reuse across requests).
crypto_engine = CryptoEngine()
auth_manager = AuthManager()
activity_logger = ActivityLogger(log_dir=os.path.join(os.path.dirname(BASE_DIR), "logs"))


# ----------------------------------------------------------------------
# PAGE ROUTE
# ----------------------------------------------------------------------
@app.route("/")
def index():
    """Serve the single-page web frontend."""
    return render_template("index.html")


# ----------------------------------------------------------------------
# API: PASSWORD STRENGTH CHECK
# ----------------------------------------------------------------------
@app.route("/api/password-strength", methods=["POST"])
def password_strength():
    """
    Accepts JSON: { "password": "..." }
    Returns JSON: { "score": int, "label": str, "suggestions": [...] }
    """
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    result = auth_manager.check_password_strength(password)
    return jsonify(result)


# ----------------------------------------------------------------------
# API: GENERATE STRONG PASSWORD
# ----------------------------------------------------------------------
@app.route("/api/generate-password", methods=["GET"])
def generate_password():
    """Returns JSON: { "password": "..." } — a freshly generated strong password."""
    length = request.args.get("length", default=16, type=int)
    pw = auth_manager.generate_strong_password(length)
    return jsonify({"password": pw})


# ----------------------------------------------------------------------
# API: ENCRYPT FILE
# ----------------------------------------------------------------------
@app.route("/api/encrypt", methods=["POST"])
def encrypt_file_route():
    """
    Accepts multipart/form-data:
        file: the file to encrypt
        password: the encryption password

    Flow:
      1. Save the uploaded file to a temp location.
      2. Compute its SHA-256 fingerprint BEFORE encryption.
      3. Encrypt it using crypto.py (same engine as the desktop app).
      4. Save the result into encrypted_files/ (per project spec).
      5. Return the encrypted file as a download, with the hash in a header.
    """
    uploaded_file = request.files.get("file")
    password = request.form.get("password", "")

    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"error": "No file provided."}), 400
    if not password:
        return jsonify({"error": "No password provided."}), 400

    # Use a UUID prefix for the temp copy to avoid filename collisions
    # between concurrent users, while preserving the original filename
    # for the final encrypted output.
    original_name = uploaded_file.filename
    temp_input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{original_name}")
    uploaded_file.save(temp_input_path)

    try:
        original_hash = calculate_sha256(temp_input_path)

        output_filename = f"{original_name}.enc"
        output_path = os.path.join(ENCRYPTED_DIR, output_filename)

        crypto_engine.encrypt_file(temp_input_path, output_path, password)

        activity_logger.log_info(
            f"[WEB] Encrypted '{original_name}' -> '{output_filename}' | SHA256={original_hash}"
        )

        response = send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype="application/octet-stream",
        )
        # Expose the original file's hash to the browser via a custom header,
        # so the frontend can display it for the user's records.
        response.headers["X-Original-SHA256"] = original_hash
        response.headers["Access-Control-Expose-Headers"] = "X-Original-SHA256"
        return response

    except Exception as e:
        activity_logger.log_error(f"[WEB] Encryption failed for '{original_name}': {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        # Always clean up the temp upload, even if encryption failed.
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)


# ----------------------------------------------------------------------
# API: DECRYPT FILE
# ----------------------------------------------------------------------
@app.route("/api/decrypt", methods=["POST"])
def decrypt_file_route():
    """
    Accepts multipart/form-data:
        file: the .enc file to decrypt
        password: the password to attempt decryption with

    Flow mirrors encrypt_file_route, but calls decrypt_file() and handles
    the "wrong password / tampered file" case explicitly.
    """
    uploaded_file = request.files.get("file")
    password = request.form.get("password", "")

    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"error": "No file provided."}), 400
    if not password:
        return jsonify({"error": "No password provided."}), 400

    original_name = uploaded_file.filename
    temp_input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{original_name}")
    uploaded_file.save(temp_input_path)

    # Strip a trailing ".enc" for the restored filename, if present.
    output_filename = original_name[:-4] if original_name.endswith(".enc") else f"decrypted_{original_name}"
    output_path = os.path.join(DECRYPTED_DIR, output_filename)

    try:
        crypto_engine.decrypt_file(temp_input_path, output_path, password)
        new_hash = calculate_sha256(output_path)

        activity_logger.log_info(
            f"[WEB] Decrypted '{original_name}' -> '{output_filename}' | SHA256={new_hash}"
        )

        response = send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype="application/octet-stream",
        )
        response.headers["X-Decrypted-SHA256"] = new_hash
        response.headers["Access-Control-Expose-Headers"] = "X-Decrypted-SHA256"
        return response

    except InvalidToken:
        activity_logger.log_error(f"[WEB] Decryption failed for '{original_name}': wrong password/tampered.")
        return jsonify({"error": "Wrong password, or the file is corrupted/tampered with."}), 400

    except Exception as e:
        activity_logger.log_error(f"[WEB] Decryption failed for '{original_name}': {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)


# ----------------------------------------------------------------------
# API: RECENT ACTIVITY LOG (for the ledger panel in the UI)
# ----------------------------------------------------------------------
@app.route("/api/logs", methods=["GET"])
def get_logs():
    """Returns JSON: { "logs": [ "line1", "line2", ... ] } — most recent first."""
    lines = activity_logger.get_recent_logs(30)
    return jsonify({"logs": list(reversed(lines))})


if __name__ == "__main__":
    # debug=True gives auto-reload during development; turn off for production.
    app.run(host="0.0.0.0", port=5000, debug=False)
