"""
secure_string_cipher - Core encryption functionality
"""

from .cli import main
from .core import (
    CryptoError,
    FileMetadata,
    StreamProcessor,
    decrypt_file,
    decrypt_file_v2,
    decrypt_stream,
    decrypt_text,
    derive_key,
    encrypt_file,
    encrypt_file_v2,
    encrypt_stream,
    encrypt_text,
)
from .passphrase_generator import generate_passphrase
from .passphrase_manager import PassphraseVault
from .secure_memory import SecureBytes, SecureString, secure_wipe
from .security import SecurityError
from .timing_safe import (
    add_timing_jitter,
    check_password_strength,
    constant_time_compare,
)
from .utils import ProgressBar, colorize, handle_timeout, secure_overwrite

__version__ = "1.0.19"
__author__ = "TheRedTower"
__email__ = "security@avondenecloud.uk"

__all__ = [
    # Encryption (v1 - legacy)
    "encrypt_text",
    "decrypt_text",
    "encrypt_file",
    "decrypt_file",
    "encrypt_stream",
    "decrypt_stream",
    "derive_key",
    "StreamProcessor",
    # Encryption (v2 - with metadata)
    "encrypt_file_v2",
    "decrypt_file_v2",
    "FileMetadata",
    # Exceptions
    "CryptoError",
    "SecurityError",
    # Security utilities
    "check_password_strength",
    "constant_time_compare",
    "add_timing_jitter",
    # Secure memory
    "SecureString",
    "SecureBytes",
    "secure_wipe",
    # Passphrase management
    "generate_passphrase",
    "PassphraseVault",
    # CLI utilities
    "colorize",
    "handle_timeout",
    "secure_overwrite",
    "ProgressBar",
    "main",
]
