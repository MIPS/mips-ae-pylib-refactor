"""Constants used throughout Atlas Explorer.

This module contains all configuration constants, API endpoints,
and other static values used across the application.
"""

import os


class AtlasConstants:
    """Global constants for Atlas Explorer configuration."""
    
    # API Configuration
    AE_GLOBAL_API = "https://gyrfalcon.api.mips.com"
    CONFIG_ENVAR = "MIPS_ATLAS_CONFIG"
    
    # API Version (changing this may break the API)
    API_EXT_VERSION = os.environ.get("API_EXT_VERSION", "0.0.97")
    
    # Timeout Configuration (seconds)
    DEFAULT_TIMEOUT = 300
    HTTP_TIMEOUT = 10
    
    # Security Configuration
    SCRYPT_N = 16384
    SCRYPT_R = 8
    SCRYPT_P = 1
    AES_KEY_SIZE = 32
    
    # File Configuration
    CONFIG_DIR_PARTS = [".config", "mips", "atlaspy"]
    CONFIG_FILENAME = "config.json"
    
    # Experiment Configuration
    DEFAULT_TOOLS_VERSION = "latest"
    DEFAULT_PLUGIN_VERSION = "0.0.97"
    DEFAULT_HEARTBEAT = "104723"
    DEFAULT_ISS = "esesc"
    CLIENT_TYPE = "python"
    VERSION = "1.0.0"
