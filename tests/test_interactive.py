"""
Comprehensive tests for Interactive CLI Module.

This module provides security-hardened testing for interactive configuration
functionality with comprehensive error handling and edge case coverage.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import os
import json
from io import StringIO

# Import the module to ensure it's loaded for coverage
import atlasexplorer.cli.interactive
from atlasexplorer.cli.interactive import InteractiveConfig, configure
from atlasexplorer.core.config import AtlasConfig
from atlasexplorer.core.constants import AtlasConstants
from atlasexplorer.utils.exceptions import ConfigurationError, AuthenticationError


class TestInteractiveConfigInitialization(unittest.TestCase):
    """Test InteractiveConfig initialization and setup."""

    def test_initialization_default_verbose(self):
        """Test initialization with default verbose setting."""
        interactive = InteractiveConfig()
        self.assertTrue(interactive.verbose)

    def test_initialization_verbose_true(self):
        """Test initialization with explicit verbose=True."""
        interactive = InteractiveConfig(verbose=True)
        self.assertTrue(interactive.verbose)

    def test_initialization_verbose_false(self):
        """Test initialization with verbose=False."""
        interactive = InteractiveConfig(verbose=False)
        self.assertFalse(interactive.verbose)

    def test_initialization_attributes(self):
        """Test that all required attributes are initialized."""
        interactive = InteractiveConfig()
        self.assertTrue(hasattr(interactive, 'verbose'))


class TestInteractiveConfigInputPrompting(unittest.TestCase):
    """Test input prompting functionality with security validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.interactive = InteractiveConfig(verbose=False)

    @patch('builtins.input', return_value='test_input')
    def test_prompt_for_input_basic(self, mock_input):
        """Test basic input prompting."""
        result = self.interactive._prompt_for_input("Enter value")
        self.assertEqual(result, 'test_input')
        mock_input.assert_called_once_with("Enter value: ")

    @patch('builtins.input', return_value='')
    def test_prompt_for_input_with_default(self, mock_input):
        """Test input prompting with default value."""
        result = self.interactive._prompt_for_input("Enter value", default="default_val")
        self.assertEqual(result, 'default_val')
        mock_input.assert_called_once_with("Enter value [default_val]: ")

    @patch('builtins.input', side_effect=['', '', 'valid_input'])
    def test_prompt_for_input_required_validation(self, mock_input):
        """Test required field validation."""
        with patch('builtins.print') as mock_print:
            result = self.interactive._prompt_for_input("Enter value", required=True)
            self.assertEqual(result, 'valid_input')
            # Should print error message twice for empty inputs
            self.assertEqual(mock_print.call_count, 2)
            mock_print.assert_called_with("This field is required.")

    @patch('builtins.input', side_effect=['invalid', 'option1'])
    def test_prompt_for_input_choices_validation(self, mock_input):
        """Test choices validation."""
        choices = ['option1', 'option2', 'option3']
        with patch('builtins.print') as mock_print:
            result = self.interactive._prompt_for_input(
                "Select option", choices=choices
            )
            self.assertEqual(result, 'option1')
            mock_print.assert_called_with("Please choose from: option1, option2, option3")

    @patch('getpass.getpass', return_value='secret_value')
    def test_prompt_for_input_sensitive(self, mock_getpass):
        """Test sensitive input handling."""
        result = self.interactive._prompt_for_input("Enter password", sensitive=True)
        self.assertEqual(result, 'secret_value')
        mock_getpass.assert_called_once_with("Enter password: ")

    @patch('getpass.getpass', return_value='')
    def test_prompt_for_input_sensitive_with_default(self, mock_getpass):
        """Test sensitive input with default value."""
        result = self.interactive._prompt_for_input(
            "Enter password", default="default_secret", sensitive=True
        )
        self.assertEqual(result, 'default_secret')
        mock_getpass.assert_called_once_with("Enter password [default_secret]: ")

    @patch('builtins.input', return_value='option2')
    def test_prompt_for_input_choices_format(self, mock_input):
        """Test choices formatting in prompt."""
        choices = ['option1', 'option2']
        result = self.interactive._prompt_for_input("Select", choices=choices)
        self.assertEqual(result, 'option2')
        mock_input.assert_called_once_with("Select (option1/option2): ")

    @patch('builtins.input', return_value='  spaced_input  ')
    def test_prompt_for_input_strips_whitespace(self, mock_input):
        """Test that input is stripped of whitespace."""
        result = self.interactive._prompt_for_input("Enter value")
        self.assertEqual(result, 'spaced_input')


