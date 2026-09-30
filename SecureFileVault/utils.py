"""
utils.py
---------
General-purpose helper functions used across the project:
  - Computing SHA-256 hashes for integrity verification
  - Ensuring output folders exist
  - Building safe output file paths

WHY SEPARATE FROM crypto.py?
crypto.py is strictly about ENCRYPTION (turning data into ciphertext).
Integrity checking (SHA-256 hashing) is a DIFFERENT concept — it's about
verifying data hasn't changed, not about hiding it. Keeping them apart
makes each module easier to understand and test independently.
"""

import hashlib
import os


def calculate_sha256(file_path: str) -> str:
    """
    Compute the SHA-256 hash ("fingerprint") of a file.

    WHY READ IN CHUNKS?
    Large files (e.g., a 2GB video) can't be safely loaded into memory
    all at once. We read the file in small fixed-size chunks (4096 bytes)
    and feed them into the hash function incrementally. This keeps memory
    usage constant regardless of file size.

    Args:
        file_path (str): path to the file to hash.

    Returns:
        str: the hex-encoded SHA-256 hash (a 64-character string).

    Raises:
        FileNotFoundError: if the file does not exist.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256_hash = hashlib.sha256()  # Create a new SHA-256 hash object.

    with open(file_path, "rb") as f:  # "rb" = read binary (works for ANY file type).
        # Iterate over the file in 4096-byte chunks until it's exhausted.
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)  # Feed each chunk into the hash.

    # .hexdigest() converts the binary hash into a readable hex string.
    return sha256_hash.hexdigest()


def ensure_folder_exists(folder_path: str):
    """
    Create a folder if it doesn't already exist.
    Used to guarantee 'encrypted_files/' and 'decrypted_files/' exist
    before we try to save files into them.

    Args:
        folder_path (str): path of the folder to check/create.
    """
    os.makedirs(folder_path, exist_ok=True)


def get_output_path(original_path: str, output_folder: str, new_extension: str = None) -> str:
    """
    Build a safe output path inside a target folder, based on the
    original file's name.

    Example:
        original_path = "C:/Users/me/photo.png"
        output_folder = "encrypted_files"
        new_extension = ".enc"
        -> "encrypted_files/photo.png.enc"

    Args:
        original_path (str): the source file's full path.
        output_folder (str): the folder we want to place the output in.
        new_extension (str, optional): extension to append (e.g. ".enc").

    Returns:
        str: the full output file path.
    """
    ensure_folder_exists(output_folder)

    # os.path.basename extracts just the filename (no folder path), e.g. "photo.png"
    filename = os.path.basename(original_path)

    if new_extension:
        filename += new_extension

    return os.path.join(output_folder, filename)


def format_file_size(size_bytes: int) -> str:
    """
    Convert a raw byte count into a human-readable string
    (e.g., 2048 -> "2.00 KB"). Purely a display helper for the GUI.

    Args:
        size_bytes (int): file size in bytes.

    Returns:
        str: human-readable size.
    """
    # Walk through units until the size becomes a manageable number.
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"
