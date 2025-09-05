"""
Minimal API Test - Basic Atlas Explorer API Client Testing

This test provides minimal coverage of the API client functionality
focusing on the core workflow used in single-core experiments.

This test will:
    - Test AtlasAPIClient initialization
    - Test basic methods without external dependencies
    - Mock the actual API calls to avoid external dependencies
"""

import unittest
from unittest.mock import Mock, patch
import os
import tempfile

from atlasexplorer.network.api_client import AtlasAPIClient
from atlasexplorer.utils.exceptions import NetworkError, AuthenticationError


class TestBasicAPIClient(unittest.TestCase):
    """Basic tests for AtlasAPIClient functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_url = "https://test-api.atlas-explorer.com"
        self.client = AtlasAPIClient(self.base_url, verbose=False)

    def test_client_initialization(self):
        """Test basic client initialization."""
        client = AtlasAPIClient(self.base_url, verbose=True)
        self.assertEqual(client.base_url, self.base_url)
        self.assertTrue(client.verbose)
        
        # Test trailing slash removal
        client_with_slash = AtlasAPIClient(self.base_url + "/", verbose=False)
        self.assertEqual(client_with_slash.base_url, self.base_url)
        self.assertFalse(client_with_slash.verbose)

    def test_session_creation(self):
        """Test HTTP session creation and reuse."""
        # Session should be None initially
        self.assertIsNone(self.client._session)
        
        # First call should create session
        session1 = self.client._get_session()
        self.assertIsNotNone(session1)
        self.assertIsNotNone(self.client._session)
        
        # Second call should reuse same session
        session2 = self.client._get_session()
        self.assertIs(session1, session2)

    @patch('requests.Session')
    def test_get_signed_urls_success(self, mock_session_class):
        """Test successful signed URL retrieval."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "upload_url": "https://s3.amazonaws.com/upload/123",
            "download_url": "https://s3.amazonaws.com/download/123"
        }
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        result = self.client.get_signed_urls("test_key", "test_uuid", "test_exp", "I8500_(1_thread)")
        
        self.assertIn("upload_url", result)
        self.assertIn("download_url", result)
        mock_session.post.assert_called_once()

    @patch('requests.Session')
    def test_get_signed_urls_auth_error(self, mock_session_class):
        """Test authentication error handling."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        with self.assertRaises(AuthenticationError):
            self.client.get_signed_urls("invalid_key", "test_uuid", "test_exp", "I8500_(1_thread)")

    @patch('requests.Session')
    def test_get_status_success(self, mock_session_class):
        """Test successful status retrieval."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "completed",
            "progress": 100
        }
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        status_url = "https://api.test.com/status/123"
        result = self.client.get_status(status_url)
        
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["progress"], 100)
        # Just verify it was called with correct URL and timeout
        mock_session.get.assert_called_once_with(status_url, timeout=10)

    @patch('requests.Session')
    def test_download_file_success(self, mock_session_class):
        """Test successful file download."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"downloaded", b" content"]
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        with tempfile.TemporaryDirectory() as temp_dir:
            download_url = "https://s3.amazonaws.com/download/test"
            filename = "result.dat"
            
            self.client.download_file(download_url, temp_dir, filename)
            
            # Verify file was created
            result_path = os.path.join(temp_dir, filename)
            self.assertTrue(os.path.exists(result_path))
            
            # Verify content
            with open(result_path, 'rb') as f:
                content = f.read()
            self.assertEqual(content, b"downloaded content")

    def test_context_manager(self):
        """Test client as context manager."""
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            with AtlasAPIClient(self.base_url) as client:
                self.assertIsNotNone(client)
                # Force session creation
                client._get_session()
            
            # Session should be closed after context exit
            mock_session.close.assert_called_once()

    @patch('requests.Session')
    def test_error_handling_network_error(self, mock_session_class):
        """Test network error handling."""
        mock_session = Mock()
        mock_session.post.side_effect = Exception("Network connection failed")
        mock_session_class.return_value = mock_session
        
        with self.assertRaises(NetworkError) as context:
            self.client.get_signed_urls("test_key", "test_uuid", "test_exp", "I8500_(1_thread)")
        
        self.assertIn("Failed to get signed URLs", str(context.exception))


class TestAPIClientBasicWorkflow(unittest.TestCase):
    """Test the very basic workflow operations."""

    @patch('requests.Session')
    def test_signed_urls_only(self, mock_session_class):
        """Test just the signed URLs functionality which is core to the workflow."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "upload_url": "https://s3.amazonaws.com/upload/123",
            "download_url": "https://s3.amazonaws.com/download/123"
        }
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = AtlasAPIClient("https://test-api.atlas-explorer.com", verbose=False)
        
        # This mimics the first step of test_ae_singlecore
        urls = client.get_signed_urls("test_key", "test_uuid", "test_experiment", "I8500_(1_thread)")
        
        # Verify we got the expected URLs
        self.assertIn("upload_url", urls)
        self.assertIn("download_url", urls)
        self.assertEqual(urls["upload_url"], "https://s3.amazonaws.com/upload/123")
        self.assertEqual(urls["download_url"], "https://s3.amazonaws.com/download/123")
        
        # Verify the API call was made correctly
        self.assertEqual(mock_session.post.call_count, 1)
        call_args = mock_session.post.call_args
        self.assertIn("test-api.atlas-explorer.com", call_args[0][0])

    @patch('requests.Session')
    def test_status_check_basic(self, mock_session_class):
        """Test basic status checking functionality."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "completed", "progress": 100}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = AtlasAPIClient("https://test-api.atlas-explorer.com", verbose=False)
        
        # This mimics the status checking part of test_ae_singlecore
        status = client.get_status("https://api.test.com/status/123")
        
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["progress"], 100)


if __name__ == '__main__':
    unittest.main()
