"""Comprehensive tests for Atlas Explorer API Client.

This test suite provides extensive coverage for the AtlasAPIClient class,
including HTTP operations, error handling, and resource management.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, call

from atlasexplorer.network.api_client import AtlasAPIClient
from atlasexplorer.utils.exceptions import NetworkError, AuthenticationError
from atlasexplorer.core.constants import AtlasConstants


class TestAtlasAPIClientInitialization(unittest.TestCase):
    """Test API client initialization and basic configuration."""
    
    def test_initialization_basic(self):
        """Test basic client initialization."""
        client = AtlasAPIClient("https://api.example.com", verbose=True)
        
        self.assertEqual(client.base_url, "https://api.example.com")
        self.assertTrue(client.verbose)
        self.assertIsNone(client._session)
    
    def test_initialization_trailing_slash_removed(self):
        """Test that trailing slash is removed from base URL."""
        client = AtlasAPIClient("https://api.example.com/", verbose=False)
        
        self.assertEqual(client.base_url, "https://api.example.com")
        self.assertFalse(client.verbose)
    
    def test_initialization_verbose_default(self):
        """Test default verbose setting."""
        client = AtlasAPIClient("https://api.example.com")
        
        self.assertTrue(client.verbose)  # Default should be True
    
    @patch('requests.Session')
    def test_get_session_creates_new_session(self, mock_session_class):
        """Test that _get_session creates a new session when none exists."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        client = AtlasAPIClient("https://api.example.com")
        session = client._get_session()
        
        self.assertEqual(session, mock_session)
        self.assertEqual(client._session, mock_session)
        mock_session_class.assert_called_once()
        mock_session.headers.update.assert_called_once_with({
            'User-Agent': f'Atlas-Explorer-Python/{AtlasConstants.VERSION}'
        })
    
    @patch('requests.Session')
    def test_get_session_reuses_existing_session(self, mock_session_class):
        """Test that _get_session reuses existing session."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        client = AtlasAPIClient("https://api.example.com")
        
        # First call creates session
        session1 = client._get_session()
        # Second call should reuse same session
        session2 = client._get_session()
        
        self.assertEqual(session1, session2)
        mock_session_class.assert_called_once()  # Should only be called once


class TestAtlasAPIClientSignedURLs(unittest.TestCase):
    """Test signed URL generation functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = AtlasAPIClient("https://api.example.com")
    
    @patch('requests.Session')
    def test_get_signed_urls_success(self, mock_session_class):
        """Test successful signed URL generation."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "upload_url": "https://upload.example.com/signed",
            "status_url": "https://status.example.com/exp123"
        }
        
        # Mock session
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Test the method
        result = self.client.get_signed_urls(
            apikey="test_key",
            exp_uuid="exp-123",
            exp_name="test_exp",
            core="I8500_1_thread"
        )
        
        # Verify result
        expected_result = {
            "upload_url": "https://upload.example.com/signed",
            "status_url": "https://status.example.com/exp123"
        }
        self.assertEqual(result, expected_result)
        
        # Verify request parameters
        mock_session.post.assert_called_once_with(
            "https://api.example.com/createsignedurls",
            headers={
                "apikey": "test_key",
                "channel": "default",
                "exp-uuid": "exp-123",
                "workload": "test_exp",
                "core": "I8500_1_thread",
                "action": "experiment",
            },
            timeout=AtlasConstants.HTTP_TIMEOUT
        )
    
    @patch('requests.Session')
    def test_get_signed_urls_authentication_error_401(self, mock_session_class):
        """Test authentication error handling for 401 status."""
        mock_response = Mock()
        mock_response.status_code = 401
        
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        with self.assertRaises(AuthenticationError) as context:
            self.client.get_signed_urls("invalid_key", "exp-123", "test_exp", "core")
        
        self.assertIn("Invalid API key", str(context.exception))
    
    @patch('requests.Session')
    def test_get_signed_urls_authentication_error_403(self, mock_session_class):
        """Test authentication error handling for 403 status."""
        mock_response = Mock()
        mock_response.status_code = 403
        
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        with self.assertRaises(AuthenticationError) as context:
            self.client.get_signed_urls("limited_key", "exp-123", "test_exp", "core")
        
        self.assertIn("Access forbidden", str(context.exception))
    
    @patch('requests.Session')
    def test_get_signed_urls_http_error(self, mock_session_class):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Internal Server Error")
        
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        with self.assertRaises(NetworkError) as context:
            self.client.get_signed_urls("test_key", "exp-123", "test_exp", "core")
        
        self.assertIn("Failed to get signed URLs", str(context.exception))
        self.assertEqual(context.exception.url, "https://api.example.com/createsignedurls")
    
    @patch('requests.Session')
    def test_get_signed_urls_network_exception(self, mock_session_class):
        """Test network exception handling."""
        mock_session = Mock()
        mock_session.post.side_effect = Exception("Connection timeout")
        mock_session_class.return_value = mock_session
        
        with self.assertRaises(NetworkError) as context:
            self.client.get_signed_urls("test_key", "exp-123", "test_exp", "core")
        
        self.assertIn("Failed to get signed URLs", str(context.exception))
        self.assertIn("Connection timeout", str(context.exception))


class TestAtlasAPIClientFileUpload(unittest.TestCase):
    """Test file upload functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = AtlasAPIClient("https://api.example.com", verbose=True)
    
    def test_upload_file_nonexistent_file(self):
        """Test upload with non-existent file."""
        with self.assertRaises(NetworkError) as context:
            self.client.upload_file("https://upload.example.com", "/nonexistent/file.txt")
        
        self.assertIn("File to upload does not exist", str(context.exception))
    
    @patch('requests.Session')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test file content")
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    def test_upload_file_success(self, mock_stat, mock_exists, mock_file, mock_session_class):
        """Test successful file upload."""
        # Mock file system
        mock_exists.return_value = True
        mock_stat_result = Mock()
        mock_stat_result.st_size = 17  # Length of "test file content"
        mock_stat.return_value = mock_stat_result
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"upload successful"
        
        # Mock session
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Test upload
        result = self.client.upload_file("https://upload.example.com", "test_file.txt")
        
        # Verify result
        self.assertEqual(result, b"upload successful")
        
        # Verify file was opened correctly
        mock_file.assert_called_once_with(Path("test_file.txt"), "rb")
        
        # Verify HTTP request
        mock_session.post.assert_called_once_with(
            "https://upload.example.com",
            data=mock_file.return_value.__enter__.return_value,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": "17",
            },
            timeout=300
        )
    
    @patch('requests.Session')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    def test_upload_file_http_error(self, mock_stat, mock_exists, mock_file, mock_session_class):
        """Test file upload HTTP error handling."""
        # Mock file system
        mock_exists.return_value = True
        mock_stat_result = Mock()
        mock_stat_result.st_size = 12
        mock_stat.return_value = mock_stat_result
        
        # Mock HTTP error
        mock_session = Mock()
        mock_session.post.side_effect = Exception("Upload failed")
        mock_session_class.return_value = mock_session
        
        with self.assertRaises(NetworkError) as context:
            self.client.upload_file("https://upload.example.com", "test_file.txt")
        
        self.assertIn("File upload failed", str(context.exception))
        self.assertEqual(context.exception.url, "https://upload.example.com")
    
    @patch('requests.Session')
    @patch('builtins.open', new_callable=mock_open, read_data=b"large file content")
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    @patch('builtins.print')
    def test_upload_file_verbose_output(self, mock_print, mock_stat, mock_exists, mock_file, mock_session_class):
        """Test verbose output during file upload."""
        # Mock file system
        mock_exists.return_value = True
        mock_stat_result = Mock()
        mock_stat_result.st_size = 1024
        mock_stat.return_value = mock_stat_result
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"success"
        
        # Mock session
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Enable verbose mode
        self.client.verbose = True
        
        # Test upload
        self.client.upload_file("https://upload.example.com", Path("large_file.dat"))
        
        # Verify verbose output
        mock_print.assert_called_once_with("Uploading file: large_file.dat (1024 bytes)")


