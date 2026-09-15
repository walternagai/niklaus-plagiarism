"""
Tests for export service and compression utilities.

Covers export/service.py (ExportService) and utils/compression.py
(ResultCompressor, ChunkedCompressor, CompressionStats, quick functions).
"""

import json

import pytest

from export.service import ExportService
from utils.compression import (
    ChunkedCompressor,
    CompressionStats,
    ResultCompressor,
    compress_result,
    get_compression_stats,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_results():
    """Minimal analysis results matching the pipeline output schema."""
    return {
        'files': ['a.py', 'b.py'],
        'language': 'python',
        'threshold': 0.7,
        'pairwise_results': [
            {
                'file1': 'a.py',
                'file2': 'b.py',
                'similarity': 0.92,
                'is_suspicious': True,
            },
            {
                'file1': 'a.py',
                'file2': 'c.py',
                'similarity': 0.30,
                'is_suspicious': False,
            },
        ],
        'patterns': {
            'a.py_b.py': {
                'plagiarism_type': 'VARIABLE_RENAMING',
                'confidence': 0.85,
                'explanation': 'renamed variables',
            }
        },
        'metrics': [
            {'loc': 10, 'cyclomatic': 2, 'functions': 1, 'nesting': 1, 'maintainability': 88.5},
            {'loc': 12, 'cyclomatic': 3, 'functions': 2, 'nesting': 2, 'maintainability': 80.0},
        ],
        'average_similarity': 0.46,
        'max_similarity': 0.92,
    }


# ---------------------------------------------------------------------------
# ExportService.to_json
# ---------------------------------------------------------------------------

class TestExportJson:
    def test_roundtrip_preserves_data(self, sample_results):
        raw = ExportService.to_json(sample_results)
        assert json.loads(raw.decode('utf-8')) == sample_results

    def test_nan_and_inf_become_null(self):
        raw = ExportService.to_json({'x': float('nan'), 'y': float('inf')})
        parsed = json.loads(raw.decode('utf-8'))
        assert parsed == {'x': None, 'y': None}

    def test_numpy_scalars_and_arrays_serialised(self):
        np = __import__('numpy')
        raw = ExportService.to_json({'arr': np.array([1, 2]), 'scalar': np.float64(1.5)})
        parsed = json.loads(raw.decode('utf-8'))
        assert parsed == {'arr': [1, 2], 'scalar': 1.5}

    def test_non_serialisable_object_falls_back_to_str(self):
        class Custom:
            def __str__(self):
                return 'custom-obj'

        raw = ExportService.to_json({'obj': Custom()})
        assert json.loads(raw.decode('utf-8')) == {'obj': 'custom-obj'}


# ---------------------------------------------------------------------------
# ExportService.to_csv
# ---------------------------------------------------------------------------

class TestExportCsv:
    def test_has_bom_and_header(self, sample_results):
        raw = ExportService.to_csv(sample_results).decode('utf-8')
        assert raw.startswith('\ufeff')
        assert 'file1,file2,similarity,is_suspicious,plagiarism_type,confidence,explanation' in raw

    def test_row_per_pair_with_pattern(self, sample_results):
        text = ExportService.to_csv(sample_results).decode('utf-8')
        assert 'a.py,b.py,0.9200,sim,VARIABLE_RENAMING,0.8500' in text
        assert 'a.py,c.py' in text

    def test_suspicious_by_threshold_without_flag(self):
        results = {
            'threshold': 0.5,
            'pairwise_results': [{'file1': 'x.py', 'file2': 'y.py', 'similarity': 0.9}],
        }
        text = ExportService.to_csv(results).decode('utf-8')
        assert 'x.py,y.py,0.9000,sim' in text

    def test_empty_results_produce_header_only(self):
        text = ExportService.to_csv({'pairwise_results': []}).decode('utf-8')
        assert text.count('\r\n') == 1  # header only

    def test_nan_similarity_exported_as_zero(self):
        results = {
            'threshold': 0.7,
            'pairwise_results': [{'file1': 'a.py', 'file2': 'b.py', 'similarity': float('nan')}],
        }
        text = ExportService.to_csv(results).decode('utf-8')
        assert 'a.py,b.py,0.0000,nao' in text


# ---------------------------------------------------------------------------
# ExportService.to_summary_csv
# ---------------------------------------------------------------------------

class TestExportSummaryCsv:
    def test_summary_rows_match_files(self, sample_results):
        text = ExportService.to_summary_csv(sample_results).decode('utf-8')
        assert 'a.py,10,2,1,1,88.50' in text
        assert 'b.py,12,3,2,2,80.00' in text

    def test_missing_metrics_leave_blank_row(self):
        text = ExportService.to_summary_csv({'files': ['orphan.py'], 'metrics': []}).decode('utf-8')
        assert 'orphan.py,,,,,\r\n' in text

    def test_safe_float_guards(self):
        assert ExportService._safe_float('n/a') == 0.0
        assert ExportService._safe_float(float('inf')) == 0.0
        assert ExportService._safe_float(0.5) == 0.5


# ---------------------------------------------------------------------------
# ResultCompressor
# ---------------------------------------------------------------------------

class TestResultCompressor:
    def test_roundtrip(self):
        data = {'files': ['a.py'], 'similarity': 0.9, 'nested': {'x': [1, 2, 3]}}
        c = ResultCompressor(compression_level=1)
        assert c.decompress(c.compress(data)) == data

    def test_base64_roundtrip(self):
        data = {'key': 'value', 'n': 42}
        c = ResultCompressor()
        encoded = c.compress_to_base64(data)
        assert isinstance(encoded, str)
        assert c.decompress_from_base64(encoded) == data

    def test_corrupt_data_raises(self):
        c = ResultCompressor()
        import pytest
        with pytest.raises(Exception):
            c.decompress(b'not-a-valid-zlib-stream')

    def test_file_roundtrip(self, tmp_path):
        src = tmp_path / 'input.json'
        gz = tmp_path / 'input.json.gz'
        out = tmp_path / 'restored.json'
        src.write_text(json.dumps({'a': 1, 'list': list(range(100))}))
        c = ResultCompressor()

        ratio = c.compress_file(str(src), str(gz))
        assert isinstance(ratio, int)
        c.decompress_file(str(gz), str(out))
        assert json.loads(out.read_text()) == json.loads(src.read_text())


# ---------------------------------------------------------------------------
# ChunkedCompressor
# ---------------------------------------------------------------------------

class TestChunkedCompressor:
    def test_roundtrip_small_chunk(self):
        data = {'values': list(range(1000)), 'name': 'x' * 100}
        cc = ChunkedCompressor(chunk_size=64)
        chunks = cc.compress_chunks(data)
        assert len(chunks) > 1  # really chunked
        assert cc.decompress_chunks(chunks) == data


# ---------------------------------------------------------------------------
# CompressionStats + quick functions
# ---------------------------------------------------------------------------

class TestCompressionStats:
    def test_record_and_ratio(self):
        stats = CompressionStats()
        stats.record('op', 100, 50)
        stats.record('op', 100, 25)
        report = stats.get_stats('op')
        assert report['total_original'] == 200
        assert report['total_compressed'] == 75

    def test_unknown_operation_returns_empty(self):
        assert CompressionStats().get_stats('missing') == {}

    def test_global_stats_recorded_by_quick_function(self):
        compress_result({'x': 1}, level=1)
        saved = get_compression_stats().get_total_savings()
        assert saved['original_bytes'] > 0
        assert saved['compressed_bytes'] > 0
        assert saved['saved_bytes'] == saved['original_bytes'] - saved['compressed_bytes']