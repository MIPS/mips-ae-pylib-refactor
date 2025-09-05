# Atlas Explorer Encryption Compatibility Fix

## Problem Analysis
The Python client encryption (`encryption.py`) is incompatible with the new TypeScript backend (`cryptohelper.ts`). The backend has updated encryption formats that the Python client must match.

## Key Differences Found

### Hybrid Encryption (RSA + AES-GCM):
1. **IV Size**: Backend uses 12 bytes, Python uses 16 bytes
2. **File Format**: Backend includes 2-byte key length header, Python doesn't
3. **Data Order**: Different ordering of encrypted components

### Password-based Encryption:
1. **Mode**: Backend uses AES-256-GCM, Python uses AES-256-ECB
2. **Salt**: Backend uses random 16-byte salt, Python uses fixed "salt"
3. **IV**: Backend uses 12-byte IV, Python uses none (ECB mode)
4. **Scrypt Parameters**: Backend uses enhanced parameters (N=32768), Python uses basic (N=16384)
5. **File Format**: Backend stores [salt][iv][tag][ciphertext], Python stores raw ciphertext

## Tasks to Complete

### 1. Update Hybrid Encryption (Priority: HIGH)
- [ ] Change IV size from 16 to 12 bytes for GCM compatibility
- [ ] Add 2-byte key length header before encrypted symmetric key
- [ ] Reorder file format to match backend: [iv][key_length][encrypted_key][encrypted_data][auth_tag]
- [ ] Ensure auth tag is appended at the end, not before encrypted data

### 2. Update Password-based Encryption (Priority: HIGH)
- [ ] Switch from AES-ECB to AES-GCM mode
- [ ] Generate random 16-byte salt instead of fixed "salt"
- [ ] Use 12-byte IV for GCM mode
- [ ] Update scrypt parameters to match backend (N=32768)
- [ ] Change file format to [salt][iv][tag][ciphertext]
- [ ] Handle auth tag properly in GCM mode

### 3. Implement Backward Compatibility (Priority: MEDIUM)
- [ ] Add version detection to identify old vs new encryption formats
- [ ] Implement fallback decryption for legacy formats
- [ ] Add migration utility to convert old encrypted files to new format
- [ ] Provide clear error messages when format detection fails

### 4. Testing & Validation (Priority: HIGH)
- [ ] Create test files encrypted with TypeScript backend
- [ ] Verify Python can decrypt TypeScript-encrypted files
- [ ] Verify TypeScript can decrypt Python-encrypted files
- [ ] Test fallback mechanisms with legacy encrypted files
- [ ] Add comprehensive unit tests for all encryption scenarios

### 5. Documentation & Safety (Priority: MEDIUM)
- [ ] Document the new encryption format specification
- [ ] Add migration guide for users with existing encrypted files
- [ ] Implement secure key handling best practices
- [ ] Add encryption format validation

## Implementation Strategy

### Phase 1: New Encryption Implementation
Create new encryption methods that match the TypeScript backend exactly, while keeping old methods for fallback.

### Phase 2: Format Detection
Implement smart detection to determine if a file uses old or new encryption format, enabling seamless backward compatibility.

### Phase 3: Migration & Testing
Provide tools and comprehensive testing to ensure production stability.

## Risk Mitigation
- Keep original encryption methods as fallback
- Implement thorough format validation
- Add extensive error handling and logging
- Test with real production data before deployment

## Success Criteria
- [ ] Python client can encrypt/decrypt files compatible with TypeScript backend
- [ ] Existing encrypted files continue to work (backward compatibility)
- [ ] All tests pass
- [ ] Production deployment successful with zero data loss
