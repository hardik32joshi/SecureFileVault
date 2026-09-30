# ◈ Secure File Vault

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-000000?style=for-the-badge&logo=flask&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-00f0ff?style=for-the-badge)
![Cryptography](https://img.shields.io/badge/Crypto-AES--256%20%7C%20Fernet-ff0055?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-00e676?style=for-the-badge)

**A dual-interface (Cyberpunk Glassmorphism Web App + Modern Desktop GUI) zero-knowledge file encryption suite.**  
*Seals any file type with military-grade PBKDF2-HMAC-SHA256 key derivation, Fernet (AES-128-CBC + HMAC authentication), and SHA-256 integrity verification.*

</div>

---

## ⚡ Highlights

- **Dual Interfaces, Zero Logic Duplication**:
  - **🌐 3D Glassmorphism Web App**: Modern web dashboard with ambient glowing gradients, interactive frosted-glass cards, live password entropy ratings, and real-time ledger receipts.
  - **🖥️ Cyberpunk-Glass Desktop GUI**: Built with CustomTkinter featuring deep obsidian themes (`#06080d`), neon cyan & magenta accents, segmented mode switching, and 1-click web launcher.
- **Enterprise-Grade Cryptography**:
  - **Unique 16-Byte Salt**: Random salt generated per file so identical passwords never produce identical ciphertexts.
  - **390,000 PBKDF2 Iterations**: Password key stretching via `PBKDF2-HMAC-SHA256` defends against modern GPU/ASIC brute-force attacks.
  - **Fernet Authenticated Encryption**: Implements AES-128-CBC encryption alongside an HMAC-SHA256 authentication tag to prevent tampering or bit-flipping.
  - **Zero-Corruption Verification**: Computes original SHA-256 fingerprint before locking and verifies it after unlocking.
- **Zero-Knowledge Architecture**: Passwords are never stored on disk or cached. Processing happens 100% locally on your machine.

---

## 🏗️ Architecture

```
SecureFileVault/
├── app.py                      # Unified launcher: starts background Flask server & Desktop GUI
├── gui.py                      # Cyberpunk-Glass Desktop application (CustomTkinter)
├── crypto.py                   # Core encryption & decryption engine (Fernet / AES)
├── auth.py                     # PBKDF2 key derivation & password entropy evaluator
├── utils.py                    # SHA-256 checksum calculator and formatting helpers
├── logger.py                   # Thread-safe activity and audit logger
├── requirements.txt            # Project dependencies
├── LICENSE                     # MIT License
├── README.md                   # Complete documentation
│
├── web/                        # Full-Stack Web Application
│   ├── server.py               # Flask REST API endpoints
│   ├── templates/
│   │   └── index.html          # Responsive single-page dashboard markup
│   ├── static/
│   │   ├── style.css           # Custom glassmorphism design system & animations
│   │   └── script.js           # Client-side reactivity, fetch handlers, and UI state
│   └── uploads_tmp/            # Temporary file upload cache (auto-cleared)
│
├── encrypted_files/            # Default storage for .enc encrypted outputs
├── decrypted_files/            # Default storage for restored files
└── logs/                       # Activity audit trail logs
```

---

## 🚀 Quick Start

### 1. Installation

Clone this repository and install the dependencies:

```bash
git clone https://github.com/hardik32joshi/SecureFileVault.git
cd SecureFileVault
pip install -r requirements.txt
```

### 2. Launch the Application

Run the unified entry point:

```bash
python app.py
```

This single command will:
1. Initialize the background web server at `http://127.0.0.1:5000`.
2. Automatically launch the **3D Glass Web Application** in your default web browser.
3. Open the **Cyberpunk Desktop GUI**.

---

## 🌐 Running the Web Application Independently

If you prefer running just the web application on a headless system or local server:

```bash
cd web
python server.py
```

Then visit **`http://127.0.0.1:5000`** in your browser.

---

## 📡 REST API Reference

The Flask backend provides RESTful endpoints consumed by the web interface:

| Endpoint | Method | Parameters | Description |
| :--- | :--- | :--- | :--- |
| `/api/encrypt` | `POST` | `multipart/form-data`: `file`, `password` | Encrypts the uploaded file and returns the `.enc` stream with `X-Original-SHA256` header. |
| `/api/decrypt` | `POST` | `multipart/form-data`: `file`, `password` | Verifies HMAC, decrypts `.enc` file, and returns decrypted binary with `X-Decrypted-SHA256`. |
| `/api/password-strength` | `POST` | `JSON`: `{ "password": "..." }` | Evaluates key entropy score (0–5), label, and suggestions. |
| `/api/generate-password` | `GET` | Query param: `length` (default: 16) | Generates a cryptographically strong random combination. |
| `/api/logs` | `GET` | None | Returns the latest 30 audit log entries in reverse chronological order. |

---

## 🔒 Security Specifications

1. **Key Derivation Function (KDF)**:
   - Algorithm: `PBKDF2HMAC`
   - Hash Algorithm: `SHA-256`
   - Iterations: `390,000` (OWASP recommended standard)
   - Salt Length: 16 random cryptographically secure bytes (`os.urandom(16)`)
2. **Authenticated Cipher**:
   - Algorithm: Fernet
   - Encryption: `AES-128-CBC` with PKCS7 padding
   - Authentication: `HMAC-SHA256` with constant-time comparison to prevent timing attacks.
3. **Payload Structure (`.enc`)**:
   `[ 16 Bytes Salt ] + [ Fernet Encrypted Ciphertext with Embedded HMAC ]`

---

## 📦 Packaging to Standalone Executable (.exe)

To bundle the desktop application into a standalone Windows `.exe`:

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name SecureFileVault app.py
```

The compiled binary will be placed in `dist/SecureFileVault.exe`.

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
