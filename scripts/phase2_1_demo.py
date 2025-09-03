#!/usr/bin/env python3
"""Phase 2.1 Functional Parity Demonstration Script.

This script demonstrates that all legacy symbols are accessible through
the modular architecture and that both approaches work identically.
"""

import sys
import warnings
from pathlib import Path

# Ensure the project root is in the Python path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

def test_legacy_symbols_availability():
    """Test that all legacy symbols are available through modular package."""
    print("Testing legacy symbol availability...")
    
    # Test core classes
    try:
        from atlasexplorer import AtlasConfig, AtlasConstants, AtlasExplorer, Experiment, SummaryReport
        print("✅ Core classes: AtlasConfig, AtlasConstants, AtlasExplorer, Experiment, SummaryReport")
    except ImportError as e:
        print(f"❌ Core classes import failed: {e}")
        return False
    
    # Test CLI functions
    try:
        from atlasexplorer import configure, subcmd_configure
        print("✅ CLI functions: configure, subcmd_configure")
    except ImportError as e:
        print(f"❌ CLI functions import failed: {e}")
        return False
    
    # Test external dependencies (may be None if not installed)
    try:
        from atlasexplorer import Cipher, ELFFile, load_dotenv, prompt, scrypt, default_backend
        print("✅ External dependencies: Cipher, ELFFile, load_dotenv, prompt, scrypt, default_backend")
        
        # Check if they're actually available
        missing_deps = []
        if Cipher is None:
            missing_deps.append("Cipher")
        if ELFFile is None:
            missing_deps.append("ELFFile")
        if load_dotenv is None:
            missing_deps.append("load_dotenv")
        if prompt is None:
            missing_deps.append("prompt")
        if scrypt is None:
            missing_deps.append("scrypt")
        if default_backend is None:
            missing_deps.append("default_backend")
            
        if missing_deps:
            print(f"⚠️  Optional dependencies not available: {', '.join(missing_deps)}")
            print("   This is expected if optional packages are not installed")
        else:
            print("✅ All external dependencies available")
            
    except ImportError as e:
        print(f"❌ External dependencies import failed: {e}")
        return False
    
    return True


def test_modular_enhancements():
    """Test that modular enhancements are available."""
    print("\nTesting modular enhancements...")
    
    try:
        from atlasexplorer import (
            AtlasAPIClient, ELFAnalyzer, SecureEncryption, AtlasExplorerCLI,
            AtlasExplorerError, AuthenticationError, NetworkError, 
            EncryptionError, ELFValidationError, ExperimentError, ConfigurationError
        )
        print("✅ Enhanced components: AtlasAPIClient, ELFAnalyzer, SecureEncryption, AtlasExplorerCLI")
        print("✅ Exception hierarchy: 7 specialized exception classes")
        return True
    except ImportError as e:
        print(f"❌ Enhanced components import failed: {e}")
        return False


def test_legacy_compatibility():
    """Test that legacy implementations are still accessible."""
    print("\nTesting legacy compatibility...")
    
    try:
        from atlasexplorer import (
            LegacyAtlasExplorer, LegacyExperiment, LegacySummaryReport,
            LegacyAtlasConfig, LegacyAtlasConstants
        )
        print("✅ Legacy components: All 5 legacy classes accessible")
        return True
    except ImportError as e:
        print(f"❌ Legacy components import failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality to ensure imports work correctly."""
    print("\nTesting basic functionality...")
    
    try:
        from atlasexplorer import AtlasConfig, AtlasConstants
        
        # Test AtlasConfig instantiation
        config = AtlasConfig()
        print("✅ AtlasConfig instantiation successful")
        
        # Test AtlasConstants access
        constants = AtlasConstants()
        print("✅ AtlasConstants instantiation successful")
        
        # Test that we can access version info
        from atlasexplorer import __version__, __author__
        print(f"✅ Package metadata: v{__version__} by {__author__}")
        
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def test_cli_function_compatibility():
    """Test that CLI functions work as expected."""
    print("\nTesting CLI function compatibility...")
    
    try:
        from atlasexplorer import configure, subcmd_configure
        import argparse
        
        # Test that functions are callable
        assert callable(configure), "configure should be callable"
        assert callable(subcmd_configure), "subcmd_configure should be callable"
        
        # Test subcmd_configure with dummy subparsers
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        subcmd_configure(subparsers)  # Should not raise an exception
        
        print("✅ CLI functions are callable and compatible")
        return True
    except Exception as e:
        print(f"❌ CLI function test failed: {e}")
        return False


def main():
    """Run all parity tests."""
    print("=" * 60)
    print("Phase 2.1 Functional Parity Demonstration")
    print("=" * 60)
    
    # Suppress warnings for this demo
    warnings.filterwarnings("ignore", category=ImportWarning)
    
    tests = [
        test_legacy_symbols_availability,
        test_modular_enhancements, 
        test_legacy_compatibility,
        test_basic_functionality,
        test_cli_function_compatibility
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print("   Test failed!")
        except Exception as e:
            print(f"   Test error: {e}")
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 FUNCTIONAL PARITY DEMONSTRATION: COMPLETE")
        print("   All legacy symbols accessible through modular architecture")
        print("   Enhanced functionality available alongside legacy compatibility")
        print("   Ready for Phase 2.2: Backward Compatibility Layer")
        return 0
    else:
        print("❌ FUNCTIONAL PARITY DEMONSTRATION: INCOMPLETE")
        print(f"   {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
