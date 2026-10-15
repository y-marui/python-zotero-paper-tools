"""Storage of the Zotero local API key in the macOS Keychain."""

from __future__ import annotations

import subprocess
import sys

SERVICE = "python-zotero-paper-tools"
ACCOUNT = "zotero-local-api"
_NOT_FOUND = 44  # errSecItemNotFound exit status of `security`


class KeystoreError(Exception):
    """Raised when the Keychain cannot be used."""


def _security(*args: str) -> subprocess.CompletedProcess[str]:
    if sys.platform != "darwin":
        raise KeystoreError("key storage needs the macOS Keychain (`security`)")
    try:
        return subprocess.run(
            ["security", *args], capture_output=True, text=True, check=False
        )
    except OSError as e:
        raise KeystoreError(f"cannot run `security`: {e}") from e


def load() -> str | None:
    r = _security("find-generic-password", "-s", SERVICE, "-a", ACCOUNT, "-w")
    if r.returncode == 0:
        return r.stdout.strip() or None
    if r.returncode == _NOT_FOUND:
        return None
    raise KeystoreError(f"Keychain read failed (exit {r.returncode})")


def save(key: str) -> None:
    # `security` only accepts the password as an argument (visible in `ps` for the
    # instant it runs); -U updates an existing item.
    r = _security("add-generic-password", "-U", "-s", SERVICE, "-a", ACCOUNT, "-w", key)
    if r.returncode != 0:
        raise KeystoreError(f"Keychain write failed (exit {r.returncode})")


def forget() -> bool:
    """Delete the stored key. Returns False if there was none."""
    r = _security("delete-generic-password", "-s", SERVICE, "-a", ACCOUNT)
    if r.returncode == 0:
        return True
    if r.returncode == _NOT_FOUND:
        return False
    raise KeystoreError(f"Keychain delete failed (exit {r.returncode})")
