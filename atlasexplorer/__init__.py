"""Atlas Explorer Python Library - Modular Architecture.

This package provides a modular, secure, and well-tested interface for 
Atlas Explorer cloud-based performance analysis.

Key Modules:
    core: Configuration and constants
    security: Encryption and authentication
    network: HTTP client and API communication
    analysis: ELF parsing and report analysis
    cli: Command-line interface
    utils: Exceptions and utilities

Example Usage:
    >>> from atlasexplorer import AtlasExplorer, Experiment
    >>> explorer = AtlasExplorer()
    >>> experiment = explorer.create_experiment("my_experiment")
    >>> experiment.add_workload("path/to/binary.elf")
    >>> experiment.set_core("I8500_(1_thread)")
    >>> experiment.run()
"""

# Version information
__version__ = "2.0.0"
__author__ = "MIPS Technologies"

# Legacy imports for backward compatibility
from .atlasexplorer import (
    AtlasExplorer as LegacyAtlasExplorer,
    Experiment as LegacyExperiment,
    SummaryReport as LegacySummaryReport,
    AtlasConfig as LegacyAtlasConfig,
    AtlasConstants as LegacyAtlasConstants
)

# New modular imports
from .core import AtlasConfig, AtlasConstants
from .security import SecureEncryption
from .network import AtlasAPIClient
from .analysis import ELFAnalyzer, SummaryReport
from .cli import AtlasExplorerCLI
from .utils import (
    AtlasExplorerError,
    AuthenticationError,
    NetworkError,
    EncryptionError,
    ELFValidationError,
    ExperimentError,
    ConfigurationError
)

# Future modular classes (to be implemented in subsequent steps)
# from .core import AtlasExplorer, Experiment

# Backward compatibility aliases
AtlasExplorer = LegacyAtlasExplorer  # Will be replaced with new implementation
Experiment = LegacyExperiment        # Will be replaced with new implementation

# Main public API exports
__all__ = [
    # Version info
    "__version__",
    "__author__",
    
    # Main classes (currently legacy, will be replaced)
    "AtlasExplorer",
    "Experiment", 
    "SummaryReport",
    
    # Configuration and constants
    "AtlasConfig",
    "AtlasConstants",
    
    # Security
    "SecureEncryption",
    
    # Network
    "AtlasAPIClient",
    
    # Analysis
    "ELFAnalyzer",
    
    # CLI
    "AtlasExplorerCLI",
    
    # Exceptions
    "AtlasExplorerError",
    "AuthenticationError",
    "NetworkError", 
    "EncryptionError",
    "ELFValidationError",
    "ExperimentError",
    "ConfigurationError",
    
    # Legacy compatibility (marked for deprecation)
    "LegacyAtlasExplorer",
    "LegacyExperiment",
    "LegacySummaryReport",
    "LegacyAtlasConfig",
    "LegacyAtlasConstants"
]

# Deprecation warnings for legacy usage
import warnings

def _warn_legacy_usage(old_name: str, new_name: str):
    """Issue deprecation warning for legacy usage."""
    warnings.warn(
        f"'{old_name}' is deprecated and will be removed in v3.0. "
        f"Use '{new_name}' instead.",
        DeprecationWarning,
        stacklevel=3
    )

# Note: Deprecation warnings will be enabled in Phase 2 after new classes are implemented