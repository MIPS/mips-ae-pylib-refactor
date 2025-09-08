"""
Tests for the main atlasexplorer __init__.py module.
"""

import unittest
import warnings
from unittest.mock import patch

import atlasexplorer


class TestAtlasExplorerInit(unittest.TestCase):
    """Test the main atlasexplorer package initialization."""

    def test_version_attributes(self):
        """Test that version attributes are properly defined."""
        self.assertTrue(hasattr(atlasexplorer, '__version__'))
        self.assertTrue(hasattr(atlasexplorer, '__author__'))
        self.assertEqual(atlasexplorer.__version__, "3.0.0")
        self.assertEqual(atlasexplorer.__author__, "MIPS Technologies")

    def test_main_exports(self):
        """Test that main classes are properly exported."""
        # Test core exports
        self.assertTrue(hasattr(atlasexplorer, 'AtlasExplorer'))
        self.assertTrue(hasattr(atlasexplorer, 'Experiment'))
        self.assertTrue(hasattr(atlasexplorer, 'SummaryReport'))
        self.assertTrue(hasattr(atlasexplorer, 'AtlasConfig'))
        self.assertTrue(hasattr(atlasexplorer, 'AtlasConstants'))
        
        # Test module exports
        self.assertTrue(hasattr(atlasexplorer, 'SecureEncryption'))
        self.assertTrue(hasattr(atlasexplorer, 'AtlasAPIClient'))
        self.assertTrue(hasattr(atlasexplorer, 'ELFAnalyzer'))
        self.assertTrue(hasattr(atlasexplorer, 'AtlasExplorerCLI'))

    def test_exception_exports(self):
        """Test that exception classes are properly exported."""
        exception_classes = [
            'AtlasExplorerError',
            'AuthenticationError',
            'NetworkError',
            'EncryptionError',
            'ELFValidationError',
            'ExperimentError',
            'ConfigurationError'
        ]
        
        for exception_class in exception_classes:
            self.assertTrue(hasattr(atlasexplorer, exception_class))

    def test_legacy_exports(self):
        """Test that legacy classes are properly exported."""
        legacy_classes = [
            'LegacyAtlasExplorer',
            'LegacyExperiment', 
            'LegacySummaryReport',
            'LegacyAtlasConfig',
            'LegacyAtlasConstants'
        ]
        
        for legacy_class in legacy_classes:
            self.assertTrue(hasattr(atlasexplorer, legacy_class))

    def test_warn_legacy_usage_function(self):
        """Test the _warn_legacy_usage function to achieve 100% coverage."""
        # This test covers line 105 in __init__.py
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")  # Capture all warnings
            
            # Call the function to trigger the warning (covers line 105)
            atlasexplorer._warn_legacy_usage("OldClass", "NewClass")
            
            # Verify warning was issued
            self.assertEqual(len(warning_list), 1)
            self.assertTrue(issubclass(warning_list[0].category, DeprecationWarning))
            self.assertIn("'OldClass' is deprecated", str(warning_list[0].message))
            self.assertIn("Use 'NewClass' instead", str(warning_list[0].message))
            self.assertIn("will be removed in v3.0", str(warning_list[0].message))

    def test_all_exports_defined(self):
        """Test that __all__ contains all expected exports."""
        expected_exports = {
            # Version info
            "__version__", "__author__",
            # Main classes
            "AtlasExplorer", "Experiment", "SummaryReport",
            # Configuration and constants
            "AtlasConfig", "AtlasConstants",
            # Security
            "SecureEncryption",
            # Network
            "AtlasAPIClient", 
            # Analysis
            "ELFAnalyzer",
            # CLI
            "AtlasExplorerCLI",
            # CLI Functions for legacy compatibility
            "configure", "subcmd_configure",
            # External dependencies for legacy compatibility
            "Cipher", "ELFFile", "load_dotenv", "prompt", "scrypt", "default_backend",
            # Exceptions
            "AtlasExplorerError", "AuthenticationError", "NetworkError",
            "EncryptionError", "ELFValidationError", "ExperimentError", "ConfigurationError",
            # Legacy compatibility
            "LegacyAtlasExplorer", "LegacyExperiment", "LegacySummaryReport",
            "LegacyAtlasConfig", "LegacyAtlasConstants"
        }
        
        self.assertEqual(set(atlasexplorer.__all__), expected_exports)


if __name__ == '__main__':
    unittest.main()
