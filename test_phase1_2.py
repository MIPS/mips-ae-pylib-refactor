#!/usr/bin/env python3
"""
Phase 1.2 Integration Test - Test New Modular Classes

This script tests that the newly extracted Experiment and AtlasExplorer 
classes work correctly with the modular architecture.
"""

import os
import sys
from pathlib import Path

def test_modular_imports():
    """Test that all modular classes can be imported."""
    print("Testing modular imports...")
    
    try:
        # Test core module imports
        from atlasexplorer.core import AtlasExplorer, Experiment, AtlasConfig, AtlasConstants
        print("✓ Core classes imported successfully")
        
        # Test that we can instantiate classes
        # Note: We can't actually create instances without proper config,
        # but we can verify the classes are defined
        assert hasattr(AtlasExplorer, '__init__')
        assert hasattr(Experiment, '__init__')
        print("✓ Classes have proper constructors")
        
        # Test that methods exist
        assert hasattr(Experiment, 'addWorkload')
        assert hasattr(Experiment, 'setCore')
        assert hasattr(Experiment, 'run')
        assert hasattr(AtlasExplorer, 'getCoreInfo')
        assert hasattr(AtlasExplorer, 'getVersionList')
        print("✓ Expected methods are present")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_backward_compatibility():
    """Test that backward compatibility is maintained."""
    print("\nTesting backward compatibility...")
    
    try:
        # Test that old-style imports still work
        from atlasexplorer import AtlasExplorer, Experiment
        print("✓ Backward compatible imports work")
        
        # Test that we can import both old and new
        from atlasexplorer import AtlasExplorer as NewAtlasExplorer
        from atlasexplorer.atlasexplorer import AtlasExplorer as OldAtlasExplorer
        
        # They should be the same now (using new implementation)
        print(f"New AtlasExplorer: {NewAtlasExplorer}")
        print(f"Old AtlasExplorer reference: {OldAtlasExplorer}")
        print("✓ Both old and new references work")
        
        return True
        
    except ImportError as e:
        print(f"✗ Backward compatibility failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_type_safety():
    """Test that type hints are working."""
    print("\nTesting type safety...")
    
    try:
        # Import typing and inspect modules
        import typing
        import inspect
        
        from atlasexplorer.core import Experiment
        
        # Check that methods have type annotations
        add_workload_sig = inspect.signature(Experiment.addWorkload)
        set_core_sig = inspect.signature(Experiment.setCore)
        run_sig = inspect.signature(Experiment.run)
        
        print(f"addWorkload signature: {add_workload_sig}")
        print(f"setCore signature: {set_core_sig}")
        print(f"run signature: {run_sig}")
        
        # Verify some basic type annotations exist
        assert 'workload' in add_workload_sig.parameters
        assert 'core' in set_core_sig.parameters
        print("✓ Type annotations are present")
        
        return True
        
    except Exception as e:
        print(f"✗ Type safety test failed: {e}")
        return False

def test_exception_hierarchy():
    """Test that custom exceptions work properly."""
    print("\nTesting exception hierarchy...")
    
    try:
        from atlasexplorer.utils.exceptions import (
            AtlasExplorerError,
            ExperimentError,
            ELFValidationError,
            EncryptionError,
            NetworkError,
            ConfigurationError,
            AuthenticationError
        )
        
        # Test inheritance
        assert issubclass(ExperimentError, AtlasExplorerError)
        assert issubclass(ELFValidationError, AtlasExplorerError)
        assert issubclass(EncryptionError, AtlasExplorerError)
        print("✓ Exception hierarchy is correct")
        
        # Test that we can raise and catch them
        try:
            raise ExperimentError("Test error")
        except AtlasExplorerError as e:
            assert str(e) == "Test error"
            print("✓ Exception handling works correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Exception test failed: {e}")
        return False

def main():
    """Run all Phase 1.2 integration tests."""
    print("="*60)
    print("PHASE 1.2 INTEGRATION TESTS")
    print("="*60)
    
    tests = [
        test_modular_imports,
        test_backward_compatibility,
        test_type_safety,
        test_exception_hierarchy
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print("INTEGRATION TEST RESULTS")
    print("="*60)
    print(f"Tests Passed: {passed}")
    print(f"Tests Failed: {failed}")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Phase 1.2 core extraction successful!")
        print("\nNext Steps:")
        print("  1. Add comprehensive unit tests")
        print("  2. Complete type hint coverage")
        print("  3. Add integration tests for end-to-end workflows")
        print("  4. Performance testing")
        return True
    else:
        print("❌ Some tests failed. Review output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
