"""Tests for the AtlasAPIClient module.

This test suite covers the current API client implementation that handles
HTTP communication with the Atlas Explorer cloud service.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

import requests

from atlasexplorer.network.api_client import AtlasAPIClient
from atlasexplorer.utils.exceptions import NetworkError, AuthenticationError


class TestAtlasAPIClientBasics(unittest.TestCase):
    """Test basic AtlasAPIClient functionality."""

    def test_initialization_default(self):
        """Test default initialization."""
        client = AtlasAPIClient("https://api.example.com")
        self.assertEqual(client.base_url, "https://api.example.com")
        self.assertTrue(client.verbose)
        self.assertIsNone(client._session)

    def test_initialization_verbose_false(self):
        """Test initialization with verbose=False."""
        client = AtlasAPIClient("https://api.example.com", verbose=False)
        self.assertFalse(client.verbose)

    def test_initialization_trailing_slash_removed(self):
        """Test that trailing slash is removed from base URL."""
        client = AtlasAPIClient("https://api.example.com/")
        self.assertEqual(client.base_url, "https://api.example.com")

    def test_get_session_creates_new(self):
        """Test that _get_session creates a new session."""
        client = AtlasAPIClient("https://api.example.com")
        session = client._get_session()
        self.assertIsNotNone(session)
        self.assertIsInstance(session, requests.Session)

    def test_get_session_reuses_existing(self):
        """Test that _get_session reuses existing session."""
        client = AtlasAPIClient("https://api.example.com")
        session1 = client._get_session()
        session2 = client._get_session()
        self.assertIs(session1, session2)


class TestAtlasAPIClientSignedURLs(unittest.TestCase):
    """Test signed URL functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = AtlasAPIClient("https://api.example.com", verbose=False)

    @patch('requests.Session.post')
    def test_get_signed_urls_success(self, mock_post):
        """Test successful signed URL retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'upload_url': 'https://upload.example.com/signed',
            'status_url': 'https://status.example.com/check',
            'download_url': 'https://download.example.com/result'
        }
        mock_post.return_value = mock_response

        result = self.client.get_signed_urls("test_key", "exp_123", "test_exp", "I8500")
        
        self.assertEqual(result['upload_url'], 'https://upload.example.com/signed')
        self.assertEqual(result['status_url'], 'https://status.example.com/check')
        self.assertEqual(result['download_url'], 'https://download.example.com/result')

    @patch('requests.Session.post')
    def test_get_signed_urls_authentication_error_401(self, mock_post):
        """Test authentication error (401)."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        with self.assertRaises(AuthenticationError) as context:
            self.client.get_signed_urls("invalid_key", "exp_123", "test_exp", "I8500")
        
        self.assertIn("Authentication failed", str(context.exception))

    @patch('requests.Session.post')
    def test_get_signed_urls_authentication_error_403(self, mock_post):
        """Test authentication error (403)."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response

        with self.assertRaises(AuthenticationError) as context:
            self.client.get_signed_urls("invalid_key", "exp_123", "test_exp", "I8500")
        
        self.assertIn("Authentication failed", str(context.exception))

    @patch('requests.Session.post')
    def test_get_signed_urls_http_error(self, mock_post):
        """Test HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server Error")
        mock_post.return_value = mock_response

        with self.assertRaises(NetworkError) as context:
            self.client.get_signed_urls("test_key", "exp_123", "test_exp", "I8500")
        
        self.assertIn("HTTP request failed", str(context.exception))

    @patch('requests.Session.post')
    def test_get_signed_urls_network_exception(self, mock_post):
        """Test network exception."""
        mock_post.side_effect = requests.ConnectionError("Network error")

        with self.assertRaises(NetworkError) as context:
            self.client.get_signed_urls("test_key", "exp_123", "test_exp", "I8500")
        
        self.assertIn("Network request failed", str(context.exception))


