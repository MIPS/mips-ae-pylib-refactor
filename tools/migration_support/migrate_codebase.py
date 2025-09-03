#!/usr/bin/env python3
"""
Automated Migration Script for Atlas Explorer Modular Architecture

This script helps migrate from legacy monolithic imports to
optimized modular imports for better performance.
"""

import re
from pathlib import Path

def migrate_file(file_path):
    """Migrate a single Python file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Apply transformations
    transformations = {
        "from atlasexplorer.atlasexplorer import AtlasExplorer": "from atlasexplorer.core import AtlasExplorer",
        "from atlasexplorer.atlasexplorer import Experiment": "from atlasexplorer.core import Experiment",
        "from atlasexplorer.atlasexplorer import SummaryReport": "from atlasexplorer.analysis import SummaryReport",
        "from atlasexplorer.atlasexplorer import AtlasConfig": "from atlasexplorer.core import AtlasConfig",
        "from atlasexplorer.atlasexplorer import AtlasConstants": "from atlasexplorer.core import AtlasConstants",
    }

    modified = False
    for old, new in transformations.items():
        if old in content:
            content = content.replace(old, new)
            modified = True
            print(f'  Migrated: {old} -> {new}')

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Main migration execution."""
    codebase_path = Path('.')
    python_files = list(codebase_path.rglob('*.py'))

    migrated_files = 0
    for file_path in python_files:
        # Skip test files and virtual environments
        if any(skip in str(file_path) for skip in ['/test', '/tests', '/venv', '/.venv']):
            continue

        print(f'Checking {file_path}...')
        if migrate_file(file_path):
            migrated_files += 1

    print(f'\nMigration complete: {migrated_files} files updated')

if __name__ == '__main__':
    main()