# Atlas Explorer Encryption Compatibility Guide

## Overview

This guide explains the encryption format updates in Atlas Explorer and how to ensure compatibility with the new TypeScript backend while maintaining backward compatibility with existing encrypted files.

## What Changed

### Backend Updates
The TypeScript backend has updated its encryption formats to improve security and performance:

1. **Hybrid Encryption (RSA + AES-GCM)**:
   - IV size changed from 16 bytes to 12 bytes (GCM standard)
   - Added 2-byte key length header for better parsing
   - Reordered components: `[iv][key_length][encrypted_key][encrypted_data][auth_tag]`

2. **Password-based Encryption**:
   - Switched from AES-ECB to AES-GCM for better security
   - Random salt generation instead of fixed "salt"
   - Enhanced scrypt parameters (N=32768 vs N=16384)
   - New format: `[salt][iv][tag][ciphertext]`

### Python Client Updates
The Python client now supports both new and legacy formats:

- **Automatic Format Detection**: Detects old vs new encryption formats
- **Seamless Fallback**: Falls back to legacy decryption for old files
- **New Format by Default**: Uses backend-compatible format for new encryptions
- **Production Safety**: Maintains full backward compatibility

## Usage

### Basic Encryption (Recommended)

```python
from atlasexplorer.security.encryption import SecureEncryption

# Initialize with new compatible encryption (default)
encryption = SecureEncryption(verbose=True)

# Encrypt files - uses new backend-compatible format
encryption.hybrid_encrypt_file(public_key_pem, "experiment.tar.gz")
encryption.decrypt_file_with_password("encrypted_file.enc", "password123")
```

### Legacy-Only Mode (For Testing)

```python
# Force legacy encryption only (for compatibility testing)
encryption = SecureEncryption(verbose=True, use_legacy_only=True)
```

### Advanced Compatible Encryption

```python
from atlasexplorer.security.compatible_encryption import CompatibleEncryption

# Direct access to new encryption with format detection
encryption = CompatibleEncryption(verbose=True)

# Password-based encryption with new backend format
encryption.encrypt_file_with_password("data.txt", "secure_password")
encryption.decrypt_file_with_password("data.txt", "secure_password")  # Auto-detects format
```

## Migration Tools

### Analyzing Existing Files

```python
from atlasexplorer.migration import EncryptionMigrator

migrator = EncryptionMigrator(verbose=True)

# Analyze a single file
result = migrator.analyze_file("encrypted_experiment.tar.gz")
print(f"Format: {result['likely_password_format']}")
print(f"Needs migration: {result['needs_migration']}")

# Analyze entire directory
analysis = migrator.analyze_directory("./myexperiments/")
print(f"Files needing migration: {analysis['summary']['needs_migration']}")
```

### Migrating Files

```python
# Migrate a single password-encrypted file
result = migrator.migrate_file("old_encrypted.tar.gz", password="mypassword")

# Migrate all encrypted files in directory
results = migrator.migrate_directory(
    "./myexperiments/", 
    file_pattern="*.tar.gz",
    password="mypassword"
)

# Check results
successful = sum(1 for r in results if r['status'] == 'migrated')
print(f"Successfully migrated {successful} files")
```

### Command Line Migration

```bash
# Analyze files
python -m atlasexplorer.migration analyze ./myexperiments/ --pattern "*.tar.gz"

# Migrate files
python -m atlasexplorer.migration migrate ./myexperiments/ \
    --password "mypassword" \
    --pattern "*.tar.gz"

# Clean up backup files after successful migration
python -m atlasexplorer.migration cleanup ./myexperiments/
```

## Format Specifications

### New Hybrid Encryption Format
```
[IV (12 bytes)][Key Length (2 bytes BE)][Encrypted AES Key][Encrypted Data][Auth Tag (16 bytes)]
```

### New Password Encryption Format
```
[Salt (16 bytes)][IV (12 bytes)][Auth Tag (16 bytes)][Ciphertext]
```

### Legacy Formats (Still Supported)
- **Legacy Hybrid**: `[IV (16 bytes)][Encrypted AES Key][Auth Tag][Encrypted Data]`
- **Legacy Password**: Raw AES-ECB encrypted data with PKCS#7 padding

