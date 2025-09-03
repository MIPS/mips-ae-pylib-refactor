#!/usr/bin/env python3
"""Phase 2.2 Preparation: Backward Compatibility Layer Setup.

This script sets up the framework for Phase 2.2 by analyzing current
compatibility status and preparing deprecation strategies.
"""

import sys
import warnings
from pathlib import Path

# Ensure the project root is in the Python path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def analyze_compatibility_status():
    """Analyze current backward compatibility implementation."""
    print("Analyzing backward compatibility status...")
    
    # Check current legacy imports in __init__.py
    init_file = repo_root / "atlasexplorer" / "__init__.py"
    content = init_file.read_text()
    
    # Count legacy imports
    legacy_classes = ["LegacyAtlasExplorer", "LegacyExperiment", "LegacySummaryReport", 
                     "LegacyAtlasConfig", "LegacyAtlasConstants"]
    legacy_present = sum(1 for cls in legacy_classes if cls in content)
    
    # Check external dependency handling
    external_deps = ["Cipher", "ELFFile", "load_dotenv", "prompt", "scrypt", "default_backend"]
    external_present = sum(1 for dep in external_deps if dep in content)
    
    # Check CLI function compatibility
    cli_functions = ["configure", "subcmd_configure"]
    cli_present = sum(1 for func in cli_functions if func in content)
    
    print(f"✅ Legacy class aliases: {legacy_present}/5 present")
    print(f"✅ External dependencies: {external_present}/6 mapped")
    print(f"✅ CLI functions: {cli_present}/2 mapped")
    
    return {
        "legacy_classes": legacy_present == 5,
        "external_deps": external_present == 6,
        "cli_functions": cli_present == 2
    }


def check_deprecation_readiness():
    """Check if we're ready to implement deprecation warnings."""
    print("\\nChecking deprecation readiness...")
    
    try:
        # Test that we can import both legacy and new implementations
        from atlasexplorer import LegacyAtlasExplorer, AtlasExplorer
        from atlasexplorer import LegacyExperiment, Experiment
        from atlasexplorer import LegacySummaryReport, SummaryReport
        
        print("✅ Dual implementation access verified")
        
        # Check that new implementations work
        config = AtlasExplorer()
        print("✅ New implementations functional")
        
        # Verify legacy still works
        legacy_config = LegacyAtlasExplorer()
        print("✅ Legacy implementations functional")
        
        return True
    except Exception as e:
        print(f"❌ Deprecation readiness check failed: {e}")
        return False


def create_deprecation_utils():
    """Create deprecation utilities module."""
    print("\\nCreating deprecation utilities...")
    
    deprecation_utils = repo_root / "atlasexplorer" / "utils" / "deprecation.py"
    if not deprecation_utils.exists():
        deprecation_content = '''"""Deprecation utilities for Atlas Explorer.

This module provides utilities for managing the transition from legacy
monolithic implementation to the new modular architecture.
"""

import warnings
import functools
from typing import Callable, Any


def deprecated_alias(old_name: str, new_name: str, version: str = "3.0"):
    """Mark a class or function as deprecated alias.
    
    Args:
        old_name: Name of the deprecated class/function
        new_name: Name of the new class/function to use instead
        version: Version when the deprecated item will be removed
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"'{old_name}' is deprecated and will be removed in v{version}. "
                f"Use '{new_name}' instead.",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


class CompatibilityLayer:
    """Manages backward compatibility during the transition period."""
    
    def __init__(self):
        self.deprecation_warnings_enabled = True
    
    def enable_deprecation_warnings(self):
        """Enable deprecation warnings."""
        self.deprecation_warnings_enabled = True
    
    def disable_deprecation_warnings(self):
        """Disable deprecation warnings for testing."""
        self.deprecation_warnings_enabled = False


# Global compatibility layer instance
compatibility = CompatibilityLayer()
'''
        deprecation_utils.write_text(deprecation_content)
        print(f"✅ Created: {deprecation_utils}")
        return True
    else:
        print(f"✅ Already exists: {deprecation_utils}")
        return True


