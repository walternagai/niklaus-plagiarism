
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

