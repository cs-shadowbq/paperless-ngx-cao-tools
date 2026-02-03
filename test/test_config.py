"""
Test configuration module.
"""


from src.pngx_cao.config import PaperlessConfig, get_config


class TestConfigDefaults:
    """Test default configuration values."""

    def test_default_values(self):
        """Test that PaperlessConfig has sensible defaults."""
        config = PaperlessConfig(url="http://test.local", token="test-token")

        assert config.url == "http://test.local"
        assert config.token == "test-token"
        assert config.skip_ssl_verify is False
        assert config.duplicate_handling == "skip"


class TestConfigValidation:
    """Test configuration validation."""

    def test_ssl_verification_flag(self):
        """Test SSL verification flag."""
        config = PaperlessConfig(url="http://test.local", token="test", skip_ssl_verify=True)
        assert config.skip_ssl_verify is True

        config = PaperlessConfig(url="http://test.local", token="test", skip_ssl_verify=False)
        assert config.skip_ssl_verify is False

    def test_duplicate_handling(self):
        """Test duplicate handling configuration."""
        config = PaperlessConfig(url="http://test.local", token="test", duplicate_handling="overwrite")
        assert config.duplicate_handling == "overwrite"


class TestGetConfig:
    """Test get_config function."""

    def test_get_config_returns_config_object(self, monkeypatch):
        """Test that get_config returns a PaperlessConfig instance."""
        # Set required environment variables for the test
        monkeypatch.setenv("PAPERLESS_URL", "http://test.local")
        monkeypatch.setenv("PAPERLESS_TOKEN", "test-token")

        config = get_config()
        assert isinstance(config, PaperlessConfig)
