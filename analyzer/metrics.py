"""
Code Metrics Module

Calculate various code complexity and quality metrics.
"""

import re
import math
from typing import Dict, List, Tuple
import ast


class CodeMetrics:
    """Calculate code complexity and quality metrics."""
    
    def calculate_cyclomatic_complexity(self, code: str, language: str = 'python') -> int:
        """
        Calculate cyclomatic complexity (McCabe).
        
        CC = E - N + 2P
        where E = edges, N = nodes, P = connected components
        
        Simplified: CC = number of decision points + 1
        """
        complexity = 1  # Base complexity
        
        if language == 'python':
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.If, ast.While, ast.For)):
                        complexity += 1
                    elif isinstance(node, ast.BoolOp):
                        # and/or operators
                        complexity += len(node.values) - 1
                    elif isinstance(node, (ast.And, ast.Or)):
                        complexity += 1
            except (SyntaxError, ValueError, TypeError):
                return complexity
        else:
            # Generic pattern matching for other languages
            decision_patterns = [
                r'\bif\s*\(',  # if statements
                r'\bwhile\s*\(',  # while loops
                r'\bfor\s*\(',  # for loops
                r'\bswitch\s*\(',  # switch statements
                r'\bcase\s+',  # case labels
                r'\b\?\s*:',  # ternary operators
                r'\b&&\b',  # AND operators
                r'\b\|\|\b'  # OR operators
            ]
            
            for pattern in decision_patterns:
                complexity += len(re.findall(pattern, code))
        
        return complexity
    
    def count_loc(self, code: str) -> Dict[str, int]:
        """
        Count lines of code (total, comments, blank).
        """
        lines = code.split('\n')
        
        total = len(lines)
        blank = sum(1 for line in lines if not line.strip())
        
        # Comments (language-specific)
        comment_lines = sum(1 for line in lines if line.strip().startswith('#') 
                          or line.strip().startswith('//') 
                          or line.strip().startswith('/*'))
        
        code_lines = total - blank - comment_lines
        
        return {
            'total': total,
            'code': code_lines,
            'comments': comment_lines,
            'blank': blank
        }
    
    def count_functions_methods(self, code: str, language: str = 'python') -> int:
        """Count number of functions/methods in code."""
        if language == 'python':
            try:
                tree = ast.parse(code)
                return sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
            except (SyntaxError, ValueError, TypeError):
                return 0
        else:
            # Pattern matching for other languages
            patterns = {
                'java': r'\b(public|private|protected|static)\s+\w+\s+\w+\s*\(',
                'javascript': r'\bfunction\s+\w+\s*\(|\w+\s*:\s*function',
                'go': r'\bfunc\s+\w+\s*\(',
                'rust': r'\bfn\s+\w+\s*\(',
                'c': r'\b\w+\s+\w+\s*\([^)]*\)\s*\{'
            }
            
            pattern = patterns.get(language, r'\bfunction\s+\w+')
            return len(re.findall(pattern, code))
        
        return 0
    
    def calculate_nesting_depth(self, code: str, language: str = 'python') -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        current_depth = 0
        
        if language == 'python':
            # Python uses indentation
            for line in code.split('\n'):
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    depth = indent // 4  # Assuming 4-space indentation
                    max_depth = max(max_depth, depth)
        else:
            # Braces-based languages
            for char in code:
                if char == '{':
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif char == '}':
                    current_depth -= 1
        
        return max_depth
    
    def calculate_maintainability_index(self, code: str, language: str = 'python') -> float:
        """
        Calculate maintainability index (0-100).
        
        MI = 171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(LOC)
        where V = Halstead Volume, G = Cyclomatic Complexity, LOC = Lines of Code
        
        Simplified version: uses heuristics
        """
        loc = self.count_loc(code)['code']
        cc = self.calculate_cyclomatic_complexity(code, language)
        
        # Simplified formula
        volume = loc  # Simplified: not exact Halstead volume
        mi = max(0, min(100, 171 - 5.2 * math.log(max(volume, 1)) - 0.23 * cc - 16.2 * math.log(max(loc, 1))))
        
        return round(mi, 2)
    
    def calculate_halstead_metrics(self, code: str, language: str = 'python') -> Dict[str, float]:
        """
        Calculate Halstead complexity metrics.
        
        Based on: n1 = unique operators, n2 = unique operands
                  N1 = total operators, N2 = total operands
        """
        # Tokenize code
        if language == 'python':
            operators = {'+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=',
                        'and', 'or', 'not', 'in', 'is', '+=', '-=', '*=', '/=',
                        '(', ')', '[', ']', '{', '}', ',', ':', ';'}
            
            # Extract tokens
            tokens = re.findall(r'\b\w+\b|[^\w\s]', code)
            
            # Simplified counting
            n1 = len(operators)  # Unique operators
            n2 = len(set(t for t in tokens if t.isalnum()))  # Unique operands
            N1 = sum(1 for t in tokens if t in operators)  # Total operators
            N2 = sum(1 for t in tokens if t.isalnum())  # Total operands
            
            n = n1 + n2  # Vocabulary
            N = N1 + N2  # Program length
            
            if n > 0 and N > 0:
                volume = N * math.log2(n) if n > 1 else 0
                difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0
                effort = volume * difficulty if volume > 0 else 0
                
                return {
                    'vocabulary': n,
                    'length': N,
                    'volume': round(volume, 2),
                    'difficulty': round(difficulty, 2),
                    'effort': round(effort, 2)
                }
        
        return {
            'vocabulary': 0,
            'length': 0,
            'volume': 0,
            'difficulty': 0,
            'effort': 0
        }
    
    def calculate_all_metrics(self, code: str, language: str = 'python') -> Dict[str, any]:
        """Calculate all available metrics for a code snippet."""
        return {
            'loc': self.count_loc(code),
            'cyclomatic_complexity': self.calculate_cyclomatic_complexity(code, language),
            'function_count': self.count_functions_methods(code, language),
            'max_nesting_depth': self.calculate_nesting_depth(code, language),
            'maintainability_index': self.calculate_maintainability_index(code, language),
            'halstead': self.calculate_halstead_metrics(code, language)
        }
    
    def compare_metrics(self, metrics1: Dict, metrics2: Dict) -> Dict[str, float]:
        """
        Compare metrics between two code snippets.
        Returns comparison scores (0.0 to 1.0 for similarity).
        """
        comparisons = {}
        
        # LOC comparison
        loc_diff = abs(metrics1['loc']['code'] - metrics2['loc']['code'])
        loc_sim = 1.0 - (loc_diff / max(metrics1['loc']['code'], metrics2['loc']['code'], 1))
        comparisons['loc_similarity'] = max(0, loc_sim)
        
        # Cyclomatic complexity comparison
        cc_diff = abs(metrics1['cyclomatic_complexity'] - metrics2['cyclomatic_complexity'])
        cc_sim = 1.0 - (cc_diff / max(metrics1['cyclomatic_complexity'], metrics2['cyclomatic_complexity'], 1))
        comparisons['cyclomatic_similarity'] = max(0, cc_sim)
        
        # Function count comparison
        func_diff = abs(metrics1['function_count'] - metrics2['function_count'])
        func_sim = 1.0 - (func_diff / max(metrics1['function_count'], metrics2['function_count'], 1))
        comparisons['function_count_similarity'] = max(0, func_sim)
        
        # Nesting depth comparison
        nest_diff = abs(metrics1['max_nesting_depth'] - metrics2['max_nesting_depth'])
        nest_sim = 1.0 - (nest_diff / max(metrics1['max_nesting_depth'], metrics2['max_nesting_depth'], 1))
        comparisons['nesting_similarity'] = max(0, nest_sim)
        
        # Maintainability index comparison
        mi_diff = abs(metrics1['maintainability_index'] - metrics2['maintainability_index'])
        mi_sim = 1.0 - (mi_diff / max(metrics1['maintainability_index'], metrics2['maintainability_index'], 1))
        comparisons['maintainability_similarity'] = max(0, mi_sim)
        
        # Overall similarity
        comparisons['overall_similarity'] = sum(comparisons.values()) / len(comparisons)
        
        return comparisons
    
    def detect_anomalies(self, textual_similarity: float, metrics_comparison: Dict) -> List[Dict]:
        """
        Detect anomalies that may indicate plagiarism with refactoring.
        """
        anomalies = []
        
        # High structural similarity but low metric similarity
        if textual_similarity > 0.7 and metrics_comparison.get('overall_similarity', 0) < 0.5:
            anomalies.append({
                'type': 'METRIC_MISMATCH',
                'description': 'Similar code with different complexity - possible refactoring',
                'confidence': 0.75
            })
        
        # Very different LOC but high complexity similarity
        if metrics_comparison.get('loc_similarity', 0) < 0.5 and metrics_comparison.get('cyclomatic_similarity', 0) > 0.8:
            anomalies.append({
                'type': 'CODE_EXPANSION',
                'description': 'Code expanded but complexity similar - possible obfuscation',
                'confidence': 0.70
            })
        
        return anomalies