## Error Handling

### Automatic Fallback
```python
encryption = SecureEncryption()

# This will automatically:
# 1. Try new format decryption
# 2. Fall back to legacy format if new fails
# 3. Provide clear error messages
try:
    encryption.decrypt_file_with_password("mystery_file.enc", "password")
except EncryptionError as e:
    print(f"Decryption failed: {e}")
```

### Manual Format Detection
```python
from atlasexplorer.security.compatible_encryption import CompatibleEncryption

enc = CompatibleEncryption()

# Check what format a file uses
hybrid_format = enc._detect_hybrid_format("file.enc")
password_format = enc._detect_password_format("file.enc")

if hybrid_format == enc.LEGACY_HYBRID_FORMAT:
    print("File uses legacy hybrid encryption")
elif password_format == enc.NEW_PASSWORD_FORMAT:
    print("File uses new password encryption")
```

## Production Deployment

### Recommended Deployment Strategy

1. **Phase 1**: Deploy with backward compatibility
   ```python
   # Default behavior - new format with legacy fallback
   encryption = SecureEncryption(verbose=True)
   ```

2. **Phase 2**: Migrate existing files (optional)
   ```bash
   # Analyze first
   python -m atlasexplorer.migration analyze /data/experiments/
   
   # Migrate when ready
   python -m atlasexplorer.migration migrate /data/experiments/ --password "prod_password"
   ```

3. **Phase 3**: Validate and monitor
   - Monitor logs for fallback usage
   - Validate encrypted files work with backend
   - Keep backups until confident

### Safety Features

- **Automatic Backups**: Migration creates `.backup` files by default
- **Format Validation**: Detects and validates encryption formats
- **Graceful Degradation**: Falls back to legacy methods on any failure
- **Comprehensive Logging**: Verbose mode shows exactly what's happening

### Environment Variables

```bash
# Force legacy mode for emergency fallback
export ATLAS_ENCRYPTION_LEGACY_ONLY=true

# Disable automatic migration prompts
export ATLAS_ENCRYPTION_AUTO_MIGRATE=false
```

## Testing

### Unit Tests
```bash
# Run encryption compatibility tests
python -m pytest tests/test_compatible_encryption.py -v

# Run all encryption tests
python -m pytest tests/ -k encryption -v
```

### Integration Testing
```python
# Test with real backend
from atlasexplorer.security.encryption import SecureEncryption

encryption = SecureEncryption()

# Encrypt a test file
encryption.hybrid_encrypt_file(backend_public_key, "test_experiment.tar.gz")

# Upload to backend and verify it can decrypt
# (This requires actual backend integration)
```

## Troubleshooting

### Common Issues

1. **"Unknown encryption format"**
   - File may be corrupted
   - Try analyzing with migration tool
   - Check file size and structure

2. **"New encryption failed, falling back to legacy"**
   - Normal during transition period
   - Indicates file is in legacy format
   - Consider migrating for better compatibility

3. **"Migration requires private key"**
   - Hybrid encryption migration needs both public and private keys
   - Password encryption can be migrated with just the password

### Debug Mode
```python
encryption = SecureEncryption(verbose=True)
# Will print detailed information about format detection and fallback usage
```

### Support

For issues with encryption compatibility:

1. Check logs for detailed error messages
2. Use migration analysis tools to identify problematic files
3. Test with legacy-only mode to isolate issues
4. Verify backend compatibility with test files

## Security Notes

- New formats use stronger encryption (AES-GCM vs AES-ECB)
- Random salt generation improves security
- Enhanced scrypt parameters increase resistance to brute force
- Backward compatibility maintains security of legacy formats
- All encryption operations use secure random number generation

## Migration Checklist

- [ ] Analyze existing encrypted files
- [ ] Test new encryption with development backend
- [ ] Create backups of critical encrypted data
- [ ] Deploy with backward compatibility enabled
- [ ] Monitor logs for fallback usage
- [ ] Migrate files during maintenance window
- [ ] Validate migrated files work with backend
- [ ] Clean up backup files after validation
- [ ] Update documentation and procedures
