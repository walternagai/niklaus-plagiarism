"""
AST Parser Module

Multi-language AST (Abstract Syntax Tree) parsing and comparison for plagiarism detection.
"""

import re
import ast
from typing import Dict, List, Tuple, Optional
import hashlib


class ASTParser:
    """Parser and comparator of abstract syntax trees for multiple languages."""
    
    SUPPORTED_LANGUAGES = {
        'python': {'extensions': ['.py'], 'comment_single': '#', 'comment_multi': ('"""', "'''")},
        'java': {'extensions': ['.java'], 'comment_single': '//', 'comment_multi': ('/*', '*/')},
        'javascript': {'extensions': ['.js', '.ts'], 'comment_single': '//', 'comment_multi': ('/*', '*/')},
        'typescript': {'extensions': ['.ts', '.tsx'], 'comment_single': '//', 'comment_multi': ('/*', '*/')},
        'c': {'extensions': ['.c', '.h'], 'comment_single': '//', 'comment_multi': ('/*', '*/')},
        'cpp': {'extensions': ['.cpp', '.hpp', '.cc', '.cxx'], 'comment_single': '//', 'comment_multi': ('/*', '*/')},
        'go': {'extensions': ['.go'], 'comment_single': '//', 'comment_multi': ('/*', '*/')},
        'rust': {'extensions': ['.rs'], 'comment_single': '//', 'comment_multi': ('/*', '*/')},
        'kotlin': {'extensions': ['.kt', '.kts'], 'comment_single': '//', 'comment_multi': ('/*', '*/')},
        'swift': {'extensions': ['.swift'], 'comment_single': '//', 'comment_multi': ('/*', '*/')},
        'r': {'extensions': ['.r', '.R'], 'comment_single': '#', 'comment_multi': None}
    }
    
    def __init__(self):
        self.language_stats = {}
    
    def detect_language(self, filename: str, content: Optional[str] = None) -> str:
        """Detect programming language from filename and optionally content."""
        ext = '.' + filename.rsplit('.', 1)[-1] if '.' in filename else ''
        
        for lang, config in self.SUPPORTED_LANGUAGES.items():
            if ext in config['extensions']:
                return lang
        
        # Fallback to content-based detection
        if content:
            if 'def ' in content or 'import ' in content and '#' in content:
                return 'python'
            elif 'public class ' in content or 'System.out.println' in content:
                return 'java'
            elif 'func main()' in content or 'package main' in content:
                return 'go'
            elif 'fn main()' in content or 'let mut' in content:
                return 'rust'
        
        return 'unknown'
    
    def parse_python_ast(self, code: str) -> Dict:
        """Parse Python code to AST structure."""
        try:
            tree = ast.parse(code)
            return self._extract_ast_features(tree)
        except SyntaxError:
            return {'error': 'Syntax error in Python code'}
    
    def _extract_ast_features(self, tree: ast.AST) -> Dict:
        """Extract features from Python AST."""
        features = {
            'functions': [],
            'classes': [],
            'imports': [],
            'variables': [],
            'calls': [],
            'loops': [],
            'conditionals': [],
            'operators': []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                features['functions'].append({
                    'name': node.name,
                    'args': [arg.arg for arg in node.args.args],
                    'line': node.lineno
                })
            elif isinstance(node, ast.ClassDef):
                features['classes'].append({
                    'name': node.name,
                    'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                features['imports'].append(node.names[0].name if hasattr(node, 'names') else '')
            elif isinstance(node, ast.Name):
                features['variables'].append(node.id)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    features['calls'].append(node.func.id)
            elif isinstance(node, (ast.For, ast.While)):
                features['loops'].append(node.__class__.__name__)
            elif isinstance(node, ast.If):
                features['conditionals'].append('if')
            elif isinstance(node, ast.BoolOp):
                features['operators'].append(node.op.__class__.__name__)
        
        return features
    
    def extract_code_fingerprint(self, code: str, k: int = 5) -> set:
        """
        Generate code fingerprint using Winnowing algorithm.
        Effective for detecting plagiarism with variable renaming.
        """
        # Tokenize code (simplified)
        tokens = re.findall(r'\b\w+\b|[^\w\s]', code)
        
        # Generate k-grams
        if len(tokens) < k:
            return {hash(''.join(tokens))}
        
        kgrams = [''.join(tokens[i:i+k]) for i in range(len(tokens)-k+1)]
        
        # Hash k-grams
        hashes = [hash(kg) for kg in kgrams]
        
        # Window size
        w = max(4, len(hashes) // 10)
        
        # Winnowing
        fingerprints = set()
        for i in range(len(hashes)-w+1):
            window = hashes[i:i+w]
            min_hash = min(window)
            fingerprints.add(min_hash)
        
        return fingerprints
    
    def compare_ast_structures(self, ast1: Dict, ast2: Dict) -> float:
        """
        Compare two AST structures and return similarity score (0.0 to 1.0).
        """
        if 'error' in ast1 or 'error' in ast2:
            return 0.0
        
        score = 0.0
        total_checks = 0
        
        # Compare functions
        if ast1.get('functions') and ast2.get('functions'):
            arg_counts1 = sorted(len(f.get('args', [])) for f in ast1['functions'])
            arg_counts2 = sorted(len(f.get('args', [])) for f in ast2['functions'])

            if arg_counts1 and arg_counts2:
                min_len = min(len(arg_counts1), len(arg_counts2))
                if min_len > 0:
                    matches = sum(1 for i in range(min_len) if arg_counts1[i] == arg_counts2[i])
                    score += matches / max(len(arg_counts1), len(arg_counts2), 1)
                else:
                    score += 0.0
            total_checks += 1
        
        # Compare classes
        if ast1.get('classes') and ast2.get('classes'):
            classes1 = {c['name']: len(c['methods']) for c in ast1['classes']}
            classes2 = {c['name']: len(c['methods']) for c in ast2['classes']}
            
            method_counts1 = list(classes1.values())
            method_counts2 = list(classes2.values())
            
            if method_counts1 and method_counts2:
                common = sum(1 for m1 in method_counts1 if m1 in method_counts2)
                score += common / max(len(method_counts1), len(method_counts2))
                total_checks += 1
        
        # Compare imports
        if ast1.get('imports') and ast2.get('imports'):
            imports1 = set(ast1['imports'])
            imports2 = set(ast2['imports'])
            
            if imports1 or imports2:
                common = len(imports1 & imports2)
                score += common / max(len(imports1 | imports2), 1)
                total_checks += 1
        
        # Compare function calls
        calls1 = set(ast1.get('calls', []))
        calls2 = set(ast2.get('calls', []))
        if calls1 or calls2:
            common = len(calls1 & calls2)
            score += common / max(len(calls1 | calls2), 1)
            total_checks += 1
        
        # Compare loops and conditionals
        loops1 = len(ast1.get('loops', []))
        loops2 = len(ast2.get('loops', []))
        
        if loops1 > 0 or loops2 > 0:
            loop_sim = 1.0 - abs(loops1 - loops2) / max(loops1, loops2, 1)
            score += loop_sim
            total_checks += 1
        
        return score / max(total_checks, 1)
    
    def structural_similarity(self, code1: str, code2: str, language: str = 'python') -> float:
        """
        Calculate structural similarity between two code snippets.
        Returns value between 0.0 and 1.0.
        """
        if language == 'python':
            ast1 = self.parse_python_ast(code1)
            ast2 = self.parse_python_ast(code2)
        else:
            # Fallback to fingerprint comparison for other languages
            fp1 = self.extract_code_fingerprint(code1)
            fp2 = self.extract_code_fingerprint(code2)
            
            if not fp1 or not fp2:
                return 0.0
            
            common = len(fp1 & fp2)
            total = len(fp1 | fp2)
            return common / max(total, 1)
        
        return self.compare_ast_structures(ast1, ast2)
    
    def detect_refactoring_patterns(self, code1: str, code2: str) -> List[Dict]:
        """Detect specific refactoring patterns between two code snippets."""
        patterns = []
        
        # Parse both codes
        try:
            tree1 = ast.parse(code1) if code1 else None
            tree2 = ast.parse(code2) if code2 else None
        except (SyntaxError, ValueError, TypeError):
            return patterns
        
        if not tree1 or not tree2:
            return patterns
        
        # Detect variable renaming
        vars1 = self._extract_variables(tree1)
        vars2 = self._extract_variables(tree2)
        
        if len(vars1) == len(vars2) and len(vars1) > 0:
            patterns.append({
                'type': 'VARIABLE_RENAME',
                'description': f'Possível renomeação de variáveis ({len(vars1)} variáveis)',
                'confidence': 0.8
            })
        
        # Detect function renaming
        funcs1 = self._extract_function_names(tree1)
        funcs2 = self._extract_function_names(tree2)
        
        if len(funcs1) == len(funcs2) and len(funcs1) > 0 and set(funcs1) != set(funcs2):
            patterns.append({
                'type': 'FUNCTION_RENAME',
                'description': f'Possível renomeação de funções ({len(funcs1)} funções)',
                'confidence': 0.8
            })
        
        return patterns
    
    def _extract_variables(self, tree: ast.AST) -> List[str]:
        """Extract variable names from AST."""
        variables = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                variables.append(node.id)
            elif isinstance(node, ast.arg):
                variables.append(node.arg)
        return list(set(variables))
    
    def _extract_function_names(self, tree: ast.AST) -> List[str]:
        """Extract function names from AST."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        return functions