class TestInteractiveConfigAPIValidation(unittest.TestCase):
    """Test API key validation with network security."""

    def setUp(self):
        """Set up test fixtures."""
        self.interactive = InteractiveConfig(verbose=False)

    @patch('requests.get')
    def test_validate_api_key_success(self, mock_get):
        """Test successful API key validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.interactive._validate_api_key("valid_key")
        self.assertTrue(result)

        mock_get.assert_called_once_with(
            f"{AtlasConstants.AE_GLOBAL_API}/user",
            headers={"apikey": "valid_key"},
            timeout=AtlasConstants.HTTP_TIMEOUT
        )

    @patch('requests.get')
    def test_validate_api_key_invalid_response(self, mock_get):
        """Test API key validation with invalid response."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = self.interactive._validate_api_key("invalid_key")
        self.assertFalse(result)

    @patch('requests.get', side_effect=Exception("Network error"))
    def test_validate_api_key_network_exception(self, mock_get):
        """Test API key validation with network exception."""
        result = self.interactive._validate_api_key("test_key")
        self.assertFalse(result)

    @patch('requests.get')
    def test_validate_api_key_timeout_handling(self, mock_get):
        """Test API key validation timeout handling."""
        mock_get.side_effect = Exception("Timeout")

        result = self.interactive._validate_api_key("test_key")
        self.assertFalse(result)


class TestInteractiveConfigChannelManagement(unittest.TestCase):
    """Test channel list retrieval and management."""

    def setUp(self):
        """Set up test fixtures."""
        self.interactive = InteractiveConfig(verbose=False)

    @patch('requests.get')
    def test_get_channel_list_success(self, mock_get):
        """Test successful channel list retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"channels": ["channel1", "channel2"]}
        mock_get.return_value = mock_response

        result = self.interactive._get_channel_list("test_key")
        self.assertEqual(result, ["channel1", "channel2"])

        mock_get.assert_called_once_with(
            f"{AtlasConstants.AE_GLOBAL_API}/channellist",
            headers={
                "apikey": "test_key",
                "extversion": AtlasConstants.API_EXT_VERSION
            },
            timeout=AtlasConstants.HTTP_TIMEOUT
        )

    @patch('requests.get')
    def test_get_channel_list_invalid_response(self, mock_get):
        """Test channel list retrieval with invalid response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.interactive._get_channel_list("test_key")
        self.assertEqual(result, [])

    @patch('requests.get')
    def test_get_channel_list_missing_channels_key(self, mock_get):
        """Test channel list retrieval with missing channels key."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"other_key": "value"}
        mock_get.return_value = mock_response

        result = self.interactive._get_channel_list("test_key")
        self.assertEqual(result, [])

    @patch('requests.get', side_effect=Exception("Network error"))
    def test_get_channel_list_network_exception(self, mock_get):
        """Test channel list retrieval with network exception."""
        result = self.interactive._get_channel_list("test_key")
        self.assertEqual(result, [])

    @patch('requests.get')
    def test_get_channel_list_json_decode_error(self, mock_get):
        """Test channel list retrieval with JSON decode error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = self.interactive._get_channel_list("test_key")
        self.assertEqual(result, [])


class TestInteractiveConfigRegionManagement(unittest.TestCase):
    """Test region list retrieval and management."""

    def setUp(self):
        """Set up test fixtures."""
        self.interactive = InteractiveConfig(verbose=False)

    def test_get_region_list(self):
        """Test region list retrieval."""
        result = self.interactive._get_region_list("test_key", "test_channel")
        expected_regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
        self.assertEqual(result, expected_regions)

    def test_get_region_list_with_different_inputs(self):
        """Test region list retrieval with different inputs."""
        result1 = self.interactive._get_region_list("key1", "channel1")
        result2 = self.interactive._get_region_list("key2", "channel2")
        
        # Should return the same regions regardless of input
        self.assertEqual(result1, result2)
        expected_regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
        self.assertEqual(result1, expected_regions)


