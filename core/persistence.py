"""
Persistence and caching module for Niklaus plagiarism detector.

Cache files are stored as JSON (not pickle) to eliminate the unsafe
deserialization risk that pickle carries.  The expiry timestamp is encoded
in the filename so that clear_old_cache() can filter without opening files.

File naming scheme:
    analysis_{content_sig}_{threshold:.2f}_{expire_ts}.json

where expire_ts is a Unix timestamp (integer seconds) indicating when the
entry is considered stale.
"""

import json
import math
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import numpy as np

from utils.config import config
from utils.exceptions import CacheError
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# JSON serialisation helpers for numpy / datetime types
# ---------------------------------------------------------------------------

class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy scalars, arrays, NaN, and Inf."""

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        return super().default(obj)

    def encode(self, obj):
        # Pre-process floats to replace NaN/Inf with None
        return super().encode(self._sanitise(obj))

    def iterencode(self, obj, _one_shot=False):
        return super().iterencode(self._sanitise(obj), _one_shot)

    @staticmethod
    def _sanitise(obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            # JSON keys must be strings — coerce numpy ints/floats to str
            return {
                (str(k.item()) if isinstance(k, np.generic) else str(k) if not isinstance(k, str) else k):
                _NumpyEncoder._sanitise(v)
                for k, v in obj.items()
            }
        if isinstance(obj, (list, tuple)):
            return [_NumpyEncoder._sanitise(v) for v in obj]
        if isinstance(obj, np.ndarray):
            return _NumpyEncoder._sanitise(obj.tolist())
        if isinstance(obj, np.generic):
            return _NumpyEncoder._sanitise(obj.item())
        return obj


def _json_object_hook(obj):
    """Restore types serialised by _NumpyEncoder."""
    if "__datetime__" in obj:
        return datetime.fromisoformat(obj["__datetime__"])
    return obj


def _json_dumps(data: Any) -> str:
    return json.dumps(data, cls=_NumpyEncoder)


def _json_loads(text: str) -> Any:
    return json.loads(text, object_hook=_json_object_hook)


# ---------------------------------------------------------------------------
# AnalysisCache
# ---------------------------------------------------------------------------

class AnalysisCache:
    """Manages persistent cache for analysis results (JSON-backed)."""

    _FILE_GLOB = "analysis_*.json"

    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir or config.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache directory: {self.cache_dir}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _content_signature(
        self,
        files: List[str],
        contents: Optional[List[str]],
        language: Optional[str],
    ) -> str:
        """Build deterministic 16-char hex signature from files, contents, language."""
        if contents is None:
            file_list = sorted(files)
            payload = f"{language or 'unknown'}::{repr(file_list)}"
            return hashlib.sha256(payload.encode()).hexdigest()[:16]

        pairs = sorted(zip(files, contents), key=lambda item: item[0])
        hasher = hashlib.sha256()
        hasher.update((language or "unknown").encode())
        hasher.update(b"\x00")
        for filename, content in pairs:
            hasher.update(str(filename).encode())
            hasher.update(b"\x00")
            hasher.update(hashlib.sha256(str(content).encode()).digest())
            hasher.update(b"\x00")
        return hasher.hexdigest()[:16]

    def _cache_filename(
        self,
        files: List[str],
        threshold: float,
        contents: Optional[List[str]] = None,
        language: Optional[str] = None,
        expire_ts: Optional[int] = None,
    ) -> str:
        sig = self._content_signature(files, contents, language)
        if expire_ts is None:
            expire_ts = int(time.time()) + int(config.CACHE_EXPIRY_HOURS * 3600)
        return f"analysis_{sig}_{threshold:.2f}_{expire_ts}.json"

    def _find_cache_file(
        self,
        files: List[str],
        threshold: float,
        contents: Optional[List[str]] = None,
        language: Optional[str] = None,
    ) -> Optional[Path]:
        """Locate a non-expired cache file matching the content signature."""
        sig = self._content_signature(files, contents, language)
        pattern = f"analysis_{sig}_{threshold:.2f}_*.json"
        now = int(time.time())
        for candidate in self.cache_dir.glob(pattern):
            # Filename: analysis_{sig}_{threshold}_{expire_ts}.json
            parts = candidate.stem.split("_")
            try:
                expire_ts = int(parts[-1])
            except (ValueError, IndexError):
                continue
            if expire_ts > now:
                return candidate
            # Expired — delete opportunistically
            try:
                candidate.unlink()
            except OSError:
                pass
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        files: List[str],
        threshold: float,
        analysis_data: Dict,
        contents: Optional[List[str]] = None,
        language: str = None,
    ) -> Path:
        """Save analysis results to a JSON cache file.

        Raises:
            CacheError: if the write fails.
        """
        cache_file = None
        try:
            expire_ts = int(time.time()) + int(config.CACHE_EXPIRY_HOURS * 3600)
            filename = self._cache_filename(
                files, threshold, contents=contents,
                language=language, expire_ts=expire_ts,
            )
            cache_file = self.cache_dir / filename

            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "expire_ts": expire_ts,
                "files": files,
                "threshold": threshold,
                "language": language,
                "data": analysis_data,
                "version": "2.0",
            }

            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(_json_dumps(cache_data))

            logger.info(f"Analysis cached to {cache_file.name}")
            return cache_file

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            raise CacheError(
                f"Failed to save analysis cache: {str(e)}",
                cache_file=str(cache_file) if cache_file else None,
            )

    def load(
        self,
        files: List[str],
        threshold: float,
        contents: Optional[List[str]] = None,
        language: Optional[str] = None,
        max_age_hours: int = None,
    ) -> Optional[Dict]:
        """Load analysis results from cache if valid and not expired.

        When *max_age_hours* is 0, cache is always considered expired (bypass).
        """
        if max_age_hours is None:
            max_age_hours = config.CACHE_EXPIRY_HOURS

        # Explicit bypass
        if max_age_hours == 0:
            return None

        cache_file = self._find_cache_file(files, threshold, contents=contents, language=language)
        if cache_file is None:
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = _json_loads(f.read())

            # Secondary age check using timestamp string (belt + suspenders)
            timestamp = datetime.fromisoformat(cache_data["timestamp"])
            age = datetime.now() - timestamp
            if age > timedelta(hours=max_age_hours):
                logger.info(f"Cache expired by age check (age: {age})")
                try:
                    cache_file.unlink()
                except OSError:
                    pass
                return None

            logger.info(f"Analysis loaded from cache (age: {age})")
            return cache_data["data"]

        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return None

    def clear_old_cache(self, max_age_days: int = 7) -> int:
        """Remove expired/old cache files by inspecting filenames only (no I/O).

        Files whose expire_ts (encoded in the filename) is in the past OR
        whose filesystem mtime is older than *max_age_days* are deleted.
        """
        removed = 0
        cutoff_ts = int(time.time()) - max_age_days * 86400

        for cache_file in self.cache_dir.glob(self._FILE_GLOB):
            parts = cache_file.stem.split("_")
            try:
                expire_ts = int(parts[-1])
            except (ValueError, IndexError):
                expire_ts = None

            should_remove = False
            if expire_ts is not None and expire_ts < int(time.time()):
                should_remove = True
            elif cache_file.stat().st_mtime < cutoff_ts:
                should_remove = True

            if should_remove:
                try:
                    cache_file.unlink()
                    removed += 1
                    logger.debug(f"Removed old cache: {cache_file.name}")
                except OSError as e:
                    logger.warning(f"Failed to remove {cache_file.name}: {e}")

        if removed > 0:
            logger.info(f"Removed {removed} old cache files")
        return removed

    def clear_all_cache(self) -> int:
        """Remove all JSON cache files."""
        removed = 0
        for cache_file in self.cache_dir.glob(self._FILE_GLOB):
            try:
                cache_file.unlink()
                removed += 1
            except OSError as e:
                logger.warning(f"Failed to remove {cache_file}: {e}")
        logger.info(f"Cleared {removed} cache files")
        return removed

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics without reading file contents."""
        cache_files = list(self.cache_dir.glob(self._FILE_GLOB))
        total_size = sum(f.stat().st_size for f in cache_files)
        now = int(time.time())
        active = sum(
            1 for f in cache_files
            if self._expire_ts_from_path(f) > now
        )
        return {
            "file_count": len(cache_files),
            "active_count": active,
            "expired_count": len(cache_files) - active,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
        }

    @staticmethod
    def _expire_ts_from_path(path: Path) -> int:
        parts = path.stem.split("_")
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            return 0


# ---------------------------------------------------------------------------
# DiskSessionManager  (was SessionManager — renamed to avoid collision with
# auth.session.SessionManager)
# ---------------------------------------------------------------------------

class DiskSessionManager:
    """Manages session state with disk persistence (JSON)."""

    def __init__(self, session_file: str = ".niklaus_session.json"):
        self.session_file = Path(session_file)

    def save_session(self, session_data: Dict[str, Any]) -> None:
        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                f.write(_json_dumps(session_data))
            logger.debug(f"Session saved to {self.session_file}")
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")

    def load_session(self) -> Dict[str, Any]:
        if not self.session_file.exists():
            return {}
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                return _json_loads(f.read())
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")
            return {}

    def clear_session(self) -> None:
        if self.session_file.exists():
            self.session_file.unlink()
            logger.debug("Session cleared")


# ---------------------------------------------------------------------------
# Backward-compatibility alias (old name kept to avoid breaking imports)
# ---------------------------------------------------------------------------

#: Deprecated alias — use DiskSessionManager instead.
SessionManager = DiskSessionManager


# ---------------------------------------------------------------------------
# AnalysisResult
# ---------------------------------------------------------------------------

class AnalysisResult:
    """Container for analysis results."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        return cls(**data)
