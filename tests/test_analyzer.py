"""
Test analyzer modules.
"""

import pytest


class TestASTParser:
    """Test AST parser module."""
    
    @pytest.fixture
    def parser(self):
        from analyzer.ast_parser import ASTParser
        return ASTParser()
    
    def test_structural_similarity_identical(self, parser):
        """Test similarity of identical code."""
        code = "def foo(a, b): return a + b"
        similarity = parser.structural_similarity(code, code, 'python')
        assert similarity >= 0.99
    
    def test_structural_similarity_renamed_vars(self, parser):
        """Test similarity with renamed variables."""
        code1 = "def add(a, b): return a + b"
        code2 = "def add(x, y): return x + y"
        similarity = parser.structural_similarity(code1, code2, 'python')
        
        # Should be high similarity (same structure)
        assert similarity > 0.7
    
    def test_structural_similarity_different(self, parser):
        """Test similarity of different code."""
        code1 = "def foo(): return 42"
        code2 = "def bar(): print('hello')"
        similarity = parser.structural_similarity(code1, code2, 'python')
        
        # Should be low similarity
        assert similarity < 0.6
    
    def test_parse_python_ast(self, parser):
        """Test Python AST parsing."""
        code = '''
def greet(name):
    """Greet someone."""
    return f"Hello, {name}"

class Person:
    def __init__(self, name):
        self.name = name
'''
        
        features = parser.parse_python_ast(code)
        
        assert 'functions' in features
        assert 'classes' in features
        assert len(features['functions']) == 2
        assert len(features['classes']) == 1
    
    def test_detect_language_from_extension(self, parser):
        """Test language detection from extension."""
        assert parser.detect_language('test.py') == 'python'
        assert parser.detect_language('test.js') == 'javascript'
        assert parser.detect_language('test.java') == 'java'
    
    def test_code_fingerprint(self, parser):
        """Test code fingerprint generation."""
        code = "def foo(a, b): return a + b"
        
        fp = parser.extract_code_fingerprint(code, k=5)
        
        assert isinstance(fp, set)
        assert len(fp) > 0
    
    def test_refactoring_patterns(self, parser):
        """Test refactoring pattern detection."""
        code1 = "def calc(a, b): return a * b"
        code2 = "def calc(x, y): return x * y"
        
        patterns = parser.detect_refactoring_patterns(code1, code2)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        assert patterns[0]['type'] == 'VARIABLE_RENAME'


class TestCodeMetrics:
    """Test code metrics module."""
    
    @pytest.fixture
    def metrics(self):
        from analyzer.metrics import CodeMetrics
        return CodeMetrics()
    
    def test_cyclomatic_complexity_simple(self, metrics):
        """Test cyclomatic complexity of simple code."""
        code = "def foo(): return 42"
        cc = metrics.calculate_cyclomatic_complexity(code, 'python')
        
        # Base complexity = 1
        assert cc == 1
    
    def test_cyclomatic_complexity_with_conditions(self, metrics):
        """Test cyclomatic complexity with conditions."""
        code = '''
def classify(x):
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"
'''
        cc = metrics.calculate_cyclomatic_complexity(code, 'python')
        
        # 1 base + 2 conditions
        assert cc == 3
    
    def test_loc_counting(self, metrics):
        """Test lines of code counting."""
        code = '''def foo():
    # Comment
    return 42

# Another comment
'''
        loc_info = metrics.count_loc(code)
        
        assert loc_info['total'] == 5
        assert loc_info['comments'] == 2
        assert loc_info['blank'] == 1
        assert loc_info['code'] == 2
    
    def test_count_functions(self, metrics):
        """Test function counting."""
        code = '''
def foo():
    pass

def bar():
    pass

class Baz:
    def method(self):
        pass
'''
        count = metrics.count_functions_methods(code, 'python')
        
        assert count == 3
    
    def test_nesting_depth(self, metrics):
        """Test maximum nesting depth."""
        code = '''
def deep():
    if a:
        if b:
            if c:
                return d
'''
        depth = metrics.calculate_nesting_depth(code, 'python')
        
        assert depth >= 2  # At least 2 levels of nesting
    
    def test_calculate_all_metrics(self, metrics):
        """Test calculating all metrics."""
        code = "def foo(a, b): return a + b"
        
        all_metrics = metrics.calculate_all_metrics(code, 'python')
        
        assert 'loc' in all_metrics
        assert 'cyclomatic_complexity' in all_metrics
        assert 'function_count' in all_metrics
        assert 'max_nesting_depth' in all_metrics
        assert 'maintainability_index' in all_metrics
    
    def test_compare_metrics(self, metrics):
        """Test comparing metrics between two code snippets."""
        code1 = "def foo(a, b): return a + b"
        code2 = "def foo(x, y): return x + y"
        
        m1 = metrics.calculate_all_metrics(code1, 'python')
        m2 = metrics.calculate_all_metrics(code2, 'python')
        
        comparison = metrics.compare_metrics(m1, m2)
        
        assert 'overall_similarity' in comparison
        assert comparison['overall_similarity'] > 0.9  # Should be very similar