class TestInteractiveConfigurationSaving(unittest.TestCase):
    """Test configuration saving functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.interactive = InteractiveConfig(verbose=False)
        self.test_config = {
            "apikey": "test_api_key",
            "channel": "test_channel",
            "region": "us-east-1"
        }

    @patch('builtins.open', new_callable=mock_open)
    def test_save_configuration_success(self, mock_file):
        """Test successful configuration saving."""
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            self.interactive._save_configuration(self.test_config)

            # Verify AtlasConfig was called correctly
            mock_config_class.assert_called_once_with(readonly=True, verbose=False)
            mock_config.save_to_file.assert_called_once_with(self.test_config)

            # Verify .env file was written
            mock_file.assert_called_once_with('.env', 'w')
            handle = mock_file()
            written_content = ''.join(call[0][0] for call in handle.write.call_args_list)
            
            self.assertIn('MIPS_ATLAS_CONFIG=test_api_key:test_channel:us-east-1', written_content)
            self.assertIn(f'API_EXT_VERSION={AtlasConstants.API_EXT_VERSION}', written_content)

    @patch('builtins.open', new_callable=mock_open)
    def test_save_configuration_verbose_output(self, mock_file):
        """Test configuration saving with verbose output."""
        interactive = InteractiveConfig(verbose=True)
        
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            with patch('builtins.print') as mock_print:
                interactive._save_configuration(self.test_config)
                mock_print.assert_called_with("Configuration also saved to .env")

    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_save_configuration_file_error(self, mock_file):
        """Test configuration saving with file write error."""
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            with self.assertRaises(IOError):
                self.interactive._save_configuration(self.test_config)

    @patch('builtins.open', new_callable=mock_open)
    def test_save_configuration_config_save_error(self, mock_file):
        """Test configuration saving with config save error."""
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            mock_config = Mock()
            mock_config.save_to_file.side_effect = Exception("Config save failed")
            mock_config_class.return_value = mock_config

            with self.assertRaises(Exception):
                self.interactive._save_configuration(self.test_config)


class TestInteractiveConfigurationWorkflow(unittest.TestCase):
    """Test complete configuration workflow integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.interactive = InteractiveConfig(verbose=False)

    @patch('builtins.print')
    @patch.object(InteractiveConfig, '_save_configuration')
    @patch.object(InteractiveConfig, '_get_region_list')
    @patch.object(InteractiveConfig, '_get_channel_list')
    @patch.object(InteractiveConfig, '_validate_api_key')
    @patch.object(InteractiveConfig, '_prompt_for_input')
    def test_run_configuration_success_workflow(self, mock_prompt,
                                               mock_validate, mock_channels, mock_regions,
                                               mock_save, mock_print):
        """Test successful complete configuration workflow."""
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            # Mock AtlasConfig
            mock_config = Mock()
            mock_config.hasConfig = False
            mock_config.apikey = ""
            
            # Mock test configuration
            test_config = Mock()
            test_config.hasConfig = True
            test_config.gateway = "https://test.gateway.com"
            mock_config_class.side_effect = [mock_config, test_config]

            # Setup mocks
            mock_prompt.side_effect = ["test_api_key", "channel1", "region1"]
            mock_validate.return_value = True
            mock_channels.return_value = ["channel1", "channel2"]
            mock_regions.return_value = ["region1", "region2"]

            self.interactive.run_configuration()

            # Verify API key validation
            mock_validate.assert_called_once_with("test_api_key")
            
            # Verify channel and region retrieval
            mock_channels.assert_called_once_with("test_api_key")
            mock_regions.assert_called_once_with("test_api_key", "channel1")

            # Verify configuration saving
            expected_config = {
                "apikey": "test_api_key",
                "channel": "channel1", 
                "region": "region1"
            }
            mock_save.assert_called_once_with(expected_config)

    @patch('builtins.print')
    @patch.object(InteractiveConfig, '_validate_api_key')
    @patch.object(InteractiveConfig, '_prompt_for_input')
    def test_run_configuration_invalid_api_key(self, mock_prompt,
                                             mock_validate, mock_print):
        """Test configuration workflow with invalid API key."""
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            mock_config = Mock()
            mock_config.hasConfig = False
            mock_config_class.return_value = mock_config

            mock_prompt.return_value = "invalid_key"
            mock_validate.return_value = False

            self.interactive.run_configuration()

            mock_print.assert_any_call("Error: Invalid API key. Please check your credentials.")

    @patch('builtins.print')
    @patch.object(InteractiveConfig, '_get_channel_list')
    @patch.object(InteractiveConfig, '_validate_api_key')
    @patch.object(InteractiveConfig, '_prompt_for_input')
    def test_run_configuration_no_channels(self, mock_prompt,
                                         mock_validate, mock_channels, mock_print):
        """Test configuration workflow with no available channels."""
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            mock_config = Mock()
            mock_config.hasConfig = False
            mock_config_class.return_value = mock_config

            mock_prompt.return_value = "valid_key"
            mock_validate.return_value = True
            mock_channels.return_value = []

            self.interactive.run_configuration()

            mock_print.assert_any_call("Error: Unable to retrieve channel list. Please check your API key.")

    @patch('builtins.print')
    @patch.object(InteractiveConfig, '_get_region_list')
    @patch.object(InteractiveConfig, '_get_channel_list')
    @patch.object(InteractiveConfig, '_validate_api_key')
    @patch.object(InteractiveConfig, '_prompt_for_input')
    def test_run_configuration_no_regions(self, mock_prompt,
                                        mock_validate, mock_channels, mock_regions, mock_print):
        """Test configuration workflow with no available regions."""
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            mock_config = Mock()
            mock_config.hasConfig = False
            mock_config_class.return_value = mock_config

            mock_prompt.side_effect = ["valid_key", "channel1"]
            mock_validate.return_value = True
            mock_channels.return_value = ["channel1"]
            mock_regions.return_value = []

            self.interactive.run_configuration()

            mock_print.assert_any_call("Error: Unable to retrieve region list. Please check your selections.")

    @patch('builtins.print')
    @patch.object(InteractiveConfig, '_save_configuration')
    @patch.object(InteractiveConfig, '_get_region_list')
    @patch.object(InteractiveConfig, '_get_channel_list')
    @patch.object(InteractiveConfig, '_validate_api_key')
    @patch.object(InteractiveConfig, '_prompt_for_input')
    def test_run_configuration_save_error(self, mock_prompt,
                                        mock_validate, mock_channels, mock_regions,
                                        mock_save, mock_print):
        """Test configuration workflow with save error."""
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            mock_config = Mock()
            mock_config.hasConfig = False
            mock_config_class.return_value = mock_config

            mock_prompt.side_effect = ["valid_key", "channel1", "region1"]
            mock_validate.return_value = True
            mock_channels.return_value = ["channel1"]
            mock_regions.return_value = ["region1"]
            mock_save.side_effect = Exception("Save failed")

            with self.assertRaises(ConfigurationError) as context:
                self.interactive.run_configuration()
            
            self.assertIn("Failed to save configuration", str(context.exception))

    @patch('builtins.print')
    @patch.object(InteractiveConfig, '_save_configuration')
    @patch.object(InteractiveConfig, '_get_region_list')
    @patch.object(InteractiveConfig, '_get_channel_list')
    @patch.object(InteractiveConfig, '_validate_api_key')
    @patch.object(InteractiveConfig, '_prompt_for_input')
    def test_run_configuration_gateway_setup_failed(self, mock_prompt,
                                                   mock_validate, mock_channels, mock_regions,
                                                   mock_save, mock_print):
        """Test configuration workflow with gateway setup failure."""
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            # Initial config
            mock_config = Mock()
            mock_config.hasConfig = False
            
            # Test config that fails gateway setup
            test_config = Mock()
            test_config.hasConfig = False  # This will trigger the warning
            test_config.gateway = None
            mock_config_class.side_effect = [mock_config, test_config]

            mock_prompt.side_effect = ["valid_key", "channel1", "region1"]
            mock_validate.return_value = True
            mock_channels.return_value = ["channel1"]
            mock_regions.return_value = ["region1"]

            self.interactive.run_configuration()

            # Verify the warning message was printed
            mock_print.assert_any_call("⚠ Configuration saved but gateway setup failed.")


