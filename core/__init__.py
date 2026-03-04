"""
Core analysis module for Niklaus plagiarism detector.
"""

from .analyzer import PlagiarismAnalyzer
from .comparison import calculate_similarity, remove_blank_spaces_and_comments, compare_files
from .file_handler import FileHandler
from .llm_client import MaritacaClient
from .persistence import AnalysisCache, SessionManager
from .pipeline import AnalysisPipeline, LegacyAdapter, compare_performance

__all__ = [
    'PlagiarismAnalyzer',
    'calculate_similarity',
    'remove_blank_spaces_and_comments',
    'compare_files',
    'FileHandler',
    'MaritacaClient',
    'AnalysisCache',
    'SessionManager',
    'AnalysisPipeline',
    'LegacyAdapter',
    'compare_performance'
]