def main():
    """Run Phase 2.2 preparation."""
    print("=" * 60)
    print("Phase 2.2 Preparation: Backward Compatibility Layer Setup")
    print("=" * 60)
    
    # Analyze current status
    status = analyze_compatibility_status()
    
    # Check deprecation readiness
    ready = check_deprecation_readiness()
    
    # Create deprecation utilities
    utils_created = create_deprecation_utils()
    
    print("\\n" + "=" * 60)
    if all(status.values()) and ready and utils_created:
        print("🎉 PHASE 2.2 PREPARATION: COMPLETE")
        print("   Backward compatibility framework established")
        print("   Deprecation utilities created")
        print("   Ready to implement deprecation warnings")
        return 0
    else:
        print("❌ PHASE 2.2 PREPARATION: INCOMPLETE")
        print("   Some prerequisites not met")
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''
        deprecation_utils.write_text(deprecation_content)
        print(f"✅ Created deprecation utilities: {deprecation_utils}")
    
    # Create backward compatibility test
    compat_test = repo_root / "tests" / "test_backward_compatibility.py"
    if not compat_test.exists():
        compat_test_content = '''"""Tests for backward compatibility layer.

These tests ensure that existing customer code will continue to work
during the transition from legacy to modular architecture.
"""

import unittest
import warnings
from atlasexplorer import *


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility features."""
    
    def setUp(self):
        """Set up test environment."""
        # Capture warnings
        self.warning_list = []
        warnings.showwarning = lambda *args: self.warning_list.append(args)
    
    def test_legacy_imports_available(self):
        """Test that legacy imports still work."""
        # These should work without errors
        from atlasexplorer import AtlasExplorer, Experiment, SummaryReport
        from atlasexplorer import AtlasConfig, AtlasConstants
        from atlasexplorer import configure, subcmd_configure
        
        # Verify they're callable/instantiable
        self.assertTrue(callable(AtlasExplorer))
        self.assertTrue(callable(Experiment))
        self.assertTrue(callable(configure))
    
    def test_external_dependencies_mapped(self):
        """Test that external dependencies are accessible."""
        from atlasexplorer import Cipher, ELFFile, load_dotenv, prompt, scrypt, default_backend
        
        # These may be None if dependencies aren't installed, but should not raise ImportError
        # Just verify the imports work
        pass
    
    def test_legacy_compatibility_layer(self):
        """Test that legacy classes are still accessible."""
        from atlasexplorer import LegacyAtlasExplorer, LegacyExperiment, LegacySummaryReport
        
        # Verify they're callable
        self.assertTrue(callable(LegacyAtlasExplorer))
        self.assertTrue(callable(LegacyExperiment))
        self.assertTrue(callable(LegacySummaryReport))
    
    def test_new_modular_components(self):
        """Test that new modular components are available."""
        from atlasexplorer import AtlasAPIClient, ELFAnalyzer, SecureEncryption
        from atlasexplorer import AtlasExplorerError, NetworkError, EncryptionError
        
        # Verify they're callable
        self.assertTrue(callable(AtlasAPIClient))
        self.assertTrue(callable(ELFAnalyzer))
        self.assertTrue(callable(SecureEncryption))


if __name__ == '__main__':
    unittest.main()
'''
        compat_test.write_text(compat_test_content)
        print(f"✅ Created compatibility tests: {compat_test}")
    
    # Create Phase 2.2 planning document
    phase2_2_plan = repo_root / "claude_done" / "phase2_2_backward_compatibility_plan.md"
    phase2_2_content = '''# Phase 2.2: Backward Compatibility Layer - PLANNING

## Objective
Implement a robust backward compatibility layer that ensures zero breaking changes for existing customers while enabling gradual migration to the modular architecture.

## Current Status (Phase 2.1 Complete)
- ✅ 100% functional parity achieved
- ✅ All 15 legacy symbols mapped and accessible
- ✅ Enhanced modular components available
- ✅ Automated parity validation in place

## Phase 2.2 Implementation Strategy

### 1. Deprecation Warning Framework
- [ ] Implement graceful deprecation warnings for legacy usage
- [ ] Create utilities for managing deprecation lifecycle
- [ ] Enable/disable warnings for testing environments

### 2. API Compatibility Verification
- [ ] Comprehensive test suite for backward compatibility
- [ ] Signature compatibility verification
- [ ] Behavior compatibility testing

### 3. Migration Helper Tools
- [ ] Code scanning tools to identify legacy usage
- [ ] Automated migration assistance utilities
- [ ] Customer migration documentation

### 4. Performance Equivalence
- [ ] Ensure modular components perform at least as well as legacy
- [ ] Benchmark critical code paths
- [ ] Optimize any performance regressions

## Success Criteria
1. **Zero Breaking Changes**: All existing customer code continues to work
2. **Clear Migration Path**: Customers can gradually adopt new APIs
3. **Performance Parity**: No performance degradation
4. **Comprehensive Testing**: Full backward compatibility test coverage

## Risk Mitigation
- Gradual rollout of deprecation warnings
- Extensive testing with real customer code patterns
- Clear communication of migration timeline
- Fallback mechanisms for critical compatibility issues

## Next Steps
1. Run this planning script to set up framework
2. Implement deprecation warning system
3. Create comprehensive compatibility tests
4. Begin customer communication about migration path
'''
    phase2_2_plan.write_text(phase2_2_content)
    print(f"✅ Created Phase 2.2 planning document: {phase2_2_plan}")


def main():
    """Run Phase 2.2 preparation."""
    print("=" * 60)
    print("Phase 2.2 Preparation: Backward Compatibility Layer Setup")
    print("=" * 60)
    
    # Analyze current status
    status = analyze_compatibility_status()
    
    # Check deprecation readiness
    ready = check_deprecation_readiness()
    
    # Create framework
    create_phase2_2_framework()
    
    print("\\n" + "=" * 60)
    if all(status.values()) and ready:
        print("🎉 PHASE 2.2 PREPARATION: COMPLETE")
        print("   Backward compatibility framework established")
        print("   Deprecation utilities created")
        print("   Test framework prepared")
        print("   Ready to implement deprecation warnings")
        return 0
    else:
        print("❌ PHASE 2.2 PREPARATION: INCOMPLETE")
        print("   Some prerequisites not met")
        return 1


if __name__ == "__main__":
    sys.exit(main())
