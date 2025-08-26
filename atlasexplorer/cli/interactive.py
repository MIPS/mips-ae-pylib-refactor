"""Interactive configuration interface.

This module provides an interactive configuration experience for setting up
Atlas Explorer credentials and settings.
"""

import os
import json
from typing import Dict, Any, Optional

from ..core.config import AtlasConfig
from ..core.constants import AtlasConstants
from ..utils.exceptions import ConfigurationError, AuthenticationError


class InteractiveConfig:
    """Interactive configuration manager for Atlas Explorer.
    
    This class provides a user-friendly interface for configuring
    API credentials and connection settings.
    """
    
    def __init__(self, verbose: bool = True):
        """Initialize interactive configuration.
        
        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
    
    def run_configuration(self) -> None:
        """Run the interactive configuration process."""
        print("Atlas Explorer Configuration")
        print("=" * 40)
        
        # Load existing configuration if available
        config = AtlasConfig(readonly=True, verbose=self.verbose)
        
        # Get API key
        default_key = config.apikey if config.hasConfig else ""
        apikey = self._prompt_for_input(
            "Enter your API key",
            default=default_key,
            required=True,
            sensitive=True
        )
        
        # Validate API key
        if not self._validate_api_key(apikey):
            print("Error: Invalid API key. Please check your credentials.")
            return
        
        # Get channel list and let user choose
        channels = self._get_channel_list(apikey)
        if not channels:
            print("Error: Unable to retrieve channel list. Please check your API key.")
            return
        
        print(f"\\nAvailable channels: {', '.join(channels)}")
        
        default_channel = config.channel if config.hasConfig and config.channel in channels else channels[0]
        channel = self._prompt_for_input(
            "Select channel",
            default=default_channel,
            choices=channels,
            required=True
        )
        
        # Get region list and let user choose  
        regions = self._get_region_list(apikey, channel)
        if not regions:
            print("Error: Unable to retrieve region list. Please check your selections.")
            return
        
        print(f"\\nAvailable regions: {', '.join(regions)}")
        
        default_region = config.region if config.hasConfig and config.region in regions else regions[0]
        region = self._prompt_for_input(
            "Select region",
            default=default_region, 
            choices=regions,
            required=True
        )
        
        # Save configuration
        config_data = {
            "apikey": apikey,
            "channel": channel,
            "region": region
        }
        
        try:
            self._save_configuration(config_data)
            print("\\n✓ Configuration saved successfully!")
            print(f"  Channel: {channel}")
            print(f"  Region: {region}")
            
            # Test the configuration
            print("\\nTesting configuration...")
            test_config = AtlasConfig(verbose=False)
            if test_config.hasConfig and test_config.gateway:
                print("✓ Configuration test successful!")
                print(f"  Gateway: {test_config.gateway}")
            else:
                print("⚠ Configuration saved but gateway setup failed.")
                
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def _prompt_for_input(
        self,
        prompt: str,
        default: str = "",
        required: bool = False,
        sensitive: bool = False,
        choices: Optional[list] = None
    ) -> str:
        """Prompt user for input with validation.
        
        Args:
            prompt: Prompt message to display
            default: Default value if user enters nothing
            required: Whether input is required
            sensitive: Whether to hide input (for passwords)
            choices: List of valid choices (if applicable)
            
        Returns:
            User input value
        """
        while True:
            # Format prompt
            prompt_text = prompt
            if default:
                prompt_text += f" [{default}]"
            if choices:
                prompt_text += f" ({'/'.join(choices)})"
            prompt_text += ": "
            
            # Get input
            if sensitive:
                import getpass
                value = getpass.getpass(prompt_text)
            else:
                value = input(prompt_text).strip()
            
            # Use default if no input
            if not value and default:
                value = default
            
            # Validate required fields
            if required and not value:
                print("This field is required.")
                continue
            
            # Validate choices
            if choices and value not in choices:
                print(f"Please choose from: {', '.join(choices)}")
                continue
            
            return value
    
    def _validate_api_key(self, apikey: str) -> bool:
        """Validate API key with the server.
        
        Args:
            apikey: API key to validate
            
        Returns:
            True if API key is valid
        """
        try:
            url = f"{AtlasConstants.AE_GLOBAL_API}/user"
            headers = {"apikey": apikey}
            
            import requests
            response = requests.get(url, headers=headers, timeout=AtlasConstants.HTTP_TIMEOUT)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def _get_channel_list(self, apikey: str) -> list:
        """Get list of available channels for the API key.
        
        Args:
            apikey: API key for authentication
            
        Returns:
            List of available channels
        """
        try:
            url = f"{AtlasConstants.AE_GLOBAL_API}/channellist"
            headers = {
                "apikey": apikey,
                "extversion": AtlasConstants.API_EXT_VERSION
            }
            
            import requests
            response = requests.get(url, headers=headers, timeout=AtlasConstants.HTTP_TIMEOUT)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            return data.get("channels", [])
            
        except Exception:
            return []
    
    def _get_region_list(self, apikey: str, channel: str) -> list:
        """Get list of available regions for the channel.
        
        Args:
            apikey: API key for authentication  
            channel: Selected channel
            
        Returns:
            List of available regions
        """
        # For now, return common regions - this could be enhanced with an API call
        return ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
    
    def _save_configuration(self, config_data: Dict[str, Any]) -> None:
        """Save configuration to both user config file and .env file.
        
        Args:
            config_data: Configuration data to save
        """
        # Save to user config file
        config = AtlasConfig(readonly=True, verbose=False)
        config.save_to_file(config_data)
        
        # Also save to .env file in current directory for project-specific config
        env_file = ".env"
        env_content = f"""# Atlas Explorer Configuration
MIPS_ATLAS_CONFIG={config_data['apikey']}:{config_data['channel']}:{config_data['region']}
API_EXT_VERSION={AtlasConstants.API_EXT_VERSION}
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        if self.verbose:
            print(f"Configuration also saved to {env_file}")


def configure(args) -> None:
    """Legacy function for backward compatibility.
    
    Args:
        args: Command line arguments (unused)
    """
    interactive = InteractiveConfig()
    interactive.run_configuration()
