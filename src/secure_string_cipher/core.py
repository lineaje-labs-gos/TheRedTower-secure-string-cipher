"""
Core encryption functionality for secure-string-cipher
"""

from __future__ import annotations

import base64
import io
import json
import os
import secrets
from dataclasses import dataclass
from typing import BinaryIO

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import (
    Cipher,
    algorithms,
    modes,
)
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .config import (
    CHUNK_SIZE,
    FILENAME_MAX_LENGTH,
    KDF_ITERATIONS,
    MAX_FILE_SIZE,
    METADATA_MAGIC,
    NONCE_SIZE,
    SALT_SIZE,
    TAG_SIZE,
)
from .utils import CryptoError, ProgressBar

__all__ = [
    "StreamProcessor",
    "CryptoError",
    "derive_key",
    "encrypt_text",
    "decrypt_text",
    "encrypt_stream",
    "decrypt_stream",
    "encrypt_file",
    "decrypt_file",
    # v2 functions with metadata support
    "encrypt_file_v2",
    "decrypt_file_v2",
    "FileMetadata",
]


class InMemoryStreamProcessor:
    """Stream processor for in-memory data like strings."""

    def __init__(self, stream: io.BytesIO, mode: str):
        """Initialize with a BytesIO stream."""
        self.stream = stream
        self.mode = mode

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)

    def write(self, data: bytes) -> int:
        return self.stream.write(data)

    def tell(self) -> int:
        return self.stream.tell()

    def seek(self, pos: int, whence: int = 0) -> int:
        return self.stream.seek(pos, whence)


