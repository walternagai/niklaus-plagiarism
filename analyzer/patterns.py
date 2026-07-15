"""
Plagiarism Pattern Detection Module

Detect specific plagiarism patterns and classify types of plagiarism.
"""

import re
import hashlib
from typing import Dict, List, Tuple, Set
import ast


class PlagiarismPatternDetector:
    """Detect and classify plagiarism patterns."""
    
    PLAGIARISM_TYPES = {
        'COPIA_DIRETA': 'Cópia direta do código com pouca ou nenhuma modificação',
        'RENOMEACAO_VARIAVEIS': 'Variáveis e/ou funções renomeadas mas estrutura idêntica',
        'REORDENACAO_CODIGO': 'Código reorganizado (ordem de funções, statements) mas funcionalmente equivalente',
        'INSERCAO_CODIGO_MORTO': 'Código morto ou comentários inseridos para mascarar similaridade',
        'REFATORACAO_LEVE': 'Pequenas modificações estruturais (loops, condições)',
        'REFATORACAO_PESADA': 'Refatoração significativa mantendo funcionalidade equivalente',
        'SIMILARIDADE_BAIXA': 'Similaridade baixa, provavelmente código original',
        'REUSO_LEGITIMO': 'Reutilização legítima (bibliotecas, código comum)'
    }
    
    def detect_variable_renaming(self, code1: str, code2: str, language: str = 'python') -> Dict:
        """
        Detect if code2 is code1 with variables renamed.
        
        Returns dict with:
        - detected: bool
        - variables_renamed: list of (old, new) tuples
        - confidence: float
        """
        if language != 'python':
            # Generic approach for other languages
            return self._detect_variable_renaming_generic(code1, code2)
        
        try:
            tree1 = ast.parse(code1)
            tree2 = ast.parse(code2)
        except (SyntaxError, ValueError, TypeError):
            return {'detected': False, 'variables_renamed': [], 'confidence': 0.0}
        
        # Extract variable names
        vars1 = self._extract_all_names(tree1, 'variable')
        vars2 = self._extract_all_names(tree2, 'variable')
        
        # Extract function names
        funcs1 = self._extract_all_names(tree1, 'function')
        funcs2 = self._extract_all_names(tree2, 'function')
        
        # Check if same number of unique identifiers AND structural similarity
        if len(vars1) == len(vars2) and len(funcs1) == len(funcs2):
            # Require at least some variables to be present to avoid trivial matches
            if len(vars1) == 0:
                return {'detected': False, 'variables_renamed': [], 'confidence': 0.0}

            # Guard: if BOTH variables AND functions are identical, it's not renaming
            if vars1 == vars2 and funcs1 == funcs2:
                return {'detected': False, 'variables_renamed': [], 'confidence': 0.0}

            # Guard: require that at least some variable names differ between the two codes
            vars_overlap = len(vars1 & vars2) / max(len(vars1), 1)
            if vars_overlap > 0.9:
                # Almost all variable names are the same — not a rename scenario
                return {'detected': False, 'variables_renamed': [], 'confidence': 0.0}

            # Guard: structural similarity — compare function argument counts
            # (same number of args per function is a strong signal of renaming)
            try:
                arg_counts1 = sorted(
                    len(node.args.args)
                    for node in ast.walk(tree1)
                    if isinstance(node, ast.FunctionDef)
                )
                arg_counts2 = sorted(
                    len(node.args.args)
                    for node in ast.walk(tree2)
                    if isinstance(node, ast.FunctionDef)
                )
                if arg_counts1 != arg_counts2:
                    # Different function signatures — unlikely to be simple renaming
                    return {'detected': False, 'variables_renamed': [], 'confidence': 0.0}
            except Exception:
                pass

            # Build variable rename mapping (by sorted order as best-effort)
            # Only map variables that actually differ between the two files
            renamed_vars = []
            seen_new: set = set()
            vars_only_in_1 = sorted(vars1 - vars2)
            vars_only_in_2 = sorted(vars2 - vars1)
            for v1, v2 in zip(vars_only_in_1, vars_only_in_2):
                if v2 not in seen_new:
                    renamed_vars.append((v1, v2))
                    seen_new.add(v2)

            if not renamed_vars:
                return {'detected': False, 'variables_renamed': [], 'confidence': 0.0}

            return {
                'detected': True,
                'variables_renamed': renamed_vars,
                'confidence': 0.75
            }

        return {'detected': False, 'variables_renamed': [], 'confidence': 0.0}
    
    def _detect_variable_renaming_generic(self, code1: str, code2: str) -> Dict:
        """Generic variable renaming detection for non-Python code."""
        # Extract identifiers (simplified)
        idents1 = set(re.findall(r'\b[a-zA-Z_]\w*\b', code1))
        idents2 = set(re.findall(r'\b[a-zA-Z_]\w*\b', code2))
        
        # Common keywords to exclude
        keywords = {'if', 'else', 'for', 'while', 'return', 'def', 'class', 'import', 
                   'from', 'as', 'in', 'not', 'and', 'or', 'True', 'False', 'None',
                   'public', 'private', 'void', 'int', 'string', 'return', 'function',
                   'var', 'let', 'const', 'func', 'fn', 'pub', 'mod'}
        
        vars1 = idents1 - keywords
        vars2 = idents2 - keywords
        
        if len(vars1) == len(vars2) and len(vars1) > 3:
            return {
                'detected': True,
                'variables_renamed': list(zip(vars1, vars2)),
                'confidence': 0.75
            }
        
        return {'detected': False, 'variables_renamed': [], 'confidence': 0.0}
    
    def _extract_all_names(self, tree: ast.AST, name_type: str) -> Set[str]:
        """Extract all names of a specific type from AST.

        For 'variable', collects:
          - assignment targets (ast.Store context)
          - function parameters (ast.arg nodes)
        Both are user-defined identifiers that could be renamed in plagiarism.
        """
        names = set()

        for node in ast.walk(tree):
            if name_type == 'variable':
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    names.add(node.id)
                elif isinstance(node, ast.arg):
                    # Function parameters are prime candidates for renaming
                    names.add(node.arg)
            elif name_type == 'function':
                if isinstance(node, ast.FunctionDef):
                    names.add(node.name)

        return names
    
    def detect_code_reordering(self, code1: str, code2: str, language: str = 'python') -> Dict:
        """
        Detect if code contains reordered functions/statements.
        
        Returns:
        - detected: bool
        - reordered_blocks: list of reordered sections
        - confidence: float
        """
        # Simple approach: compare lines/sections
        lines1 = [l.strip() for l in code1.split('\n') if l.strip()]
        lines2 = [l.strip() for l in code2.split('\n') if l.strip()]
        
        # Use line hashing to find matching lines
        hash1 = [hashlib.md5(l.encode()).hexdigest() for l in lines1]
        hash2 = [hashlib.md5(l.encode()).hexdigest() for l in lines2]
        
        set1 = set(hash1)
        set2 = set(hash2)
        
        # Similar line content
        common = set1 & set2
        total = set1 | set2
        
        similarity = len(common) / max(len(total), 1)
        
        # Check if order is different
        if similarity > 0.7:
            # Lines are similar, check order
            order_similarity = sum(1 for i, h in enumerate(hash1[:min(len(hash1), len(hash2))])
                                   if hash2[i] == h) / max(len(hash1), len(hash2))
            
            if order_similarity < 0.5:
                return {
                    'detected': True,
                    'reordered_blocks': [],
                    'confidence': 0.80
                }
        
        return {'detected': False, 'reordered_blocks': [], 'confidence': 0.0}
    
    def detect_dead_code_insertion(self, code1: str, code2: str) -> Dict:
        """
        Detect if code2 has dead code or excessive comments inserted.
        
        Returns:
        - detected: bool
        - inserted_lines: approximate count
        - confidence: float
        """
        lines1_without_comments = self._remove_comments(code1)
        lines2_without_comments = self._remove_comments(code2)
        
        # Count non-comment, non-blank lines
        code_lines1 = [l for l in lines1_without_comments.split('\n') if l.strip()]
        code_lines2 = [l for l in lines2_without_comments.split('\n') if l.strip()]
        
        # If significantly more lines in code2 but similar functionality
        if len(code_lines2) > len(code_lines1) * 1.5:
            # Check if functional code is similar
            from analyzer.ast_parser import ASTParser
            parser = ASTParser()
            
            similarity = parser.structural_similarity(code1, code2)
            
            if similarity > 0.7:
                return {
                    'detected': True,
                    'inserted_lines': len(code_lines2) - len(code_lines1),
                    'confidence': 0.75
                }
        
        return {'detected': False, 'inserted_lines': 0, 'confidence': 0.0}
    
    def _remove_comments(self, code: str, language: str = 'python') -> str:
        """Remove comments from code."""
        if language == 'python':
            # Remove docstrings
            code = re.sub(r'""".*?"""|\'\'\'.*?\'\'\'', '', code, flags=re.DOTALL)
            # Remove inline comments
            code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        else:
            # C-style comments
            code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
            code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        
        return code
    
    def classify_plagiarism_type(self, 
                                 textual_similarity: float,
                                 ast_similarity: float,
                                 metrics_comparison: Dict,
                                 pattern_analysis: Dict) -> str:
        """
        Classify the type of plagiarism based on multiple signals.
        
        Args:
            textual_similarity: Similarity of raw text (0-1)
            ast_similarity: Structural similarity (0-1)
            metrics_comparison: Metrics comparison dict
            pattern_analysis: Pattern analysis results
        
        Returns:
            Plagiarism type classification
        """
        # Direct copy
        if textual_similarity > 0.95 and ast_similarity > 0.95:
            return 'COPIA_DIRETA'
        
        # Variable renaming
        if pattern_analysis.get('variable_renaming', {}).get('detected', False):
            if textual_similarity > 0.6 and ast_similarity > 0.85:
                return 'RENOMEACAO_VARIAVEIS'
        
        # Code reordering
        if pattern_analysis.get('code_reordering', {}).get('detected', False):
            if ast_similarity > 0.9:
                return 'REORDENACAO_CODIGO'
        
        # Dead code insertion
        if pattern_analysis.get('dead_code_insertion', {}).get('detected', False):
            return 'INSERCAO_CODIGO_MORTO'
        
        # Refactoring
        if textual_similarity < 0.7 and ast_similarity > 0.8:
            return 'REFATORACAO_PESADA'
        
        if textual_similarity > 0.7 and ast_similarity > 0.85:
            if metrics_comparison.get('overall_similarity', 0) > 0.7:
                return 'REFATORACAO_LEVE'
        
        # Low similarity
        if textual_similarity < 0.5 and ast_similarity < 0.6:
            return 'SIMILARIDADE_BAIXA'
        
        # Default
        return 'REUSO_LEGITIMO'
    
    def comprehensive_analysis(self, 
                              code1: str, 
                              code2: str, 
                              textual_sim: float,
                              ast_sim: float,
                              metrics_comp: Dict) -> Dict:
        """
        Perform comprehensive plagiarism pattern analysis.
        
        Args:
            code1, code2: Source code strings
            textual_sim: Textual similarity from main analyzer
            ast_sim: AST similarity from AST parser
            metrics_comp: Metrics comparison from Metrics module
        
        Returns:
            Complete analysis with detected patterns and classification
        """
        # Detect patterns
        var_renaming = self.detect_variable_renaming(code1, code2)
        code_reordering = self.detect_code_reordering(code1, code2)
        dead_code = self.detect_dead_code_insertion(code1, code2)
        
        pattern_analysis = {
            'variable_renaming': var_renaming,
            'code_reordering': code_reordering,
            'dead_code_insertion': dead_code
        }
        
        # Classify plagiarism type
        plagiarism_type = self.classify_plagiarism_type(
            textual_sim,
            ast_sim,
            metrics_comp,
            pattern_analysis
        )
        
        # Generate explanation
        explanation = self._generate_explanation(
            plagiarism_type,
            textual_sim,
            ast_sim,
            pattern_analysis
        )
        
        return {
            'plagiarism_type': plagiarism_type,
            'plagiarism_description': self.PLAGIARISM_TYPES.get(plagiarism_type, 'Unknown'),
            'confidence': self._calculate_confidence(
                plagiarism_type,
                textual_sim,
                ast_sim,
                pattern_analysis
            ),
            'patterns_detected': pattern_analysis,
            'explanation': explanation
        }
    
    def _generate_explanation(self, 
                            plagiarism_type: str,
                            textual_sim: float,
                            ast_sim: float,
                            pattern_analysis: Dict) -> str:
        """Generate human-readable explanation of the analysis."""
        explanations = {
            'COPIA_DIRETA': f'O código apresenta alta similaridade textual ({textual_sim:.1%}) ' +
                          f'e estrutural ({ast_sim:.1%}), indicando cópia direta sem modificações.',
            
            'RENOMEACAO_VARIAVEIS': f'O código estrutural é muito similar ({ast_sim:.1%}), ' +
                                   f'mas com nomes de variáveis diferentes. ' +
                                   f'Detectadas {len(pattern_analysis["variable_renaming"]["variables_renamed"])} renomeações.',
            
            'REORDENACAO_CODIGO': f'O código mantém estrutura similar ({ast_sim:.1%}) ' +
                                 f'mas com blocos reorganizados. Similaridade textual: {textual_sim:.1%}.',
            
            'INSERCAO_CODIGO_MORTO': f'Inserção de código morto ou comentários excessivos detectada. ' +
                                    f'Aproximadamente {pattern_analysis["dead_code_insertion"]["inserted_lines"]} ' +
                                    f'linhas inseridas.',
            
            'REFATORACAO_PESADA': f'Código com refatoração significativa. Similaridade estrutural alta ' +
                                 f'({ast_sim:.1%}) mas textual baixa ({textual_sim:.1%}). ' +
                                 f'Possível plágio com reescrita.',
            
            'REFATORACAO_LEVE': f'Código com refatoração leve. Similaridade textual e estrutural moderadas ' +
                              f'({textual_sim:.1%} e {ast_sim:.1%} respectivamente).',
            
            'SIMILARIDADE_BAIXA': f'Não foram detectadas similaridades significativas ' +
                                 f'({textual_sim:.1%} textual, {ast_sim:.1%} estrutural). ' +
                                 f'Provavelmente código original.',
            
            'REUSO_LEGITIMO': 'Código pode ser reutilização legítima de bibliotecas ou código comum.'
        }
        
        return explanations.get(plagiarism_type, 'Análise inconclusiva.')
    
    def _calculate_confidence(self,
                            plagiarism_type: str,
                            textual_sim: float,
                            ast_sim: float,
                            pattern_analysis: Dict) -> float:
        """Calculate confidence score for plagiarism classification."""
        if plagiarism_type == 'COPIA_DIRETA':
            return min(textual_sim, ast_sim)
        
        if plagiarism_type == 'RENOMEACAO_VARIAVEIS':
            return pattern_analysis['variable_renaming']['confidence'] * ast_sim
        
        if plagiarism_type == 'REORDENACAO_CODIGO':
            return ast_sim * 0.9
        
        if plagiarism_type == 'INSERCAO_CODIGO_MORTO':
            return pattern_analysis['dead_code_insertion']['confidence']
        
        if plagiarism_type in ['REFATORACAO_LEVE', 'REFATORACAO_PESADA']:
            return ast_sim * 0.85
        
        if plagiarism_type == 'SIMILARIDADE_BAIXA':
            return (1 - textual_sim) * (1 - ast_sim)
        
        return 0.5
