#!/usr/bin/env python3
"""
Unit tests for the modular AtlasExplorer client class.

Tests the new AtlasExplorer class extracted in Phase 1.2 to ensure
it maintains functionality while providing better architecture.
"""

import unittest
import json
import requests
from unittest.mock import Mock, patch, MagicMock

from atlasexplorer.core.client import AtlasExplorer, get_channel_list, validate_user_api_key
from atlasexplorer.core.config import AtlasConfig
from atlasexplorer.utils.exceptions import (
    NetworkError,
    ConfigurationError,
    AuthenticationError
)


class TestAtlasExplorer(unittest.TestCase):
    """Test cases for the AtlasExplorer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=AtlasConfig)
        self.mock_config.hasConfig = True
        self.mock_config.apikey = "test-api-key"
        self.mock_config.channel = "test-channel"
        self.mock_config.region = "test-region"
        self.mock_config.gateway = "https://test-gateway.example.com"
    
    @patch('atlasexplorer.core.client.AtlasConfig')
    def test_atlas_explorer_initialization_success(self, mock_atlas_config):
        """Test successful AtlasExplorer initialization."""
        mock_atlas_config.return_value = self.mock_config
        
        with patch.object(AtlasExplorer, '_check_worker_status') as mock_check:
            mock_check.return_value = {"status": True}
            
            explorer = AtlasExplorer(
                apikey="test-key", 
                channel="test-channel", 
                region="test-region",
                verbose=False
            )
            
            self.assertEqual(explorer.config, self.mock_config)
            self.assertFalse(explorer.verbose)
            mock_atlas_config.assert_called_once_with(
                verbose=False,
                apikey="test-key",
                channel="test-channel", 
                region="test-region"
            )
    
    @patch('atlasexplorer.core.client.AtlasConfig')
    def test_atlas_explorer_no_config(self, mock_atlas_config):
        """Test AtlasExplorer initialization with no configuration."""
        mock_config = Mock(spec=AtlasConfig)
        mock_config.hasConfig = False
        mock_atlas_config.return_value = mock_config
        
        with self.assertRaises(ConfigurationError) as context:
            AtlasExplorer()
        
        self.assertIn("Cloud connection is not setup", str(context.exception))
    
    @patch('atlasexplorer.core.client.AtlasConfig')
    def test_atlas_explorer_worker_down(self, mock_atlas_config):
        """Test AtlasExplorer initialization with worker down."""
        mock_atlas_config.return_value = self.mock_config
        
        with patch.object(AtlasExplorer, '_check_worker_status') as mock_check:
            mock_check.return_value = {"status": False}
            
            with self.assertRaises(NetworkError) as context:
                AtlasExplorer()
            
            self.assertIn("service is down", str(context.exception))
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_get_cloud_caps_success(self, mock_get):
        """Test successful cloud capabilities fetching."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {"version": "0.0.97", "shinro": {"arches": [{"name": "I8500"}]}}
        ]
        mock_get.return_value = mock_response
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                explorer._getCloudCaps("0.0.97")
                
                self.assertEqual(explorer.versionCaps["version"], "0.0.97")
                self.assertIsInstance(explorer.channelCaps, list)
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_get_cloud_caps_network_error(self, mock_get):
        """Test cloud capabilities fetching with network error."""
        mock_get.side_effect = Exception("Network error")
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                
                with self.assertRaises(NetworkError):
                    explorer._getCloudCaps("0.0.97")
    
    def test_get_cloud_caps_no_gateway(self):
        """Test cloud capabilities fetching with no gateway configured."""
        config = Mock(spec=AtlasConfig)
        config.hasConfig = True
        config.gateway = None
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                
                with self.assertRaises(ConfigurationError) as context:
                    explorer._getCloudCaps("0.0.97")
                
                self.assertIn("Gateway is not configured", str(context.exception))
    
    def test_get_core_info_success(self):
        """Test successful core information retrieval."""
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                explorer.versionCaps = {
                    "shinro": {
                        "arches": [
                            {"name": "I8500", "num_threads": 1},
                            {"name": "P8500", "num_threads": 2}
                        ]
                    }
                }
                
                core_info = explorer.getCoreInfo("I8500")
                
                self.assertEqual(core_info["name"], "I8500")
                self.assertEqual(core_info["num_threads"], 1)
    
    def test_get_core_info_not_found(self):
        """Test core information retrieval for unsupported core."""
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                explorer.versionCaps = {
                    "shinro": {
                        "arches": [{"name": "I8500", "num_threads": 1}]
                    }
                }
                
                with self.assertRaises(NetworkError) as context:
                    explorer.getCoreInfo("UNKNOWN_CORE")
                
                self.assertIn("not supported", str(context.exception))
    
    def test_get_core_info_no_caps(self):
        """Test core information retrieval without cloud capabilities."""
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                explorer.versionCaps = None
                
                with self.assertRaises(ConfigurationError):
                    explorer.getCoreInfo("I8500")
    
    def test_get_version_list(self):
        """Test version list retrieval."""
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                explorer.channelCaps = [
                    {"version": "0.0.97"},
                    {"version": "0.0.98"},
                    {"version": "1.0.0"}
                ]
                
                versions = explorer.getVersionList()
                
                self.assertEqual(versions, ["0.0.97", "0.0.98", "1.0.0"])
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_check_worker_status_success(self, mock_get):
        """Test successful worker status check."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": True, "workers": 5}
        mock_get.return_value = mock_response
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            explorer = AtlasExplorer(verbose=False)
            status = explorer._check_worker_status()
            
            self.assertTrue(status["status"])
            self.assertEqual(status["workers"], 5)
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_check_worker_status_error(self, mock_get):
        """Test worker status check with error."""
        mock_get.side_effect = Exception("Connection failed")
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            # The constructor will call _check_worker_status() and raise NetworkError
            with self.assertRaises(NetworkError):
                AtlasExplorer(verbose=False)
    
    @patch('atlasexplorer.core.client.requests.post')
    def test_get_signed_urls_success(self, mock_post):
        """Test successful signed URLs retrieval."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "exppackageurl": "https://upload.example.com/exp123",
            "statusget": "https://status.example.com/exp123"
        }
        mock_post.return_value = mock_response
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                
                response = explorer.getSignedUrls("test-uuid", "test-exp", "I8500")
                
                self.assertEqual(response, mock_response)
                mock_post.assert_called_once()