class TestAtlasAPIClientFileUpload(unittest.TestCase):
    """Test file upload functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = AtlasAPIClient("https://api.example.com", verbose=False)

    @patch('requests.Session.put')
    def test_upload_file_success(self, mock_put):
        """Test successful file upload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"upload_success"
        mock_put.return_value = mock_response

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test file content")
            temp_file_path = temp_file.name

        try:
            result = self.client.upload_file("https://upload.example.com", temp_file_path)
            self.assertEqual(result, b"upload_success")
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_upload_file_nonexistent_file(self):
        """Test upload of non-existent file."""
        with self.assertRaises(NetworkError) as context:
            self.client.upload_file("https://upload.example.com", "/nonexistent/file.txt")
        
        self.assertIn("File not found", str(context.exception))

    @patch('requests.Session.put')
    def test_upload_file_http_error(self, mock_put):
        """Test upload HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server Error")
        mock_put.return_value = mock_response

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name

        try:
            with self.assertRaises(NetworkError) as context:
                self.client.upload_file("https://upload.example.com", temp_file_path)
            
            self.assertIn("Upload failed", str(context.exception))
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    @patch('requests.Session.put')
    def test_upload_file_verbose_output(self, mock_put):
        """Test verbose output during upload."""
        client_verbose = AtlasAPIClient("https://api.example.com", verbose=True)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"success"
        mock_put.return_value = mock_response

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name

        try:
            with patch('builtins.print') as mock_print:
                client_verbose.upload_file("https://upload.example.com", temp_file_path)
                # Should have printed upload message
                mock_print.assert_called()
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)


class TestAtlasAPIClientStatusOperations(unittest.TestCase):
    """Test status checking functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = AtlasAPIClient("https://api.example.com", verbose=False)

    @patch('requests.Session.get')
    def test_get_status_success(self, mock_get):
        """Test successful status retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'completed', 'progress': 100}
        mock_get.return_value = mock_response

        result = self.client.get_status("https://status.example.com/check")
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['progress'], 100)

    @patch('requests.Session.get')
    def test_get_status_network_error(self, mock_get):
        """Test status check network error."""
        mock_get.side_effect = requests.ConnectionError("Network error")

        with self.assertRaises(NetworkError) as context:
            self.client.get_status("https://status.example.com/check")
        
        self.assertIn("Status check failed", str(context.exception))

    @patch('atlasexplorer.network.api_client.AtlasAPIClient.get_status')
    @patch('time.sleep')
    def test_poll_status_success_completed(self, mock_sleep, mock_get_status):
        """Test successful status polling until completion."""
        # Simulate status progression
        mock_get_status.side_effect = [
            {'status': 'running', 'progress': 25},
            {'status': 'running', 'progress': 50},
            {'status': 'completed', 'progress': 100}
        ]

        result = self.client.poll_status("https://status.example.com", max_attempts=5, delay=0.1)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(mock_get_status.call_count, 3)

    @patch('atlasexplorer.network.api_client.AtlasAPIClient.get_status')
    @patch('time.sleep')
    def test_poll_status_timeout(self, mock_sleep, mock_get_status):
        """Test status polling timeout."""
        # Always return running status
        mock_get_status.return_value = {'status': 'running', 'progress': 50}

        with self.assertRaises(NetworkError) as context:
            self.client.poll_status("https://status.example.com", max_attempts=3, delay=0.1)
        
        self.assertIn("Polling timeout", str(context.exception))
        self.assertEqual(mock_get_status.call_count, 3)

    @patch('atlasexplorer.network.api_client.AtlasAPIClient.get_status')
    def test_poll_status_experiment_failed(self, mock_get_status):
        """Test polling when experiment fails."""
        mock_get_status.return_value = {'status': 'failed', 'error': 'Processing error'}

        with self.assertRaises(NetworkError) as context:
            self.client.poll_status("https://status.example.com", max_attempts=3)
        
        self.assertIn("Experiment failed", str(context.exception))


class TestAtlasAPIClientFileDownload(unittest.TestCase):
    """Test file download functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = AtlasAPIClient("https://api.example.com", verbose=False)

    @patch('requests.Session.get')
    def test_download_file_success(self, mock_get):
        """Test successful file download."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2", b"chunk3"]
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            self.client.download_file("https://download.example.com/file", temp_dir, "result.zip")
            
            result_path = os.path.join(temp_dir, "result.zip")
            self.assertTrue(os.path.exists(result_path))
            
            with open(result_path, 'rb') as f:
                content = f.read()
            self.assertEqual(content, b"chunk1chunk2chunk3")

    @patch('requests.Session.get')
    def test_download_file_directory_creation(self, mock_get):
        """Test download with directory creation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"test_content"]
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = os.path.join(temp_dir, "nested", "subdir")
            self.client.download_file("https://download.example.com/file", nested_dir, "result.zip")
            
            result_path = os.path.join(nested_dir, "result.zip")
            self.assertTrue(os.path.exists(result_path))

    @patch('requests.Session.get')
    def test_download_file_http_error(self, mock_get):
        """Test download HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("Not Found")
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(NetworkError) as context:
                self.client.download_file("https://download.example.com/missing", temp_dir, "result.zip")
            
            self.assertIn("Download failed", str(context.exception))


class TestAtlasAPIClientResourceManagement(unittest.TestCase):
    """Test resource management functionality."""

    def test_close_no_session(self):
        """Test close when no session exists."""
        client = AtlasAPIClient("https://api.example.com")
        # Should not raise exception
        client.close()

    def test_close_session(self):
        """Test close with existing session."""
        client = AtlasAPIClient("https://api.example.com")
        session = client._get_session()
        
        with patch.object(session, 'close') as mock_close:
            client.close()
            mock_close.assert_called_once()

    def test_context_manager(self):
        """Test context manager usage."""
        with AtlasAPIClient("https://api.example.com") as client:
            self.assertIsNotNone(client)
            session = client._get_session()
            
            with patch.object(session, 'close') as mock_close:
                pass  # Exit context
        
        # close() should have been called on exit

    def test_context_manager_with_exception(self):
        """Test context manager with exception."""
        try:
            with AtlasAPIClient("https://api.example.com") as client:
                session = client._get_session()
                
                with patch.object(session, 'close') as mock_close:
                    raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
        
        # close() should still have been called


class TestAtlasAPIClientIntegration(unittest.TestCase):
    """Test integration scenarios."""

    @patch('requests.Session.get')
    @patch('requests.Session.put')
    @patch('requests.Session.post')
    def test_full_workflow_simulation(self, mock_post, mock_put, mock_get):
        """Test a full workflow simulation."""
        client = AtlasAPIClient("https://api.example.com", verbose=False)
        
        # Mock signed URLs response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'upload_url': 'https://upload.example.com/signed',
            'status_url': 'https://status.example.com/check',
            'download_url': 'https://download.example.com/result'
        }
        
        # Mock upload response
        mock_put.return_value.status_code = 200
        mock_put.return_value.content = b"upload_success"
        
        # Mock status responses (progression)
        mock_get.side_effect = [
            # Status checks
            Mock(status_code=200, json=lambda: {'status': 'running', 'progress': 50}),
            Mock(status_code=200, json=lambda: {'status': 'completed', 'progress': 100}),
            # Download
            Mock(status_code=200, iter_content=lambda chunk_size: [b"result_data"])
        ]
        
        # 1. Get signed URLs
        urls = client.get_signed_urls("test_key", "exp_123", "test_exp", "I8500")
        self.assertIn('upload_url', urls)
        
        # 2. Upload file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test data")
            temp_file_path = temp_file.name
        
        try:
            upload_result = client.upload_file(urls['upload_url'], temp_file_path)
            self.assertEqual(upload_result, b"upload_success")
            
            # 3. Poll status
            with patch('time.sleep'):  # Speed up test
                final_status = client.poll_status(urls['status_url'], max_attempts=3, delay=0.1)
            self.assertEqual(final_status['status'], 'completed')
            
            # 4. Download result
            with tempfile.TemporaryDirectory() as temp_dir:
                client.download_file(urls['download_url'], temp_dir, "result.zip")
                result_path = os.path.join(temp_dir, "result.zip")
                self.assertTrue(os.path.exists(result_path))
        
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)


if __name__ == '__main__':
    unittest.main()
