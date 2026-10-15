"""Personal settings and vault resolution.

The vault location is resolved in the same order as ``obsidian-project-home``:
``--vault``, the ``OBSIDIAN_VAULT_ROOT`` environment variable, then the config
file. If none yields an existing directory, resolution fails.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

ENV_VAULT = "OBSIDIAN_VAULT_ROOT"
ENV_CONFIG = "ZOTERO_PAPER_TOOLS_CONFIG"


class ConfigError(Exception):
    """Raised when the vault or config cannot be resolved."""


@dataclass(frozen=True)
class Vault:
    root: Path
    name: str


def config_path(env: dict[str, str] | None = None) -> Path:
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
) -> Vault:
    env = dict(os.environ) if env is None else env
    path = config_file if config_file is not None else config_path(env)
    config = _read_config(path)

    if cli_vault:
        raw: str | None = cli_vault
    elif env.get(ENV_VAULT):
        raw = env[ENV_VAULT]
    else:
        value = config.get("vault_root")
        raw = value if isinstance(value, str) and value else None
    if raw is None:
        raise ConfigError(
            f"vault is not configured: use --vault, ${ENV_VAULT}, "
            f"or vault_root in {path}"
        )

    root = Path(raw).expanduser()
    if not root.is_absolute():
        root = Path.home() / root
    if not root.is_dir():
        raise ConfigError(f"vault directory does not exist: {root}")

    name = config.get("vault_name")
    return Vault(root=root, name=name if isinstance(name, str) and name else root.name)
