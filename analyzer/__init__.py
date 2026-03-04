"""
Niklaus Analyzer Module

Advanced plagiarism detection with AST analysis, metrics, and clustering.
"""

from .ast_parser import ASTParser
from .metrics import CodeMetrics
from .clustering import ClusterDetector
from .patterns import PlagiarismPatternDetector

__all__ = ['ASTParser', 'CodeMetrics', 'ClusterDetector', 'PlagiarismPatternDetector']