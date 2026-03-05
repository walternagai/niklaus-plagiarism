"""
File handling utilities for Niklaus plagiarism detector.
"""

import os
import io
import re
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
import chardet

from utils.config import config
from utils.exceptions import FileValidationError, ZipExtractionError, LanguageDetectionError
from utils.logger import get_logger

logger = get_logger(__name__)


class FileHandler:
    """Handles file upload, validation, and extraction."""
    
    def __init__(self, max_size_mb: int = None):
        """
        Initialize FileHandler.
        
        Args:
            max_size_mb: Maximum file size in MB
        """
        self.max_size_mb = max_size_mb or config.MAX_ZIP_SIZE_MB
        self.max_size_bytes = self.max_size_mb * 1024 * 1024
        self.allowed_extensions = config.ALLOWED_EXTENSIONS
    
    def validate_zip_file(self, zip_file_bytes: bytes, filename: str) -> None:
        """
        Validate ZIP file before extraction.
        
        Args:
            zip_file_bytes: ZIP file content as bytes
            filename: Original filename
        
        Raises:
            FileValidationError: If validation fails
        """
        # Check file size
        if len(zip_file_bytes) > self.max_size_bytes:
            raise FileValidationError(
                f"File too large. Maximum size is {self.max_size_mb}MB. "
                f"Received {len(zip_file_bytes) / 1024 / 1024:.2f}MB",
                filename=filename
            )
        
        # Check if it's a valid ZIP
        if not zipfile.is_zipfile(io.BytesIO(zip_file_bytes)):
            raise FileValidationError(
                "File is not a valid ZIP archive",
                filename=filename
            )
        
        # Check for dangerous paths (path traversal)
        with zipfile.ZipFile(io.BytesIO(zip_file_bytes), 'r') as zf:
            for member in zf.namelist():
                # Check for absolute paths
                if os.path.isabs(member):
                    raise FileValidationError(
                        f"ZIP contains absolute path: {member}",
                        filename=filename
                    )
                
                # Check for parent directory references
                if '..' in member:
                    raise FileValidationError(
                        f"ZIP contains path traversal attempt: {member}",
                        filename=filename
                    )
    
    def extract_zip(
        self,
        zip_file,
        language: str,
        extract_dir: str = None
    ) -> Tuple[List[str], List[str], str]:
        """
        Extract and validate ZIP file contents.
        
        Args:
            zip_file: Streamlit UploadedFile object
            language: Expected programming language
            extract_dir: Optional extraction directory (temp dir created if None)
        
        Returns:
            Tuple of (files, file_contents, extract_path)
        
        Raises:
            FileValidationError: If validation fails
            ZipExtractionError: If extraction fails
        """
        # Create temp directory if not provided
        if extract_dir is None:
            extract_dir = tempfile.mkdtemp(prefix="niklaus_")
        
        try:
            # Read file content
            file_bytes = zip_file.getvalue()
            
            # Validate
            self.validate_zip_file(file_bytes, zip_file.name)
            
            # Extract
            with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as zf:
                zf.extractall(extract_dir)
            
            logger.info(f"Extracted ZIP to {extract_dir}")
            
            # Find extracted directory (ZIP often creates a subdirectory)
            extracted_items = os.listdir(extract_dir)
            
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                files_path = os.path.join(extract_dir, extracted_items[0])
            else:
                files_path = extract_dir
            
            # Get expected extension
            expected_ext = self.get_extension_for_language(language)
            
            # Find all source files
            files = []
            file_contents = []
            
            for root, dirs, filenames in os.walk(files_path):
                for filename in filenames:
                    if filename.endswith(f'.{expected_ext}'):
                        filepath = os.path.join(root, filename)
                        relative_path = os.path.relpath(filepath, files_path).replace('\\', '/')
                        files.append(relative_path)
                        content = self.read_file(filepath)
                        file_contents.append(content)
            
            if not files:
                raise FileValidationError(
                    f"No files with extension .{expected_ext} found in ZIP",
                    filename=zip_file.name
                )
            
            logger.info(f"Found {len(files)} {language} files")
            
            return files, file_contents, extract_dir
            
        except (FileValidationError, ZipExtractionError):
            # Clean up on validation error
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise
        except Exception as e:
            # Clean up on any error
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            logger.error(f"Failed to extract ZIP: {e}")
            raise ZipExtractionError(
                f"Failed to extract ZIP file: {str(e)}",
                original_error=e
            )
    
    def read_file(self, filepath: str) -> str:
        """
        Read file with automatic encoding detection.
        
        Args:
            filepath: Path to file
        
        Returns:
            File content as string
        """
        try:
            with open(filepath, 'rb') as f:
                file_bytes = f.read()
            
            # Detect encoding
            detected = chardet.detect(file_bytes)
            encoding = detected.get('encoding', 'utf-8')
            
            try:
                return file_bytes.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                # Fallback to utf-8 with error handling
                return file_bytes.decode('utf-8', errors='ignore')
                
        except Exception as e:
            logger.error(f"Failed to read file {filepath}: {e}")
            raise FileValidationError(
                f"Failed to read file: {str(e)}",
                filename=filepath
            )
    
    def get_extension_for_language(self, language: str) -> str:
        """
        Get file extension for a programming language.
        
        Args:
            language: Programming language name
        
        Returns:
            File extension (without dot)
        
        Raises:
            LanguageDetectionError: If language not supported
        """
        lang_map = config.LANGUAGE_EXTENSIONS
        
        language_normalized = language.strip().title()
        
        if language_normalized not in lang_map:
            raise LanguageDetectionError(language)
        
        return lang_map[language_normalized]
    
    def detect_language_from_extension(self, extension: str) -> str:
        """
        Detect programming language from file extension.
        
        Args:
            extension: File extension (with or without dot)
        
        Returns:
            Language name
        
        Raises:
            LanguageDetectionError: If extension not supported
        """
        # Normalize extension
        ext = extension.lstrip('.').lower()
        
        lang_map = config.LANGUAGE_EXTENSIONS
        
        for lang, lang_ext in lang_map.items():
            if lang_ext == ext:
                return lang
        
        raise LanguageDetectionError(extension)
    
    def cleanup(self, extract_dir: str) -> None:
        """
        Clean up extracted files.
        
        Args:
            extract_dir: Directory to remove
        """
        try:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
                logger.info(f"Cleaned up {extract_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {extract_dir}: {e}")
    
    def get_file_stats(self, files: List[str], contents: List[str]) -> dict:
        """
        Get statistics about extracted files.
        
        Args:
            files: List of filenames
            contents: List of file contents
        
        Returns:
            Dictionary with statistics
        """
        total_lines = sum(len(c.split('\n')) for c in contents)
        total_chars = sum(len(c) for c in contents)
        
        return {
            'file_count': len(files),
            'total_lines': total_lines,
            'total_chars': total_chars,
            'avg_lines': total_lines / len(files) if files else 0,
            'avg_chars': total_chars / len(files) if files else 0,
        }
