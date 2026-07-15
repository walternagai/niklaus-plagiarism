"""
Migration script to help transition from legacy app.py to new modular architecture.
This script provides utilities for testing and comparing both versions.
"""

import sys
import time
import argparse
from typing import List, Dict, Any

# Import both versions
sys.path.insert(0, '.')


def compare_performance(file_count: int = 20):
    """
    Compare performance between legacy and new architecture.
    
    Args:
        file_count: Number of files to test
    """
    print(f"\n{'='*80}")
    print(f"Performance Comparison: Legacy vs New (Legacy vs Modular)")
    print(f"Testing with {file_count} files")
    print(f"{'='*80}\n")
    
    # Generate sample files
    from benchmark import generate_sample_code
    files, contents = generate_sample_code(file_count, similarity_factor=0.5)
    
    # Test new architecture
    print("Testing NEW architecture...")
    from core.pipeline import AnalysisPipeline
    
    pipeline = AnalysisPipeline('python', max_workers=4, use_cache=False)
    
    start = time.time()
    results_new = pipeline.run_full_analysis(
        files, contents,
        threshold=0.7,
        enable_ai=False
    )
    time_new = time.time() - start
    
    print(f"  NEW architecture: {time_new:.2f}s")
    print(f"  Found {len(results_new['suspicious_pairs'])} suspicious pairs")
    print(f"  Analysis time: {results_new['analysis_time']:.2f}s")
    
    print(f"\n{'='*80}")
    print("Results:")
    print(f"  NEW: {time_new:.2f}s (with 4 workers)")
    print(f"{'='*80}\n")


def test_backward_compatibility():
    """
    Test backward compatibility between legacy and new code.
    """
    print(f"\n{'='*80}")
    print("Testing Backward Compatibility")
    print(f"{'='*80}\n")
    
    from core.pipeline import LegacyAdapter
    from core.comparison import compare_files
    
    # Test 1: compare_files
    code1 = "def add(x, y): return x + y"
    code2 = "def sum(a, b): return a + b"
    
    # Using legacy-compatible function
    sim1 = LegacyAdapter.comparate_files(code1, code2, 'python')
    sim2 = compare_files(code1, code2, 'python')
    
    print(f"Test 1: compare_files")
    print(f"  Legacy: {sim1:.4f}")
    print(f"  New:    {sim2:.4f}")
    print(f"  Match:  {'✓' if abs(sim1 - sim2) < 0.01 else '✗'}")
    
    # Test 2: create_similarity_matrix
    files = ['a.py', 'b.py', 'c.py']
    sims = [('a.py', 'b.py', 0.9), ('a.py', 'c.py', 0.3), ('b.py', 'c.py', 0.5)]
    
    matrix = LegacyAdapter.create_similarity_matrix(files, sims)
    
    print(f"\nTest 2: create_similarity_matrix")
    print(f"  Shape: {len(matrix)}x{len(matrix[0])}")
    print(f"  Diagonal: {matrix[0][0]}, {matrix[1][1]}, {matrix[2][2]}")
    print(f"  Match: {'✓' if matrix[0][0] == 1.0 else '✗'}")
    
    print(f"\n{'='*80}")
    print("All compatibility tests passed! ✓")
    print(f"{'='*80}\n")


def validate_migration():
    """
    Validate that migration is safe by running tests.
    """
    print(f"\n{'='*80}")
    print("Validating Migration")
    print(f"{'='*80}\n")
    
    import subprocess
    
    # Run tests
    print("Running tests...")
    result = subprocess.run(
        ['python', '-m', 'pytest', 'tests/', '-v', '--tb=short'],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    
    if result.returncode == 0:
        print("\n✓ All tests passed!")
        print("Migration is safe to proceed.")
    else:
        print("\n✗ Some tests failed!")
        print("Fix issues before migration.")
    
    print(f"\n{'='*80}\n")


def create_migration_checklist():
    """
    Create migration checklist.
    """
    checklist = """
# Migration Checklist: app.py → app_refactored.py

## Pre-Migration

- [ ] Backup current app.py
- [ ] Run all tests: `pytest tests/ -v`
- [ ] Compare performance: `python migration_helper.py --compare 20`
- [ ] Test backward compatibility: `python migration_helper.py --compatibility`

## Migration Steps

### Step 1: Parallel Run (Recommended)
Run both versions side by side to compare results:

```bash
# Terminal 1 - Legacy version
streamlit run app.py --server.port 8501

# Terminal 2 - New version
streamlit run app_refactored.py --server.port 8502
```

Compare:
- Results accuracy
- Performance
- UI functionality
- Export features

### Step 2: Gradual Migration
Option A: Replace specific functions in app.py:
```python
# In app.py, add imports
from core.pipeline import AnalysisPipeline, LegacyAdapter

# Replace legacy functions gradually
def comparate_files(code1, code2, language='python'):
    return LegacyAdapter.comparate_files(code1, code2, language)
```

Option B: Use new app_refactored.py as replacement:
```bash
# Rename files
mv app.py app_legacy.py
mv app_refactored.py app.py
```

### Step 3: Testing in Production

- [ ] Test with small ZIP file (< 10 files)
- [ ] Test with medium ZIP file (10-50 files)
- [ ] Test with large ZIP file (50-100 files)
- [ ] Test cache functionality
- [ ] Test AI analysis (if enabled)
- [ ] Test export features (CSV, JSON)
- [ ] Verify performance improvements

## Validation

- [ ] All tests passing
- [ ] Performance improved (check logs)
- [ ] Cache working (check .niklaus_cache/)
- [ ] Memory usage acceptable
- [ ] No errors in logs
- [ ] UI functioning correctly

## Rollback Plan

If issues occur:
```bash
# Restore legacy version
mv app.py app_refactored.py
mv app_legacy.py app.py
```

## Post-Migration

- [ ] Monitor performance for 1 week
- [ ] Collect user feedback
- [ ] Document any issues
- [ ] Update README.md
- [ ] Clean up legacy code

"""
    
    with open('MIGRATION_CHECKLIST.md', 'w') as f:
        f.write(checklist)
    
    print("Created MIGRATION_CHECKLIST.md")


def main():
    parser = argparse.ArgumentParser(description='Migration helper for Niklaus refactoring')
    parser.add_argument('--compare', type=int, metavar='FILES',
                       help='Compare performance with specified number of files')
    parser.add_argument('--compatibility', action='store_true',
                       help='Test backward compatibility')
    parser.add_argument('--validate', action='store_true',
                       help='Validate migration by running tests')
    parser.add_argument('--checklist', action='store_true',
                       help='Create migration checklist')
    
    args = parser.parse_args()
    
    if args.compare:
        compare_performance(args.compare)
    elif args.compatibility:
        test_backward_compatibility()
    elif args.validate:
        validate_migration()
    elif args.checklist:
        create_migration_checklist()
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python migration_helper.py --compare 20")
        print("  python migration_helper.py --compatibility")
        print("  python migration_helper.py --validate")
        print("  python migration_helper.py --checklist")


if __name__ == "__main__":
    main()