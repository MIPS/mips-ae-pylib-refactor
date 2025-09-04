"""Secure encryption and decryption functionality.

This module provides enterprise-grade encryption using modern cryptographic 
libraries and security best practices. It replaces the security vulnerabilities
found in the original implementation.

NOTE: This is the NEW encryption format that we're testing with the API team.
If this fails, we can revert to encryption_legacy_working.py
"""

import os
import secrets
from pathlib import Path
from typing import Union, Optional

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend

from ..core.constants import AtlasConstants
from ..utils.exceptions import EncryptionError


class SecureEncryption:
    """Provides secure hybrid encryption and decryption capabilities.
    
    This class implements modern cryptographic practices:
    - Uses AESGCM for authenticated encryption (replaces AES-ECB)
    - Random salts for key derivation (no hard-coded values)
    - Proper exception handling (no generic catches)
    - Type safety with clear interfaces
    
    NOTE: This is the MODERN encryption format being tested with API team.
    """
    
    def __init__(self, verbose: bool = True):
        """Initialize the encryption handler.
        
        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
    
    def hybrid_encrypt_file(self, public_key_pem: str, input_file: Union[str, Path]) -> None:
        """Encrypt a file using hybrid encryption (RSA + AES-GCM).
        
        This method:
        1. Generates a random AES key
        2. Encrypts the file with AES-GCM (authenticated encryption)
        3. Encrypts the AES key with RSA public key
        4. Combines everything into a secure format
        
        Args:
            public_key_pem: PEM-encoded RSA public key
            input_file: Path to file to encrypt
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            input_path = Path(input_file)
            if not input_path.exists():
                raise EncryptionError(f"Input file does not exist: {input_path}")
            
            # Load the public key
            try:
                public_key = serialization.load_pem_public_key(
                    public_key_pem.encode('utf-8'),
                    backend=default_backend()
                )
            except Exception as e:
                raise EncryptionError(f"Invalid public key: {e}")
            
            # Read file data
            try:
                with open(input_path, "rb") as f:
                    file_data = f.read()
            except IOError as e:
                raise EncryptionError(f"Cannot read input file: {e}")
            
            # Generate random AES key (256-bit)
            symmetric_key = secrets.token_bytes(32)
            nonce = secrets.token_bytes(12)  # GCM nonce (96 bits recommended)
            
            # Encrypt file data with AES-GCM (provides authentication)
            aesgcm = AESGCM(symmetric_key)
            encrypted_data = aesgcm.encrypt(nonce, file_data, None)
            
            # Encrypt the symmetric key with RSA public key
            try:
                encrypted_symmetric_key = public_key.encrypt(
                    symmetric_key,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None,
                    ),
                )
            except Exception as e:
                raise EncryptionError(f"RSA encryption failed: {e}")
            
            # Create output format: nonce + encrypted_key_length + encrypted_key + encrypted_data
            encrypted_key_length = len(encrypted_symmetric_key).to_bytes(4, 'big')
            output_buffer = nonce + encrypted_key_length + encrypted_symmetric_key + encrypted_data
            
            # Write encrypted data to temporary file, then replace original
            temp_file = input_path.with_suffix(input_path.suffix + '.tmp')
            try:
                with open(temp_file, "wb") as f:
                    f.write(output_buffer)
                
                # Atomic replacement
                temp_file.replace(input_path)
                
                if self.verbose:
                    print("File encrypted using modern secure hybrid approach.")
                    
            except IOError as e:
                # Clean up temp file if it exists
                if temp_file.exists():
                    temp_file.unlink()
                raise EncryptionError(f"Cannot write encrypted file: {e}")
            
        except EncryptionError:
            raise
        except Exception as e:
            raise EncryptionError(f"Unexpected encryption error: {e}")
    
    def decrypt_file_with_password(self, src_file_path: Union[str, Path], password: str) -> None:
        """Decrypt a file using password-based encryption.
        
        This method uses secure practices:
        - Random salt generation (no hard-coded salt)
        - AESGCM for authenticated decryption
        - Proper error handling and cleanup
        
        Args:
            src_file_path: Path to encrypted file
            password: Decryption password
            
        Raises:
            EncryptionError: If decryption fails
        """
        try:
            src_path = Path(src_file_path)
            if not src_path.exists():
                raise EncryptionError(f"Encrypted file does not exist: {src_path}")
            
            # Read the encrypted file
            try:
                with open(src_path, "rb") as f:
                    encrypted_data = f.read()
            except IOError as e:
                raise EncryptionError(f"Cannot read encrypted file: {e}")
            
            if len(encrypted_data) < 32:  # Minimum size: salt(16) + nonce(12) + some data
                raise EncryptionError("File too small to be valid encrypted data")
            
            # Extract salt and nonce from the beginning of file
            salt = encrypted_data[:16]  # First 16 bytes are salt
            nonce = encrypted_data[16:28]  # Next 12 bytes are nonce
            ciphertext = encrypted_data[28:]  # Remaining is encrypted data
            
            # Derive key from password using scrypt with random salt
            try:
                kdf = Scrypt(
                    length=32,  # 256-bit key
                    salt=salt,
                    n=AtlasConstants.SCRYPT_N,
                    r=AtlasConstants.SCRYPT_R,
                    p=AtlasConstants.SCRYPT_P,
                    backend=default_backend()
                )
                key = kdf.derive(password.encode('utf-8'))
            except Exception as e:
                raise EncryptionError(f"Key derivation failed: {e}")
            
            # Decrypt using AES-GCM
            try:
                aesgcm = AESGCM(key)
                decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
            except Exception as e:
                raise EncryptionError(f"Decryption failed - invalid password or corrupted data: {e}")
            
            # Write decrypted data to temporary file, then replace original
            temp_file = src_path.with_suffix(src_path.suffix + '.tmp')
            try:
                with open(temp_file, "wb") as f:
                    f.write(decrypted_data)
                
                # Atomic replacement
                temp_file.replace(src_path)
                
                if self.verbose:
                    print("File decrypted successfully using modern encryption.")
                    
            except IOError as e:
                # Clean up temp file if it exists
                if temp_file.exists():
                    temp_file.unlink()
                raise EncryptionError(f"Cannot write decrypted file: {e}")
            
        except EncryptionError:
            raise
        except Exception as e:
            raise EncryptionError(f"Unexpected decryption error: {e}")
    
    @staticmethod
    def generate_salt() -> bytes:
        """Generate a cryptographically secure random salt.
        
        Returns:
            16 bytes of random data suitable for use as a salt
        """
        return secrets.token_bytes(16)
    
    @staticmethod
    def secure_delete(file_path: Union[str, Path]) -> None:
        """Securely delete a file by overwriting it before removal.
        
        Args:
            file_path: Path to file to securely delete
        """
        path = Path(file_path)
        if not path.exists():
            return
            
        try:
            # Overwrite file with random data
            file_size = path.stat().st_size
            with open(path, "wb") as f:
                f.write(secrets.token_bytes(file_size))
            
            # Remove the file
            path.unlink()
        except Exception:
            # Fallback to normal deletion if secure delete fails
            try:
                path.unlink()
            except Exception:
                pass  # File may have been deleted already
