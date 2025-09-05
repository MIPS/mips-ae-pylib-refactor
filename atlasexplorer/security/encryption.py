"""Encryption functionality for Atlas Explorer with backend compatibility.

This module provides encryption/decryption that is compatible with both the new
TypeScript backend format and maintains backward compatibility with legacy formats.
"""

import os
from pathlib import Path
from typing import Union

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import scrypt

from ..utils.exceptions import EncryptionError

# Import the new compatible encryption class
try:
    from .compatible_encryption import CompatibleEncryption
    COMPATIBLE_ENCRYPTION_AVAILABLE = True
except ImportError:
    COMPATIBLE_ENCRYPTION_AVAILABLE = False


class SecureEncryption:
    """Provides encryption/decryption with automatic backend compatibility.
    
    This class now uses the new backend-compatible encryption by default,
    with automatic fallback to legacy formats for existing encrypted files.
    """
    
    def __init__(self, verbose: bool = True, use_legacy_only: bool = False):
        """Initialize the encryption handler.
        
        Args:
            verbose: Enable verbose logging
            use_legacy_only: Force use of legacy encryption only (for compatibility testing)
        """
        self.verbose = verbose
        self.use_legacy_only = use_legacy_only
        
        # Initialize the appropriate encryption handler
        if COMPATIBLE_ENCRYPTION_AVAILABLE and not use_legacy_only:
            self._encryption_handler = CompatibleEncryption(verbose=verbose)
            if verbose:
                print("Using new backend-compatible encryption with legacy fallback")
        else:
            self._encryption_handler = self
            if verbose:
                print("Using legacy encryption only")
    
    def hybrid_encrypt_file(self, public_key_pem: str, input_file: Union[str, Path]) -> None:
        """Encrypt a file using hybrid encryption.
        
        Uses new backend-compatible format by default, with legacy fallback available.
        
        Args:
            public_key_pem: PEM-encoded RSA public key
            input_file: Path to file to encrypt
            
        Raises:
            EncryptionError: If encryption fails
        """
        if hasattr(self._encryption_handler, 'hybrid_encrypt_file') and self._encryption_handler != self:
            # Use the new compatible encryption
            try:
                self._encryption_handler.hybrid_encrypt_file(public_key_pem, input_file)
                return
            except Exception as e:
                if self.verbose:
                    print(f"New encryption failed, falling back to legacy: {e}")
                # Fall through to legacy method
        
        # Legacy encryption method
        self._legacy_hybrid_encrypt_file(public_key_pem, input_file)
    
    def decrypt_file_with_password(self, src_file_path: Union[str, Path], password: str) -> None:
        """Decrypt a file using password-based decryption.
        
        Automatically detects and handles both new and legacy formats.
        
        Args:
            src_file_path: Path to encrypted file
            password: Decryption password
            
        Raises:
            EncryptionError: If decryption fails
        """
        if hasattr(self._encryption_handler, 'decrypt_file_with_password') and self._encryption_handler != self:
            # Use the new compatible encryption with auto-detection
            try:
                self._encryption_handler.decrypt_file_with_password(src_file_path, password)
                return
            except Exception as e:
                if self.verbose:
                    print(f"New decryption failed, falling back to legacy: {e}")
                # Fall through to legacy method
        
        # Legacy decryption method
        self._legacy_decrypt_file_with_password(src_file_path, password)
    
    def _legacy_hybrid_encrypt_file(self, public_key_pem: str, input_file: Union[str, Path]) -> None:
        """Encrypt a file using the original hybrid encryption format.
        
        This exactly replicates the original __hybrid_encrypt method to maintain
        API compatibility with legacy systems.
        
        Args:
            public_key_pem: PEM-encoded RSA public key
            input_file: Path to file to encrypt
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Read the public key from PEM file
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),  # Convert the string to bytes
                backend=default_backend(),
            )

            input_path = Path(input_file)
            output_file = input_path.with_name("temp.enc")

            # Read file data
            with open(input_file, "rb") as f:
                file_data = f.read()

            # Generate random AES key and IV
            symmetric_key = get_random_bytes(32)  # 256 bits
            iv = get_random_bytes(16)

            cipher = Cipher(
                algorithms.AES(symmetric_key), modes.GCM(iv), backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Encrypt the file data
            encrypted_data = encryptor.update(file_data) + encryptor.finalize()
            # Get the authentication tag (required for GCM mode)
            auth_tag = encryptor.tag

            public_key = serialization.load_pem_public_key(
                public_key_pem.encode("utf-8"), backend=default_backend()
            )

            # Encrypt the symmetric key with the recipient's public key
            encrypted_symmetric_key = public_key.encrypt(
                symmetric_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            # Prepend IV, encrypted symmetric key, and authentication tag to the encrypted data
            output_buffer = iv + encrypted_symmetric_key + auth_tag + encrypted_data

            with open(output_file, "wb") as f:
                f.write(output_buffer)

            os.remove(input_file)
            os.rename(output_file, input_file)

            if self.verbose:
                print("File encrypted using legacy hybrid approach.")

        except Exception as error:
            raise EncryptionError(f"Legacy encryption error: {error}")

    def _legacy_decrypt_file_with_password(self, src_file_path: Union[str, Path], password: str) -> None:
        """Decrypt a file using the original password-based decryption.
        
        This exactly replicates the original __decrypt_file_with_password method.
        
        Args:
            src_file_path: Path to encrypted file
            password: Decryption password
            
        Raises:
            EncryptionError: If decryption fails
        """
        try:
            # Step 1: Read the encrypted file
            with open(src_file_path, "rb") as f:
                encrypted_data = f.read()

            # Step 2: Derive a 256-bit key from the password
            key = scrypt(password.encode(), salt=b"salt", key_len=32, N=16384, r=8, p=1)

            # Step 3: Create a decipher instance (AES-256-ECB mode, no IV)
            cipher = AES.new(key, AES.MODE_ECB)

            # Step 4: Decrypt the file data (remove PKCS#7 padding)
            decrypted_data = cipher.decrypt(encrypted_data)
            pad_len = decrypted_data[-1]
            if pad_len < 1 or pad_len > 16:
                raise ValueError("Invalid padding length.")
            decrypted_data = decrypted_data[:-pad_len]

            # Step 5: Write the decrypted data to a new file
            decrypted_file_path = str(src_file_path) + ".decrypted"
            with open(decrypted_file_path, "wb") as f:
                f.write(decrypted_data)

            # Delete the encrypted file
            os.remove(src_file_path)
            # Rename the decrypted file to the original file name
            os.rename(decrypted_file_path, src_file_path)
            
        except Exception as error:
            raise EncryptionError(f"Decryption failed. Please check the password and try again. Error: {error}")

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
        
        # Check if file exists
        if not path_obj.exists():
            return  # Nothing to delete
        
        try:
            # Get file size
            file_size = path_obj.stat().st_size
            
            # Overwrite file with random data multiple times
            with open(path_obj, "r+b") as f:
                for _ in range(3):  # Multiple overwrites for security
                    f.seek(0)
                    f.write(get_random_bytes(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Finally delete the file
            path_obj.unlink()
            
        except (IOError, OSError):
            # If secure deletion fails, try normal deletion
            try:
                path_obj.unlink()
            except (IOError, OSError):
                # If all deletion attempts fail, silently continue
                pass
