#!/usr/bin/env python3
"""
Test script for backward compatibility layer.
"""

import sys
import warnings
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_legacy_imports():
    """Test that legacy imports still work."""
    print("Testing legacy imports...")
    
    try:
        # These should work with deprecation warnings
        from atlasexplorer import (
            LegacyAtlasConfig,
            LegacyAtlasConstants,
            LegacyAtlasExplorer,
            LegacyExperiment,
            LegacySummaryReport
        )
        print("   ✅ Legacy imports successful")
        return True
    except ImportError as e:
        print(f"   ❌ Legacy import failed: {e}")
        return False

def test_deprecation_warnings():
    """Test that deprecation warnings are shown."""
    print("Testing deprecation warnings...")
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        from atlasexplorer import LegacyAtlasConfig
        
        # This should trigger a deprecation warning
        config = LegacyAtlasConfig()
        
        # Check if warning was issued
        if w and any("deprecated" in str(warning.message).lower() for warning in w):
            print("   ✅ Deprecation warnings working")
            return True
        else:
            print("   ❌ No deprecation warning issued")
            return False

def test_functional_compatibility():
    """Test that legacy classes still provide the same functionality."""
    print("Testing functional compatibility...")
    
    try:
        from atlasexplorer import LegacyAtlasConfig, AtlasConfig
        
        # Test that legacy classes can be instantiated
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Suppress warnings for this test
            legacy_config = LegacyAtlasConfig()
            modern_config = AtlasConfig()
        
        # Both should have same basic interface (check for key attributes)
        legacy_attrs = dir(legacy_config)
        modern_attrs = dir(modern_config)
        
        # Check that legacy has at least the same core attributes as modern
        core_attrs = ['gateway_url', 'access_token', 'org_id']
        for attr in core_attrs:
            if hasattr(modern_config, attr):
                assert hasattr(legacy_config, attr), f"Legacy missing attribute: {attr}"
        
        # Test that legacy classes are actually the wrapped modular classes
        assert isinstance(legacy_config, type(modern_config)), "Legacy should inherit from modern"
        
        print("   ✅ Functional compatibility confirmed")
        return True
    except Exception as e:
        print(f"   ❌ Functional compatibility failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all compatibility tests."""
    print("🔧 Backward Compatibility Test Suite")
    print("=" * 40)
    
    tests = [
        test_legacy_imports,
        test_deprecation_warnings, 
        test_functional_compatibility
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    if all(results):
        print("🎉 All backward compatibility tests PASSED!")
        return 0
    else:
        print("❌ Some backward compatibility tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
