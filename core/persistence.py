"""
Persistence and caching module for Niklaus plagiarism detector.
"""

import json
import pickle
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from utils.config import config
from utils.exceptions import CacheError
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisCache:
    """Manages persistent cache for analysis results."""
    
    def __init__(self, cache_dir: str = None):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir or config.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache directory: {self.cache_dir}")
    
    def _content_signature(self, files: List[str], contents: Optional[List[str]], language: Optional[str]) -> str:
        """Build deterministic signature from files, contents, and language."""
        if contents is None:
            file_list = sorted(files)
            payload = f"{language or 'unknown'}::{repr(file_list)}"
            return hashlib.sha256(payload.encode()).hexdigest()[:16]

        pairs = sorted(zip(files, contents), key=lambda item: item[0])
        hasher = hashlib.sha256()
        hasher.update((language or 'unknown').encode())
        hasher.update(b"\x00")

        for filename, content in pairs:
            hasher.update(str(filename).encode())
            hasher.update(b"\x00")
            hasher.update(hashlib.sha256(str(content).encode()).digest())
            hasher.update(b"\x00")

        return hasher.hexdigest()[:16]

    def _get_cache_key(
        self,
        files: List[str],
        threshold: float,
        contents: Optional[List[str]] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Generate unique cache key for file set.
        
        Args:
            files: List of filenames
            threshold: Similarity threshold
        
        Returns:
            Cache filename
        """
        file_hash = self._content_signature(files, contents, language)
        
        return f"analysis_{file_hash}_{threshold:.2f}.pkl"

    def _get_cache_path(
        self,
        files: List[str],
        threshold: float,
        contents: Optional[List[str]] = None,
        language: Optional[str] = None
    ) -> Path:
        """Get full path to cache file."""
        return self.cache_dir / self._get_cache_key(files, threshold, contents=contents, language=language)
    
    def save(
        self,
        files: List[str],
        threshold: float,
        analysis_data: Dict,
        contents: Optional[List[str]] = None,
        language: str = None
    ) -> Path:
        """
        Save analysis results to cache.
        
        Args:
            files: List of filenames analyzed
            threshold: Similarity threshold used
            analysis_data: Analysis results dictionary
            language: Programming language (optional)
        
        Returns:
            Path to cache file
        
        Raises:
            CacheError: If save fails
        """
        try:
            cache_file = self._get_cache_path(files, threshold, contents=contents, language=language)
            
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'files': files,
                'threshold': threshold,
                'language': language,
                'data': analysis_data,
                'version': '1.0'
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            logger.info(f"Analysis cached to {cache_file.name}")
            return cache_file
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            raise CacheError(
                f"Failed to save analysis cache: {str(e)}",
                cache_file=str(cache_file) if 'cache_file' in locals() else None
            )
    
    def load(
        self,
        files: List[str],
        threshold: float,
        contents: Optional[List[str]] = None,
        language: Optional[str] = None,
        max_age_hours: int = None
    ) -> Optional[Dict]:
        """
        Load analysis results from cache if valid.
        
        Args:
            files: List of filenames
            threshold: Similarity threshold
            max_age_hours: Maximum cache age in hours
        
        Returns:
            Cached analysis data or None if not found/expired
        """
        if max_age_hours is None:
            max_age_hours = config.CACHE_EXPIRY_HOURS
        cache_file = self._get_cache_path(files, threshold, contents=contents, language=language)
        
        if not cache_file.exists():
            logger.debug(f"Cache not found: {cache_file.name}")
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Check age
            timestamp = datetime.fromisoformat(cache_data['timestamp'])
            age = datetime.now() - timestamp
            
            if age > timedelta(hours=max_age_hours):
                logger.info(f"Cache expired (age: {age})")
                cache_file.unlink()
                return None
            
            # Verify files match
            if cache_data['files'] != files:
                logger.warning("Cache files mismatch")
                return None
            
            logger.info(f"Analysis loaded from cache (age: {age})")
            return cache_data['data']
            
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return None
    
    def clear_old_cache(self, max_age_days: int = 7) -> int:
        """
        Remove cache files older than max_age_days.
        
        Args:
            max_age_days: Maximum age in days
        
        Returns:
            Number of files removed
        """
        removed = 0
        
        for cache_file in self.cache_dir.glob("analysis_*.pkl"):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                
                timestamp = datetime.fromisoformat(data['timestamp'])
                age = datetime.now() - timestamp
                
                if age > timedelta(days=max_age_days):
                    cache_file.unlink()
                    removed += 1
                    logger.debug(f"Removed old cache: {cache_file.name}")
                    
            except Exception as e:
                logger.warning(f"Failed to process {cache_file.name}: {e}")
        
        if removed > 0:
            logger.info(f"Removed {removed} old cache files")
        
        return removed
    
    def clear_all_cache(self) -> int:
        """
        Remove all cache files.
        
        Returns:
            Number of files removed
        """
        removed = 0
        
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
                removed += 1
            except Exception as e:
                logger.warning(f"Failed to remove {cache_file}: {e}")
        
        logger.info(f"Cleared {removed} cache files")
        return removed
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        cache_files = list(self.cache_dir.glob("analysis_*.pkl"))
        
        total_size = sum(f.stat().st_size for f in cache_files)
        
        oldest = None
        newest = None
        
        for cache_file in cache_files:
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                
                timestamp = datetime.fromisoformat(data['timestamp'])
                
                if oldest is None or timestamp < oldest:
                    oldest = timestamp
                if newest is None or timestamp > newest:
                    newest = timestamp
                    
            except Exception:
                pass
        
        return {
            'file_count': len(cache_files),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'oldest_cache': oldest.isoformat() if oldest else None,
            'newest_cache': newest.isoformat() if newest else None,
        }


class SessionManager:
    """Manages session state with disk persistence."""
    
    def __init__(self, session_file: str = ".niklaus_session.json"):
        """
        Initialize session manager.
        
        Args:
            session_file: Path to session file
        """
        self.session_file = Path(session_file)
    
    def save_session(self, session_data: Dict[str, Any]) -> None:
        """
        Save session state to disk.
        
        Args:
            session_data: Session data dictionary
        """
        try:
            # Convert non-serializable objects
            serializable_data = self._make_serializable(session_data)
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, default=str)
            
            logger.debug(f"Session saved to {self.session_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")
    
    def load_session(self) -> Dict[str, Any]:
        """
        Load session state from disk.
        
        Returns:
            Session data dictionary
        """
        if not self.session_file.exists():
            return {}
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")
            return {}
    
    def clear_session(self) -> None:
        """Clear session state."""
        if self.session_file.exists():
            self.session_file.unlink()
            logger.debug("Session cleared")
    
    def _make_serializable(self, data: Any) -> Any:
        """
        Convert non-serializable objects to serializable format.
        
        Args:
            data: Data to convert
        
        Returns:
            Serializable data
        """
        if isinstance(data, dict):
            return {
                k: self._make_serializable(v)
                for k, v in data.items()
                if not k.startswith('_')  # Skip private attributes
            }
        elif isinstance(data, (list, tuple)):
            return [self._make_serializable(item) for item in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, '__dict__'):
            # Convert objects to dictionaries
            return self._make_serializable(data.__dict__)
        else:
            # Return string representation for other types
            return str(data)


class AnalysisResult:
    """Container for analysis results."""
    
    def __init__(self, **kwargs):
        """Initialize result with any keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_')
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """Create instance from dictionary."""
        return cls(**data)
