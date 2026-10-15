import pytest

from zotero_paper_tools.config import ConfigError, resolve_vault


def test_order_cli_env_config(tmp_path):
    cli, env, cfg = (tmp_path / n for n in ("cli", "env", "cfg"))
    for d in (cli, env, cfg):
        d.mkdir()
    conf = tmp_path / "c.toml"
    conf.write_text(f'vault_root = "{cfg}"\nvault_name = "my-vault"\n')
    e = {"OBSIDIAN_VAULT_ROOT": str(env)}
    assert resolve_vault(str(cli), e, conf).root == cli
    assert resolve_vault(None, e, conf).root == env
    v = resolve_vault(None, {}, conf)
    assert (v.root, v.name) == (cfg, "my-vault")


def test_name_defaults_to_dir_name(tmp_path):
    d = tmp_path / "vault"
    d.mkdir()
    assert resolve_vault(str(d), {}, tmp_path / "none.toml").name == "vault"


def test_unresolved_stops(tmp_path):
    with pytest.raises(ConfigError):
        resolve_vault(None, {}, tmp_path / "none.toml")


def test_missing_dir_stops(tmp_path):
    with pytest.raises(ConfigError):
        resolve_vault(str(tmp_path / "nope"), {}, tmp_path / "none.toml")


def test_invalid_toml(tmp_path):
    conf = tmp_path / "c.toml"
    conf.write_text("vault_root = ")
    with pytest.raises(ConfigError):
        resolve_vault(None, {}, conf)
