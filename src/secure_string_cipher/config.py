"""
Configuration settings for secure-string-cipher
"""

# =============================================================================
# Key Derivation Function (KDF) Settings
# =============================================================================

# Argon2id settings (memory-hard, GPU/ASIC resistant)
# These follow OWASP recommendations for password hashing
ARGON2_TIME_COST = 3  # Number of iterations
ARGON2_MEMORY_COST = 65536  # Memory in KiB (64 MB)
ARGON2_PARALLELISM = 4  # Degree of parallelism
ARGON2_HASH_LENGTH = 32  # Output key length (256 bits for AES-256)

# =============================================================================
# Encryption Parameters
# =============================================================================

CHUNK_SIZE = 64 * 1024
SALT_SIZE = 16
NONCE_SIZE = 12
TAG_SIZE = 16
KEY_COMMITMENT_SIZE = 32  # HMAC-SHA256 output size

# Key commitment constant - used to bind ciphertext to a specific key
# This prevents "invisible salamanders" attacks where a ciphertext
# could decrypt to different plaintexts under different keys
KEY_COMMITMENT_CONTEXT = b"secure-string-cipher-v1-key-commitment"

# File metadata format
METADATA_VERSION = 4  # Version 4: Argon2id + key commitment
METADATA_MAGIC = b"SSCV2"  # Magic bytes to identify format
FILENAME_MAX_LENGTH = 255  # Maximum stored filename length

MAX_FILE_SIZE = 100 * 1024 * 1024
MIN_PASSWORD_LENGTH = 12
PASSWORD_PATTERNS = {
    "uppercase": lambda s: any(c.isupper() for c in s),
    "lowercase": lambda s: any(c.islower() for c in s),
    "digits": lambda s: any(c.isdigit() for c in s),
    "symbols": lambda s: any(not c.isalnum() for c in s),
}
COMMON_PASSWORDS = {
    "password",
    "123456",
    "qwerty",
    "admin",
    "letmein",
    "welcome",
    "monkey",
    "dragon",
}

COLORS = {
    "reset": "\033[0m",
    "cyan": "\033[96m",
    "blue": "\033[34m",
    "red": "\033[91m",
    "green": "\033[92m",
}

DEFAULT_MODE = 1
CLIPBOARD_ENABLED = True
CLI_TIMEOUT = 300