class StreamProcessor:
    """Context manager for secure file operations with progress tracking."""

    def __init__(self, path: str, mode: str):
        """
        Initialize a secure file stream processor.

        Args:
            path: Path to the file to process
            mode: File mode ('rb' for read, 'wb' for write)

        Raises:
            CryptoError: If file operations fail or security checks fail
        """
        self.path = path
        self.mode = mode
        self.file: BinaryIO | None = None
        self._progress: ProgressBar | None = None
        self.bytes_processed = 0

        if isinstance(path, (str, bytes, os.PathLike)):
            # Security check for large files
            if mode == "rb" and os.path.exists(path):
                size = os.path.getsize(path)
                if size > MAX_FILE_SIZE:
                    raise CryptoError(
                        f"File too large. Maximum size is {MAX_FILE_SIZE / (1024 * 1024):.1f} MB"
                    )

    def _check_path(self) -> None:
        """
        Validate file path and prevent unsafe operations.

        Raises:
            CryptoError: If path is unsafe or permissions are incorrect
        """
        if self.mode == "wb":
            if os.path.exists(self.path):
                ans = input(
                    f"\nWarning: {self.path} exists. Overwrite? [y/N]: "
                ).lower()
                if ans not in ("y", "yes"):
                    raise CryptoError("Operation cancelled")

            try:
                directory = os.path.dirname(self.path) or "."
                test_file = os.path.join(directory, ".write_test")
                with open(test_file, "wb") as f:
                    f.write(b"test")
                os.unlink(test_file)
            except OSError as e:
                raise CryptoError(f"Cannot write to directory: {e}") from e

    def __enter__(self) -> StreamProcessor:
        """
        Open file and setup progress tracking.

        Returns:
            Self for context manager use

        Raises:
            CryptoError: If file operations fail
        """
        if isinstance(self.path, (str, bytes, os.PathLike)):
            self._check_path()
            try:
                self.file = open(self.path, self.mode)  # type: ignore[assignment]
            except OSError as e:
                raise CryptoError(f"Failed to open file: {e}") from e

            # Setup progress bar for reading
            if self.mode == "rb":
                try:
                    size = os.path.getsize(self.path)
                    self._progress = ProgressBar(size)
                except OSError:
                    pass  # Skip progress if we can't get file size
        else:
            self.file = self.path

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up file handle."""
        if self.file:
            self.file.close()

    def read(self, size: int = -1) -> bytes:
        """
        Read with progress tracking.

        Args:
            size: Number of bytes to read, -1 for all

        Returns:
            Bytes read from file

        Raises:
            CryptoError: If read fails
        """
        if not self.file:
            raise CryptoError("File not open")
        data = self.file.read(size)
        self.bytes_processed += len(data)
        if self._progress:
            self._progress.update(self.bytes_processed)
        return data

    def write(self, data: bytes) -> int:
        """
        Write with progress tracking.

        Args:
            data: Bytes to write

        Returns:
            Number of bytes written

        Raises:
            CryptoError: If write fails
        """
        if not self.file:
            raise CryptoError("File not open")
        try:
            n = self.file.write(data)
            self.bytes_processed += n
            return n
        except OSError as e:
            raise CryptoError(f"Write failed: {e}") from e


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """
    Derive encryption key from passphrase using PBKDF2.

    Args:
        passphrase: User-provided password
        salt: Random salt for key derivation

    Returns:
        32-byte key suitable for AES-256

    Raises:
        CryptoError: If key derivation fails
    """
    from .secure_memory import SecureBytes, SecureString

    try:
        with SecureString(passphrase) as secure_pass:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=KDF_ITERATIONS,
                backend=default_backend(),
            )
            with SecureBytes(secure_pass.string.encode()) as secure_bytes:
                return kdf.derive(secure_bytes.data)
    except Exception as e:
        raise CryptoError(f"Key derivation failed: {e}") from e


def encrypt_stream(r: StreamProcessor, w: StreamProcessor, passphrase: str) -> None:
    """
    Encrypt a file stream using AES-256-GCM.

    Args:
        r: Input stream processor
        w: Output stream processor
        passphrase: Encryption password

    Raises:
        CryptoError: If encryption fails
    """
    from .secure_memory import SecureBytes
    from .timing_safe import add_timing_jitter

    try:
        salt = secrets.token_bytes(SALT_SIZE)
        nonce = secrets.token_bytes(NONCE_SIZE)

        with SecureBytes(derive_key(passphrase, salt)) as secure_key:
            w.write(salt + nonce)
            encryptor = Cipher(
                algorithms.AES(secure_key.data),
                modes.GCM(nonce),
                backend=default_backend(),
            ).encryptor()

            for chunk in iter(lambda: r.read(CHUNK_SIZE), b""):
                w.write(encryptor.update(chunk))
                add_timing_jitter()

            w.write(encryptor.finalize() + encryptor.tag)
    except Exception as e:
        raise CryptoError(f"Encryption failed: {e}") from e


def decrypt_stream(r: StreamProcessor, w: StreamProcessor, passphrase: str) -> None:
    """
    Decrypt a file stream using AES-256-GCM.

    Args:
        r: Input stream processor
        w: Output stream processor
        passphrase: Decryption password

    Raises:
        CryptoError: If decryption fails or data is corrupted
    """
    try:
        header = r.read(SALT_SIZE + NONCE_SIZE)
        if len(header) != SALT_SIZE + NONCE_SIZE:
            raise CryptoError("Invalid encrypted file format")

        salt, nonce = header[:SALT_SIZE], header[SALT_SIZE:]
        data = r.read()

        if len(data) < TAG_SIZE:
            raise CryptoError("File too short - not a valid encrypted file")

        tag = data[-TAG_SIZE:]
        ciphertext = data[:-TAG_SIZE]
        key = derive_key(passphrase, salt)

        decryptor = Cipher(
            algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend()
        ).decryptor()

        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        w.write(plaintext)
    except CryptoError:
        raise
    except Exception as e:
        raise CryptoError(f"Decryption failed: {e}") from e


def encrypt_text(text: str, passphrase: str) -> str:
    """
    Encrypt text using AES-256-GCM.

    Args:
        text: Text to encrypt
        passphrase: Encryption password

    Returns:
        Base64-encoded encrypted text
    """
    ri = io.BytesIO(text.encode("utf-8"))
    wi = io.BytesIO()

    try:
        # Use in-memory processors to avoid closing the BytesIO buffers
        r = InMemoryStreamProcessor(ri, "rb")
        w = InMemoryStreamProcessor(wi, "wb")
        encrypt_stream(r, w, passphrase)  # type: ignore[arg-type]

        wi.seek(0)
        encrypted = wi.getvalue()
        return base64.b64encode(encrypted).decode("ascii")
    except Exception as e:
        raise CryptoError(f"Text encryption failed: {e}") from e
    finally:
        try:
            ri.close()
        except Exception:  # nosec B110
            pass  # BytesIO close errors can be safely ignored
        try:
            wi.close()
        except Exception:  # nosec B110
            pass  # BytesIO close errors can be safely ignored


def decrypt_text(token: str, passphrase: str) -> str:
    """
    Decrypt text using AES-256-GCM.

    Args:
        token: Base64-encoded encrypted text
        passphrase: Decryption password

    Returns:
        Decrypted text

    Raises:
        CryptoError: If decryption fails
    """
    try:
        encrypted = base64.b64decode(token)
    except ValueError:
        # Wrap base64 errors to provide a consistent decryption error message
        raise CryptoError("Text decryption failed") from None

    ri = io.BytesIO(encrypted)
    wi = io.BytesIO()

    try:
        r = InMemoryStreamProcessor(ri, "rb")
        w = InMemoryStreamProcessor(wi, "wb")
        decrypt_stream(r, w, passphrase)  # type: ignore[arg-type]
        wi.seek(0)
        result = wi.getvalue().decode("utf-8", "ignore")
        return result
    except Exception as e:
        raise CryptoError(f"Text decryption failed: {e}") from e
    finally:
        ri.close()
        wi.close()


def encrypt_file(input_path: str, output_path: str, passphrase: str) -> None:
    """
    Encrypt a file using AES-256-GCM.

    Args:
        input_path: Path to file to encrypt
        output_path: Path for encrypted output
        passphrase: Encryption password

    Raises:
        CryptoError: If encryption fails
    """
    with (
        StreamProcessor(input_path, "rb") as r,
        StreamProcessor(output_path, "wb") as w,
    ):
        encrypt_stream(r, w, passphrase)


def decrypt_file(input_path: str, output_path: str, passphrase: str) -> None:
    """
    Decrypt a file using AES-256-GCM.

    Args:
        input_path: Path to encrypted file
        output_path: Path for decrypted output
        passphrase: Decryption password

    Raises:
        CryptoError: If decryption fails
    """
    with (
        StreamProcessor(input_path, "rb") as r,
        StreamProcessor(output_path, "wb") as w,
    ):
        decrypt_stream(r, w, passphrase)


# =============================================================================
# v2 File Format with Metadata Support
# =============================================================================
#
# Format: MAGIC(5) + META_LEN(2 big-endian) + META_JSON + SALT(16) + NONCE(12) + CIPHERTEXT + TAG(16)
#
# The metadata JSON contains:
#   - original_filename: The original filename before encryption
#   - version: Metadata format version (currently 2)
#
# Legacy v1 files (without MAGIC header) are auto-detected and supported.
# =============================================================================


@dataclass
class FileMetadata:
    """Metadata stored with encrypted files."""

    original_filename: str | None = None
    version: int = 2

    def to_bytes(self) -> bytes:
        """Serialize metadata to JSON bytes."""
        data: dict[str, str | int] = {
            "version": self.version,
        }
        if self.original_filename:
            # Truncate filename if too long
            data["original_filename"] = self.original_filename[:FILENAME_MAX_LENGTH]
        return json.dumps(data, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> FileMetadata:
        """Deserialize metadata from JSON bytes."""
        try:
            obj = json.loads(data.decode("utf-8"))
            return cls(
                original_filename=obj.get("original_filename"),
                version=obj.get("version", 2),
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise CryptoError(f"Invalid metadata format: {e}") from e


def encrypt_file_v2(
    input_path: str,
    output_path: str,
    passphrase: str,
    *,
    store_filename: bool = True,
) -> None:
    """
    Encrypt a file using AES-256-GCM with metadata support (v2 format).

    The v2 format stores optional metadata including the original filename,
    which can be restored during decryption.

    Args:
        input_path: Path to file to encrypt
        output_path: Path for encrypted output
        passphrase: Encryption password
        store_filename: If True, store original filename in metadata

    Raises:
        CryptoError: If encryption fails
    """
    from .secure_memory import SecureBytes
    from .timing_safe import add_timing_jitter

    # Build metadata
    metadata = FileMetadata(
        original_filename=os.path.basename(input_path) if store_filename else None,
        version=2,
    )
    meta_bytes = metadata.to_bytes()

    if len(meta_bytes) > 65535:
        raise CryptoError("Metadata too large")

    try:
        salt = secrets.token_bytes(SALT_SIZE)
        nonce = secrets.token_bytes(NONCE_SIZE)

        with SecureBytes(derive_key(passphrase, salt)) as secure_key:
            with (
                StreamProcessor(input_path, "rb") as r,
                StreamProcessor(output_path, "wb") as w,
            ):
                # Write v2 header: MAGIC + metadata length (2 bytes big-endian) + metadata
                w.write(METADATA_MAGIC)
                w.write(len(meta_bytes).to_bytes(2, "big"))
                w.write(meta_bytes)

                # Write encryption header
                w.write(salt + nonce)

                # Encrypt data
                encryptor = Cipher(
                    algorithms.AES(secure_key.data),
                    modes.GCM(nonce),
                    backend=default_backend(),
                ).encryptor()

                for chunk in iter(lambda: r.read(CHUNK_SIZE), b""):
                    w.write(encryptor.update(chunk))
                    add_timing_jitter()

                w.write(encryptor.finalize() + encryptor.tag)
    except CryptoError:
        raise
    except Exception as e:
        raise CryptoError(f"Encryption failed: {e}") from e


def decrypt_file_v2(
    input_path: str,
    output_path: str | None,
    passphrase: str,
    *,
    restore_filename: bool = True,
) -> tuple[str, FileMetadata | None]:
    """
    Decrypt a file using AES-256-GCM with metadata support.

    Automatically detects v1 (legacy) and v2 file formats.

    Args:
        input_path: Path to encrypted file
        output_path: Path for decrypted output (if None, uses original filename or input_path + ".dec")
        passphrase: Decryption password
        restore_filename: If True and output_path is None, attempt to restore original filename

    Returns:
        Tuple of (actual_output_path, metadata_or_none)

    Raises:
        CryptoError: If decryption fails
    """
    from .security import sanitize_filename

    try:
        with open(input_path, "rb") as f:
            # Check for v2 magic header
            magic = f.read(len(METADATA_MAGIC))

            if magic == METADATA_MAGIC:
                # v2 format with metadata
                meta_len_bytes = f.read(2)
                if len(meta_len_bytes) != 2:
                    raise CryptoError("Invalid v2 file: truncated metadata length")
                meta_len = int.from_bytes(meta_len_bytes, "big")

                if meta_len > 65535:
                    raise CryptoError("Invalid v2 file: metadata too large")

                meta_bytes = f.read(meta_len)
                if len(meta_bytes) != meta_len:
                    raise CryptoError("Invalid v2 file: truncated metadata")

                metadata = FileMetadata.from_bytes(meta_bytes)

                # Read encryption header
                header = f.read(SALT_SIZE + NONCE_SIZE)
                if len(header) != SALT_SIZE + NONCE_SIZE:
                    raise CryptoError("Invalid encrypted file format")

                salt, nonce = header[:SALT_SIZE], header[SALT_SIZE:]
                encrypted_data = f.read()

            else:
                # v1 format (legacy) - magic is actually start of salt
                metadata = None
                header = magic + f.read(SALT_SIZE + NONCE_SIZE - len(magic))
                if len(header) != SALT_SIZE + NONCE_SIZE:
                    raise CryptoError("Invalid encrypted file format")

                salt, nonce = header[:SALT_SIZE], header[SALT_SIZE:]
                encrypted_data = f.read()

        # Determine output path
        if output_path is None:
            if restore_filename and metadata and metadata.original_filename:
                # Sanitize the stored filename for security
                safe_name = sanitize_filename(metadata.original_filename)
                # Use sanitized name if it's valid (not empty after sanitization)
                if safe_name:
                    # Use the sanitized original filename in the same directory as input
                    output_dir = os.path.dirname(input_path) or "."
                    output_path = os.path.join(output_dir, safe_name)
                else:
                    # Fallback if filename is empty after sanitization
                    output_path = input_path + ".dec"
            else:
                output_path = input_path + ".dec"

        # Decrypt
        if len(encrypted_data) < TAG_SIZE:
            raise CryptoError("File too short - not a valid encrypted file")

        tag = encrypted_data[-TAG_SIZE:]
        ciphertext = encrypted_data[:-TAG_SIZE]
        key = derive_key(passphrase, salt)

        decryptor = Cipher(
            algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend()
        ).decryptor()

        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        with StreamProcessor(output_path, "wb") as w:
            w.write(plaintext)

        return output_path, metadata

    except CryptoError:
        raise
    except Exception as e:
        raise CryptoError(f"Decryption failed: {e}") from e
