"""Tests for the new backend-compatible encryption functionality.

This test suite validates:
1. New encryption format compatibility with TypeScript backend
2. Backward compatibility with legacy formats
3. Fallback mechanisms
4. Error handling
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from atlasexplorer.security.encryption import SecureEncryption
from atlasexplorer.security.compatible_encryption import CompatibleEncryption
from atlasexplorer.utils.exceptions import EncryptionError


class TestCompatibleEncryption:
    """Test suite for the new compatible encryption functionality."""
    
    @pytest.fixture
    def temp_file(self):
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b"This is test data for encryption testing"
            f.write(test_data)
            temp_path = f.name
        
        yield temp_path, test_data
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def sample_public_key(self):
        """Sample RSA public key for testing."""
        return """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1234567890ABCDEF...
-----END PUBLIC KEY-----"""
    
    @pytest.fixture
    def sample_private_key(self):
        """Sample RSA private key for testing."""
        return """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDXYZ...
-----END PRIVATE KEY-----"""
    
    def test_encryption_initialization(self):
        """Test that encryption classes initialize correctly."""
        # Test compatible encryption
        enc = CompatibleEncryption(verbose=True)
        assert enc.verbose is True
        
        # Test secure encryption with compatible handler
        secure_enc = SecureEncryption(verbose=True, use_legacy_only=False)
        assert secure_enc.verbose is True
        
        # Test legacy-only mode
        legacy_enc = SecureEncryption(verbose=True, use_legacy_only=True)
        assert legacy_enc.use_legacy_only is True
    
    def test_format_detection_hybrid(self):
        """Test detection of hybrid encryption formats."""
        enc = CompatibleEncryption()
        
        # Test with mock file data representing new format
        with tempfile.NamedTemporaryFile() as f:
            # New format: 12-byte IV + 2-byte key length + key + data + tag
            mock_data = b'A' * 12 + b'\x01\x00' + b'B' * 256 + b'C' * 100 + b'D' * 16
            f.write(mock_data)
            f.flush()
            
            format_type = enc._detect_hybrid_format(f.name)
            assert format_type == enc.NEW_HYBRID_FORMAT
        
        # Test with mock file data representing legacy format
        with tempfile.NamedTemporaryFile() as f:
            # Legacy format: 16-byte IV + encrypted key + tag + data
            mock_data = b'A' * 16 + b'B' * 256 + b'C' * 16 + b'D' * 100
            f.write(mock_data)
            f.flush()
            
            format_type = enc._detect_hybrid_format(f.name)
            assert format_type == enc.LEGACY_HYBRID_FORMAT
    
    def test_format_detection_password(self):
        """Test detection of password encryption formats."""
        enc = CompatibleEncryption()
        
        # Test with mock file data representing new format
        with tempfile.NamedTemporaryFile() as f:
            # New format: 16-byte salt + 12-byte IV + 16-byte tag + ciphertext
            mock_data = b'A' * 16 + b'B' * 12 + b'C' * 16 + b'D' * 100
            f.write(mock_data)
            f.flush()
            
            format_type = enc._detect_password_format(f.name)
            assert format_type == enc.NEW_PASSWORD_FORMAT
        
        # Test with smaller file (legacy format)
        with tempfile.NamedTemporaryFile() as f:
            mock_data = b'A' * 32  # Smaller than new format header
            f.write(mock_data)
            f.flush()
            
            format_type = enc._detect_password_format(f.name)
            assert format_type == enc.LEGACY_PASSWORD_FORMAT
    
    def test_password_encryption_new_format(self, temp_file):
        """Test new password-based encryption format."""
        file_path, original_data = temp_file
        password = "test_password_123"
        
        enc = CompatibleEncryption(verbose=True)
        
        # Encrypt the file
        enc.encrypt_file_with_password(file_path, password)
        
        # Verify file structure matches new format
        with open(file_path, "rb") as f:
            encrypted_data = f.read()
        
        # Should have: salt(16) + iv(12) + tag(16) + ciphertext
        assert len(encrypted_data) >= 44  # Minimum header size
        
        # Decrypt and verify
        enc.decrypt_file_with_password(file_path, password)
        
        with open(file_path, "rb") as f:
            decrypted_data = f.read()
        
        assert decrypted_data == original_data
    
    def test_legacy_fallback(self, temp_file):
        """Test fallback to legacy encryption methods."""
        file_path, original_data = temp_file
        
        # Create SecureEncryption instance
        enc = SecureEncryption(verbose=True, use_legacy_only=False)
        
        # Mock the new encryption to fail, forcing fallback
        with patch.object(enc._encryption_handler, 'decrypt_file_with_password', 
                         side_effect=Exception("New method failed")):
            
            # This should fall back to legacy method
            with patch.object(enc, '_legacy_decrypt_file_with_password') as mock_legacy:
                enc.decrypt_file_with_password(file_path, "password")
                mock_legacy.assert_called_once()
    
    def test_error_handling(self, temp_file):
        """Test error handling in encryption operations."""
        file_path, _ = temp_file
        
        enc = CompatibleEncryption()
        
        # Test with invalid password format
        with pytest.raises(EncryptionError):
            enc.decrypt_file_with_password(file_path, "")
        
        # Test with non-existent file
        with pytest.raises(EncryptionError):
            enc.encrypt_file_with_password("/nonexistent/file.txt", "password")
    
    def test_secure_encryption_compatibility_mode(self):
        """Test SecureEncryption class in compatibility mode."""
        # Test with compatible encryption available
        enc = SecureEncryption(verbose=True, use_legacy_only=False)
        assert hasattr(enc, '_encryption_handler')
        
        # Test with legacy-only mode
        enc_legacy = SecureEncryption(verbose=True, use_legacy_only=True)
        assert enc_legacy._encryption_handler == enc_legacy
    
    def test_salt_generation(self):
        """Test salt generation functionality."""
        salt1 = CompatibleEncryption.generate_salt()
        salt2 = CompatibleEncryption.generate_salt()
        
        assert len(salt1) == 16
        assert len(salt2) == 16
        assert salt1 != salt2  # Should be random
    
    def test_secure_delete(self, temp_file):
        """Test secure file deletion."""
        file_path, _ = temp_file
        
        # Ensure file exists
        assert os.path.exists(file_path)
        
        # Secure delete
        CompatibleEncryption.secure_delete(file_path)
        
        # File should be gone
        assert not os.path.exists(file_path)
        
        # Test with non-existent file (should not raise error)
        CompatibleEncryption.secure_delete("/nonexistent/file.txt")


class TestBackendCompatibility:
    """Test compatibility with TypeScript backend format specifications."""
    
    def test_hybrid_format_specification(self):
        """Test that hybrid encryption matches backend specification."""
        # Backend format: [iv(12)][key_length(2)][encrypted_key][encrypted_data][auth_tag(16)]
        
        enc = CompatibleEncryption()
        
        # Mock the encryption process to verify format
        with tempfile.NamedTemporaryFile() as f:
            f.write(b"test data")
            f.flush()
            
            # Note: This would require real keys to test fully
            # For now, we test the format detection logic
            
            # Create mock encrypted data in new format
            iv = b'A' * 12
            key_length = 256
            encrypted_key = b'B' * key_length
            encrypted_data = b'C' * 100
            auth_tag = b'D' * 16
            
            mock_encrypted = (iv + 
                            key_length.to_bytes(2, 'big') + 
                            encrypted_key + 
                            encrypted_data + 
                            auth_tag)
            
            with tempfile.NamedTemporaryFile() as encrypted_file:
                encrypted_file.write(mock_encrypted)
                encrypted_file.flush()
                
                format_type = enc._detect_hybrid_format(encrypted_file.name)
                assert format_type == enc.NEW_HYBRID_FORMAT
    
    def test_password_format_specification(self):
        """Test that password encryption matches backend specification."""
        # Backend format: [salt(16)][iv(12)][tag(16)][ciphertext]
        
        enc = CompatibleEncryption()
        
        # Create mock encrypted data in new format
        salt = b'A' * 16
        iv = b'B' * 12
        tag = b'C' * 16
        ciphertext = b'D' * 100
        
        mock_encrypted = salt + iv + tag + ciphertext
        
        with tempfile.NamedTemporaryFile() as encrypted_file:
            encrypted_file.write(mock_encrypted)
            encrypted_file.flush()
            
            format_type = enc._detect_password_format(encrypted_file.name)
            assert format_type == enc.NEW_PASSWORD_FORMAT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
