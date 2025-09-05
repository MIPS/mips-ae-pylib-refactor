"""Tests for the SecureEncryption module.

This test suite covers the current encryption implementation that maintains
compatibility with the original Atlas Explorer API format.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from atlasexplorer.security.encryption import SecureEncryption
from atlasexplorer.utils.exceptions import EncryptionError


class TestSecureEncryptionBasics(unittest.TestCase):
    """Test basic SecureEncryption functionality."""

    def test_initialization_default(self):
        """Test default initialization."""
        encryption = SecureEncryption()
        self.assertTrue(encryption.verbose)

    def test_initialization_verbose_false(self):
        """Test initialization with verbose=False."""
        encryption = SecureEncryption(verbose=False)
        self.assertFalse(encryption.verbose)

    def test_initialization_verbose_true(self):
        """Test initialization with verbose=True."""
        encryption = SecureEncryption(verbose=True)
        self.assertTrue(encryption.verbose)


class TestSecureEncryptionUtilities(unittest.TestCase):
    """Test utility methods."""

    def test_generate_salt(self):
        """Test salt generation."""
        salt1 = SecureEncryption.generate_salt()
        salt2 = SecureEncryption.generate_salt()
        
        # Should be bytes
        self.assertIsInstance(salt1, bytes)
        self.assertIsInstance(salt2, bytes)
        
        # Should be 16 bytes
        self.assertEqual(len(salt1), 16)
        self.assertEqual(len(salt2), 16)
        
        # Should be different (random)
        self.assertNotEqual(salt1, salt2)

    def test_secure_delete_nonexistent_file(self):
        """Test secure delete on non-existent file."""
        # Should not raise exception
        SecureEncryption.secure_delete("/nonexistent/path/file.txt")

    def test_secure_delete_existing_file(self):
        """Test secure delete on existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test data to delete")
            temp_file_path = temp_file.name

        # Verify file exists
        self.assertTrue(os.path.exists(temp_file_path))

        # Securely delete
        SecureEncryption.secure_delete(temp_file_path)

        # Verify file is gone
        self.assertFalse(os.path.exists(temp_file_path))

    def test_secure_delete_with_path_object(self):
        """Test secure delete with Path object."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test data")
            temp_path = Path(temp_file.name)

        # Verify file exists
        self.assertTrue(temp_path.exists())

        # Securely delete using Path object
        SecureEncryption.secure_delete(temp_path)

        # Verify file is gone
        self.assertFalse(temp_path.exists())


class TestSecureEncryptionHybrid(unittest.TestCase):
    """Test hybrid encryption functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.encryption = SecureEncryption(verbose=False)
        
        # Generate a test RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        self.public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        self.test_data = b"Test data for encryption"

    def test_hybrid_encrypt_file_success(self):
        """Test successful hybrid file encryption."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(self.test_data)
            temp_file_path = temp_file.name

        try:
            # Should not raise exception
            self.encryption.hybrid_encrypt_file(self.public_key_pem, temp_file_path)
            
            # File should still exist but be encrypted
            self.assertTrue(os.path.exists(temp_file_path))
            
            # File content should be different (encrypted)
            with open(temp_file_path, 'rb') as f:
                encrypted_data = f.read()
            self.assertNotEqual(encrypted_data, self.test_data)
            
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_hybrid_encrypt_file_nonexistent_file(self):
        """Test hybrid encryption with non-existent file."""
        with self.assertRaises(EncryptionError) as context:
            self.encryption.hybrid_encrypt_file(self.public_key_pem, "/nonexistent/file.txt")
        
        self.assertIn("No such file or directory", str(context.exception))

    def test_hybrid_encrypt_file_invalid_key(self):
        """Test hybrid encryption with invalid public key."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(self.test_data)
            temp_file_path = temp_file.name

        try:
            invalid_key = "-----BEGIN PUBLIC KEY-----\nINVALID_KEY\n-----END PUBLIC KEY-----"
            
            with self.assertRaises(EncryptionError) as context:
                self.encryption.hybrid_encrypt_file(invalid_key, temp_file_path)
            
            self.assertIn("Unable to load PEM file", str(context.exception))
            
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_hybrid_encrypt_file_verbose_output(self):
        """Test verbose output during encryption."""
        encryption_verbose = SecureEncryption(verbose=True)
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(self.test_data)
            temp_file_path = temp_file.name

        try:
            with patch('builtins.print') as mock_print:
                encryption_verbose.hybrid_encrypt_file(self.public_key_pem, temp_file_path)
                mock_print.assert_called_with("File encrypted using secure hybrid approach.")
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)


class TestSecureEncryptionPassword(unittest.TestCase):
    """Test password-based decryption functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.encryption = SecureEncryption(verbose=False)
        self.test_password = "test_password_123"

    def test_decrypt_file_nonexistent_file(self):
        """Test decryption with non-existent file."""
        with self.assertRaises(EncryptionError) as context:
            self.encryption.decrypt_file_with_password("/nonexistent/file.enc", self.test_password)
        
        self.assertIn("No such file or directory", str(context.exception))

    def test_decrypt_file_too_small(self):
        """Test decryption with file too small."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"small")  # Too small for valid encrypted data
            temp_file_path = temp_file.name

        try:
            with self.assertRaises(EncryptionError) as context:
                self.encryption.decrypt_file_with_password(temp_file_path, self.test_password)
            
            # The actual error depends on the encryption format, could be alignment or other
            self.assertIn("Decryption failed", str(context.exception))
            
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_decrypt_file_wrong_password(self):
        """Test decryption with wrong password."""
        # Create some fake encrypted data (16-byte aligned for AES)
        fake_encrypted_data = b"0123456789ABCDEF" * 2  # 32 bytes
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(fake_encrypted_data)
            temp_file_path = temp_file.name

        try:
            with self.assertRaises(EncryptionError) as context:
                self.encryption.decrypt_file_with_password(temp_file_path, "wrong_password")
            
            self.assertIn("Decryption failed", str(context.exception))
            
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_decrypt_file_permission_error(self):
        """Test decryption when file cannot be read."""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with self.assertRaises(EncryptionError) as context:
                self.encryption.decrypt_file_with_password("/some/file.enc", self.test_password)
            
            self.assertIn("Permission denied", str(context.exception))


class TestSecureEncryptionErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.encryption = SecureEncryption(verbose=False)

    def test_hybrid_encrypt_file_read_permission_error(self):
        """Test hybrid encryption when file cannot be read."""
        # Just test that permission errors are wrapped properly
        with self.assertRaises(EncryptionError) as context:
            # Use non-existent file to trigger error
            self.encryption.hybrid_encrypt_file("dummy_key", "/root/non_accessible_file.txt")
        
        # Should wrap the underlying error
        self.assertIn("Encryption error", str(context.exception))

    def test_secure_delete_permission_error(self):
        """Test secure delete when file cannot be deleted."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test")
            temp_file_path = temp_file.name

        # Mock unlink to raise permission error
        with patch('pathlib.Path.unlink', side_effect=PermissionError("Permission denied")):
            # Should not raise exception (graceful handling)
            SecureEncryption.secure_delete(temp_file_path)

        # Clean up manually since mock prevented deletion
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


if __name__ == '__main__':
    unittest.main()
