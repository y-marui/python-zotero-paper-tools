"""Personal settings and vault resolution.

The vault location is resolved in the same order as ``obsidian-project-home``:
``--vault``, the ``OBSIDIAN_VAULT_ROOT`` environment variable, then the config
file. If none yields an existing directory, resolution fails.

The vault name (used in ``obsidian://`` links) is resolved separately:
``--vault-name``, ``OBSIDIAN_VAULT_NAME``, the config ``vault_name`` (only when
the selected root is the config's ``vault_root``), then the root's directory
name. A name configured for another root is never used silently.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ENV_VAULT = "OBSIDIAN_VAULT_ROOT"
ENV_VAULT_NAME = "OBSIDIAN_VAULT_NAME"
ENV_CONFIG = "ZOTERO_PAPER_TOOLS_CONFIG"


class ConfigError(Exception):
    """Raised when the vault or config cannot be resolved."""


@dataclass(frozen=True)
class Vault:
    root: Path
    name: str


def config_path(env: Mapping[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    if env.get(ENV_CONFIG):
        return Path(env[ENV_CONFIG]).expanduser()
    base = env.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "zotero-paper-tools" / "config.toml"


def _read_config(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"invalid config file {path}: {e}") from e


def resolve_vault(
    cli_vault: str | None = None,
    env: dict[str, str] | None = None,
    config_file: Path | None = None,
    cli_name: str | None = None,
) -> Vault:
    env = dict(os.environ) if env is None else env
    path = config_file if config_file is not None else config_path(env)
    config = _read_config(path)

    config_root = _to_root(config.get("vault_root"))
    raw: object
    if cli_vault:
        raw = cli_vault
    elif env.get(ENV_VAULT):
        raw = env[ENV_VAULT]
    else:
        raw = config.get("vault_root") if config_root is not None else None
    if not isinstance(raw, str) or not raw:
        raise ConfigError(
            f"vault is not configured: use --vault, ${ENV_VAULT}, "
            f"or vault_root in {path}"
        )

    root = _to_root(raw)
    if root is None or not root.is_dir():
        raise ConfigError(f"vault directory does not exist: {root}")

    name = cli_name or env.get(ENV_VAULT_NAME)
    if not name:
        configured = config.get("vault_name")
        if (
            isinstance(configured, str)
            and configured
            and config_root is not None
            and _same_dir(root, config_root)
        ):
            name = configured
    return Vault(root=root, name=name or root.name)


def _to_root(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    root = Path(value).expanduser()
    return root if root.is_absolute() else Path.home() / root


def _same_dir(a: Path, b: Path) -> bool:
    return os.path.realpath(a) == os.path.realpath(b)
