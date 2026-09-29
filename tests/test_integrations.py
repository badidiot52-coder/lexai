import pytest

from lexai.config import IntegrationsConfig
from lexai.integrations import (
    Integration,
    IntegrationRegistry,
    get_registry,
    reset_registry,
)


class FakeIntegration(Integration):
    name = "fake"
    description = "test double"

    def __init__(self, config=None):
        super().__init__(config)
        self.set_up = False
        self.torn_down = False

    def setup(self):
        self.set_up = True

    def teardown(self):
        self.torn_down = True


class OtherIntegration(Integration):
    name = "other"

    def setup(self):
        pass

    def teardown(self):
        pass



@pytest.fixture(autouse=True)
def fresh_registry():
    reg = reset_registry()
    yield reg
    reset_registry()


class TestRegistry:
    def test_starts_empty(self):
        reg = get_registry()
        assert reg.registered_names() == []
        assert reg.active_names() == []
        assert reg.declared_names() == []

    def test_register_and_lookup(self):
        reg = get_registry()
        reg.register(FakeIntegration)
        assert reg.is_registered("fake")
        assert reg.registered_names() == ["fake"]

    def test_duplicate_register_rejected(self):
        reg = get_registry()
        reg.register(FakeIntegration)
        with pytest.raises(ValueError):
            reg.register(FakeIntegration)

    def test_subclass_without_name_rejected(self):
        with pytest.raises(TypeError):
            class NoName(Integration):
                def setup(self):
                    pass

                def teardown(self):
                    pass

    def test_declare_and_activate(self):
        reg = get_registry()
        reg.register(FakeIntegration)
        reg.declare("fake", {"scopes": ["read"]})
        assert reg.declared_names() == ["fake"]
        instance = reg.activate("fake")
        assert isinstance(instance, FakeIntegration)
        assert instance.set_up is True
        assert instance.config == {"scopes": ["read"]}
        assert reg.get("fake") is instance
        assert reg.active_names() == ["fake"]

    def test_activate_idempotent(self):
        reg = get_registry()
        reg.register(FakeIntegration)
        first = reg.activate("fake")
        assert reg.activate("fake") is first

    def test_activate_unregistered_raises(self):
        with pytest.raises(KeyError):
            get_registry().activate("gmail")

    def test_unregister(self):
        reg = get_registry()
        reg.register(FakeIntegration)
        reg.declare("fake", {})
        reg.unregister("fake")
        assert not reg.is_registered("fake")
        assert reg.declared_names() == ["fake"]

    def test_integration_config_default_empty(self):
        reg = get_registry()
        reg.register(FakeIntegration)
        instance = reg.activate("fake")
        assert instance.config == {}

    def test_status_string(self):
        assert FakeIntegration().status() == "fake: ready"


class TestConfigWiring:
    def test_yaml_names_can_be_declared(self, tmp_path):
        (tmp_path / "integrations.yaml").write_text(
            "integrations:\n  gmail: {}\n  calendar: {}\n", encoding="utf-8"
        )
        cfg = IntegrationsConfig.load(tmp_path / "integrations.yaml")
        reg = get_registry()
        for name, config in cfg.entries.items():
            reg.declare(name, config)
        assert reg.declared_names() == ["calendar", "gmail"]
        assert reg.registered_names() == []