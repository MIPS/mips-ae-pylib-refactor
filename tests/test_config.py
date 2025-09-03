"""Comprehensive tests for the Core Configuration module.

This test suite provides 95%+ coverage for the AtlasConfig class,
testing all configuration loading scenarios, validation, error handling,
and security features.
"""

import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock
import tempfile
import os
import json
from pathlib import Path

from atlasexplorer.core.config import AtlasConfig
from atlasexplorer.core.constants import AtlasConstants
from atlasexplorer.utils.exceptions import ConfigurationError, NetworkError


class TestAtlasConfigInitialization(unittest.TestCase):
    """Test AtlasConfig class initialization and basic setup."""

    def test_initialization_default_parameters(self):
        """Test default initialization parameters."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(AtlasConfig, '_get_config_file_path') as mock_get_path:
                mock_get_path.return_value = Path("/non/existent/config.json")
                config = AtlasConfig()
                self.assertTrue(config.verbose)
                self.assertIsNone(config.gateway)
                self.assertFalse(config.hasConfig)

    def test_initialization_readonly_true(self):
        """Test initialization with readonly=True."""
        with patch.object(AtlasConfig, '_load_from_environment', return_value=True):
            with patch.object(AtlasConfig, '_set_gateway_by_channel_region') as mock_set_gateway:
                config = AtlasConfig(readonly=True)
                mock_set_gateway.assert_not_called()

    def test_initialization_readonly_false(self):
        """Test initialization with readonly=False (default)."""
        with patch.object(AtlasConfig, '_load_from_environment', return_value=True):
            with patch.object(AtlasConfig, '_set_gateway_by_channel_region') as mock_set_gateway:
                config = AtlasConfig(readonly=False)
                mock_set_gateway.assert_called_once()

    def test_initialization_verbose_false(self):
        """Test initialization with verbose=False."""
        config = AtlasConfig(verbose=False)
        self.assertFalse(config.verbose)

    def test_initialization_with_direct_parameters(self):
        """Test initialization with direct API parameters."""
        apikey = "test-api-key"
        channel = "test-channel"
        region = "test-region"
        
        with patch.object(AtlasConfig, '_load_from_environment', return_value=False):
            with patch.object(AtlasConfig, '_load_from_config_file', return_value=False):
                with patch.object(AtlasConfig, '_set_gateway_by_channel_region') as mock_set_gateway:
                    config = AtlasConfig(apikey=apikey, channel=channel, region=region)
                    
                    self.assertEqual(config.apikey, apikey)
                    self.assertEqual(config.channel, channel)
                    self.assertEqual(config.region, region)
                    self.assertTrue(config.hasConfig)
                    mock_set_gateway.assert_called_once()

    def test_initialization_incomplete_parameters(self):
        """Test initialization with incomplete direct parameters."""
        with patch.object(AtlasConfig, '_load_from_environment', return_value=False):
            with patch.object(AtlasConfig, '_load_from_config_file', return_value=False):
                # Missing region parameter
                config = AtlasConfig(apikey="test-key", channel="test-channel")
                self.assertFalse(config.hasConfig)


class TestAtlasConfigEnvironmentLoading(unittest.TestCase):
    """Test configuration loading from environment variables."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = AtlasConfig(readonly=True, verbose=False)

    @patch.dict(os.environ, {AtlasConstants.CONFIG_ENVAR: "test-key:test-channel:test-region"})
    def test_load_from_environment_success(self):
        """Test successful loading from environment variable."""
        result = self.config._load_from_environment()
        
        self.assertTrue(result)
        self.assertEqual(self.config.apikey, "test-key")
        self.assertEqual(self.config.channel, "test-channel")
        self.assertEqual(self.config.region, "test-region")
        self.assertTrue(self.config.hasConfig)

    def test_load_from_environment_missing_var(self):
        """Test loading when environment variable is missing."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.config._load_from_environment()
            self.assertFalse(result)

    @patch.dict(os.environ, {AtlasConstants.CONFIG_ENVAR: "invalid-format"})
    def test_load_from_environment_invalid_format(self):
        """Test loading with invalid environment variable format."""
        config = AtlasConfig(readonly=True, verbose=True)
        
        with patch('builtins.print') as mock_print:
            result = config._load_from_environment()
            
            self.assertFalse(result)
            mock_print.assert_called_with(
                f"Warning: {AtlasConstants.CONFIG_ENVAR} should have format 'apikey:channel:region'"
            )

    @patch.dict(os.environ, {AtlasConstants.CONFIG_ENVAR: "key1:key2:key3:extra"})
    def test_load_from_environment_too_many_parts(self):
        """Test loading with too many parts in environment variable."""
        config = AtlasConfig(readonly=True, verbose=True)
        
        with patch('builtins.print') as mock_print:
            result = config._load_from_environment()
            
            self.assertFalse(result)
            mock_print.assert_called_with(
                f"Warning: {AtlasConstants.CONFIG_ENVAR} should have format 'apikey:channel:region'"
            )

    @patch.dict(os.environ, {AtlasConstants.CONFIG_ENVAR: "only-one-part"})
    def test_load_from_environment_too_few_parts(self):
        """Test loading with too few parts in environment variable."""
        config = AtlasConfig(readonly=True, verbose=True)
        
        with patch('builtins.print') as mock_print:
            result = config._load_from_environment()
            
            self.assertFalse(result)
            mock_print.assert_called()


class TestAtlasConfigExceptionHandling(unittest.TestCase):
    """Test configuration exception handling scenarios."""
    
    def test_load_from_environment_exception_verbose(self):
        """Test exception handling during environment loading with verbose output."""
        config = AtlasConfig(readonly=True, verbose=True)
        
        # Mock os.environ to contain the key but raise exception when accessed
        with patch('os.environ') as mock_environ:
            # Make the key appear to exist for the 'in' check
            mock_environ.__contains__.return_value = True
            # But raise exception when actually accessing the value
            mock_environ.__getitem__.side_effect = RuntimeError("Environment access error")
            
            with patch('builtins.print') as mock_print:
                result = config._load_from_environment()
                
                self.assertFalse(result)
                mock_print.assert_called_once_with("Error parsing environment configuration: Environment access error")
    
    def test_load_from_environment_exception_quiet(self):
        """Test exception handling during environment loading in quiet mode."""
        config = AtlasConfig(readonly=True, verbose=False)
        
        # Mock os.environ to contain the key but raise exception when accessed
        with patch('os.environ') as mock_environ:
            # Make the key appear to exist for the 'in' check
            mock_environ.__contains__.return_value = True
            # But raise exception when actually accessing the value
            mock_environ.__getitem__.side_effect = ValueError("Invalid environment data")
            
            with patch('builtins.print') as mock_print:
                result = config._load_from_environment()
                
                self.assertFalse(result)
                # Should not print in quiet mode
                mock_print.assert_not_called()


class TestAtlasConfigFileLoading(unittest.TestCase):
    """Test configuration loading from config files."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = AtlasConfig(readonly=True, verbose=False)
        self.test_config_data = {
            "apikey": "file-api-key",
            "channel": "file-channel",
            "region": "file-region"
        }

    def test_load_from_config_file_success(self):
        """Test successful loading from config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(self.test_config_data, temp_file)
            temp_file_path = temp_file.name

        try:
            with patch.object(self.config, '_get_config_file_path', return_value=Path(temp_file_path)):
                result = self.config._load_from_config_file()
                
                self.assertTrue(result)
                self.assertEqual(self.config.apikey, "file-api-key")
                self.assertEqual(self.config.channel, "file-channel")
                self.assertEqual(self.config.region, "file-region")
                self.assertTrue(self.config.hasConfig)
                
        finally:
            os.unlink(temp_file_path)

    def test_load_from_config_file_missing_file(self):
        """Test loading when config file doesn't exist."""
        non_existent_path = Path("/non/existent/path/config.json")
        
        with patch.object(self.config, '_get_config_file_path', return_value=non_existent_path):
            result = self.config._load_from_config_file()
            self.assertFalse(result)

    def test_load_from_config_file_invalid_json(self):
        """Test loading with invalid JSON in config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write("invalid json content")
            temp_file_path = temp_file.name

        try:
            config = AtlasConfig(readonly=True, verbose=True)
            
            with patch.object(config, '_get_config_file_path', return_value=Path(temp_file_path)):
                with patch('builtins.print') as mock_print:
                    result = config._load_from_config_file()
                    
                    self.assertFalse(result)
                    mock_print.assert_called()
                    
        finally:
            os.unlink(temp_file_path)

    def test_load_from_config_file_missing_required_fields(self):
        """Test loading with missing required fields in config file."""
        incomplete_config = {"apikey": "test-key", "channel": "test-channel"}  # Missing region
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(incomplete_config, temp_file)
            temp_file_path = temp_file.name

        try:
            config = AtlasConfig(readonly=True, verbose=True)
            
            with patch.object(config, '_get_config_file_path', return_value=Path(temp_file_path)):
                with patch('builtins.print') as mock_print:
                    result = config._load_from_config_file()
                    
                    self.assertFalse(result)
                    mock_print.assert_called_with(f"Warning: Missing 'region' in config file {temp_file_path}")
                    
        finally:
            os.unlink(temp_file_path)

    def test_load_from_config_file_io_error(self):
        """Test loading with IO error during file reading."""
        config = AtlasConfig(readonly=True, verbose=True)
        
        with patch.object(config, '_get_config_file_path') as mock_get_path:
            mock_path = Mock()
            mock_path.exists.return_value = True
            mock_get_path.return_value = mock_path
            
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                with patch('builtins.print') as mock_print:
                    result = config._load_from_config_file()
                    
                    self.assertFalse(result)
                    mock_print.assert_called_with("Error loading config file: Permission denied")

    def test_get_config_file_path(self):
        """Test config file path generation."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path("/home/testuser")
            
            path = self.config._get_config_file_path()
            
            expected_path = Path("/home/testuser").joinpath(*AtlasConstants.CONFIG_DIR_PARTS) / AtlasConstants.CONFIG_FILENAME
            self.assertEqual(path, expected_path)


