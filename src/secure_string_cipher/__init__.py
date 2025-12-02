"""
secure_string_cipher - Core encryption functionality
"""

from .cli import main
from .core import (
    CryptoError,
    FileMetadata,
    StreamProcessor,
    compute_key_commitment,
    decrypt_file,
    decrypt_text,
    derive_key,
    encrypt_file,
    encrypt_text,
    verify_key_commitment,
)
from .passphrase_generator import generate_passphrase
from .passphrase_manager import PassphraseVault
from .secure_memory import SecureBytes, SecureString, has_secure_memory, secure_wipe
from .security import SecurityError
from .timing_safe import (
    add_timing_jitter,
    check_password_strength,
    constant_time_compare,
)
from .utils import ProgressBar, colorize, handle_timeout, secure_overwrite

__version__ = "1.0.22"
__author__ = "TheRedTower"
__email__ = "security@avondenecloud.uk"

__all__ = [
    # Encryption
    "encrypt_text",
    "decrypt_text",
    "encrypt_file",
    "decrypt_file",
    "derive_key",
    "StreamProcessor",
    "FileMetadata",
    # Key commitment
    "compute_key_commitment",
    "verify_key_commitment",
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
    "has_secure_memory",
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
