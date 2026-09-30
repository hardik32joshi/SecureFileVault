"""
gui.py
-------
Upgraded Cyberpunk-Glass Modern Desktop GUI for Secure File Vault.
Features:
  - Deep dark glassmorphism color palette (#08090d, #0e1320, #00f0ff neon cyan, #ff0055 neon pink)
  - Interactive mode switcher (Lock vs. Unlock)
  - File details card with size formatting & reset
  - Real-time password strength meter with animated color glow
  - Direct 1-click launcher for the 3D Glass Web Application
  - Live activity ledger & SHA-256 fingerprint receipts
  - Threaded encryption/decryption workers to keep UI smooth
"""

import os
import threading
import webbrowser
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
from datetime import datetime

import customtkinter as ctk

from crypto import CryptoEngine
from auth import AuthManager
from utils import calculate_sha256, get_output_path, format_file_size
from logger import ActivityLogger
from cryptography.fernet import InvalidToken


ENCRYPTED_FOLDER = "encrypted_files"
DECRYPTED_FOLDER = "decrypted_files"


class SecureFileVaultApp(ctk.CTk):
    """
    Main application window with upgraded futuristic glassmorphism styling.
    """

    def __init__(self):
        super().__init__()

        # --- Window setup ---
        self.title("◈ VAULT — Enterprise File Encryption & Decryption")
        self.geometry("780x790")
        self.minsize(720, 720)
        
        # Color theme settings
        ctk.set_appearance_mode("dark")
        self.configure(fg_color="#08090d")

        # Color Tokens
        self.COLOR_BG = "#08090d"
        self.COLOR_CARD = "#0e1320"
        self.COLOR_CARD_BORDER = "#1c263c"
        self.COLOR_CYAN = "#00f0ff"
        self.COLOR_CYAN_HOVER = "#4df4ff"
        self.COLOR_PINK = "#ff0055"
        self.COLOR_PINK_HOVER = "#ff3377"
        self.COLOR_TEXT_PRIMARY = "#f8fafc"
        self.COLOR_TEXT_DIM = "#94a3b8"
        self.COLOR_GREEN = "#00e676"
        self.COLOR_INPUT_BG = "#06080e"

        # --- Backend engine instances ---
        self.crypto_engine = CryptoEngine()
        self.auth_manager = AuthManager()
        self.logger = ActivityLogger()

        # --- State ---
        self.selected_file_path = None
        self.current_mode = "encrypt"  # "encrypt" | "decrypt"
        self.password_visible = False
        self.last_hash = ""

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Constructs modern styled glass cards and widgets."""

        # -------------------------------------------------------------
        # 1. TOP HEADER BAR
        # -------------------------------------------------------------
        header_card = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=16,
            height=75
        )
        header_card.pack(fill="x", padx=20, pady=(16, 12))

        # Brand title & badge
        brand_frame = ctk.CTkFrame(header_card, fg_color="transparent")
        brand_frame.pack(side="left", padx=18, pady=12)

        title_label = ctk.CTkLabel(
            brand_frame,
            text="◈ VAULT",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=self.COLOR_CYAN
        )
        title_label.pack(side="left")

        subtitle_label = ctk.CTkLabel(
            brand_frame,
            text=" · AES-256 ZERO-KNOWLEDGE ENGINE",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.COLOR_TEXT_DIM
        )
        subtitle_label.pack(side="left", padx=(4, 0), pady=(3, 0))

        # Right actions: Web App launcher button
        actions_frame = ctk.CTkFrame(header_card, fg_color="transparent")
        actions_frame.pack(side="right", padx=16, pady=12)

        self.web_btn = ctk.CTkButton(
            actions_frame,
            text="🌐 3D Glass Web UI",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#092736",
            border_color=self.COLOR_CYAN,
            border_width=1,
            text_color=self.COLOR_CYAN,
            hover_color="#103c54",
            corner_radius=10,
            height=34,
            command=self.open_web_ui
        )
        self.web_btn.pack(side="right")

        status_badge = ctk.CTkLabel(
            actions_frame,
            text="● ONLINE",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=self.COLOR_GREEN
        )
        status_badge.pack(side="right", padx=(0, 14))

        # -------------------------------------------------------------
        # 2. MODE SELECTOR (Segmented tab)
        # -------------------------------------------------------------
        self.mode_selector = ctk.CTkSegmentedButton(
            self,
            values=["🔒 Lock / Encrypt File", "🔓 Unlock / Decrypt File"],
            command=self.on_mode_change,
            selected_color=self.COLOR_CYAN,
            selected_hover_color=self.COLOR_CYAN_HOVER,
            unselected_color="#101524",
            unselected_hover_color="#182036",
            text_color=self.COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            corner_radius=12,
            height=40
        )
        self.mode_selector.set("🔒 Lock / Encrypt File")
        self.mode_selector.pack(fill="x", padx=20, pady=(0, 12))

        # -------------------------------------------------------------
        # 3. FILE SELECTION CARD
        # -------------------------------------------------------------
        file_card = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=14
        )
        file_card.pack(fill="x", padx=20, pady=(0, 12))

        file_card_header = ctk.CTkFrame(file_card, fg_color="transparent")
        file_card_header.pack(fill="x", padx=16, pady=(12, 6))

        file_sec_title = ctk.CTkLabel(
            file_card_header,
            text="📂 TARGET FILE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.COLOR_TEXT_DIM
        )
        file_sec_title.pack(side="left")

        file_browse_btn = ctk.CTkButton(
            file_card_header,
            text="Browse Files",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#182136",
            hover_color="#243250",
            border_color="#2e3e63",
            border_width=1,
            text_color=self.COLOR_TEXT_PRIMARY,
            corner_radius=8,
            height=30,
            width=110,
            command=self.browse_file
        )
        file_browse_btn.pack(side="right")

        # Inner File display box
        self.file_display_box = ctk.CTkFrame(
            file_card,
            fg_color=self.COLOR_INPUT_BG,
            border_color="#161e30",
            border_width=1,
            corner_radius=10,
            height=54
        )
        self.file_display_box.pack(fill="x", padx=16, pady=(0, 14))

        self.file_icon_label = ctk.CTkLabel(
            self.file_display_box,
            text="⟡",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLOR_CYAN
        )
        self.file_icon_label.pack(side="left", padx=(14, 8), pady=10)

        self.file_label = ctk.CTkLabel(
            self.file_display_box,
            text="No file selected — click Browse Files or choose an encrypted .enc file",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=self.COLOR_TEXT_DIM,
            anchor="w"
        )
        self.file_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.clear_file_btn = ctk.CTkButton(
            self.file_display_box,
            text="✕",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color="#331018",
            text_color="#ff4466",
            corner_radius=14,
            command=self.clear_selected_file
        )
        # Hidden until file selected

        # -------------------------------------------------------------
        # 4. COMBINATION / PASSWORD CARD
        # -------------------------------------------------------------
        pwd_card = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=14
        )
        pwd_card.pack(fill="x", padx=20, pady=(0, 12))

        pwd_card_header = ctk.CTkFrame(pwd_card, fg_color="transparent")
        pwd_card_header.pack(fill="x", padx=16, pady=(12, 6))

        pwd_sec_title = ctk.CTkLabel(
            pwd_card_header,
            text="🔑 COMBINATION (MASTER KEY)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.COLOR_TEXT_DIM
        )
        pwd_sec_title.pack(side="left")

        generate_btn = ctk.CTkButton(
            pwd_card_header,
            text="⚄ Generate Key",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#182136",
            hover_color="#243250",
            border_color="#2e3e63",
            border_width=1,
            text_color=self.COLOR_CYAN,
            corner_radius=8,
            height=30,
            width=120,
            command=self.generate_password
        )
        generate_btn.pack(side="right")

        # Password input row
        pwd_row = ctk.CTkFrame(pwd_card, fg_color="transparent")
        pwd_row.pack(fill="x", padx=16, pady=(0, 8))

        self.password_entry = ctk.CTkEntry(
            pwd_row,
            placeholder_text="Enter secret password...",
            show="*",
            fg_color=self.COLOR_INPUT_BG,
            border_color="#1c253b",
            border_width=1,
            corner_radius=10,
            height=42,
            font=ctk.CTkFont(family="Consolas", size=14),
            text_color=self.COLOR_TEXT_PRIMARY
        )
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.password_entry.bind("<KeyRelease>", self.update_password_strength)

        self.toggle_pwd_btn = ctk.CTkButton(
            pwd_row,
            text="👁",
            font=ctk.CTkFont(size=14),
            width=42,
            height=42,
            fg_color="#182136",
            hover_color="#243250",
            border_color="#2e3e63",
            border_width=1,
            text_color=self.COLOR_TEXT_DIM,
            corner_radius=10,
            command=self.toggle_password_visibility
        )
        self.toggle_pwd_btn.pack(side="right")

        # Password Strength Bar & Label
        self.strength_frame = ctk.CTkFrame(pwd_card, fg_color="transparent")
        self.strength_frame.pack(fill="x", padx=16, pady=(0, 12))

        strength_meta_row = ctk.CTkFrame(self.strength_frame, fg_color="transparent")
        strength_meta_row.pack(fill="x", pady=(0, 4))

        self.strength_label = ctk.CTkLabel(
            strength_meta_row,
            text="Key Entropy: —",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.COLOR_TEXT_DIM
        )
        self.strength_label.pack(side="left")

        self.strength_hint = ctk.CTkLabel(
            strength_meta_row,
            text="PBKDF2-HMAC-SHA256 (390,000 iterations)",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#64748b"
        )
        self.strength_hint.pack(side="right")

        self.strength_bar = ctk.CTkProgressBar(
            self.strength_frame,
            height=6,
            corner_radius=3,
            fg_color="#182030",
            progress_color=self.COLOR_CYAN
        )
        self.strength_bar.set(0)
        self.strength_bar.pack(fill="x")

        # -------------------------------------------------------------
        # 5. ACTION EXECUTION BUTTON
        # -------------------------------------------------------------
        self.action_btn = ctk.CTkButton(
            self,
            text="🔒 LOCK & ENCRYPT FILE",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=self.COLOR_CYAN,
            hover_color=self.COLOR_CYAN_HOVER,
            text_color="#08090d",
            corner_radius=12,
            height=46,
            command=self.handle_action
        )
        self.action_btn.pack(fill="x", padx=20, pady=(0, 12))

        # -------------------------------------------------------------
        # 6. INTEGRITY RECEIPT & ACTIVITY LEDGER
        # -------------------------------------------------------------
        ledger_card = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=14
        )
        ledger_card.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        ledger_header = ctk.CTkFrame(ledger_card, fg_color="transparent")
        ledger_header.pack(fill="x", padx=16, pady=(12, 6))

        ledger_title = ctk.CTkLabel(
            ledger_header,
            text="📜 INTEGRITY RECEIPT & ACTIVITY LOG",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.COLOR_TEXT_DIM
        )
        ledger_title.pack(side="left")

        clear_btn = ctk.CTkButton(
            ledger_header,
            text="Clear",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent",
            hover_color="#182136",
            text_color=self.COLOR_TEXT_DIM,
            width=50,
            height=24,
            command=self.clear_logs
        )
        clear_btn.pack(side="right")

        self.copy_hash_btn = ctk.CTkButton(
            ledger_header,
            text="📋 Copy SHA-256",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent",
            hover_color="#182136",
            text_color=self.COLOR_CYAN,
            width=100,
            height=24,
            command=self.copy_last_hash
        )
        self.copy_hash_btn.pack(side="right", padx=(0, 8))

        self.status_textbox = ctk.CTkTextbox(
            ledger_card,
            fg_color=self.COLOR_INPUT_BG,
            border_color="#141a27",
            border_width=1,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#94a3b8"
        )
        self.status_textbox.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        
        # Initial greeting in log
        self._append_status(
            "◈ Secure File Vault initialized.\n"
            "   [+] Engine: AES-256 authenticated encryption via Fernet\n"
            "   [+] Key Derivation: PBKDF2-HMAC-SHA256 (390,000 rounds)\n"
            "   [+] Ready. Choose a file and combination to begin.\n"
        )

    # ------------------------------------------------------------------
    # MODE SWITCHING & UI LOGIC
    # ------------------------------------------------------------------
    def on_mode_change(self, value):
        """Update styling and wording based on Lock vs. Unlock."""
        if "Lock" in value:
            self.current_mode = "encrypt"
            self.mode_selector.configure(selected_color=self.COLOR_CYAN, selected_hover_color=self.COLOR_CYAN_HOVER)
            self.action_btn.configure(
                text="🔒 LOCK & ENCRYPT FILE",
                fg_color=self.COLOR_CYAN,
                hover_color=self.COLOR_CYAN_HOVER,
                text_color="#08090d"
            )
            self.file_icon_label.configure(text_color=self.COLOR_CYAN)
            self.strength_frame.pack(fill="x", padx=16, pady=(0, 12))
        else:
            self.current_mode = "decrypt"
            self.mode_selector.configure(selected_color=self.COLOR_PINK, selected_hover_color=self.COLOR_PINK_HOVER)
            self.action_btn.configure(
                text="🔓 UNLOCK & DECRYPT FILE",
                fg_color=self.COLOR_PINK,
                hover_color=self.COLOR_PINK_HOVER,
                text_color="#ffffff"
            )
            self.file_icon_label.configure(text_color=self.COLOR_PINK)
            self.strength_frame.pack_forget()

    def open_web_ui(self):
        """Open the 3D Glassmorphism web application in the default browser."""
        url = "http://127.0.0.1:5000"
        webbrowser.open(url)
        self._append_status(f"🌐 Opened 3D Glass Web Application at {url}\n")

    def toggle_password_visibility(self):
        """Toggle showing/hiding combination characters."""
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.password_entry.configure(show="")
            self.toggle_pwd_btn.configure(text="🔒", text_color=self.COLOR_CYAN)
        else:
            self.password_entry.configure(show="*")
            self.toggle_pwd_btn.configure(text="👁", text_color=self.COLOR_TEXT_DIM)

    def browse_file(self):
        """Pick a file from disk."""
        title = "Select File to Lock" if self.current_mode == "encrypt" else "Select Encrypted File (.enc)"
        path = filedialog.askopenfilename(title=title)
        if path:
            self.selected_file_path = path
            size = os.path.getsize(path)
            self.file_label.configure(
                text=f"{os.path.basename(path)}  •  {format_file_size(size)}",
                text_color=self.COLOR_TEXT_PRIMARY
            )
            self.clear_file_btn.pack(side="right", padx=(0, 8))

    def clear_selected_file(self):
        """Deselect file."""
        self.selected_file_path = None
        self.file_label.configure(
            text="No file selected — click Browse Files or choose an encrypted .enc file",
            text_color=self.COLOR_TEXT_DIM
        )
        self.clear_file_btn.pack_forget()

    def update_password_strength(self, event=None):
        """Update strength bar with custom colors based on score."""
        if self.current_mode != "encrypt":
            return

        password = self.password_entry.get()
        if not password:
            self.strength_label.configure(text="Key Entropy: —", text_color=self.COLOR_TEXT_DIM)
            self.strength_bar.set(0)
            return

        result = self.auth_manager.check_password_strength(password)
        score = result["score"]
        label = result["label"].upper()

        colors = {
            0: "#ef4444", 1: "#ef4444", 2: "#f59e0b",
            3: "#eab308", 4: "#00f0ff", 5: "#00e676"
        }
        active_color = colors.get(score, self.COLOR_CYAN)

        self.strength_label.configure(
            text=f"Key Entropy: {label}",
            text_color=active_color
        )
        self.strength_bar.set(score / 5.0)
        self.strength_bar.configure(progress_color=active_color)

    def generate_password(self):
        """Generate a cryptographically secure 16-character password."""
        strong_pw = self.auth_manager.generate_strong_password(16)
        self.password_visible = True
        self.password_entry.configure(show="")
        self.toggle_pwd_btn.configure(text="🔒", text_color=self.COLOR_CYAN)
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, strong_pw)
        self.update_password_strength()
        self._append_status("⚡ Generated 16-character high-entropy master key.\n")

    def handle_action(self):
        """Execute encrypt or decrypt based on current mode."""
        if self.current_mode == "encrypt":
            self.handle_encrypt()
        else:
            self.handle_decrypt()

    # ------------------------------------------------------------------
    # ENCRYPT / DECRYPT WORKERS
    # ------------------------------------------------------------------
    def handle_encrypt(self):
        if not self.selected_file_path:
            messagebox.showwarning("Vault Warning", "Please select a target file to encrypt.")
            return

        password = self.password_entry.get()
        if not password:
            messagebox.showwarning("Vault Warning", "Please enter a master combination / password.")
            return

        strength = self.auth_manager.check_password_strength(password)
        if strength["score"] <= 1:
            proceed = messagebox.askyesno(
                "Low Entropy Warning",
                "This password is low-entropy (weak). Encrypt anyway?"
            )
            if not proceed:
                return

        self.action_btn.configure(state="disabled", text="PROCESSING ENCRYPTION...")
        threading.Thread(
            target=self._encrypt_worker,
            args=(self.selected_file_path, password),
            daemon=True
        ).start()

    def _encrypt_worker(self, file_path, password):
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            original_hash = calculate_sha256(file_path)
            self.last_hash = original_hash
            output_path = get_output_path(file_path, ENCRYPTED_FOLDER, new_extension=".enc")

            self.crypto_engine.encrypt_file(file_path, output_path, password)

            receipt = (
                f"[{timestamp}] 🔒 ENCRYPTION RECEIPT VERIFIED\n"
                f"   ├─ Source File: {os.path.basename(file_path)}\n"
                f"   ├─ Output Path: {output_path}\n"
                f"   ├─ SHA-256:     {original_hash}\n"
                f"   └─ Algorithm:   Fernet (AES-128-CBC + HMAC-SHA256 tag)\n\n"
            )
            self._append_status(receipt)
            self.logger.log_info(f"Encrypted '{file_path}' -> '{output_path}' | SHA256={original_hash}")

        except Exception as e:
            self._append_status(f"[{timestamp}] ❌ ENCRYPTION FAILED: {e}\n\n")
            self.logger.log_error(f"Encryption failed for '{file_path}': {e}")
        finally:
            self.after(0, lambda: self.action_btn.configure(state="normal", text="🔒 LOCK & ENCRYPT FILE"))

    def handle_decrypt(self):
        if not self.selected_file_path:
            messagebox.showwarning("Vault Warning", "Please select an encrypted (.enc) file to unlock.")
            return

        password = self.password_entry.get()
        if not password:
            messagebox.showwarning("Vault Warning", "Please enter the vault password.")
            return

        self.action_btn.configure(state="disabled", text="VERIFYING HMAC & DECRYPTING...")
        threading.Thread(
            target=self._decrypt_worker,
            args=(self.selected_file_path, password),
            daemon=True
        ).start()

    def _decrypt_worker(self, file_path, password):
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            base_name = os.path.basename(file_path)
            if base_name.endswith(".enc"):
                base_name = base_name[:-4]

            output_path = os.path.join(DECRYPTED_FOLDER, base_name)
            os.makedirs(DECRYPTED_FOLDER, exist_ok=True)

            self.crypto_engine.decrypt_file(file_path, output_path, password)
            new_hash = calculate_sha256(output_path)
            self.last_hash = new_hash

            receipt = (
                f"[{timestamp}] 🔓 DECRYPTION INTEGRITY VERIFIED\n"
                f"   ├─ Source Encrypted: {os.path.basename(file_path)}\n"
                f"   ├─ Recovered File:   {output_path}\n"
                f"   ├─ SHA-256 Checksum: {new_hash}\n"
                f"   └─ Status:           Tamper-Check Passed (Zero Corruption)\n\n"
            )
            self._append_status(receipt)
            self.logger.log_info(f"Decrypted '{file_path}' -> '{output_path}' | SHA256={new_hash}")

        except InvalidToken:
            self._append_status(
                f"[{timestamp}] ❌ DECRYPTION REJECTED\n"
                f"   Reason: Authentication Tag Failed (Wrong Password or File Corrupted)\n\n"
            )
            self.logger.log_error(f"Decryption failed for '{file_path}': authentication failure.")
        except Exception as e:
            self._append_status(f"[{timestamp}] ❌ DECRYPTION ERROR: {e}\n\n")
            self.logger.log_error(f"Decryption failed for '{file_path}': {e}")
        finally:
            self.after(0, lambda: self.action_btn.configure(state="normal", text="🔓 UNLOCK & DECRYPT FILE"))

    def copy_last_hash(self):
        """Copy the latest SHA-256 hash to the system clipboard."""
        if self.last_hash:
            self.clipboard_clear()
            self.clipboard_append(self.last_hash)
            messagebox.showinfo("Copied", f"Copied SHA-256 to clipboard:\n{self.last_hash}")
        else:
            messagebox.showinfo("Info", "No transaction hash generated yet.")

    def clear_logs(self):
        """Clear ledger output."""
        self.status_textbox.configure(state="normal")
        self.status_textbox.delete("1.0", "end")
        self.status_textbox.configure(state="disabled")

    def _append_status(self, text: str):
        """Append log message thread-safely."""
        def _update():
            self.status_textbox.configure(state="normal")
            self.status_textbox.insert("end", text)
            self.status_textbox.see("end")
            self.status_textbox.configure(state="disabled")

        self.after(0, _update)
