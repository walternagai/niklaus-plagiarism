"""
Performance benchmarks and example usage for FASE 2.
"""

import time
import random
from typing import List, Tuple
from core.pipeline import AnalysisPipeline, compare_performance
from core.analyzer import PlagiarismAnalyzer
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_sample_code(num_files: int, similarity_factor: float = 0.3) -> Tuple[List[str], List[str]]:
    """
    Generate sample Python code files for benchmarking.
    
    Args:
        num_files: Number of files to generate
        similarity_factor: Factor to control similarity between files
    
    Returns:
        Tuple of (filenames, contents)
    """
    
    base_functions = [
        "def add(a, b):\n    return a + b",
        "def multiply(x, y):\n    return x * y",
        "def divide(numerator, denominator):\n    if denominator == 0:\n        return None\n    return numerator / denominator",
        "def calculate_average(numbers):\n    if not numbers:\n        return 0\n    return sum(numbers) / len(numbers)",
        "def find_maximum(values):\n    if not values:\n        return None\n    max_val = values[0]\n    for val in values:\n        if val > max_val:\n            max_val = val\n    return max_val",
    ]
    
    names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Henry"]
    
    files = []
    contents = []
    
    for i in range(num_files):
        filename = f"student_{i}_{random.choice(names)}.py"
        
        # Pick random functions
        num_functions = random.randint(2, 5)
        selected_functions = random.sample(base_functions, num_functions)
        
        # Add some variation
        code_lines = [f"# Solution {i}", ""]
        
        for func in selected_functions:
            if random.random() < similarity_factor:
                # Keep original
                code_lines.append(func)
            else:
                # Minor variation (variable renaming)
                modified = func.replace("a, b", "x, y").replace("a + b", "x + y")
                code_lines.append(modified)
            code_lines.append("")
        
        files.append(filename)
        contents.append("\n".join(code_lines))
    
    return files, contents


def benchmark_sequential_vs_parallel():
    """
    Benchmark sequential (1 worker) vs parallel (4 workers) analysis.
    """
    print("\n" + "="*80)
    print("BENCHMARK: Sequential vs Parallel Analysis")
    print("="*80 + "\n")
    
    test_cases = [10, 20, 30]
    
    for file_count in test_cases:
        print(f"\nTesting with {file_count} files...")
        files, contents = generate_sample_code(file_count)
        
        # Sequential
        print(f"  Sequential (1 worker)...")
        pipeline_seq = AnalysisPipeline('python', max_workers=1, use_cache=False)
        
        start = time.time()
        results_seq = pipeline_seq.run_textual_only(files, contents)
        time_seq = time.time() - start
        
        # Parallel
        print(f"  Parallel (4 workers)...")
        pipeline_par = AnalysisPipeline('python', max_workers=4, use_cache=False)
        
        start = time.time()
        results_par = pipeline_par.run_textual_only(files, contents)
        time_par = time.time() - start
        
        # Results
        speedup = time_seq / time_par if time_par > 0 else 0
        
        print(f"  ✓ Sequential: {time_seq:.2f}s")
        print(f"  ✓ Parallel:   {time_par:.2f}s")
        print(f"  ✓ Speedup:    {speedup:.2f}x")
        print(f"  ✓ Found {len(results_seq['suspicious_pairs'])} suspicious pairs")


def benchmark_full_pipeline():
    """
    Benchmark full analysis pipeline (textual + AST + metrics).
    """
    print("\n" + "="*80)
    print("BENCHMARK: Full Analysis Pipeline")
    print("="*80 + "\n")
    
    file_counts = [10, 20]
    
    for file_count in file_counts:
        print(f"\n--- Testing with {file_count} files ---")
        files, contents = generate_sample_code(file_count, similarity_factor=0.5)
        
        pipeline = AnalysisPipeline('python', max_workers=4, use_cache=False)
        
        # Get predictions
        stats = pipeline.get_performance_stats(file_count)
        print(f"  Predictions:")
        print(f"    - Comparisons: {stats['comparisons']}")
        print(f"    - Est. time: {stats['estimated_total_time']:.2f}s")
        
        # Run actual
        print(f"  Running analysis...")
        start = time.time()
        
        def progress_callback(stage, current, total):
            if stage == "analysis":
                pct = (current / total * 100) if total > 0 else 0
                print(f"    Progress: {pct:.0f}%", end='\r')
        
        results = pipeline.run_full_analysis(
            files, contents, 
            threshold=0.7, 
            enable_ai=False,  # Skip AI for benchmark
            progress_callback=progress_callback
        )
        
        elapsed = time.time() - start
        
        print(f"\n  Results:")
        print(f"    - Actual time: {elapsed:.2f}s")
        print(f"    - Textual comparisons: {len(results['textual_similarities'])}")
        print(f"    - AST comparisons: {len(results['ast_similarities'])}")
        print(f"    - Files analyzed: {len(results['metrics'])}")
        print(f"    - Suspicious pairs: {len(results['suspicious_pairs'])}")


