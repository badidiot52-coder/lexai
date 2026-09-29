import pytest

from lexai.config import BrainConfig, ConfigError, IntegrationsConfig, load_integrations_config


class TestBrainConfig:
    def test_reads_env(self):
        cfg = BrainConfig.from_env({
            "LEXAI_API_BASE": "https://api.example.com/v1/",
            "LEXAI_API_KEY": "sk-test",
            "LEXAI_MODEL": "test-model",
        })
        assert cfg.api_base == "https://api.example.com/v1"
        assert cfg.api_key == "sk-test"
        assert cfg.model == "test-model"

    @pytest.mark.parametrize("missing", ["LEXAI_API_BASE", "LEXAI_API_KEY", "LEXAI_MODEL"])
    def test_missing_var_raises(self, missing):
        env = {
            "LEXAI_API_BASE": "https://api.example.com/v1",
            "LEXAI_API_KEY": "sk-test",
            "LEXAI_MODEL": "test-model",
        }
        env.pop(missing)
        with pytest.raises(ConfigError) as exc:
            BrainConfig.from_env(env)
        assert missing in str(exc.value)

    def test_missing_error_lists_all_missing(self):
        with pytest.raises(ConfigError) as exc:
            BrainConfig.from_env({})
        assert "LEXAI_API_BASE" in str(exc.value)
        assert "LEXAI_API_KEY" in str(exc.value)
        assert "LEXAI_MODEL" in str(exc.value)

    def test_blank_var_counts_as_missing(self):
        with pytest.raises(ConfigError):
            BrainConfig.from_env({"LEXAI_API_BASE": "  ", "LEXAI_API_KEY": "k", "LEXAI_MODEL": "m"})


def _write_yaml(tmp_path, text):
    path = tmp_path / "integrations.yaml"
    path.write_text(text, encoding="utf-8")
    return path


class TestIntegrationsConfig:
    def test_missing_file_is_empty(self, tmp_path):
        cfg = IntegrationsConfig.load(tmp_path / "nope.yaml")
        assert cfg.entries == {}

    def test_empty_integrations(self, tmp_path):
        cfg = IntegrationsConfig.load(_write_yaml(tmp_path, "integrations: {}"))
        assert cfg.entries == {}

    def test_declared_integrations(self, tmp_path):
        cfg = IntegrationsConfig.load(_write_yaml(tmp_path, """
integrations:
  gmail:
    scopes: [read, send]
  calendar:
"""))
        assert cfg.entries["gmail"] == {"scopes": ["read", "send"]}
        assert cfg.entries["calendar"] == {}

    def test_invalid_yaml_raises(self, tmp_path):
        with pytest.raises(ConfigError):
            IntegrationsConfig.load(_write_yaml(tmp_path, "integrations: [unclosed"))

    def test_non_mapping_top_level_raises(self, tmp_path):
        with pytest.raises(ConfigError):
            IntegrationsConfig.load(_write_yaml(tmp_path, "- just\n- a\n- list\n"))

    def test_non_mapping_integration_value_raises(self, tmp_path):
        with pytest.raises(ConfigError):
            IntegrationsConfig.load(_write_yaml(tmp_path, "integrations:\n  gmail: not-a-mapping\n"))

    def test_load_integrations_config_uses_project_root(self, tmp_path):
        cfg = load_integrations_config(tmp_path)
        assert cfg.entries == {}