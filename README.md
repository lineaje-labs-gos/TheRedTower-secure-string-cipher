# secure-string-cipher

[![CI](https://github.com/TheRedTower/secure-string-cipher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/TheRedTower/secure-string-cipher/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)

A security-focused AES-256-GCM encryption CLI tool with passphrase vault and modern cryptographic defaults.

## Features

- **AES-256-GCM encryption** for text and files with authenticated encryption
- **Argon2id key derivation** – memory-hard, GPU/ASIC resistant
- **Key commitment scheme** – prevents partitioning oracle attacks
- **Hidden password input** – passwords hidden in interactive terminals, visible for scripts/tests
- **Inline passphrase generation** – type `/gen` at any password prompt
- **Encrypted passphrase vault** with HMAC-SHA256 integrity verification
- **Secure memory handling** via libsodium (PyNaCl) when available
- **Timing-safe operations** – constant-time comparisons prevent side-channel attacks
- Chunked file streaming (64KB) for low memory usage
- Automatic vault backups (last 5 kept)

## Installation

```bash
# Recommended: install with pipx
pipx install secure-string-cipher

# Or with pip
pip install secure-string-cipher

# Or from source
git clone https://github.com/TheRedTower/secure-string-cipher.git
cd secure-string-cipher
pip install .
```

> Requires Python 3.12+

## Usage

Run the interactive CLI:

```bash
cipher-start
```

You'll see this menu:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                       AVAILABLE OPERATIONS                     ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                                ┃
┃  TEXT & FILE ENCRYPTION                                        ┃
┃                                                                ┃
┃    [1] Encrypt Text      →  Encrypt a message (base64 output)  ┃
┃    [2] Decrypt Text      →  Decrypt an encrypted message       ┃
┃    [3] Encrypt File      →  Encrypt a file (creates .enc)      ┃
┃    [4] Decrypt File      →  Decrypt an encrypted file          ┃
┃                                                                ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  PASSPHRASE VAULT (Optional)                                   ┃
┃                                                                ┃
┃    [5] Generate Passphrase  →  Create secure random password   ┃
┃    [6] Store in Vault       →  Save passphrase securely        ┃
┃    [7] Retrieve from Vault  →  Get stored passphrase           ┃
┃    [8] List Vault Entries   →  View all stored labels          ┃
┃    [9] Manage Vault         →  Update or delete entries        ┃
┃                                                                ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃    [0] Exit                →  Quit application                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

```

Choose an option and follow the prompts.

### Quick Passphrase Generation

When prompted for a password during encryption, you can type `/gen` (or `/generate` or `/g`) to instantly generate a strong passphrase:

```
Enter passphrase: /gen

🔑 Auto-Generating Secure Passphrase...

✅ Generated Passphrase:
8w@!-@_#M)wF,Qn(ms.Uv+3z

Entropy: 155.0 bits

💾 Store this passphrase in vault? (y/n) [n]: y
Enter a label for this passphrase: backup-2025
Enter master password to encrypt vault: ••••••••••••
✅ Passphrase 'backup-2025' stored in vault!

✅ Using this passphrase for current operation...
```

Generated passphrases have 155+ bits of entropy and can be stored directly in the encrypted vault.

### Passphrase Vault

The vault stores passphrases encrypted with your master password at `~/.secure-cipher/passphrase_vault.enc`:

- **Generate & store** – Option 5 or `/gen` during encryption
- **Manual storage** – Option 6 for existing passphrases
- **Retrieve/manage** – Options 7-9 for lookup, listing, and deletion

All vault operations use HMAC integrity verification and maintain automatic backups.

## Docker

Use the pre-built image (Python 3.14-alpine based):

```bash
# Pull and run
docker pull ghcr.io/theredtower/secure-string-cipher:latest
docker run --rm -it ghcr.io/theredtower/secure-string-cipher:latest

# Or with Docker Compose
git clone https://github.com/TheRedTower/secure-string-cipher.git
cd secure-string-cipher
docker compose up -d
docker compose exec cipher cipher-start
```

To encrypt files in your current directory:

```bash
docker run --rm -it \
  -v "$PWD:/data" \
  ghcr.io/theredtower/secure-string-cipher:latest
```

With persistent vault and backups:

```bash
docker run --rm -it \
  -v "$PWD/data:/data" \
  -v "$PWD/vault:/vault" \
  -v "$PWD/backups:/backups" \
  ghcr.io/theredtower/secure-string-cipher:latest
```

**Image details:** ~65MB Alpine-based, runs as non-root (UID 1000), network-isolated.

## Security

| Component | Implementation | Details |
|-----------|---------------|---------|
| **Encryption** | AES-256-GCM | Authenticated encryption, 128-bit tags |
| **Key Derivation** | Argon2id | 64MB memory, 3 iterations, parallelism 4 |
| **Key Commitment** | HMAC-SHA256 | Prevents partitioning oracle attacks |
| **Vault Integrity** | HMAC-SHA256 | Detects tampering before decryption |
| **Memory Security** | libsodium | `sodium_memzero()` via PyNaCl |
| **Timing Safety** | Constant-time | All password/hash comparisons |

**Additional protections:** Path traversal prevention, symlink attack detection, atomic writes, user-only file permissions (600), 12-character minimum password with complexity requirements.

**Password input:** When running interactively, passwords are hidden (using `getpass`). When stdin is piped or redirected (scripts, automation, tests), passwords are visible. This allows both secure interactive use and scriptable automation.

**Python memory limitations:** Even with libsodium, Python strings are immutable and GC may copy objects. Use `has_secure_memory()` to check libsodium availability.

## Development

```bash
git clone https://github.com/TheRedTower/secure-string-cipher.git
cd secure-string-cipher
pip install -e ".[dev]"

make format   # Auto-format with Ruff
make ci       # Run full CI pipeline (lint + type check + 353 tests)
```

See [DEVELOPER.md](DEVELOPER.md) for detailed development workflow and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT License. See [LICENSE](LICENSE) for details.