def test_cache_functionality():
    """
    Test cache save, load, and expiry.
    """
    print("\n" + "="*80)
    print("TEST: Cache Functionality")
    print("="*80 + "\n")
    
    from core.persistence import AnalysisCache
    
    files, contents = generate_sample_code(5)
    
    # Create pipeline with cache
    pipeline = AnalysisPipeline('python', max_workers=2, use_cache=True)
    
    print("  First run (no cache)...")
    start = time.time()
    results1 = pipeline.run_full_analysis(files, contents, enable_ai=False)
    time1 = time.time() - start
    print(f"    Time: {time1:.2f}s")
    
    print("\n  Second run (from cache)...")
    start = time.time()
    results2 = pipeline.run_full_analysis(files, contents, enable_ai=False)
    time2 = time.time() - start
    print(f"    Time: {time2:.2f}s")
    print(f"    Speedup: {time1/time2:.1f}x faster")
    
    # Verify results match
    assert results1['files'] == results2['files']
    print(f"    ✓ Results match")


def test_rate_limiting():
    """
    Test rate limiter functionality.
    """
    print("\n" + "="*80)
    print("TEST: Rate Limiting")
    print("="*80 + "\n")
    
    from core.llm_client import RateLimiter
    
    limiter = RateLimiter(calls_per_minute=60)  # 1 per second
    
    print("  Testing rate limiter (60 calls/min = 1 per second)...")
    
    # First call should be immediate
    start = time.time()
    limiter.wait()
    elapsed1 = time.time() - start
    print(f"    1st call: {elapsed1:.3f}s (should be ~0)")
    
    # Second call should wait ~1 second
    start = time.time()
    limiter.wait()
    elapsed2 = time.time() - start
    print(f"    2nd call: {elapsed2:.3f}s (should be ~1.0)")
    
    assert elapsed1 < 0.1, "First call should be immediate"
    assert 0.8 < elapsed2 < 1.2, "Second call should wait ~1 second"
    print("    ✓ Rate limiter working correctly")


def demo_simple_usage():
    """
    Demonstrate simple usage of the pipeline.
    """
    print("\n" + "="*80)
    print("DEMO: Simple Usage")
    print("="*80 + "\n")
    
    # Create sample files
    code1 = """
def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

def find_maximum(values):
    if not values:
        return None
    max_val = values[0]
    for val in values:
        if val > max_val:
            max_val = val
    return max_val
"""
    
    code2 = """
def calc_avg(nums):
    if len(nums) == 0:
        return 0
    total = sum(nums)
    count = len(nums)
    return total / count

def get_max(items):
    if not items:
        return None
    maximum = items[0]
    for item in items:
        if item > maximum:
            maximum = item
    return maximum
"""
    
    files = ["student1.py", "student2.py"]
    contents = [code1, code2]
    
    # Create pipeline
    pipeline = AnalysisPipeline('python', max_workers=2, use_cache=False)
    
    # Run analysis
    print("  Running analysis...")
    results = pipeline.run_full_analysis(files, contents, enable_ai=False)
    
    print(f"\n  Results:")
    print(f"    - Files: {results['files']}")
    print(f"    - Threshold: {results['threshold']}")
    print(f"    - Textual similarity: {results['textual_similarities'][0][2]:.2%}")
    print(f"    - AST similarity: {results['ast_similarities'][0][2]:.2%}")
    print(f"    - Suspicious: {len(results['suspicious_pairs']) > 0}")
    print(f"    - Analysis time: {results['analysis_time']:.3f}s")
    
    # Show metrics
    print(f"\n  Metrics:")
    for i, metrics in enumerate(results['metrics']):
        print(f"    File {i+1}:")
        print(f"      - LOC: {metrics['loc']}")
        print(f"      - Cyclomatic: {metrics['cyclomatic']}")
        print(f"      - Functions: {metrics['functions']}")


def demo_performance_estimates():
    """
    Demonstrate performance estimation API.
    """
    print("\n" + "="*80)
    print("DEMO: Performance Estimates")
    print("="*80 + "\n")
    
    file_counts = [10, 20, 50, 100, 200]
    
    pipeline = AnalysisPipeline('python', max_workers=4)
    
    print(f"  Files | Comparisons | Est. Time | Speedup")
    print(f"  ------|-------------|-----------|---------")
    
    for count in file_counts:
        stats = pipeline.get_performance_stats(count)
        print(f"  {count:5d} | {stats['comparisons']:11d} | {stats['estimated_total_time']:8.1f}s | {stats['speedup_factor']}x")


if __name__ == "__main__":
    print("\n" + "="*80)
    print(" FASE 2: PERFORMANCE BENCHMARKS AND EXAMPLES")
    print("="*80)
    
    # Run demos
    demo_simple_usage()
    demo_performance_estimates()
    
    # Run tests
    test_rate_limiting()
    test_cache_functionality()
    
    # Run benchmarks (optional, takes longer)
    run_benchmarks = input("\nRun full benchmarks? (y/n): ").lower().strip() == 'y'
    
    if run_benchmarks:
        benchmark_sequential_vs_parallel()
        benchmark_full_pipeline()
    
    print("\n" + "="*80)
    print(" All tests and demos completed!")
    print("="*80 + "\n")