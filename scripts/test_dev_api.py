"""No-provider regression checks for local startup configuration."""

import importlib.util
import os
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("dev_api", Path(__file__).with_name("dev-api.py"))
assert spec is not None and spec.loader is not None
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_local_file_replaces_inherited_settings_and_omissions(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "environ", {
        "PATH": "keep-system-path", "OPENAI_API_KEY": "old-test-key",
        "OPENAI_BASE_URL": "https://unused.invalid", "DATABASE_URL": "old-database",
        "SOURCEPILOT_AI_MODEL": "old-model",
    })
    (tmp_path / ".env.example").write_text("OPENAI_API_KEY=\nDATABASE_URL=\n")
    (tmp_path / ".env").write_text('OPENAI_API_KEY="local-test-key"\n')
    launcher.load_local_environment(tmp_path)
    assert os.environ == {"PATH": "keep-system-path", "OPENAI_API_KEY": "local-test-key"}


def test_missing_file_does_not_fall_back_to_inherited_key(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "environ", {"OPENAI_API_KEY": "old-test-key"})
    with pytest.raises(SystemExit, match="Create the repository root .env"):
        launcher.load_local_environment(tmp_path)
