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


def _two_vaults(tmp_path):
    a, b = tmp_path / "vault-a", tmp_path / "vault-b"
    a.mkdir()
    b.mkdir()
    conf = tmp_path / "c.toml"
    conf.write_text(f'vault_root = "{a}"\nvault_name = "Registered-A"\n')
    return a, b, conf


def test_configured_name_not_used_for_overridden_root(tmp_path):
    # Issue #1: the name registered for vault-a must not follow --vault / env
    a, b, conf = _two_vaults(tmp_path)
    assert resolve_vault(str(b), {}, conf).name == "vault-b"
    assert resolve_vault(None, {"OBSIDIAN_VAULT_ROOT": str(b)}, conf).name == "vault-b"


def test_configured_name_kept_for_the_configured_root(tmp_path):
    a, b, conf = _two_vaults(tmp_path)
    assert resolve_vault(None, {}, conf).name == "Registered-A"
    assert resolve_vault(str(a), {}, conf).name == "Registered-A"


def test_same_root_in_other_notation(tmp_path):
    a, b, conf = _two_vaults(tmp_path)
    link = tmp_path / "link-to-a"
    link.symlink_to(a)
    assert resolve_vault(f"{a}/", {}, conf).name == "Registered-A"
    assert resolve_vault(
        str(tmp_path / "vault-b" / ".." / "vault-a"), {}, conf
    ).name == ("Registered-A")
    assert resolve_vault(str(link), {}, conf).name == "Registered-A"


def test_name_override_order(tmp_path):
    a, b, conf = _two_vaults(tmp_path)
    env = {"OBSIDIAN_VAULT_NAME": "FromEnv"}
    assert resolve_vault(str(b), env, conf).name == "FromEnv"
    assert resolve_vault(str(b), env, conf, cli_name="FromCli").name == "FromCli"
    assert resolve_vault(None, env, conf).name == "FromEnv"  # env beats config