class TestInteractiveConfigExistingConfiguration(unittest.TestCase):
    """Test handling of existing configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.interactive = InteractiveConfig(verbose=False)

    @patch('builtins.print')
    @patch.object(InteractiveConfig, '_save_configuration')
    @patch.object(InteractiveConfig, '_get_region_list')
    @patch.object(InteractiveConfig, '_get_channel_list')
    @patch.object(InteractiveConfig, '_validate_api_key')
    @patch.object(InteractiveConfig, '_prompt_for_input')
    def test_run_configuration_with_existing_config(self, mock_prompt,
                                                   mock_validate, mock_channels, mock_regions,
                                                   mock_save, mock_print):
        """Test configuration workflow with existing configuration."""
        with patch('atlasexplorer.cli.interactive.AtlasConfig') as mock_config_class:
            # Mock existing configuration
            mock_config = Mock()
            mock_config.hasConfig = True
            mock_config.apikey = "existing_key"
            mock_config.channel = "existing_channel"
            mock_config.region = "existing_region"

            # Mock test configuration
            test_config = Mock()
            test_config.hasConfig = True
            test_config.gateway = "https://test.gateway.com"
            mock_config_class.side_effect = [mock_config, test_config]

            # Setup mocks - user keeps existing values by entering empty strings
            mock_prompt.side_effect = ["existing_key", "existing_channel", "existing_region"]
            mock_validate.return_value = True
            mock_channels.return_value = ["existing_channel", "other_channel"]
            mock_regions.return_value = ["existing_region", "other_region"]

            self.interactive.run_configuration()

            # Verify API key validation was called
            mock_validate.assert_called_once_with("existing_key")
            
            # Verify channel and region retrieval
            mock_channels.assert_called_once_with("existing_key")
            mock_regions.assert_called_once_with("existing_key", "existing_channel")

            # Verify configuration saving
            expected_config = {
                "apikey": "existing_key",
                "channel": "existing_channel", 
                "region": "existing_region"
            }
            mock_save.assert_called_once_with(expected_config)


class TestLegacyConfigureFunction(unittest.TestCase):
    """Test legacy configure function for backward compatibility."""

    @patch.object(InteractiveConfig, 'run_configuration')
    def test_configure_function(self, mock_run):
        """Test legacy configure function."""
        args = Mock()
        configure(args)
        mock_run.assert_called_once()

    @patch.object(InteractiveConfig, 'run_configuration')
    def test_configure_function_with_none_args(self, mock_run):
        """Test legacy configure function with None args."""
        configure(None)
        mock_run.assert_called_once()


class TestInteractiveConfigErrorHandling(unittest.TestCase):
    """Test comprehensive error handling and edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.interactive = InteractiveConfig(verbose=False)

    def test_prompt_for_input_keyboard_interrupt(self):
        """Test handling of keyboard interrupt during input."""
        with patch('builtins.input', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.interactive._prompt_for_input("Enter value")

    @patch('requests.get')
    def test_validate_api_key_connection_timeout(self, mock_get):
        """Test API key validation with connection timeout."""
        mock_get.side_effect = Exception("Connection timeout")
        result = self.interactive._validate_api_key("test_key")
        self.assertFalse(result)

    @patch('requests.get')
    def test_get_channel_list_empty_response(self, mock_get):
        """Test channel list retrieval with empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        result = self.interactive._get_channel_list("test_key")
        self.assertEqual(result, [])

    def test_save_configuration_invalid_config_data(self):
        """Test configuration saving with invalid data types."""
        invalid_config = {
            "apikey": None,
            "channel": 123,
            "region": []
        }
        
        with patch('atlasexplorer.core.config.AtlasConfig') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config
            
            with patch('builtins.open', new_callable=mock_open):
                # Should not raise an exception - the method handles any data types
                self.interactive._save_configuration(invalid_config)


class TestInteractiveConfigSecurityFeatures(unittest.TestCase):
    """Test security features and input validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.interactive = InteractiveConfig(verbose=False)

    @patch('getpass.getpass', return_value='secure_password')
    def test_sensitive_input_security(self, mock_getpass):
        """Test that sensitive inputs are handled securely."""
        result = self.interactive._prompt_for_input("Password", sensitive=True)
        self.assertEqual(result, 'secure_password')
        # Verify getpass was used instead of regular input
        mock_getpass.assert_called_once()

    @patch('builtins.input', return_value='<script>alert("xss")</script>')
    def test_input_xss_handling(self, mock_input):
        """Test handling of potentially malicious input."""
        result = self.interactive._prompt_for_input("Enter value")
        # Should return the input as-is (filtering would be done at application level)
        self.assertEqual(result, '<script>alert("xss")</script>')

    @patch('builtins.input', return_value='a' * 10000)
    def test_input_length_handling(self, mock_input):
        """Test handling of very long input."""
        result = self.interactive._prompt_for_input("Enter value")
        # Should handle long inputs without error
        self.assertEqual(len(result), 10000)

    @patch('requests.get')
    def test_api_validation_headers_security(self, mock_get):
        """Test that API validation includes proper security headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        self.interactive._validate_api_key("test_key")

        # Verify security headers are included
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        headers = call_args[1]['headers']
        self.assertIn('apikey', headers)
        self.assertEqual(headers['apikey'], 'test_key')


if __name__ == '__main__':
    unittest.main()
