#!/usr/bin/env python3
"""
AtlasExplorer client for Atlas Explorer - Phase 1.2 Extraction

This module contains the AtlasExplorer class extracted from the monolithic atlasexplorer.py
with modern Python patterns, type safety, and dependency injection.
"""

import sys
import json
from typing import Optional, Dict, Any, List

import requests

from ..utils.exceptions import (
    AtlasExplorerError,
    AuthenticationError,
    NetworkError,
    ConfigurationError
)
from ..core.config import AtlasConfig
from ..core.constants import AtlasConstants


class AtlasExplorer:
    """
    Main client for interacting with the Atlas Explorer cloud platform.
    
    This class handles:
    - Authentication and configuration management
    - Cloud capability discovery and validation
    - Core architecture information retrieval
    - Signed URL generation for secure uploads
    - Worker status monitoring
    """
    
    def __init__(self, apikey: Optional[str] = None, channel: Optional[str] = None, 
                 region: Optional[str] = None, verbose: bool = False):
        """
        Initialize Atlas Explorer client with credentials.
        
        Args:
            apikey: API key for authentication (loaded from config if None)
            channel: Channel identifier (loaded from config if None)
            region: Region identifier (loaded from config if None)
            verbose: Enable verbose logging output
            
        Raises:
            ConfigurationError: If configuration cannot be loaded
            AuthenticationError: If authentication fails
            NetworkError: If worker status check fails
        """
        self.verbose = verbose
        
        # Load configuration
        self.config = AtlasConfig(
            verbose=verbose, 
            apikey=apikey, 
            channel=channel, 
            region=region
        )
        
        if not self.config.hasConfig:
            raise ConfigurationError(
                "Cloud connection is not setup. Please run atlas explorer configuration."
            )
        
        # Initialize cloud capabilities cache
        self.versionCaps: Optional[Dict[str, Any]] = None
        self.channelCaps: Optional[List[Dict[str, Any]]] = None
        
        # Check worker status if gateway is configured
        if hasattr(self.config, "gateway") and self.config.gateway:
            worker_status = self._check_worker_status()
            if worker_status and worker_status.get("status") is False:
                raise NetworkError("Atlas Explorer service is down, please try later")
        else:
            if self.verbose:
                print("Warning: Gateway is not set. Skipping worker status check.")
    
    def _getCloudCaps(self, version: str) -> None:
        """
        Fetch cloud capabilities for specified version.
        
        Args:
            version: API version to fetch capabilities for
            
        Raises:
            NetworkError: If capabilities cannot be fetched
            ConfigurationError: If gateway is not configured
        """
        if self.config.gateway is None:
            raise ConfigurationError(
                "Gateway is not configured. Cannot fetch cloud capabilities. "
                "This usually means there's an issue with the API service or your configuration. "
                "Please reconfigure your settings."
            )
        
        url = f"{self.config.gateway}/cloudcaps"
        headers = {
            "Content-Type": "application/json",
            "apikey": self.config.apikey,
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise NetworkError(f"Error fetching cloud capabilities: {e}")
        
        try:
            self.channelCaps = resp.json()
        except json.JSONDecodeError as e:
            raise NetworkError(f"Invalid JSON response from cloud capabilities API: {e}")
        
        # Find capabilities for specific version
        if isinstance(self.channelCaps, list):
            for cap in self.channelCaps:
                if cap.get("version") == version:
                    self.versionCaps = cap
                    return
            
            raise NetworkError(f"No capabilities found for version {version}")
        else:
            raise NetworkError("Unexpected format for cloud capabilities response")
    
    def getCoreInfo(self, core: str) -> Dict[str, Any]:
        """
        Get architecture information for specified core.
        
        Args:
            core: Core identifier (e.g., 'I8500', 'P8500')
            
        Returns:
            Dictionary containing core architecture information
            
        Raises:
            NetworkError: If core is not supported
            ConfigurationError: If cloud capabilities not fetched
        """
        if self.versionCaps is None:
            raise ConfigurationError(
                "Cloud capabilities not fetched. Please run _getCloudCaps first."
            )
        
        shinro_caps = self.versionCaps.get("shinro")
        if not shinro_caps:
            raise NetworkError("No 'shinro' section found in cloud capabilities")
        
        arches = shinro_caps.get("arches")
        if not isinstance(arches, list):
            raise NetworkError("Invalid architecture list in cloud capabilities")
        
        for arch in arches:
            if arch.get("name") == core:
                return arch
        
        raise NetworkError(f"Core {core} is not supported by the cloud capabilities")
    
    def getVersionList(self) -> List[str]:
        """
        Get list of available API versions.
        
        Returns:
            List of available version strings
            
        Raises:
            ConfigurationError: If cloud capabilities not fetched
        """
        if self.channelCaps is None:
            raise ConfigurationError(
                "Cloud capabilities not fetched. Please run _getCloudCaps first."
            )
        
        if isinstance(self.channelCaps, list):
            return [cap.get("version", "") for cap in self.channelCaps if cap.get("version")]
        
        return []
    
    def _check_worker_status(self) -> Dict[str, Any]:
        """
        Check the status of the Atlas Explorer worker.
        
        Returns:
            Dictionary containing worker status information
            
        Raises:
            NetworkError: If status check fails
            ConfigurationError: If gateway not configured
        """
        if self.verbose:
            print("Checking worker status...")
        
        if not hasattr(self.config, "gateway") or not self.config.gateway:
            raise ConfigurationError("Gateway is not set. Cannot check worker status.")
        
        headers = {
            "apikey": self.config.apikey,
            "channel": self.config.channel,
            "region": self.config.region,
        }
        
        url = f"{self.config.gateway}/dataworkerstatus"
        
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            result = resp.json()
            if self.verbose:
                print(f"Worker status response: {result}")
            
            return result
            
        except requests.RequestException as e:
            error_details = ""
            if hasattr(e, 'response') and e.response is not None:
                error_details = f" (Status: {e.response.status_code}, Text: {e.response.text})"
            
            raise NetworkError(f"Error checking worker status: {e}{error_details}")
        except json.JSONDecodeError as e:
            raise NetworkError(f"Invalid JSON response from worker status API: {e}")
    
    def getSignedUrls(self, exp_uuid: str, name: str, core: str) -> requests.Response:
        """
        Get signed URLs for experiment upload and status monitoring.
        
        Args:
            exp_uuid: Unique experiment identifier
            name: Experiment name
            core: Target core identifier
            
        Returns:
            Response object containing signed URLs and metadata
            
        Raises:
            NetworkError: If signed URL generation fails
            ConfigurationError: If gateway not configured
        """
        if not hasattr(self.config, "gateway") or not self.config.gateway:
            raise ConfigurationError("Gateway is not configured")
        
        url = f"{self.config.gateway}/createsignedurls"
        headers = {
            "apikey": self.config.apikey,
            "channel": self.config.channel,
            "exp-uuid": exp_uuid,
            "workload": name,
            "core": core,
            "action": "experiment",
        }
        
        try:
            resp = requests.post(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp
            
        except requests.RequestException as e:
            error_msg = f"Error fetching signed URLs: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" (Status: {e.response.status_code}, Text: {e.response.text})"
            raise NetworkError(error_msg)


def get_channel_list(apikey: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch the list of available channels for the given API key.
    
    Args:
        apikey: API key for authentication
        
    Returns:
        Dictionary containing channel list under 'channels' key
        
    Raises:
        NetworkError: If channel list cannot be fetched
        AuthenticationError: If API key is invalid
    """
    url = f"{AtlasConstants.AE_GLOBAL_API}/channellist"
    headers = {
        "apikey": apikey,
        "extversion": AtlasConstants.API_VERSION
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
        
    except requests.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            error_msg = f"Error fetching channel list: {e.response.status_code} {e.response.text}"
        else:
            error_msg = f"Network error fetching channel list: {e}"
        
        raise NetworkError(error_msg)
    except json.JSONDecodeError as e:
        raise NetworkError(f"Invalid JSON response from channel list API: {e}")


def validate_user_api_key(apikey: str) -> bool:
    """
    Validate if the provided API key is valid.
    
    Args:
        apikey: API key to validate
        
    Returns:
        True if API key is valid, False otherwise
    """
    url = f"{AtlasConstants.AE_GLOBAL_API}/user"
    headers = {"apikey": apikey}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        return response.status_code == 200
    except requests.RequestException:
        return False
