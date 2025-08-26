"""Custom exception classes for Atlas Explorer.

This module defines a hierarchy of exceptions that provide better error handling
and debugging capabilities compared to generic Python exceptions.
"""

from typing import Optional, Dict, Any


class AtlasExplorerError(Exception):
    """Base exception for all Atlas Explorer errors.
    
    All other Atlas Explorer exceptions inherit from this base class,
    allowing for catch-all error handling when needed.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(AtlasExplorerError):
    """Raised when API authentication fails.
    
    This includes invalid API keys, expired tokens, insufficient permissions,
    or other authentication-related failures.
    """
    pass


class NetworkError(AtlasExplorerError):
    """Raised for network-related failures.
    
    This includes connection timeouts, DNS resolution failures, 
    HTTP errors, and other network connectivity issues.
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 url: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.url = url


class EncryptionError(AtlasExplorerError):
    """Raised when encryption/decryption operations fail.
    
    This includes key generation failures, cipher errors, 
    invalid encrypted data, and other cryptographic issues.
    """
    pass


class ELFValidationError(AtlasExplorerError):
    """Raised when ELF file validation fails.
    
    This includes invalid ELF format, missing sections, 
    unsupported architectures, and other ELF-related issues.
    """
    
    def __init__(self, message: str, elf_path: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.elf_path = elf_path


class ExperimentError(AtlasExplorerError):
    """Raised during experiment execution.
    
    This includes experiment configuration errors, execution failures,
    timeout issues, and other experiment-related problems.
    """
    
    def __init__(self, message: str, experiment_id: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.experiment_id = experiment_id


class ConfigurationError(AtlasExplorerError):
    """Raised when configuration is invalid or missing.
    
    This includes missing required settings, invalid values,
    and configuration file issues.
    """
    pass
