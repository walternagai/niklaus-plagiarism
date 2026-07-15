"""
ExportService — convert analysis results to CSV and JSON.

Usage::

    from export.service import ExportService

    # JSON bytes (UTF-8)
    json_bytes = ExportService.to_json(results)

    # CSV bytes (UTF-8 with BOM for Excel compatibility)
    csv_bytes = ExportService.to_csv(results)

Both methods accept the analysis-results dict produced by AnalysisPipeline
and return raw bytes ready to be passed to st.download_button().
"""

from __future__ import annotations

import csv
import io
import json
import math
from typing import Any, Dict, List, Optional


class ExportService:
    """Serialise analysis results to portable formats."""

    # ------------------------------------------------------------------
    # JSON export
    # ------------------------------------------------------------------

    @classmethod
    def to_json(cls, results: Dict[str, Any], indent: int = 2) -> bytes:
        """Serialise *results* to JSON bytes (UTF-8).

        NaN / Inf floats are replaced with ``null`` so the output is valid JSON.
        numpy scalars / arrays are converted automatically.
        """
        safe = cls._make_json_safe(results)
        return json.dumps(safe, ensure_ascii=False, indent=indent).encode("utf-8")

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    @classmethod
    def to_csv(cls, results: Dict[str, Any]) -> bytes:
        """Serialise pairwise comparison results to CSV bytes (UTF-8 BOM).

        The CSV contains one row per compared pair with columns:
            file1, file2, similarity, is_suspicious, plagiarism_type, confidence

        A UTF-8 BOM is prepended so Microsoft Excel opens the file correctly.
        """
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=[
                "file1",
                "file2",
                "similarity",
                "is_suspicious",
                "plagiarism_type",
                "confidence",
                "explanation",
            ],
            extrasaction="ignore",
            lineterminator="\r\n",
        )
        writer.writeheader()

        pairwise: List[Dict[str, Any]] = results.get("pairwise_results", [])
        threshold: float = float(results.get("threshold", 0.7) or 0.7)
        patterns: Dict[str, Any] = results.get("patterns", {}) or {}

        for pair in pairwise:
            file1 = pair.get("file1", "")
            file2 = pair.get("file2", "")
            sim = cls._safe_float(pair.get("similarity", 0.0))
            is_suspicious = bool(pair.get("is_suspicious")) or sim >= threshold

            # Look up pattern info
            pattern_key = f"{file1}_{file2}"
            alt_key = f"{file2}_{file1}"
            pattern = patterns.get(pattern_key) or patterns.get(alt_key) or {}

            writer.writerow(
                {
                    "file1": file1,
                    "file2": file2,
                    "similarity": f"{sim:.4f}",
                    "is_suspicious": "sim" if is_suspicious else "nao",
                    "plagiarism_type": pattern.get("plagiarism_type", ""),
                    "confidence": f"{cls._safe_float(pattern.get('confidence', 0.0)):.4f}",
                    "explanation": pattern.get("explanation", ""),
                }
            )

        # UTF-8 BOM + content
        return ("\ufeff" + buf.getvalue()).encode("utf-8")

    # ------------------------------------------------------------------
    # Summary CSV
    # ------------------------------------------------------------------

    @classmethod
    def to_summary_csv(cls, results: Dict[str, Any]) -> bytes:
        """One-row-per-file summary CSV with per-file metrics."""
        buf = io.StringIO()
        files: List[str] = results.get("files", [])
        metrics_list: List[Dict[str, Any]] = results.get("metrics") or []

        fieldnames = [
            "filename",
            "loc",
            "cyclomatic_complexity",
            "function_count",
            "max_nesting_depth",
            "maintainability_index",
        ]

        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\r\n")
        writer.writeheader()

        for i, filename in enumerate(files):
            metrics = metrics_list[i] if i < len(metrics_list) else {}
            writer.writerow(
                {
                    "filename": filename,
                    "loc": metrics.get("loc", ""),
                    "cyclomatic_complexity": metrics.get("cyclomatic", ""),
                    "function_count": metrics.get("functions", ""),
                    "max_nesting_depth": metrics.get("nesting", ""),
                    "maintainability_index": (
                        f"{cls._safe_float(metrics.get('maintainability', 0)):.2f}"
                        if metrics
                        else ""
                    ),
                }
            )

        return ("\ufeff" + buf.getvalue()).encode("utf-8")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _safe_float(cls, value: Any) -> float:
        try:
            f = float(value)
            if math.isnan(f) or math.isinf(f):
                return 0.0
            return f
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _make_json_safe(cls, obj: Any) -> Any:
        """Recursively make *obj* JSON-serialisable."""
        if isinstance(obj, dict):
            return {str(k): cls._make_json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [cls._make_json_safe(v) for v in obj]
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, (str, int, bool)) or obj is None:
            return obj
        # numpy scalars / arrays
        try:
            import numpy as np

            if isinstance(obj, np.ndarray):
                return cls._make_json_safe(obj.tolist())
            if isinstance(obj, np.generic):
                return cls._make_json_safe(obj.item())
        except ImportError:
            pass
        return str(obj)
