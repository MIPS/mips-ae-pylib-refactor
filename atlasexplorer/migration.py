"""Migration utility for Atlas Explorer encryption formats.

This utility helps users migrate from legacy encryption formats to the new
backend-compatible formats, ensuring data integrity and backward compatibility.
"""

import os
import shutil
from pathlib import Path
from typing import Union, List, Dict, Optional

from .security.encryption import SecureEncryption
from .security.compatible_encryption import CompatibleEncryption
from .utils.exceptions import EncryptionError


class EncryptionMigrator:
    """Utility for migrating between encryption formats."""
    
    def __init__(self, verbose: bool = True, backup: bool = True):
        """Initialize the migration utility.
        
        Args:
            verbose: Enable verbose logging
            backup: Create backups before migration
        """
        self.verbose = verbose
        self.backup = backup
        self.legacy_encryption = SecureEncryption(verbose=verbose, use_legacy_only=True)
        self.new_encryption = CompatibleEncryption(verbose=verbose)
    
    def migrate_file(self, file_path: Union[str, Path], password: Optional[str] = None,
                    public_key_pem: Optional[str] = None) -> Dict[str, str]:
        """Migrate a single encrypted file to new format.
        
        Args:
            file_path: Path to encrypted file
            password: Password for password-encrypted files
            public_key_pem: Public key for hybrid-encrypted files
            
        Returns:
            Dictionary with migration status and details
            
        Raises:
            EncryptionError: If migration fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise EncryptionError(f"File does not exist: {file_path}")
        
        # Create backup if requested
        backup_path = None
        if self.backup:
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            shutil.copy2(file_path, backup_path)
            if self.verbose:
                print(f"Created backup: {backup_path}")
        
        try:
            # Detect current format
            if password:
                format_type = self.new_encryption._detect_password_format(file_path)
                if format_type == self.new_encryption.NEW_PASSWORD_FORMAT:
                    return {
                        'status': 'already_new_format',
                        'message': 'File is already in new password format',
                        'format': format_type
                    }
                
                # Decrypt with legacy method
                temp_decrypted = file_path.with_suffix('.temp_decrypted')
                shutil.copy2(file_path, temp_decrypted)
                self.legacy_encryption._legacy_decrypt_file_with_password(temp_decrypted, password)
                
                # Re-encrypt with new method
                self.new_encryption.encrypt_file_with_password(temp_decrypted, password)
                
                # Replace original file
                shutil.move(temp_decrypted, file_path)
                
                return {
                    'status': 'migrated',
                    'message': 'Successfully migrated password-encrypted file to new format',
                    'format': 'new_password_format',
                    'backup': str(backup_path) if backup_path else None
                }
                
            elif public_key_pem:
                format_type = self.new_encryption._detect_hybrid_format(file_path)
                if format_type == self.new_encryption.NEW_HYBRID_FORMAT:
                    return {
                        'status': 'already_new_format',
                        'message': 'File is already in new hybrid format',
                        'format': format_type
                    }
                
                # For hybrid encryption, we need the private key to decrypt first
                # This is a limitation - we can only re-encrypt, not migrate existing files
                # without the private key
                return {
                    'status': 'requires_private_key',
                    'message': 'Hybrid format migration requires private key for decryption',
                    'format': format_type
                }
            
            else:
                raise EncryptionError("Either password or public_key_pem must be provided")
                
        except Exception as e:
            # Restore backup on failure
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, file_path)
                if self.verbose:
                    print(f"Restored backup due to migration failure")
            
            raise EncryptionError(f"Migration failed: {e}")
    
    def migrate_directory(self, directory_path: Union[str, Path], 
                         file_pattern: str = "*.enc",
                         password: Optional[str] = None,
                         public_key_pem: Optional[str] = None) -> List[Dict[str, str]]:
        """Migrate all encrypted files in a directory.
        
        Args:
            directory_path: Path to directory containing encrypted files
            file_pattern: Glob pattern to match encrypted files
            password: Password for password-encrypted files
            public_key_pem: Public key for hybrid-encrypted files
            
        Returns:
            List of migration results for each file
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            raise EncryptionError(f"Directory does not exist: {directory_path}")
        
        encrypted_files = list(directory_path.glob(file_pattern))
        
        if not encrypted_files:
            if self.verbose:
                print(f"No files matching pattern '{file_pattern}' found in {directory_path}")
            return []
        
        results = []
        
        for file_path in encrypted_files:
            if self.verbose:
                print(f"Processing: {file_path}")
            
            try:
                result = self.migrate_file(file_path, password, public_key_pem)
                result['file'] = str(file_path)
                results.append(result)
                
            except Exception as e:
                results.append({
                    'file': str(file_path),
                    'status': 'error',
                    'message': str(e)
                })
                
                if self.verbose:
                    print(f"Error migrating {file_path}: {e}")
        
        return results
    
    def analyze_file(self, file_path: Union[str, Path]) -> Dict[str, str]:
        """Analyze an encrypted file to determine its format and characteristics.
        
        Args:
            file_path: Path to encrypted file
            
        Returns:
            Dictionary with file analysis results
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                'status': 'file_not_found',
                'path': str(file_path)
            }
        
        file_size = file_path.stat().st_size
        
        # Try to detect both formats
        try:
            hybrid_format = self.new_encryption._detect_hybrid_format(file_path)
        except:
            hybrid_format = 'unknown'
        
        try:
            password_format = self.new_encryption._detect_password_format(file_path)
        except:
            password_format = 'unknown'
        
        return {
            'path': str(file_path),
            'size_bytes': file_size,
            'likely_hybrid_format': hybrid_format,
            'likely_password_format': password_format,
            'needs_migration': (
                hybrid_format == self.new_encryption.LEGACY_HYBRID_FORMAT or
                password_format == self.new_encryption.LEGACY_PASSWORD_FORMAT
            )
        }
    
    def analyze_directory(self, directory_path: Union[str, Path], 
                         file_pattern: str = "*.enc") -> Dict[str, any]:
        """Analyze all encrypted files in a directory.
        
        Args:
            directory_path: Path to directory
            file_pattern: Glob pattern to match files
            
        Returns:
            Dictionary with analysis summary
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            return {'error': f"Directory does not exist: {directory_path}"}
        
        encrypted_files = list(directory_path.glob(file_pattern))
        
        if not encrypted_files:
            return {
                'directory': str(directory_path),
                'pattern': file_pattern,
                'total_files': 0,
                'message': 'No matching files found'
            }
        
        analysis_results = []
        summary = {
            'total_files': len(encrypted_files),
            'legacy_hybrid': 0,
            'new_hybrid': 0,
            'legacy_password': 0,
            'new_password': 0,
            'unknown': 0,
            'needs_migration': 0
        }
        
        for file_path in encrypted_files:
            result = self.analyze_file(file_path)
            analysis_results.append(result)
            
            # Update summary
            if result.get('likely_hybrid_format') == self.new_encryption.LEGACY_HYBRID_FORMAT:
                summary['legacy_hybrid'] += 1
            elif result.get('likely_hybrid_format') == self.new_encryption.NEW_HYBRID_FORMAT:
                summary['new_hybrid'] += 1
            
            if result.get('likely_password_format') == self.new_encryption.LEGACY_PASSWORD_FORMAT:
                summary['legacy_password'] += 1
            elif result.get('likely_password_format') == self.new_encryption.NEW_PASSWORD_FORMAT:
                summary['new_password'] += 1
            
            if result.get('needs_migration'):
                summary['needs_migration'] += 1
            
            if (result.get('likely_hybrid_format') == 'unknown' and 
                result.get('likely_password_format') == 'unknown'):
                summary['unknown'] += 1
        
        return {
            'directory': str(directory_path),
            'pattern': file_pattern,
            'summary': summary,
            'files': analysis_results
        }
    
    def cleanup_backups(self, directory_path: Union[str, Path], 
                       backup_pattern: str = "*.backup") -> int:
        """Clean up backup files created during migration.
        
        Args:
            directory_path: Path to directory containing backups
            backup_pattern: Glob pattern to match backup files
            
        Returns:
            Number of backup files removed
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            return 0
        
        backup_files = list(directory_path.glob(backup_pattern))
        removed_count = 0
        
        for backup_file in backup_files:
            try:
                backup_file.unlink()
                removed_count += 1
                if self.verbose:
                    print(f"Removed backup: {backup_file}")
            except Exception as e:
                if self.verbose:
                    print(f"Failed to remove backup {backup_file}: {e}")
        
        return removed_count


# CLI interface for the migration utility
def main():
    """Command-line interface for encryption migration."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Atlas Explorer Encryption Migration Utility"
    )
    
    parser.add_argument("command", choices=["analyze", "migrate", "cleanup"],
                       help="Command to execute")
    parser.add_argument("path", help="File or directory path")
    parser.add_argument("--password", help="Password for encrypted files")
    parser.add_argument("--public-key", help="Path to public key file")
    parser.add_argument("--pattern", default="*.enc", 
                       help="File pattern for directory operations")
    parser.add_argument("--no-backup", action="store_true",
                       help="Skip creating backups during migration")
    parser.add_argument("--quiet", action="store_true",
                       help="Suppress verbose output")
    
    args = parser.parse_args()
    
    migrator = EncryptionMigrator(verbose=not args.quiet, backup=not args.no_backup)
    
    if args.command == "analyze":
        path = Path(args.path)
        if path.is_file():
            result = migrator.analyze_file(path)
            print(f"Analysis for {path}:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            result = migrator.analyze_directory(path, args.pattern)
            print(f"Analysis for directory {path}:")
            print(f"  Total files: {result['summary']['total_files']}")
            print(f"  Need migration: {result['summary']['needs_migration']}")
            print(f"  Legacy hybrid: {result['summary']['legacy_hybrid']}")
            print(f"  Legacy password: {result['summary']['legacy_password']}")
    
    elif args.command == "migrate":
        public_key_pem = None
        if args.public_key:
            with open(args.public_key, 'r') as f:
                public_key_pem = f.read()
        
        path = Path(args.path)
        if path.is_file():
            result = migrator.migrate_file(path, args.password, public_key_pem)
            print(f"Migration result: {result['status']} - {result['message']}")
        else:
            results = migrator.migrate_directory(path, args.pattern, 
                                               args.password, public_key_pem)
            successful = sum(1 for r in results if r['status'] == 'migrated')
            print(f"Migrated {successful}/{len(results)} files successfully")
    
    elif args.command == "cleanup":
        removed = migrator.cleanup_backups(args.path)
        print(f"Removed {removed} backup files")


if __name__ == "__main__":
    main()
