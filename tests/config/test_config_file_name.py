"""Tests for the config file name constant."""

from wiggum.config import CONFIG_FILE


class TestConfigFileName:
    """Tests for CONFIG_FILE constant."""

    def test_config_file_is_wiggum_toml(self) -> None:
        """CONFIG_FILE should be .wiggum.toml (not .ralph-loop.toml)."""
        assert CONFIG_FILE == ".wiggum.toml"
