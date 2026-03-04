"""
Test pipeline module.
"""

import pytest
import time
from core.pipeline import AnalysisPipeline, LegacyAdapter, compare_performance


class TestAnalysisPipeline:
    """Test analysis pipeline."""
    
    @pytest.fixture
    def sample_files(self):
        """Generate sample files for testing."""
        files = ['a.py', 'b.py']
        contents = [
            "def add(x, y): return x + y\n",
            "def sum(a, b): return a + b\n"
        ]
        return files, contents
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = AnalysisPipeline('python', max_workers=2)
        
        assert pipeline.language == 'python'
        assert pipeline.max_workers == 2
        assert pipeline.analyzer is not None
        assert pipeline.cache is not None
    
    def test_pipeline_initialization_without_cache(self):
        """Test pipeline without cache."""
        pipeline = AnalysisPipeline('python', max_workers=2, use_cache=False)
        
        assert pipeline.cache is None
    
    def test_run_textual_only(self, sample_files):
        """Test textual-only analysis."""
        files, contents = sample_files
        
        pipeline = AnalysisPipeline('python', max_workers=2, use_cache=False)
        results = pipeline.run_textual_only(files, contents)
        
        assert 'files' in results
        assert 'textual_similarities' in results
        assert 'similarity_matrix' in results
        assert len(results['textual_similarities']) == 1  # 1 pair
    
    def test_run_full_analysis_no_ai(self, sample_files):
        """Test full analysis without AI."""
        files, contents = sample_files
        
        pipeline = AnalysisPipeline('python', max_workers=2, use_cache=False)
        results = pipeline.run_full_analysis(
            files, contents,
            threshold=0.7,
            enable_ai=False
        )
        
        assert 'textual_similarities' in results
        assert 'ast_similarities' in results
        assert 'metrics' in results
        assert 'similarity_matrix' in results
        assert 'cluster_data' in results
        assert 'patterns' in results
        assert 'ai_analyses' in results
        assert results['ai_analyses'] == {}  # No AI
        assert results['analysis_time'] >= 0
    
    def test_run_full_analysis_with_cache(self, sample_files, tmp_path):
        """Test full analysis with cache."""
        files, contents = sample_files
        
        # Use temp cache directory
        pipeline = AnalysisPipeline(
            'python', 
            max_workers=2, 
            use_cache=True
        )
        pipeline.cache = type(pipeline.cache)(cache_dir=str(tmp_path))
        
        # First run
        results1 = pipeline.run_full_analysis(
            files, contents,
            threshold=0.7,
            enable_ai=False
        )
        
        # Second run (from cache)
        results2 = pipeline.run_full_analysis(
            files, contents,
            threshold=0.7,
            enable_ai=False
        )
        
        # Should have same results
        assert results1['files'] == results2['files']
    
    def test_get_performance_stats(self):
        """Test performance statistics."""
        pipeline = AnalysisPipeline('python', max_workers=4)
        
        stats = pipeline.get_performance_stats(100)
        
        assert stats['files'] == 100
        assert stats['comparisons'] == 4950  # 100 * 99 / 2
        assert stats['parallel_workers'] == 4
        assert 'estimated_total_time' in stats
    
    def test_progress_callback(self, sample_files):
        """Test progress callback."""
        files, contents = sample_files
        
        progress_calls = []
        
        def callback(stage, current, total):
            progress_calls.append({
                'stage': stage,
                'current': current,
                'total': total
            })
        
        pipeline = AnalysisPipeline('python', max_workers=2, use_cache=False)
        pipeline.run_full_analysis(
            files, contents,
            threshold=0.7,
            enable_ai=False,
            progress_callback=callback
        )
        
        # Should have received progress updates
        assert len(progress_calls) > 0
        
        # Check stages were called
        stages = [call['stage'] for call in progress_calls]
        assert 'analysis' in stages
        assert 'matrix' in stages


class TestLegacyAdapter:
    """Test legacy adapter for backward compatibility."""
    
    def test_comparate_files(self):
        """Test file comparison adapter."""
        code1 = "def add(x, y): return x + y"
        code2 = "def sum(a, b): return a + b"
        
        similarity = LegacyAdapter.comparate_files(code1, code2, 'python')
        
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Should be similar
    
    def test_create_similarity_matrix(self):
        """Test similarity matrix creation."""
        files = ['a.py', 'b.py', 'c.py']
        textual_sims = [
            ('a.py', 'b.py', 0.9),
            ('a.py', 'c.py', 0.3),
            ('b.py', 'c.py', 0.5)
        ]
        
        matrix = LegacyAdapter.create_similarity_matrix(files, textual_sims)
        
        assert len(matrix) == 3
        assert len(matrix[0]) == 3
        assert matrix[0][0] == 1.0  # Diagonal
        assert matrix[0][1] == 0.9  # a-b
        assert matrix[1][0] == 0.9  # b-a (symmetric)


class TestComparePerformance:
    """Test performance comparison utility."""
    
    def test_compare_performance(self):
        """Test performance comparison."""
        result = compare_performance(file_counts=[10, 20])
        
        assert 'comparison' in result
        assert len(result['comparison']) == 2
        assert 'speedup' in result['comparison'][0]  # Corrected key
        
        # Speedup should be positive
        for item in result['comparison']:
            assert item['speedup'] > 1.0
        
        # Overall speedup should be positive
        assert result['speedup_avg'] > 1.0


class TestPipelineIntegration:
    """Integration tests for pipeline."""
    
    def test_end_to_end_analysis(self):
        """Test complete end-to-end analysis."""
        # Create sample code
        code1 = """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)
"""
        
        code2 = """def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

def fact(n):
    if n <= 1:
        return 1
    return n * fact(n-1)
"""
        
        files = ['student1.py', 'student2.py']
        contents = [code1, code2]
        
        # Run analysis
        pipeline = AnalysisPipeline('python', max_workers=2, use_cache=False)
        results = pipeline.run_full_analysis(
            files, contents,
            threshold=0.5,  # Lower threshold to catch the similarity
            enable_ai=False
        )
        
        # Verify basic structure
        assert len(results['textual_similarities']) == 1
        assert len(results['ast_similarities']) == 1
        assert len(results['metrics']) == 2
        
        # Check that analysis completed
        assert results['analysis_time'] >= 0
        assert 'similarity_matrix' in results
        assert 'cluster_data' in results
    
    def test_large_dataset_performance(self):
        """Test performance with larger dataset."""
        # Generate 30 sample files
        import random
        
        base_func = "def add(x, y): return x + y\n"
        
        files = []
        contents = []
        
        for i in range(30):
            files.append(f'file_{i}.py')
            # Add some variation
            if random.random() > 0.5:
                contents.append(base_func.replace('x, y', f'a{i}, b{i}'))
            else:
                contents.append(base_func)
        
        # Run analysis
        pipeline = AnalysisPipeline('python', max_workers=4, use_cache=False)
        
        start = time.time()
        results = pipeline.run_full_analysis(
            files, contents,
            threshold=0.7,
            enable_ai=False
        )
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0
        
        # Should have correct number of comparisons
        expected_comparisons = 30 * 29 // 2  # 435
        assert len(results['textual_similarities']) == expected_comparisons


if __name__ == "__main__":
    pytest.main([__file__, "-v"])