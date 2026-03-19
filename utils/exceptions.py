"""
Custom exceptions for Niklaus plagiarism detector.
"""

from typing import Optional


class NiklausError(Exception):
    """Base exception for Niklaus application."""
    pass


class FileValidationError(NiklausError):
    """Raised when file validation fails."""
    
    def __init__(self, message: str, filename: Optional[str] = None):
        self.filename = filename
        super().__init__(message)


class ZipExtractionError(NiklausError):
    """Raised when ZIP extraction fails."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(message)


class LanguageDetectionError(NiklausError):
    """Raised when language cannot be detected from file extension."""
    
    def __init__(self, extension: str):
        self.extension = extension
        super().__init__(f"Unsupported file extension: {extension}")


class MaritacaAPIError(NiklausError):
    """Raised when Maritaca API call fails."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, original_error: Optional[Exception] = None):
        self.status_code = status_code
        self.original_error = original_error
        super().__init__(message)


class RateLimitError(MaritacaAPIError):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after} seconds" if retry_after 
            else "Rate limit exceeded"
        )


class AnalysisError(NiklausError):
    """Raised when analysis fails."""
    
    def __init__(self, message: str, file1: Optional[str] = None, file2: Optional[str] = None):
        self.file1 = file1
        self.file2 = file2
        super().__init__(message)


class AnalysisCancelledError(NiklausError):
    """Raised when analysis is cancelled by the user."""

    pass


class CacheError(NiklausError):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str, cache_file: Optional[str] = None):
        self.cache_file = cache_file
        super().__init__(message)


class ConfigurationError(NiklausError):
    """Raised when configuration is invalid."""
    pass


class ParallelProcessingError(NiklausError):
    """Raised when parallel processing fails."""

    def __init__(self, message: str, task_id: Optional[int] = None, original_error: Optional[Exception] = None):
        self.task_id = task_id
        self.original_error = original_error
        super().__init__(message)


# ---------------------------------------------------------------------------
# Shared cancellation helper
# ---------------------------------------------------------------------------

def raise_if_cancelled(cancel_check) -> None:
    """Raise AnalysisCancelledError if *cancel_check* is set and returns True.

    Centralised so that pipeline.py and analyzer.py don't duplicate this logic.

    Args:
        cancel_check: Callable[[], bool] or None.  If None, this is a no-op.
    """
    if cancel_check is not None and cancel_check():
        raise AnalysisCancelledError("Analysis cancelled by user")