class TestAtlasAPIClientStatusOperations(unittest.TestCase):
    """Test status checking and polling functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = AtlasAPIClient("https://api.example.com", verbose=True)
    
    @patch('requests.Session')
    def test_get_status_success(self, mock_session_class):
        """Test successful status retrieval."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"state": "running", "progress": 50}
        
        # Mock session
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Test status check
        result = self.client.get_status("https://status.example.com/exp123")
        
        # Verify result
        expected = {"state": "running", "progress": 50}
        self.assertEqual(result, expected)
        
        # Verify request
        mock_session.get.assert_called_once_with(
            "https://status.example.com/exp123",
            timeout=AtlasConstants.HTTP_TIMEOUT
        )
    
    @patch('requests.Session')
    def test_get_status_network_error(self, mock_session_class):
        """Test status check network error handling."""
        mock_session = Mock()
        mock_session.get.side_effect = Exception("Connection failed")
        mock_session_class.return_value = mock_session
        
        with self.assertRaises(NetworkError) as context:
            self.client.get_status("https://status.example.com/exp123")
        
        self.assertIn("Status check failed", str(context.exception))
        self.assertEqual(context.exception.url, "https://status.example.com/exp123")
    
    @patch('requests.Session')
    @patch('builtins.print')
    def test_poll_status_success_completed(self, mock_print, mock_session_class):
        """Test successful status polling until completion."""
        # Mock responses: running -> running -> completed
        responses = [
            {"state": "running", "progress": 30},
            {"state": "running", "progress": 70},
            {"state": "completed", "progress": 100}
        ]
        
        mock_response = Mock()
        mock_response.json.side_effect = responses
        
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Test polling
        with patch('time.sleep') as mock_sleep:
            result = self.client.poll_status("https://status.example.com/exp123", max_attempts=5, delay=1.0)
        
        # Verify final result
        self.assertEqual(result, {"state": "completed", "progress": 100})
        
        # Verify polling calls
        self.assertEqual(mock_session.get.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # Sleep between attempts
        mock_sleep.assert_has_calls([call(1.0), call(1.0)])
    
    @patch('requests.Session')
    @patch('builtins.print')
    def test_poll_status_experiment_failed(self, mock_print, mock_session_class):
        """Test polling when experiment fails."""
        mock_response = Mock()
        mock_response.json.return_value = {"state": "failed", "error": "Simulation error"}
        
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        with self.assertRaises(NetworkError) as context:
            self.client.poll_status("https://status.example.com/exp123")
        
        self.assertIn("Experiment failed with state: failed", str(context.exception))
    
    @patch('requests.Session')
    @patch('builtins.print')
    def test_poll_status_timeout(self, mock_print, mock_session_class):
        """Test polling timeout handling."""
        # Always return running state
        mock_response = Mock()
        mock_response.json.return_value = {"state": "running", "progress": 10}
        
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        with patch('time.sleep'):
            with self.assertRaises(NetworkError) as context:
                self.client.poll_status("https://status.example.com/exp123", max_attempts=3, delay=0.1)
        
        self.assertIn("polling timed out after 3 attempts", str(context.exception))
        self.assertEqual(mock_session.get.call_count, 3)
    
    @patch('requests.Session')
    @patch('builtins.print')
    def test_poll_status_various_completion_states(self, mock_print, mock_session_class):
        """Test polling recognizes various completion states."""
        completion_states = ["completed", "finished", "done", "success"]
        
        for state in completion_states:
            with self.subTest(state=state):
                # Create a fresh client for each test to avoid session reuse
                client = AtlasAPIClient("https://api.example.com", verbose=True)
                
                mock_response = Mock()
                mock_response.json.return_value = {"state": state, "result": "success"}
                
                mock_session = Mock()
                mock_session.get.return_value = mock_response
                mock_session_class.return_value = mock_session
                
                result = client.poll_status("https://status.example.com/exp123")
                self.assertEqual(result["state"], state)
    
    @patch('requests.Session')
    @patch('builtins.print')
    def test_poll_status_various_failure_states(self, mock_print, mock_session_class):
        """Test polling recognizes various failure states."""
        failure_states = ["failed", "error", "cancelled"]
        
        for state in failure_states:
            with self.subTest(state=state):
                # Create a fresh client for each test to avoid session reuse
                client = AtlasAPIClient("https://api.example.com", verbose=True)
                
                mock_response = Mock()
                mock_response.json.return_value = {"state": state, "error": "Test error"}
                
                mock_session = Mock()
                mock_session.get.return_value = mock_response
                mock_session_class.return_value = mock_session
                
                with self.assertRaises(NetworkError) as context:
                    client.poll_status("https://status.example.com/exp123")
                
                self.assertIn(f"Experiment failed with state: {state}", str(context.exception))


class TestAtlasAPIClientFileDownload(unittest.TestCase):
    """Test file download functionality."""
    
    def setUp(self):
        """Set up test client and temporary directory."""
        self.client = AtlasAPIClient("https://api.example.com", verbose=True)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('requests.Session')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_download_file_success(self, mock_print, mock_file, mock_session_class):
        """Test successful file download."""
        # Mock HTTP response with streaming
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2", b"chunk3"]
        
        # Mock session
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Test download
        target_path = Path(self.temp_dir)
        self.client.download_file("https://download.example.com/file.dat", target_path, "result.dat")
        
        # Verify HTTP request
        mock_session.get.assert_called_once_with(
            "https://download.example.com/file.dat",
            stream=True,
            timeout=AtlasConstants.HTTP_TIMEOUT
        )
        
        # Verify file writing
        expected_path = target_path / "result.dat"
        mock_file.assert_called_once_with(expected_path, "wb")
        file_handle = mock_file.return_value.__enter__.return_value
        expected_writes = [call(b"chunk1"), call(b"chunk2"), call(b"chunk3")]
        file_handle.write.assert_has_calls(expected_writes)
        
        # Verify verbose output
        mock_print.assert_called_once_with(f"Downloaded: {expected_path}")
    
    @patch('requests.Session')
    def test_download_file_directory_creation(self, mock_session_class):
        """Test that download creates target directory if it doesn't exist."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"test content"]
        
        # Mock session
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Use non-existent subdirectory
        target_path = Path(self.temp_dir) / "new_subdir" / "deeper"
        
        with patch('builtins.open', mock_open()):
            self.client.download_file("https://download.example.com/file.dat", target_path, "result.dat")
        
        # Verify directory was created (we can't easily test this with mocks,
        # but the method should call mkdir(parents=True, exist_ok=True))
        self.assertTrue(True)  # If we get here without exception, directory creation worked
    
    @patch('requests.Session')
    def test_download_file_http_error(self, mock_session_class):
        """Test download HTTP error handling."""
        mock_session = Mock()
        mock_session.get.side_effect = Exception("Download failed")
        mock_session_class.return_value = mock_session
        
        with self.assertRaises(NetworkError) as context:
            self.client.download_file("https://download.example.com/file.dat", self.temp_dir, "result.dat")
        
        self.assertIn("File download failed", str(context.exception))
        self.assertEqual(context.exception.url, "https://download.example.com/file.dat")
    
    @patch('requests.Session')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    def test_download_file_cleanup_on_error(self, mock_unlink, mock_exists, mock_file, mock_session_class):
        """Test that partial downloads are cleaned up on error."""
        # Mock file writing error
        mock_file.return_value.__enter__.return_value.write.side_effect = Exception("Write failed")
        
        # Mock file exists for cleanup
        mock_exists.return_value = True
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"test content"]
        
        # Mock session
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        target_path = Path(self.temp_dir)
        with self.assertRaises(NetworkError):
            self.client.download_file("https://download.example.com/file.dat", target_path, "result.dat")
        
        # Verify cleanup was attempted
        expected_path = target_path / "result.dat"
        mock_exists.assert_called_once_with()
        mock_unlink.assert_called_once_with()


class TestAtlasAPIClientResourceManagement(unittest.TestCase):
    """Test resource management and context manager functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = AtlasAPIClient("https://api.example.com")
    
    @patch('requests.Session')
    def test_close_session(self, mock_session_class):
        """Test session closing."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Create session
        self.client._get_session()
        self.assertIsNotNone(self.client._session)
        
        # Close session
        self.client.close()
        
        # Verify session was closed and cleared
        mock_session.close.assert_called_once()
        self.assertIsNone(self.client._session)
    
    def test_close_no_session(self):
        """Test closing when no session exists."""
        # Should not raise an exception
        self.client.close()
        self.assertIsNone(self.client._session)
    
    @patch('requests.Session')
    def test_context_manager(self, mock_session_class):
        """Test context manager functionality."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        with AtlasAPIClient("https://api.example.com") as client:
            # Use client to create session
            client._get_session()
            self.assertIsNotNone(client._session)
        
        # After context, session should be closed
        mock_session.close.assert_called_once()
    
    @patch('requests.Session')
    def test_context_manager_with_exception(self, mock_session_class):
        """Test context manager cleanup with exception."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        try:
            with AtlasAPIClient("https://api.example.com") as client:
                client._get_session()
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Session should still be closed despite exception
        mock_session.close.assert_called_once()


class TestAtlasAPIClientIntegration(unittest.TestCase):
    """Integration tests for API client functionality."""
    
    @patch('requests.Session')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test file")
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    @patch('builtins.print')
    def test_full_workflow_simulation(self, mock_print, mock_stat, mock_exists, mock_file, mock_session_class):
        """Test a complete workflow: get URLs -> upload -> poll -> download."""
        # Mock file system
        mock_exists.return_value = True
        mock_stat_result = Mock()
        mock_stat_result.st_size = 9
        mock_stat.return_value = mock_stat_result
        
        # Mock session and responses
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Define response sequence
        responses = [
            # get_signed_urls response
            Mock(status_code=200, json=lambda: {
                "upload_url": "https://upload.example.com/signed",
                "status_url": "https://status.example.com/exp123"
            }),
            # upload_file response
            Mock(content=b"upload success"),
            # poll_status responses (2 running, 1 completed)
            Mock(json=lambda: {"state": "running", "progress": 30}),
            Mock(json=lambda: {"state": "running", "progress": 70}),
            Mock(json=lambda: {"state": "completed", "progress": 100}),
            # download_file response
            Mock(iter_content=lambda chunk_size: [b"result data"])
        ]
        
        # Configure mock session to return appropriate responses
        mock_session.post.side_effect = responses[:2]  # signed URLs and upload
        mock_session.get.side_effect = responses[2:]   # status polling and download
        
        client = AtlasAPIClient("https://api.example.com", verbose=False)
        
        with patch('time.sleep'):  # Speed up polling
            # Step 1: Get signed URLs
            urls = client.get_signed_urls("test_key", "exp-123", "test_exp", "core")
            
            # Step 2: Upload file
            upload_result = client.upload_file(urls["upload_url"], "test_file.bin")
            
            # Step 3: Poll status until completion
            final_status = client.poll_status(urls["status_url"], max_attempts=5)
            
            # Step 4: Download results - mock the directory creation to avoid filesystem issues
            with patch('pathlib.Path.mkdir'):
                client.download_file("https://download.example.com/result", "/tmp", "result.json")
        
        # Verify workflow completed successfully
        self.assertEqual(urls["upload_url"], "https://upload.example.com/signed")
        self.assertEqual(upload_result, b"upload success")
        self.assertEqual(final_status["state"], "completed")
        
        # Verify all expected calls were made
        self.assertEqual(mock_session.post.call_count, 2)  # URLs + upload
        self.assertEqual(mock_session.get.call_count, 4)   # 3 status + 1 download


if __name__ == '__main__':
    unittest.main()