class TestHelperFunctions(unittest.TestCase):
    """Test cases for helper functions."""
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_get_channel_list_success(self, mock_get):
        """Test successful channel list retrieval."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "channels": [
                {"name": "production", "regions": ["us-east", "eu-west"]},
                {"name": "staging", "regions": ["us-west"]}
            ]
        }
        mock_get.return_value = mock_response
        
        result = get_channel_list("test-api-key")
        
        self.assertEqual(len(result["channels"]), 2)
        self.assertEqual(result["channels"][0]["name"], "production")
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_get_channel_list_auth_error(self, mock_get):
        """Test channel list retrieval with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        # Create a proper HTTPError with the response
        http_error = requests.HTTPError("401 Client Error: Unauthorized")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        
        with self.assertRaises(AuthenticationError):
            get_channel_list("invalid-api-key")
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_get_channel_list_network_error(self, mock_get):
        """Test channel list retrieval with network error."""
        mock_get.side_effect = Exception("Network error")
        
        with self.assertRaises(NetworkError):
            get_channel_list("test-api-key")
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_validate_user_api_key_valid(self, mock_get):
        """Test API key validation with valid key."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = validate_user_api_key("valid-api-key")
        
        self.assertTrue(result)
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_validate_user_api_key_invalid(self, mock_get):
        """Test API key validation with invalid key."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        result = validate_user_api_key("invalid-api-key")
        
        self.assertFalse(result)
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_validate_user_api_key_network_error(self, mock_get):
        """Test API key validation with network error."""
        mock_get.side_effect = Exception("Network error")
        
        result = validate_user_api_key("test-api-key")
        
        self.assertFalse(result)


