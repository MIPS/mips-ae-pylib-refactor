#!/usr/bin/env python3
"""Migration script for Atlas Explorer modular refactoring.

This script helps migrate from the monolithic atlasexplorer.py to the new
modular architecture while maintaining backward compatibility.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Any


class MigrationManager:
    """Manages the migration from monolithic to modular architecture."""
    
    def __init__(self, root_dir: Path):
        """Initialize migration manager.
        
        Args:
            root_dir: Root directory of the atlasexplorer package
        """
        self.root_dir = Path(root_dir)
        self.backup_dir = self.root_dir / "backup_monolithic"
        
    def create_backup(self) -> None:
        """Create backup of the original monolithic file."""
        print("Creating backup of original atlasexplorer.py...")
        
        self.backup_dir.mkdir(exist_ok=True)
        
        original_file = self.root_dir / "atlasexplorer.py"
        if original_file.exists():
            backup_file = self.backup_dir / "atlasexplorer_original.py"
            shutil.copy2(original_file, backup_file)
            print(f"✓ Backup created: {backup_file}")
        else:
            print("⚠ Original atlasexplorer.py not found")
    
    def validate_modular_structure(self) -> bool:
        """Validate that all modular components are present.
        
        Returns:
            True if all required modules are present
        """
        required_modules = [
            "core/__init__.py",
            "core/constants.py", 
            "core/config.py",
            "security/__init__.py",
            "security/encryption.py",
            "network/__init__.py",
            "network/api_client.py",
            "analysis/__init__.py",
            "analysis/elf_parser.py",
            "analysis/reports.py",
            "cli/__init__.py",
            "cli/commands.py",
            "cli/interactive.py",
            "utils/__init__.py",
            "utils/exceptions.py"
        ]
        
        print("Validating modular structure...")
        missing_modules = []
        
        for module in required_modules:
            module_path = self.root_dir / module
            if not module_path.exists():
                missing_modules.append(module)
        
        if missing_modules:
            print("✗ Missing modules:")
            for module in missing_modules:
                print(f"  - {module}")
            return False
        else:
            print("✓ All required modules present")
            return True
    
    def run_migration_tests(self) -> bool:
        """Run basic tests to ensure migration is working.
        
        Returns:
            True if all tests pass
        """
        print("Running migration tests...")
        
        tests = [
            self._test_imports,
            self._test_exceptions,
            self._test_config,
            self._test_cli
        ]
        
        all_passed = True
        for test in tests:
            try:
                test()
                print(f"✓ {test.__name__}")
            except Exception as e:
                print(f"✗ {test.__name__}: {e}")
                all_passed = False
        
        return all_passed
    
    def _test_imports(self) -> None:
        """Test that all modules can be imported."""
        sys.path.insert(0, str(self.root_dir.parent))
        
        # Test core imports
        from atlasexplorer.core import AtlasConfig, AtlasConstants
        from atlasexplorer.utils import AtlasExplorerError
        from atlasexplorer.security import SecureEncryption
        from atlasexplorer.network import AtlasAPIClient
        from atlasexplorer.analysis import ELFAnalyzer, SummaryReport
        from atlasexplorer.cli import AtlasExplorerCLI
    
    def _test_exceptions(self) -> None:
        """Test exception hierarchy."""
        from atlasexplorer.utils.exceptions import (
            AtlasExplorerError, AuthenticationError, NetworkError
        )
        
        # Test exception inheritance
        assert issubclass(AuthenticationError, AtlasExplorerError)
        assert issubclass(NetworkError, AtlasExplorerError)
        
        # Test exception creation
        error = AuthenticationError("Test error")
        assert str(error) == "Test error"
    
    def _test_config(self) -> None:
        """Test configuration loading."""
        from atlasexplorer.core import AtlasConfig
        
        # Test config creation (should not fail even without credentials)
        config = AtlasConfig(readonly=True, verbose=False)
        assert hasattr(config, 'hasConfig')
    
    def _test_cli(self) -> None:
        """Test CLI functionality."""
        from atlasexplorer.cli import AtlasExplorerCLI
        
        # Test CLI creation
        cli = AtlasExplorerCLI()
        assert 'configure' in cli.commands
        
        # Test parser creation
        parser = AtlasExplorerCLI.create_parser()
        assert parser.prog == "atlasexplorer"
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate a comprehensive migration report.
        
        Returns:
            Migration status report
        """
        report = {
            "migration_status": "unknown",
            "modules_present": {},
            "tests_passed": False,
            "recommendations": []
        }
        
        # Check module presence
        structure_valid = self.validate_modular_structure()
        report["modules_present"]["structure_valid"] = structure_valid
        
        # Run tests
        if structure_valid:
            tests_passed = self.run_migration_tests()
            report["tests_passed"] = tests_passed
            
            if tests_passed:
                report["migration_status"] = "success"
                report["recommendations"].append(
                    "Migration completed successfully! You can now use the modular architecture."
                )
            else:
                report["migration_status"] = "partial"
                report["recommendations"].extend([
                    "Some tests failed. Check error messages above.",
                    "Review module implementations for issues.",
                    "Consider running tests individually to isolate problems."
                ])
        else:
            report["migration_status"] = "failed"
            report["recommendations"].extend([
                "Missing required modules. Complete the module extraction first.",
                "Ensure all __init__.py files are present.",
                "Check that module paths are correct."
            ])
        
        return report
    
    def print_next_steps(self) -> None:
        """Print recommended next steps for completing the refactoring."""
        print("\\n" + "="*60)
        print("PHASE 1.1 MIGRATION STATUS & NEXT STEPS")
        print("="*60)
        
        report = self.generate_migration_report()
        
        print(f"Status: {report['migration_status'].upper()}")
        print(f"Modules Present: {report['modules_present']['structure_valid']}")
        print(f"Tests Passed: {report['tests_passed']}")
        
        print("\\nRecommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
        
        if report['migration_status'] == 'success':
            print("\\nPhase 1.1 COMPLETE! ✓")
            print("\\nNext Steps (Phase 1.2):")
            print("  1. Add comprehensive type hints to all modules")
            print("  2. Extract remaining Experiment and AtlasExplorer classes")
            print("  3. Implement proper dependency injection")
            print("  4. Add comprehensive unit tests")
            print("  5. Remove eval() usage completely")
        
        print("\\nFor detailed implementation plan, see:")
        print("  - TODO.md (Phase 1.2 section)")
        print("  - tests/ directory for testing framework")


def main():
    """Main migration script entry point."""
    print("Atlas Explorer Phase 1.1 Migration")
    print("="*40)
    
    # Find the atlasexplorer directory
    current_dir = Path(__file__).parent
    atlas_dir = current_dir / "atlasexplorer"
    
    if not atlas_dir.exists():
        atlas_dir = current_dir
    
    migration = MigrationManager(atlas_dir)
    
    # Create backup
    migration.create_backup()
    
    # Run validation and tests
    print("\\n" + "-"*40)
    migration.print_next_steps()


if __name__ == "__main__":
    main()
