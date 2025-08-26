"""Configuration management for Atlas Explorer.

This module handles loading, validating, and managing configuration
from various sources including environment variables, config files,
and direct parameters.
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path

from .constants import AtlasConstants
from ..utils.exceptions import ConfigurationError, NetworkError


class AtlasConfig:
    """Manages Atlas Explorer configuration from multiple sources.
    
    Configuration is loaded in the following priority order:
    1. Environment variable (MIPS_ATLAS_CONFIG)
    2. User config file (~/.config/mips/atlaspy/config.json)
    3. Direct parameters passed to constructor
    """
    
    def __init__(
        self, 
        readonly: bool = False, 
        verbose: bool = True, 
        apikey: Optional[str] = None, 
        channel: Optional[str] = None, 
        region: Optional[str] = None
    ):
        """Initialize configuration from available sources.
        
        Args:
            readonly: If True, don't attempt to set gateway endpoint
            verbose: Enable verbose logging
            apikey: Direct API key (fallback if no other config found)
            channel: Direct channel (fallback if no other config found)  
            region: Direct region (fallback if no other config found)
        """
        self.verbose = verbose
        self.gateway: Optional[str] = None
        self.hasConfig = False
        
        # Try loading from environment variable first
        if self._load_from_environment():
            if not readonly:
                self._set_gateway_by_channel_region()
        # Try loading from config file
        elif self._load_from_config_file():
            if not readonly:
                self._set_gateway_by_channel_region()
        # Use direct parameters as fallback
        elif apikey and channel and region:
            self.apikey = apikey
            self.channel = channel
            self.region = region
            self.hasConfig = True
            if not readonly:
                self._set_gateway_by_channel_region()
        else:
            self.hasConfig = False
    
    def _load_from_environment(self) -> bool:
        """Load configuration from environment variable.
        
        Returns:
            True if configuration was successfully loaded from environment
        """
        if AtlasConstants.CONFIG_ENVAR not in os.environ:
            return False
            
        try:
            envvarval = os.environ[AtlasConstants.CONFIG_ENVAR]
            data = envvarval.split(":")
            if len(data) != 3:
                if self.verbose:
                    print(f"Warning: {AtlasConstants.CONFIG_ENVAR} should have format 'apikey:channel:region'")
                return False
                
            self.apikey = data[0]
            self.channel = data[1]
            self.region = data[2]
            self.hasConfig = True
            return True
        except Exception as e:
            if self.verbose:
                print(f"Error parsing environment configuration: {e}")
            return False
    
    def _load_from_config_file(self) -> bool:
        """Load configuration from user config file.
        
        Returns:
            True if configuration was successfully loaded from file
        """
        try:
            config_path = self._get_config_file_path()
            if not config_path.exists():
                return False
                
            with open(config_path) as f:
                data = json.load(f)
                
            # Validate required fields
            required_fields = ["apikey", "channel", "region"]
            for field in required_fields:
                if field not in data:
                    if self.verbose:
                        print(f"Warning: Missing '{field}' in config file {config_path}")
                    return False
                    
            self.apikey = data["apikey"]
            self.channel = data["channel"]
            self.region = data["region"]
            self.hasConfig = True
            return True
            
        except (json.JSONDecodeError, IOError, KeyError) as e:
            if self.verbose:
                print(f"Error loading config file: {e}")
            return False
    
    def _get_config_file_path(self) -> Path:
        """Get the path to the user configuration file.
        
        Returns:
            Path to the configuration file
        """
        home_dir = Path.home()
        config_dir = home_dir.joinpath(*AtlasConstants.CONFIG_DIR_PARTS)
        return config_dir / AtlasConstants.CONFIG_FILENAME
    
    def _set_gateway_by_channel_region(self) -> None:
        """Set the API gateway endpoint based on channel and region.
        
        Raises:
            NetworkError: If gateway endpoint cannot be retrieved
            ConfigurationError: If configuration is invalid
        """
        if not all([self.apikey, self.channel, self.region]):
            raise ConfigurationError("Missing required configuration: apikey, channel, or region")
            
        if self.verbose:
            print("Setting up selected gateway...")
            
        url = f"{AtlasConstants.AE_GLOBAL_API}/gwbychannelregion"
        headers = {
            "apikey": self.apikey,
            "channel": self.channel,
            "region": self.region,
        }
        
        try:
            import requests
            response = requests.get(url, headers=headers, timeout=AtlasConstants.HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            endpoint = data.get("endpoint")
            if not endpoint:
                raise ConfigurationError("No 'endpoint' found in response from gateway API")
                
            self.gateway = endpoint
            if self.verbose:
                print(f"Gateway has been set: {self.gateway}")
                
        except requests.RequestException as e:
            error_msg = f"Error connecting to gateway API: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nStatus: {e.response.status_code}\nText: {e.response.text}"
            raise NetworkError(error_msg, getattr(e.response, 'status_code', None), url)
        except (ValueError, KeyError) as e:
            raise ConfigurationError(f"Invalid response from gateway API: {e}")
    
    def save_to_file(self, config_data: Dict[str, Any]) -> None:
        """Save configuration to the user config file.
        
        Args:
            config_data: Dictionary containing configuration to save
            
        Raises:
            ConfigurationError: If config cannot be saved
        """
        try:
            config_path = self._get_config_file_path()
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
                
            if self.verbose:
                print(f"Configuration saved to {config_path}")
                
        except (IOError, json.JSONEncodeError) as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    # Legacy method for backward compatibility
    def setGWbyChannelRegion(self) -> None:
        """Legacy method name - use _set_gateway_by_channel_region instead."""
        self._set_gateway_by_channel_region()