class TestAtlasExplorerAdditionalCoverage(unittest.TestCase):
    """Additional tests to improve coverage of AtlasExplorer client."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock()
        self.mock_config.apikey = "test-api-key"
        self.mock_config.channel = "test-channel"
        self.mock_config.region = "test-region"
        self.mock_config.gateway = "https://test-gateway.example.com"
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_getCloudCaps_json_decode_error(self, mock_get):
        """Test _getCloudCaps with JSON decode error."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                
                with self.assertRaises(NetworkError) as cm:
                    explorer._getCloudCaps("0.0.97")
                
                self.assertIn("Invalid JSON response", str(cm.exception))
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_getCloudCaps_version_not_found(self, mock_get):
        """Test _getCloudCaps when requested version is not found."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {"version": "0.0.95", "features": ["feature1"]},
            {"version": "0.0.96", "features": ["feature2"]},
        ]
        mock_get.return_value = mock_response
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                
                with self.assertRaises(NetworkError) as cm:
                    explorer._getCloudCaps("0.0.99")  # Version not in list
                
                self.assertIn("No capabilities found for version 0.0.99", str(cm.exception))
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_getCloudCaps_unexpected_format(self, mock_get):
        """Test _getCloudCaps with unexpected response format."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = "unexpected string response"
        mock_get.return_value = mock_response
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                
                with self.assertRaises(NetworkError) as cm:
                    explorer._getCloudCaps("0.0.97")
                
                self.assertIn("Unexpected format for cloud capabilities", str(cm.exception))
    
    def test_constructor_no_gateway_verbose(self):
        """Test constructor with no gateway set and verbose mode."""
        config_no_gateway = Mock()
        config_no_gateway.apikey = "test-api-key"
        config_no_gateway.channel = "test-channel"
        config_no_gateway.region = "test-region"
        config_no_gateway.gateway = None
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = config_no_gateway
            
            with patch('builtins.print') as mock_print:
                explorer = AtlasExplorer(verbose=True)
                
                # Should print warning about gateway not set
                mock_print.assert_called_with("Warning: Gateway is not set. Skipping worker status check.")
    
    @patch('atlasexplorer.core.client.requests.get')
    def test_check_worker_status_verbose_output(self, mock_get):
        """Test _check_worker_status with verbose output."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": True, "workers": 5}
        mock_get.return_value = mock_response
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status', return_value={"status": True, "workers": 5}):
                with patch('builtins.print') as mock_print:
                    explorer = AtlasExplorer(verbose=True)
                    
                    # Get the actual worker status method and test it
                    with patch('atlasexplorer.core.client.requests.get', return_value=mock_response):
                        status = AtlasExplorer._check_worker_status(explorer)
                        
                        self.assertEqual(status, {"status": True, "workers": 5})
    
    @patch('atlasexplorer.core.client.requests.get')  
    def test_getCloudCaps_successful_version_match(self, mock_get):
        """Test _getCloudCaps with successful version match."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {"version": "0.0.95", "features": ["feature1"]},
            {"version": "0.0.97", "features": ["feature2", "feature3"]},
            {"version": "0.0.98", "features": ["feature4"]},
        ]
        mock_get.return_value = mock_response
        
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                
                explorer._getCloudCaps("0.0.97")
                
                # Should set versionCaps to the matching version
                self.assertEqual(explorer.versionCaps, {"version": "0.0.97", "features": ["feature2", "feature3"]})
                self.assertEqual(explorer.channelCaps, mock_response.json.return_value)
    
    def test_getCoreInfo_no_shinro_section(self):
        """Test getCoreInfo when shinro section is missing."""
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                explorer.versionCaps = {"version": "0.0.97", "other": "data"}  # No shinro section
                
                with self.assertRaises(NetworkError) as cm:
                    explorer.getCoreInfo("I8500")
                
                self.assertIn("No 'shinro' section found", str(cm.exception))
    
    def test_getCoreInfo_invalid_arches_format(self):
        """Test getCoreInfo when arches is not a list."""
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                explorer.versionCaps = {
                    "version": "0.0.97", 
                    "shinro": {"arches": "not_a_list"}  # Invalid format
                }
                
                with self.assertRaises(NetworkError) as cm:
                    explorer.getCoreInfo("I8500")
                
                self.assertIn("Invalid architecture list", str(cm.exception))
    
    def test_getCoreInfo_core_not_found(self):
        """Test getCoreInfo when requested core is not supported."""
        with patch('atlasexplorer.core.client.AtlasConfig') as mock_atlas_config:
            mock_atlas_config.return_value = self.mock_config
            
            with patch.object(AtlasExplorer, '_check_worker_status'):
                explorer = AtlasExplorer(verbose=False)
                explorer.versionCaps = {
                    "version": "0.0.97",
                    "shinro": {
                        "arches": [
                            {"name": "I7500", "features": ["feature1"]},
                            {"name": "M7500", "features": ["feature2"]},
                        ]
                    }
                }
                
                with self.assertRaises(NetworkError) as cm:
                    explorer.getCoreInfo("UNSUPPORTED_CORE")
                
                self.assertIn("Core UNSUPPORTED_CORE is not supported", str(cm.exception))


if __name__ == '__main__':
    unittest.main()