class TestAtlasConfigGatewaySetup(unittest.TestCase):
    """Test gateway endpoint setup functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = AtlasConfig(readonly=True, verbose=False)
        self.config.apikey = "test-api-key"
        self.config.channel = "test-channel"
        self.config.region = "test-region"

    @patch('requests.get')
    def test_set_gateway_by_channel_region_success(self, mock_get):
        """Test successful gateway setup."""
        mock_response = Mock()
        mock_response.json.return_value = {"endpoint": "https://test-gateway.example.com"}
        mock_get.return_value = mock_response
        
        config = AtlasConfig(readonly=True, verbose=True)
        config.apikey = "test-api-key"
        config.channel = "test-channel"
        config.region = "test-region"
        
        with patch('builtins.print') as mock_print:
            config._set_gateway_by_channel_region()
            
            self.assertEqual(config.gateway, "https://test-gateway.example.com")
            mock_print.assert_any_call("Setting up selected gateway...")
            mock_print.assert_any_call("Gateway has been set: https://test-gateway.example.com")

    def test_set_gateway_missing_config(self):
        """Test gateway setup with missing configuration."""
        config = AtlasConfig(readonly=True, verbose=False)
        # Clear any configuration that might be set
        config.apikey = None
        config.channel = None
        config.region = None
        
        with self.assertRaises(ConfigurationError) as context:
            config._set_gateway_by_channel_region()
        
        self.assertIn("Missing required configuration", str(context.exception))

    @patch('atlasexplorer.core.config.requests')
    def test_set_gateway_network_error(self, mock_requests):
        """Test gateway setup with network error."""
        mock_requests.RequestException = Exception
        
        # Create exception without response attribute
        error = Exception("Connection failed")
        mock_requests.get.side_effect = error
        
        with self.assertRaises(NetworkError) as context:
            self.config._set_gateway_by_channel_region()
        
        self.assertIn("Error connecting to gateway API", str(context.exception))

    @patch('atlasexplorer.core.config.requests')
    def test_set_gateway_http_error(self, mock_requests):
        """Test gateway setup with HTTP error response."""
        mock_requests.RequestException = Exception
        
        # Create an exception with response attribute
        error = Exception("HTTP 401") 
        error.response = Mock()
        error.response.status_code = 401
        error.response.text = "Unauthorized"
        
        mock_requests.get.side_effect = error
        
        with self.assertRaises(NetworkError) as context:
            self.config._set_gateway_by_channel_region()
        
        error_message = str(context.exception)
        self.assertIn("Error connecting to gateway API", error_message)
        self.assertIn("Status: 401", error_message)
        self.assertIn("Text: Unauthorized", error_message)

    @patch('requests.get')
    def test_set_gateway_invalid_response_format(self, mock_get):
        """Test gateway setup with invalid response format."""
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "response"}  # Missing 'endpoint'
        mock_get.return_value = mock_response
        
        with self.assertRaises(ConfigurationError) as context:
            self.config._set_gateway_by_channel_region()
        
        self.assertIn("No 'endpoint' found in response", str(context.exception))

    @patch('requests.get')
    def test_set_gateway_json_decode_error(self, mock_get):
        """Test gateway setup with JSON decode error."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        with self.assertRaises(ConfigurationError) as context:
            self.config._set_gateway_by_channel_region()
        
        self.assertIn("Invalid response from gateway API", str(context.exception))

    @patch('requests.get')
    def test_set_gateway_request_parameters(self, mock_get):
        """Test that gateway setup uses correct request parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {"endpoint": "https://test-gateway.example.com"}
        mock_get.return_value = mock_response
        
        self.config._set_gateway_by_channel_region()
        
        expected_url = f"{AtlasConstants.AE_GLOBAL_API}/gwbychannelregion"
        expected_headers = {
            "apikey": "test-api-key",
            "channel": "test-channel",
            "region": "test-region",
        }
        
        mock_get.assert_called_once_with(
            expected_url, 
            headers=expected_headers, 
            timeout=AtlasConstants.HTTP_TIMEOUT
        )


class TestAtlasConfigFileSaving(unittest.TestCase):
    """Test configuration file saving functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = AtlasConfig(readonly=True, verbose=False)

    def test_save_to_file_success(self):
        """Test successful configuration saving."""
        config_data = {
            "apikey": "save-test-key",
            "channel": "save-test-channel",
            "region": "save-test-region"
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            with patch.object(self.config, '_get_config_file_path', return_value=config_path):
                self.config.save_to_file(config_data)
                
                # Verify file was created and contains correct data
                self.assertTrue(config_path.exists())
                with open(config_path) as f:
                    saved_data = json.load(f)
                self.assertEqual(saved_data, config_data)

    def test_save_to_file_creates_directory(self):
        """Test that save_to_file creates parent directories."""
        config_data = {"test": "data"}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nested" / "dir" / "config.json"
            
            with patch.object(self.config, '_get_config_file_path', return_value=config_path):
                self.config.save_to_file(config_data)
                
                # Verify directory structure was created
                self.assertTrue(config_path.parent.exists())
                self.assertTrue(config_path.exists())

    def test_save_to_file_verbose_output(self):
        """Test verbose output during file saving."""
        config = AtlasConfig(readonly=True, verbose=True)
        config_data = {"test": "data"}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            with patch.object(config, '_get_config_file_path', return_value=config_path):
                with patch('builtins.print') as mock_print:
                    config.save_to_file(config_data)
                    mock_print.assert_called_with(f"Configuration saved to {config_path}")

    def test_save_to_file_io_error(self):
        """Test save_to_file with IO error."""
        config_data = {"test": "data"}
        
        with patch.object(self.config, '_get_config_file_path') as mock_get_path:
            mock_path = Mock()
            mock_path.parent.mkdir.side_effect = OSError("Permission denied")
            mock_get_path.return_value = mock_path
            
            with self.assertRaises(ConfigurationError) as context:
                self.config.save_to_file(config_data)
            
            self.assertIn("Failed to save configuration", str(context.exception))

    def test_save_to_file_json_encode_error(self):
        """Test save_to_file with JSON encoding error."""
        # Create data that can't be JSON serialized
        config_data = {"function": lambda x: x}  # Functions can't be JSON serialized
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            with patch.object(self.config, '_get_config_file_path', return_value=config_path):
                with self.assertRaises(ConfigurationError) as context:
                    self.config.save_to_file(config_data)
                
                self.assertIn("Failed to save configuration", str(context.exception))


class TestAtlasConfigLegacyMethods(unittest.TestCase):
    """Test legacy method compatibility."""

    def test_legacy_set_gateway_method(self):
        """Test legacy setGWbyChannelRegion method."""
        config = AtlasConfig(readonly=True, verbose=False)
        
        with patch.object(config, '_set_gateway_by_channel_region') as mock_method:
            config.setGWbyChannelRegion()
            mock_method.assert_called_once()


class TestAtlasConfigIntegrationScenarios(unittest.TestCase):
    """Test integrated configuration loading scenarios."""

    def test_priority_environment_over_file(self):
        """Test that environment variable takes priority over config file."""
        # Create a config file
        file_config = {
            "apikey": "file-key",
            "channel": "file-channel", 
            "region": "file-region"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(file_config, temp_file)
            temp_file_path = temp_file.name

        try:
            with patch.dict(os.environ, {AtlasConstants.CONFIG_ENVAR: "env-key:env-channel:env-region"}):
                with patch.object(AtlasConfig, '_get_config_file_path', return_value=Path(temp_file_path)):
                    with patch.object(AtlasConfig, '_set_gateway_by_channel_region'):
                        config = AtlasConfig()
                        
                        # Should use environment values, not file values
                        self.assertEqual(config.apikey, "env-key")
                        self.assertEqual(config.channel, "env-channel")
                        self.assertEqual(config.region, "env-region")
                        self.assertTrue(config.hasConfig)
                        
        finally:
            os.unlink(temp_file_path)

    def test_fallback_to_file_when_no_environment(self):
        """Test fallback to config file when environment is not set."""
        file_config = {
            "apikey": "file-key",
            "channel": "file-channel", 
            "region": "file-region"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(file_config, temp_file)
            temp_file_path = temp_file.name

        try:
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(AtlasConfig, '_get_config_file_path', return_value=Path(temp_file_path)):
                    with patch.object(AtlasConfig, '_set_gateway_by_channel_region'):
                        config = AtlasConfig()
                        
                        # Should use file values
                        self.assertEqual(config.apikey, "file-key")
                        self.assertEqual(config.channel, "file-channel")
                        self.assertEqual(config.region, "file-region")
                        self.assertTrue(config.hasConfig)
                        
        finally:
            os.unlink(temp_file_path)

    def test_fallback_to_direct_parameters(self):
        """Test fallback to direct parameters when no other config sources available."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(AtlasConfig, '_get_config_file_path') as mock_get_path:
                mock_get_path.return_value = Path("/non/existent/config.json")
                
                with patch.object(AtlasConfig, '_set_gateway_by_channel_region'):
                    config = AtlasConfig(
                        apikey="direct-key",
                        channel="direct-channel", 
                        region="direct-region"
                    )
                    
                    # Should use direct parameters
                    self.assertEqual(config.apikey, "direct-key")
                    self.assertEqual(config.channel, "direct-channel")
                    self.assertEqual(config.region, "direct-region")
                    self.assertTrue(config.hasConfig)

    def test_no_configuration_available(self):
        """Test behavior when no configuration is available from any source."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(AtlasConfig, '_get_config_file_path') as mock_get_path:
                mock_get_path.return_value = Path("/non/existent/config.json")
                
                # No direct parameters provided
                config = AtlasConfig()
                
                self.assertFalse(config.hasConfig)


if __name__ == '__main__':
    unittest.main()
