import os
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import tempfile
import shutil
from datetime import datetime, timedelta
import threading
import time
import logging
import uuid

logger = logging.getLogger(__name__)

class SecureFileHandler:
    """
    Handles secure processing of uploaded files with encryption and automatic cleanup.
    Files are only stored in memory or in temporary locations and are encrypted.
    """
    
    def __init__(self, temp_dir=None, retention_minutes=60):
        """
        Initialize the secure file handler.
        
        Args:
            temp_dir (str, optional): Directory for temporary files. If None, system temp is used.
            retention_minutes (int): Minutes to retain files before deletion.
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.retention_minutes = retention_minutes
        self.file_registry = {}
        
        # Create a secure temp directory if needed
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir, mode=0o700)  # Secure permissions
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start a background thread to clean up expired files."""
        def cleanup_task():
            while True:
                try:
                    self._cleanup_expired_files()
                    # Sleep for 5 minutes before next cleanup
                    time.sleep(300)
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {str(e)}")
        
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_expired_files(self):
        """Clean up expired temporary files."""
        now = datetime.now()
        expired_ids = []
        
        # Find expired files
        for file_id, info in self.file_registry.items():
            if info['expires_at'] < now:
                # Delete the file
                try:
                    if os.path.exists(info['file_path']):
                        os.remove(info['file_path'])
                    expired_ids.append(file_id)
                    logger.info(f"Deleted expired file: {file_id}")
                except Exception as e:
                    logger.error(f"Error deleting file {file_id}: {str(e)}")
        
        # Remove expired entries from registry
        for file_id in expired_ids:
            self.file_registry.pop(file_id, None)
    
    def process_uploaded_file(self, file_bytes, file_type):
        """
        Process an uploaded file: encrypt it and store temporarily.
        
        Args:
            file_bytes (bytes): Raw file bytes.
            file_type (str): MIME type of the file.
            
        Returns:
            tuple: (file_id, encryption_key) for later retrieval.
        """
        try:
            # Generate a unique ID and encryption key
            file_id = str(uuid.uuid4())
            encryption_key = secrets.token_bytes(32)  # 256-bit key
            iv = secrets.token_bytes(16)  # 128-bit IV for AES
            
            # Encrypt the file content
            encrypted_content = self._encrypt_file(file_bytes, encryption_key, iv)
            
            # Create a temporary file path
            file_extension = self._get_extension_from_type(file_type)
            temp_file_path = os.path.join(self.temp_dir, f"{file_id}{file_extension}")
            
            # Write encrypted content to file
            with open(temp_file_path, 'wb') as f:
                f.write(encrypted_content)
            
            # Set secure permissions
            os.chmod(temp_file_path, 0o600)
            
            # Register file with expiration
            expires_at = datetime.now() + timedelta(minutes=self.retention_minutes)
            self.file_registry[file_id] = {
                'file_path': temp_file_path,
                'encryption_key': encryption_key,
                'iv': iv,
                'file_type': file_type,
                'expires_at': expires_at
            }
            
            return file_id, encryption_key, iv
        
        except Exception as e:
            logger.error(f"Error processing uploaded file: {str(e)}")
            raise
    
    def get_decrypted_file(self, file_id, encryption_key, iv):
        """
        Retrieve and decrypt a temporarily stored file.
        
        Args:
            file_id (str): File ID from process_uploaded_file.
            encryption_key (bytes): Encryption key.
            iv (bytes): Initialization vector.
            
        Returns:
            tuple: (file_bytes, file_type)
        """
        if file_id not in self.file_registry:
            raise ValueError("File not found or expired")
        
        file_info = self.file_registry[file_id]
        
        # Check if file has expired
        if file_info['expires_at'] < datetime.now():
            self._cleanup_expired_files()  # Trigger cleanup
            raise ValueError("File has expired")
        
        # Read encrypted content
        with open(file_info['file_path'], 'rb') as f:
            encrypted_content = f.read()
        
        # Decrypt content
        file_bytes = self._decrypt_file(encrypted_content, encryption_key, iv)
        
        return file_bytes, file_info['file_type']
    
    def delete_file(self, file_id):
        """
        Delete a temporarily stored file.
        
        Args:
            file_id (str): File ID to delete.
        """
        if file_id in self.file_registry:
            file_info = self.file_registry[file_id]
            
            try:
                if os.path.exists(file_info['file_path']):
                    os.remove(file_info['file_path'])
                self.file_registry.pop(file_id)
                logger.info(f"Deleted file: {file_id}")
            except Exception as e:
                logger.error(f"Error deleting file {file_id}: {str(e)}")
                raise
    
    def _encrypt_file(self, file_bytes, key, iv):
        """Encrypt file bytes using AES-256-CBC."""
        # Create a padder for CBC mode
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(file_bytes) + padder.finalize()
        
        # Create AES cipher with CBC mode
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt the data
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Combine IV and encrypted data for storage
        return iv + encrypted_data
    
    def _decrypt_file(self, encrypted_data, key, iv):
        """Decrypt file bytes using AES-256-CBC."""
        # Create AES cipher with CBC mode
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Get encrypted content (excluding IV)
        encrypted_content = encrypted_data[16:]
        
        # Decrypt the data
        padded_data = decryptor.update(encrypted_content) + decryptor.finalize()
        
        # Unpad the data
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        return unpadder.update(padded_data) + unpadder.finalize()
    
    def _get_extension_from_type(self, file_type):
        """Get file extension from MIME type."""
        if file_type == 'application/pdf':
            return '.pdf'
        elif file_type == 'image/jpeg':
            return '.jpg'
        elif file_type == 'image/png':
            return '.png'
        else:
            return '.bin'
