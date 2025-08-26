"""HTTP client for Atlas Explorer API interactions.

This module provides a robust HTTP client with proper error handling,
timeouts, and retry logic for communicating with Atlas Explorer APIs.
"""

import time
from typing import Dict, Any, Optional, Union
from pathlib import Path

from ..core.constants import AtlasConstants
from ..utils.exceptions import NetworkError, AuthenticationError


class AtlasAPIClient:
    """HTTP client for Atlas Explorer API with robust error handling.
    
    This client provides:
    - Proper timeout handling
    - Status monitoring with polling
    - File upload capabilities
    - JSON response parsing
    - Comprehensive error handling
    """
    
    def __init__(self, base_url: str, verbose: bool = True):
        """Initialize the API client.
        
        Args:
            base_url: Base URL for API endpoints
            verbose: Enable verbose logging
        """
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self._session = None
    
    def _get_session(self):
        """Get or create HTTP session with proper configuration."""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': f'Atlas-Explorer-Python/{AtlasConstants.VERSION}'
            })
        return self._session
    
    def get_signed_urls(self, apikey: str, exp_uuid: str, exp_name: str, core: str) -> Dict[str, Any]:
        """Get signed URLs for experiment upload.
        
        Args:
            apikey: API authentication key
            exp_uuid: Experiment UUID
            exp_name: Experiment name
            core: Core configuration
            
        Returns:
            Dictionary containing signed URLs and metadata
            
        Raises:
            NetworkError: If request fails
            AuthenticationError: If API key is invalid
        """
        url = f"{self.base_url}/createsignedurls"
        headers = {
            "apikey": apikey,
            "channel": "default",  # This should come from config
            "exp-uuid": exp_uuid,
            "workload": exp_name,
            "core": core,
            "action": "experiment",
        }
        
        try:
            session = self._get_session()
            response = session.post(url, headers=headers, timeout=AtlasConstants.HTTP_TIMEOUT)
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key or insufficient permissions")
            elif response.status_code == 403:
                raise AuthenticationError("Access forbidden - check your permissions")
            
            response.raise_for_status()
            return response.json()
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise NetworkError(f"Failed to get signed URLs: {e}", url=url)
    
    def upload_file(self, url: str, file_path: Union[str, Path]) -> bytes:
        """Upload a file to the given URL.
        
        Args:
            url: Upload URL (typically a signed URL)
            file_path: Path to file to upload
            
        Returns:
            Response content
            
        Raises:
            NetworkError: If upload fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise NetworkError(f"File to upload does not exist: {file_path}")
        
        if self.verbose:
            print(f"Uploading file: {file_path.name} ({file_path.stat().st_size} bytes)")
        
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(file_path.stat().st_size),
        }
        
        try:
            session = self._get_session()
            with open(file_path, "rb") as f:
                response = session.post(
                    url, 
                    data=f, 
                    headers=headers,
                    timeout=300  # Longer timeout for file uploads
                )
            
            response.raise_for_status()
            return response.content
            
        except Exception as e:
            raise NetworkError(f"File upload failed: {e}", url=url)
    
    def get_status(self, status_url: str) -> Dict[str, Any]:
        """Get experiment status from status URL.
        
        Args:
            status_url: Status endpoint URL
            
        Returns:
            Status information as dictionary
            
        Raises:
            NetworkError: If status check fails
        """
        try:
            session = self._get_session()
            response = session.get(status_url, timeout=AtlasConstants.HTTP_TIMEOUT)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            raise NetworkError(f"Status check failed: {e}", url=status_url)
    
    def poll_status(self, status_url: str, max_attempts: int = 10, delay: float = 2.0) -> Dict[str, Any]:
        """Poll experiment status until completion or timeout.
        
        Args:
            status_url: Status endpoint URL
            max_attempts: Maximum number of polling attempts
            delay: Delay between polling attempts (seconds)
            
        Returns:
            Final status information
            
        Raises:
            NetworkError: If polling fails or times out
        """
        for attempt in range(max_attempts):
            try:
                status = self.get_status(status_url)
                
                if self.verbose:
                    print(f"Status check {attempt + 1}/{max_attempts}: {status.get('state', 'unknown')}")
                
                # Check if experiment is complete (this logic may need adjustment based on actual API)
                state = status.get('state', '').lower()
                if state in ['completed', 'finished', 'done', 'success']:
                    return status
                elif state in ['failed', 'error', 'cancelled']:
                    raise NetworkError(f"Experiment failed with state: {state}")
                
                if attempt < max_attempts - 1:
                    time.sleep(delay)
                    
            except NetworkError:
                raise
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise NetworkError(f"Status polling failed: {e}")
                time.sleep(delay)
        
        raise NetworkError(f"Experiment status polling timed out after {max_attempts} attempts")
    
    def download_file(self, url: str, target_path: Union[str, Path], filename: str) -> None:
        """Download a file from URL to target location.
        
        Args:
            url: Download URL
            target_path: Target directory path
            filename: Target filename
            
        Raises:
            NetworkError: If download fails
        """
        target_path = Path(target_path)
        target_path.mkdir(parents=True, exist_ok=True)
        
        full_path = target_path / filename
        
        try:
            session = self._get_session()
            response = session.get(url, stream=True, timeout=AtlasConstants.HTTP_TIMEOUT)
            response.raise_for_status()
            
            with open(full_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if self.verbose:
                print(f"Downloaded: {full_path}")
                
        except Exception as e:
            # Clean up partial download
            if full_path.exists():
                full_path.unlink()
            raise NetworkError(f"File download failed: {e}", url=url)
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
