"""
Text comparison utilities for Niklaus plagiarism detector.
"""

import re
from difflib import SequenceMatcher
from typing import Tuple


def remove_blank_spaces_and_comments(code: str, language: str) -> str:
    """
    Remove blank spaces and comments from code.
    
    Args:
        code: Source code string
        language: Programming language name
    
    Returns:
        Cleaned code string
    """
    if language.lower() == 'python':
        # Remove Python docstrings and comments
        code = re.sub(r'""".*?"""|\'\'\'.*?\'\'\'', '', code, flags=re.DOTALL)
        code = re.sub(r'#.*', '', code)
    elif language.lower() in ['c', 'c++', 'java', 'javascript']:
        # Remove C-style comments
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'//.*', '', code)
        # Remove strings (to avoid removing code that looks like comments)
        code = re.sub(r'(".*?"|\'.*?\')', '', code, flags=re.DOTALL)
        code = re.sub(r'\s+', ' ', code)
    
    return code.strip()


def calculate_similarity(code1: str, code2: str) -> float:
    """
    Calculate text similarity between two code snippets.
    
    Args:
        code1: First code snippet
        code2: Second code snippet
    
    Returns:
        Similarity ratio (0.0 to 1.0)
    """
    if not code1 or not code2:
        return 0.0
    
    matcher = SequenceMatcher(a=code1, b=code2)
    return matcher.ratio()


def compare_files(code1: str, code2: str, language: str = 'python') -> float:
    """
    Compare two code files and return similarity score.
    
    Args:
        code1: First code snippet
        code2: Second code snippet
        language: Programming language name
    
    Returns:
        Similarity score (0.0 to 1.0)
    """
    if not code1 or not code2:
        return 0.0
    
    language = language.lower()
    clean_code1 = remove_blank_spaces_and_comments(code1, language)
    clean_code2 = remove_blank_spaces_and_comments(code2, language)
    
    similarity = calculate_similarity(clean_code1, clean_code2)
    return similarity


def find_similar_blocks(code1: str, code2: str, min_block_size: int = 10) -> list:
    """
    Find similar blocks between two code snippets.
    
    Args:
        code1: First code snippet
        code2: Second code snippet
        min_block_size: Minimum size of a block to be considered similar
    
    Returns:
        List of tuples (block1_start, block1_end, block2_start, block2_end, similarity)
    """
    lines1 = code1.split('\n')
    lines2 = code2.split('\n')
    
    similar_blocks = []
    
    matcher = SequenceMatcher(a=lines1, b=lines2)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            block_size = i2 - i1
            if block_size >= min_block_size:
                similar_blocks.append({
                    'code1_lines': (i1, i2),
                    'code2_lines': (j1, j2),
                    'size': block_size,
                    'similarity': 1.0
                })
    
    return similar_blocks


def calculate_levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.
    
    Args:
        s1: First string
        s2: Second string
    
    Returns:
        Levenshtein distance
    """
    if len(s1) < len(s2):
        return calculate_levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def normalize_code(code: str, language: str) -> str:
    """
    Normalize code by removing formatting differences.
    
    Args:
        code: Source code string
        language: Programming language name
    
    Returns:
        Normalized code string
    """
    # Remove extra whitespace
    code = re.sub(r'\s+', ' ', code)
    
    # Normalize quotes
    code = code.replace('"', "'")
    
    # Remove comments
    code = remove_blank_spaces_and_comments(code, language)
    
    return code.strip()