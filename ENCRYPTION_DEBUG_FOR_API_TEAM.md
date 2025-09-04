# Encryption Format Debug Information for API Team

## Issue Summary
The new modern encryption format fails on the backend with:
```
Decryption error: Error: Unsupported state or unable to authenticate data
```

## Test Results

### ✅ WORKING: Legacy Encryption (encryption_legacy_working.py)
- **Upload**: Success
- **Status**: `experiment is being generated..... experiment is ready`
- **Download**: Success  
- **Result**: `Total Cycles: 102639`

### ❌ FAILING: Modern Encryption (encryption.py)  
- **Upload**: Success
- **Status**: `Status check error: Expecting value: line 1 column 1 (char 0)`
- **Download**: Fails - `Package does not exist`
- **Backend Error**: `Decryption error: Error: Unsupported state or unable to authenticate data`

## Technical Differences

### Hybrid Encryption (for experiment upload)

**Legacy Format:**
```
File Structure: IV(16 bytes) + encrypted_symmetric_key + auth_tag(16 bytes) + encrypted_data
AES Mode: Cipher(algorithms.AES, modes.GCM)
IV: get_random_bytes(16) 
Auth Tag: encryptor.tag (separate)
```

**Modern Format:**
```
File Structure: nonce(12 bytes) + key_length(4 bytes) + encrypted_symmetric_key + encrypted_data  
AES Mode: AESGCM
Nonce: secrets.token_bytes(12)
Auth Tag: integrated into encrypted_data
```

### Password Decryption (for result download)

**Legacy Format:**
```
AES Mode: AES.MODE_ECB (no IV)
Salt: b"salt" (hardcoded)
KDF: scrypt(password, salt=b"salt", key_len=32, N=16384, r=8, p=1)
```

**Modern Format:**
```
AES Mode: AES-GCM with nonce
Salt: Random 16 bytes (stored in file)  
KDF: Scrypt with random salt
File Structure: salt(16) + nonce(12) + encrypted_data
```

## Files for Testing
- **Working**: `atlasexplorer/security/encryption_legacy_working.py`
- **Failing**: `atlasexplorer/security/encryption.py` 

## Reproduction Steps
```bash
# Test working format
cp atlasexplorer/security/encryption_legacy_working.py atlasexplorer/security/encryption.py
uv run examples/ae_singlecore.py --elf resources/dhrystone_rv64.elf --verbose

# Test failing format  
git checkout atlasexplorer/security/encryption.py  # or restore modern version
uv run examples/ae_singlecore.py --elf resources/dhrystone_rv64.elf --verbose
```

## Question for API Team
Which specific part of the encryption format change is causing the backend decryption to fail?
1. The hybrid encryption format change (IV vs nonce, auth tag handling)?
2. The password decryption format change (ECB vs GCM, salt handling)?
3. Both?

This will help us understand if we can upgrade part of the encryption while maintaining compatibility.
