"""
Export module for generating reports in various formats.

Supported formats:
  - JSON  (ExportService.to_json)   — complete analysis results
  - CSV   (ExportService.to_csv)    — pairwise comparison table
  - CSV   (ExportService.to_summary_csv) — per-file metrics summary
"""

from export.service import ExportService

__all__ = ["ExportService"]