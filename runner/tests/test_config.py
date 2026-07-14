import pytest

from ceops_runner.config import RunnerConfig


def _cfg(**over):
    env = {"CEOPS_RUNNER_PORT": "8799", "CEOPS_ALLOWED_ORIGINS": "https://experiment.ceops.org"}
    env.update(over)
    return RunnerConfig.from_env(env)


def test_refuses_wildcard_bind():
    with pytest.raises(SystemExit):
        _cfg(CEOPS_RUNNER_BIND="0.0.0.0")


def test_refuses_ipv6_wildcard_bind():
    with pytest.raises(SystemExit):
        _cfg(CEOPS_RUNNER_BIND="::")


def test_refuses_public_bind():
    with pytest.raises(SystemExit):
        _cfg(CEOPS_RUNNER_BIND="8.8.8.8")


def test_accepts_loopback():
    cfg = _cfg(CEOPS_RUNNER_BIND="127.0.0.1")
    assert not cfg.lan_bound
    assert "127.0.0.1:8799" in cfg.host_allowlist
    assert "[::1]:8799" in cfg.host_allowlist


def test_accepts_private_lan_and_derives_authority():
    cfg = _cfg(CEOPS_RUNNER_BIND="192.168.1.200")
    assert cfg.lan_bound
    assert "192.168.1.200:8799" in cfg.host_allowlist
    assert "http://192.168.1.200:8799" in cfg.local_origins
    assert "http://192.168.1.200:8799" in cfg.allowed_origins


def test_public_and_local_ui_origins_allowed():
    cfg = _cfg(CEOPS_RUNNER_BIND="127.0.0.1")
    assert "https://experiment.ceops.org" in cfg.allowed_origins
    assert "http://127.0.0.1:8799" in cfg.allowed_origins