class TestPlagiarismPatternDetector:
    """Test plagiarism pattern detector."""
    
    @pytest.fixture
    def detector(self):
        from analyzer.patterns import PlagiarismPatternDetector
        return PlagiarismPatternDetector()
    
    def test_detect_variable_renaming(self, detector):
        """Test variable renaming detection."""
        code1 = "def calc(a, b): return a * b + a"
        code2 = "def calc(x, y): return x * y + x"
        
        result = detector.detect_variable_renaming(code1, code2, 'python')
        
        assert result['detected'] == True
        assert result['confidence'] > 0.6
    
    def test_detect_code_reordering(self, detector):
        """Test code reordering detection."""
        code1 = '''
def foo():
    a()
    b()
    c()
'''
        code2 = '''
def foo():
    c()
    a()
    b()
'''
        result = detector.detect_code_reordering(code1, code2)

        # The reordering detector should return a well-formed dict
        assert isinstance(result, dict)
        assert 'detected' in result
        assert 'confidence' in result
        assert isinstance(result['detected'], bool)
        assert 0.0 <= result['confidence'] <= 1.0

        # Both snippets share the same lines — reordering should be detected
        assert result['detected'] is True
        assert result['confidence'] >= 0.7
    
    def test_classify_direct_copy(self, detector):
        """Test classification of direct copy."""
        code1 = "def foo(): return 42"
        code2 = "def foo(): return 42"
        
        result = detector.comprehensive_analysis(
            code1, code2,
            textual_sim=0.99,
            ast_sim=0.99,
            metrics_comp={'overall_similarity': 1.0}
        )
        
        assert result['plagiarism_type'] == 'COPIA_DIRETA'
        assert result['confidence'] > 0.9
    
    def test_classify_low_similarity(self, detector):
        """Test classification of low similarity."""
        code1 = "def foo(): return 42"
        code2 = "def bar(): print('hello')"
        
        result = detector.comprehensive_analysis(
            code1, code2,
            textual_sim=0.1,
            ast_sim=0.2,
            metrics_comp={'overall_similarity': 0.3}
        )
        
        assert result['plagiarism_type'] == 'SIMILARIDADE_BAIXA'


class TestClusterDetector:
    """Test cluster detector module."""
    
    @pytest.fixture
    def detector(self):
        from analyzer.clustering import ClusterDetector
        return ClusterDetector()
    
    def test_hierarchical_clustering(self, detector):
        """Test hierarchical clustering."""
        import numpy as np
        
        similarity_matrix = np.array([
            [1.0, 0.9, 0.3],
            [0.9, 1.0, 0.2],
            [0.3, 0.2, 1.0]
        ])
        files = ['a.py', 'b.py', 'c.py']
        
        clusters = detector.hierarchical_clustering(
            similarity_matrix, files, threshold=0.3
        )
        
        # Files a and b should be in same cluster (high similarity)
        assert len(clusters) >= 1
    
    def test_build_similarity_graph(self, detector):
        """Test similarity graph building."""
        import numpy as np
        
        similarity_matrix = np.array([
            [1.0, 0.9, 0.3],
            [0.9, 1.0, 0.2],
            [0.3, 0.2, 1.0]
        ])
        files = ['a.py', 'b.py', 'c.py']
        
        G = detector.build_similarity_graph(
            similarity_matrix, files, min_similarity=0.5
        )
        
        # Only edge a-b should exist (similarity 0.9 > 0.5)
        assert G.number_of_nodes() == 3
        assert G.number_of_edges() == 1
    
    def test_analyze_clusters(self, detector):
        """Test complete cluster analysis."""
        import numpy as np
        
        similarity_matrix = np.array([
            [1.0, 0.9, 0.3, 0.2],
            [0.9, 1.0, 0.2, 0.3],
            [0.3, 0.2, 1.0, 0.95],
            [0.2, 0.3, 0.95, 1.0]
        ])
        files = ['a.py', 'b.py', 'c.py', 'd.py']
        
        result = detector.analyze_clusters(
            similarity_matrix, files, min_similarity=0.7
        )
        
        assert 'clusters' in result
        assert 'num_clusters' in result
        assert 'graph_density' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])