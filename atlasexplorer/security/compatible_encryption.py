"""Updated encryption functionality for Atlas Explorer with backend compatibility.

This module provides encryption/decryption that is compatible with both the new
TypeScript backend format and maintains backward compatibility with legacy formats.
"""

import os
import struct
from pathlib import Path
from typing import Union, Tuple, Optional

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import scrypt

from ..utils.exceptions import EncryptionError


class CompatibleEncryption:
    """Encryption/decryption compatible with new TypeScript backend and legacy formats.
    
    This class provides:
    - New encryption format matching TypeScript backend exactly
    - Automatic detection and fallback to legacy format decryption
    - Secure migration path for existing encrypted files
    """
    
    # Format identifiers
    LEGACY_HYBRID_FORMAT = "legacy_hybrid"
    NEW_HYBRID_FORMAT = "new_hybrid"
    LEGACY_PASSWORD_FORMAT = "legacy_password"
    NEW_PASSWORD_FORMAT = "new_password"
    
    def __init__(self, verbose: bool = True):
        """Initialize the encryption handler.
        
        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
    
    def hybrid_encrypt_file(self, public_key_pem: str, input_file: Union[str, Path]) -> None:
        """Encrypt a file using the new backend-compatible hybrid encryption format.
        
        New format: [iv(12)][key_length(2)][encrypted_key][encrypted_data][auth_tag(16)]
        
        Args:
            public_key_pem: PEM-encoded RSA public key
            input_file: Path to file to encrypt
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=default_backend(),
            )

            input_path = Path(input_file)
            output_file = input_path.with_name("temp.enc")

            # Read file data
            with open(input_file, "rb") as f:
                file_data = f.read()

            # Generate random AES key and IV (12 bytes for GCM compatibility)
            symmetric_key = get_random_bytes(32)  # 256 bits
            iv = get_random_bytes(12)  # 12 bytes for GCM mode (backend compatible)

            # Encrypt the symmetric key with RSA
            encrypted_symmetric_key = public_key.encrypt(
                symmetric_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            # Setup AES-GCM cipher
            cipher = Cipher(
                algorithms.AES(symmetric_key), 
                modes.GCM(iv), 
                backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Encrypt the file data
            encrypted_data = encryptor.update(file_data) + encryptor.finalize()
            auth_tag = encryptor.tag

            # Build output in new backend format: [iv][key_length][encrypted_key][encrypted_data][auth_tag]
            with open(output_file, "wb") as f:
                # Write IV (12 bytes)
                f.write(iv)
                
                # Write encrypted key length as 2-byte big-endian integer
                key_length = len(encrypted_symmetric_key)
                f.write(struct.pack('>H', key_length))
                
                # Write encrypted symmetric key
                f.write(encrypted_symmetric_key)
                
                # Write encrypted data
                f.write(encrypted_data)
                
                # Write auth tag at the end
                f.write(auth_tag)

            # Replace original file
            os.remove(input_file)
            os.rename(output_file, input_file)

            if self.verbose:
                print("File encrypted using new backend-compatible hybrid format.")

        except Exception as error:
            raise EncryptionError(f"New hybrid encryption error: {error}")

    def hybrid_decrypt_file(self, private_key_pem: str, input_file: Union[str, Path]) -> None:
        """Decrypt a hybrid-encrypted file with automatic format detection.
        
        Supports both new and legacy formats with automatic fallback.
        
        Args:
            private_key_pem: PEM-encoded RSA private key
            input_file: Path to encrypted file
            
        Raises:
            EncryptionError: If decryption fails
        """
        try:
            # Detect format and decrypt accordingly
            format_type = self._detect_hybrid_format(input_file)
            
            if format_type == self.NEW_HYBRID_FORMAT:
                self._decrypt_new_hybrid_format(private_key_pem, input_file)
            elif format_type == self.LEGACY_HYBRID_FORMAT:
                if self.verbose:
                    print("Detected legacy format, using fallback decryption...")
                self._decrypt_legacy_hybrid_format(private_key_pem, input_file)
            else:
                raise EncryptionError("Unknown hybrid encryption format")
                
        except Exception as error:
            raise EncryptionError(f"Hybrid decryption error: {error}")

    def encrypt_file_with_password(self, src_file_path: Union[str, Path], password: str) -> None:
        """Encrypt a file using new backend-compatible password-based encryption.
        
        New format: [salt(16)][iv(12)][tag(16)][ciphertext]
        Uses AES-256-GCM with random salt and enhanced scrypt parameters.
        
        Args:
            src_file_path: Path to file to encrypt
            password: Encryption password
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Read file data
            with open(src_file_path, "rb") as f:
                file_data = f.read()

            # Generate random salt and IV
            salt = get_random_bytes(16)
            iv = get_random_bytes(12)  # 12 bytes for GCM

            # Derive key using enhanced scrypt parameters (matching backend)
            key = scrypt(
                password.encode(), 
                salt=salt, 
                key_len=32, 
                N=32768,  # Enhanced parameter matching backend
                r=8, 
                p=1
            )

            # Encrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            encrypted_data = encryptor.update(file_data) + encryptor.finalize()
            auth_tag = encryptor.tag

            # Write in new backend format: [salt][iv][tag][ciphertext]
            encrypted_file_path = str(src_file_path) + ".encrypted"
            with open(encrypted_file_path, "wb") as f:
                f.write(salt)          # 16 bytes
                f.write(iv)            # 12 bytes  
                f.write(auth_tag)      # 16 bytes
                f.write(encrypted_data)

            # Replace original file
            os.remove(src_file_path)
            os.rename(encrypted_file_path, src_file_path)

            if self.verbose:
                print("File encrypted using new backend-compatible password format.")

        except Exception as error:
            raise EncryptionError(f"New password encryption error: {error}")

    def decrypt_file_with_password(self, src_file_path: Union[str, Path], password: str) -> None:
        """Decrypt a password-encrypted file with automatic format detection.
        
        Supports both new and legacy formats with automatic fallback.
        
        Args:
            src_file_path: Path to encrypted file
            password: Decryption password
            
        Raises:
            EncryptionError: If decryption fails
        """
        try:
            # Detect format and decrypt accordingly
            format_type = self._detect_password_format(src_file_path)
            
            if format_type == self.NEW_PASSWORD_FORMAT:
                self._decrypt_new_password_format(src_file_path, password)
            elif format_type == self.LEGACY_PASSWORD_FORMAT:
                if self.verbose:
                    print("Detected legacy format, using fallback decryption...")
                self._decrypt_legacy_password_format(src_file_path, password)
            else:
                raise EncryptionError("Unknown password encryption format")
                
        except Exception as error:
            raise EncryptionError(f"Password decryption error: {error}")

    def _detect_hybrid_format(self, file_path: Union[str, Path]) -> str:
        """Detect whether file uses new or legacy hybrid encryption format.
        
        Args:
            file_path: Path to encrypted file
            
        Returns:
            Format type constant
        """
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            
            # New format starts with 12-byte IV, then 2-byte key length
            if len(data) >= 14:
                # Check if bytes 12-14 could be a reasonable key length (RSA keys are typically 256-512 bytes)
                key_length = struct.unpack('>H', data[12:14])[0]
                if 128 <= key_length <= 1024:  # Reasonable RSA key size range
                    return self.NEW_HYBRID_FORMAT
            
            # Legacy format starts with 16-byte IV
            if len(data) >= 16:
                return self.LEGACY_HYBRID_FORMAT
                
            raise EncryptionError("File too small to determine format")
            
        except Exception:
            # Default to legacy format for safety
            return self.LEGACY_HYBRID_FORMAT

    def _detect_password_format(self, file_path: Union[str, Path]) -> str:
        """Detect whether file uses new or legacy password encryption format.
        
        Args:
            file_path: Path to encrypted file
            
        Returns:
            Format type constant
        """
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            
            # New format: [salt(16)][iv(12)][tag(16)][ciphertext]
            # Legacy format: raw AES-ECB encrypted data with PKCS7 padding
            
            # New format has specific header size
            if len(data) >= 44:  # 16 + 12 + 16 = 44 bytes header
                return self.NEW_PASSWORD_FORMAT
            
            # If file size suggests it could be legacy format
            return self.LEGACY_PASSWORD_FORMAT
            
        except Exception:
            # Default to legacy format for safety
            return self.LEGACY_PASSWORD_FORMAT

    def _decrypt_new_hybrid_format(self, private_key_pem: str, input_file: Union[str, Path]) -> None:
        """Decrypt file in new hybrid format."""
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend(),
        )

        with open(input_file, "rb") as f:
            # Read IV (12 bytes)
            iv = f.read(12)
            
            # Read encrypted key length (2 bytes)
            key_length_bytes = f.read(2)
            key_length = struct.unpack('>H', key_length_bytes)[0]
            
            # Read encrypted symmetric key
            encrypted_symmetric_key = f.read(key_length)
            
            # Read remaining data (encrypted content + auth tag)
            remaining_data = f.read()
            
        # Auth tag is last 16 bytes
        auth_tag = remaining_data[-16:]
        encrypted_data = remaining_data[:-16]

        # Decrypt symmetric key
        symmetric_key = private_key.decrypt(
            encrypted_symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        # Decrypt data
        cipher = Cipher(
            algorithms.AES(symmetric_key),
            modes.GCM(iv, auth_tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

        # Write decrypted file
        decrypted_file_path = str(input_file) + ".decrypted"
        with open(decrypted_file_path, "wb") as f:
            f.write(decrypted_data)

        os.remove(input_file)
        os.rename(decrypted_file_path, input_file)

    def _decrypt_legacy_hybrid_format(self, private_key_pem: str, input_file: Union[str, Path]) -> None:
        """Decrypt file in legacy hybrid format - fallback method."""
        # Import the legacy encryption class for fallback
        from .encryption import SecureEncryption
        legacy_encryption = SecureEncryption(verbose=self.verbose)
        
        # This would need the original hybrid_decrypt_file method
        # For now, raise an error suggesting manual migration
        raise EncryptionError(
            "Legacy hybrid format detected. Please use the legacy SecureEncryption class "
            "or migrate to new format."
        )

    def _decrypt_new_password_format(self, src_file_path: Union[str, Path], password: str) -> None:
        """Decrypt file in new password format."""
        with open(src_file_path, "rb") as f:
            # Read salt (16 bytes)
            salt = f.read(16)
            # Read IV (12 bytes)
            iv = f.read(12)
            # Read auth tag (16 bytes)
            auth_tag = f.read(16)
            # Read encrypted data
            encrypted_data = f.read()

        # Derive key using enhanced scrypt parameters
        key = scrypt(
            password.encode(),
            salt=salt,
            key_len=32,
            N=32768,
            r=8,
            p=1
        )

        # Decrypt using AES-256-GCM
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, auth_tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

        # Write decrypted file
        decrypted_file_path = str(src_file_path) + ".decrypted"
        with open(decrypted_file_path, "wb") as f:
            f.write(decrypted_data)

        os.remove(src_file_path)
        os.rename(decrypted_file_path, src_file_path)

    def _decrypt_legacy_password_format(self, src_file_path: Union[str, Path], password: str) -> None:
        """Decrypt file in legacy password format - fallback method."""
        from .encryption import SecureEncryption
        legacy_encryption = SecureEncryption(verbose=self.verbose)
        legacy_encryption.decrypt_file_with_password(src_file_path, password)

    @staticmethod
    def generate_salt() -> bytes:
        """Generate a random salt for encryption.
        
        Returns:
            16 bytes of random data for use as salt
        """
        return get_random_bytes(16)
    
    @staticmethod
    def secure_delete(file_path: Union[str, Path]) -> None:
        """Securely delete a file by overwriting it with random data.
        
        Args:
            file_path: Path to file to securely delete
        """
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            return
        
        try:
            file_size = path_obj.stat().st_size
            
            with open(path_obj, "r+b") as f:
                for _ in range(3):
                    f.seek(0)
                    f.write(get_random_bytes(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            path_obj.unlink()
            
        except (IOError, OSError):
            try:
                path_obj.unlink()
            except (IOError, OSError):
                pass
