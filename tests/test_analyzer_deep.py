"""
Deep coverage for analyzer (ast_parser, metrics, patterns),
core/file_handler and core/pipeline cache/llm wiring.
"""

import ast
import io
import zipfile
from unittest.mock import patch

import pytest

from analyzer.ast_parser import ASTParser
from analyzer.metrics import CodeMetrics
from analyzer.patterns import PlagiarismPatternDetector
from core.pipeline import AnalysisPipeline


class FakeUpload:
    """Mimics st.UploadedFile surface used by FileHandler.extract_zip."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self):
        return self._data


# ---------------------------------------------------------------------------
# ASTParser
# ---------------------------------------------------------------------------

class TestDetectLanguage:
    def test_by_extension(self):
        parser = ASTParser()
        assert parser.detect_language('a.py') == 'python'
        assert parser.detect_language('b.java') == 'java'
        assert parser.detect_language('c.cpp') == 'cpp'
        assert parser.detect_language('d.js') == 'javascript'
        assert parser.detect_language('e.go') == 'go'
        assert parser.detect_language('f.rs') == 'rust'

    def test_content_fallback(self):
        parser = ASTParser()
        assert parser.detect_language('unknown.xyz', 'def foo(): pass') == 'python'
        assert parser.detect_language('unknown.xyz', 'public class Main {}') == 'java'
        assert parser.detect_language('unknown.xyz', 'func main() {}') == 'go'
        assert parser.detect_language('unknown.xyz', 'fn main() {}') == 'rust'
        assert parser.detect_language('unknown.xyz', 'random text here') == 'unknown'


class TestPythonAst:
    def test_parse_valid(self):
        parser = ASTParser()
        features = parser.parse_python_ast("def f(x):\n    return x + 1")
        assert 'functions' in features or 'calls' in features

    def test_parse_syntax_error(self):
        assert 'error' in ASTParser().parse_python_ast('def broken(:')


class TestStructuralSimilarity:
    def test_identical_code(self):
        parser = ASTParser()
        code = "def calc(a, b):\n    return a + b\n\nclass Helper:\n    def run(self):\n        pass"
        assert parser.structural_similarity(code, code, 'python') > 0.9

    def test_non_python_fingerprint(self):
        parser = ASTParser()
        java = "public class Main { public static void main(String[] args) {} }"
        sim = parser.structural_similarity(java, java, 'java')
        assert 0 <= sim <= 1

    def test_refactoring_patterns(self):
        parser = ASTParser()
        code1 = "def add(a, b):\n    return a + b\nresult = add(1, 2)\nprint(result)"
        code2 = "def sum_values(x, y):\n    total = x + y\n    return total"
        patterns = parser.detect_refactoring_patterns(code1, code2)
        assert isinstance(patterns, list)

    def test_extract_variables_and_functions(self):
        tree = ast.parse("value = 10\ndef process(item):\n    return item")
        parser = ASTParser()
        assert 'value' in parser._extract_variables(tree)
        assert 'process' in parser._extract_function_names(tree)


# ---------------------------------------------------------------------------
# CodeMetricsCalculator
# ---------------------------------------------------------------------------

class TestCodeMetrics:
    def test_cyclomatic_python_with_branches(self):
        calc = CodeMetrics()
        code = "def f(x):\n    if x:\n        for i in range(3):\n            return i\n    return 0"
        assert calc.calculate_cyclomatic_complexity(code, 'python') >= 3

    def test_cyclomatic_generic_language(self):
        calc = CodeMetrics()
        code = "int f(int x) { if (x) { while (true) { return 1; } } return 0; }"
        assert calc.calculate_cyclomatic_complexity(code, 'c') >= 2

    def test_cyclomatic_syntax_error(self):
        calc = CodeMetrics()
        assert calc.calculate_cyclomatic_complexity("def f(:\nbad", 'python') >= 1

    def test_count_functions_python_and_generic(self):
        calc = CodeMetrics()
        assert calc.count_functions_methods("def a(): pass\ndef b(): pass", 'python') == 2
        assert calc.count_functions_methods("func doWork() {}", 'go') == 1

    def test_nesting_depth(self):
        calc = CodeMetrics()
        nested = "if a:\n    if b:\n        if c:\n            return 1"
        assert calc.calculate_nesting_depth(nested, 'python') >= 3

    def test_maintainability_range(self):
        calc = CodeMetrics()
        mi = calc.calculate_maintainability_index("x = 1\ny = 2", 'python')
        assert 0 <= mi <= 100

    def test_calculate_all_metrics_shape(self):
        calc = CodeMetrics()
        metrics = calc.calculate_all_metrics("def f():\n    return 1", 'python')
        assert 'loc' in metrics
        assert metrics['loc']['code'] == 2  # def + return
        assert metrics['cyclomatic_complexity'] >= 1
        assert metrics['function_count'] == 1

    def test_compare_metrics(self):
        calc = CodeMetrics()
        code1 = "def f():\n    return 1"
        code2 = "def f():\n    return 1\n\nx = 2\ny = 3"
        m1 = calc.calculate_all_metrics(code1, 'python')
        m2 = calc.calculate_all_metrics(code2, 'python')
        comparison = calc.compare_metrics(m1, m2)
        assert isinstance(comparison, dict)
        assert 'loc_similarity' in comparison

    def test_detect_anomalies(self):
        calc = CodeMetrics()
        anomalies = calc.detect_anomalies(0.95, {'loc_similarity': 0.1, 'cyclomatic_similarity': 0.9})
        assert isinstance(anomalies, list)


# ---------------------------------------------------------------------------
# PlagiarismPatternDetector — remaining branches
# ---------------------------------------------------------------------------

@pytest.fixture
def detector():
    return PlagiarismPatternDetector()


class TestPatternsBranches:
    def test_variable_renaming_generic_fallback(self, detector):
        # Non-Python code falls back to generic name matching
        result = detector.detect_variable_renaming("int a = 1;", "int b = 1;", 'c')
        assert isinstance(result, dict)
        assert 'detected' in result

    def test_dead_code_insertion_detected(self, detector):
        base = "def calc(a, b):\n    return a + b\ncalc(1, 2)"
        inflated = base + "\n" + base  # duplicated code = dead insertion
        result = detector.detect_dead_code_insertion(base, inflated)
        assert result['detected'] is True
        assert result['inserted_lines'] == 3

    def test_dead_code_insertion_not_detected(self, detector):
        base = "\n".join(f"x{i} = {i}" for i in range(10))
        result = detector.detect_dead_code_insertion(base, base)
        assert result['detected'] is False

    def test_remove_comments(self, detector):
        code = "x = 1  # trailing\n# whole line\ny = 2"
        cleaned = detector._remove_comments(code, 'python')
        assert '#' not in cleaned

    def test_classify_plagiarism_type(self, detector):
        pattern_analysis = {
            'variable_renaming': {'detected': True, 'variables_renamed': ['a', 'b']},
            'code_reordering': {'detected': False},
            'dead_code_insertion': {'detected': False},
        }
        classification = detector.classify_plagiarism_type(
            textual_similarity=0.5,
            ast_similarity=0.9,
            metrics_comparison={},
            pattern_analysis=pattern_analysis,
        )
        assert isinstance(classification, str)
        assert classification  # non-empty type name

    def test_comprehensive_analysis_shape(self, detector):
        from analyzer.metrics import CodeMetrics
        code1 = "def f(a, b):\n    return a * b + a\nfor i in range(3):\n    print(i)"
        code2 = "def g(x, y):\n    return x * y + x\nfor j in range(3):\n    print(j)"
        metrics_comp = CodeMetrics().compare_metrics(
            CodeMetrics().calculate_all_metrics(code1, 'python'),
            CodeMetrics().calculate_all_metrics(code2, 'python'),
        )
        analysis = detector.comprehensive_analysis(
            code1, code2, textual_sim=0.6, ast_sim=0.8, metrics_comp=metrics_comp)
        assert 'patterns' in analysis or isinstance(analysis, dict)


# ---------------------------------------------------------------------------
# core/file_handler — branches
# ---------------------------------------------------------------------------

class TestFileHandler:
    def test_extract_zip_ok(self, tmp_path):
        from core.file_handler import FileHandler
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('a.py', 'x = 1')
            zf.writestr('sub/b.py', 'y = 2')

        handler = FileHandler()
        files, contents, extract_path = handler.extract_zip(
            FakeUpload('src.zip', buf.getvalue()), 'python')
        assert len(files) == 2
        import shutil
        shutil.rmtree(extract_path, ignore_errors=True)

    def test_extract_zip_single_subdir(self, tmp_path):
        from core.file_handler import FileHandler
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('project/a.py', 'x = 1')
            zf.writestr('project/b.py', 'y = 2')
        handler = FileHandler()
        files, contents, extract_path = handler.extract_zip(
            FakeUpload('z.zip', buf.getvalue()), 'python')
        assert len(files) == 2
        import shutil
        shutil.rmtree(extract_path, ignore_errors=True)

    def test_extract_no_matching_files_raises(self, tmp_path):
        from core.file_handler import FileHandler
        from utils.exceptions import FileValidationError
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('note.txt', 'hello')
        with pytest.raises(FileValidationError):
            FileHandler().extract_zip(FakeUpload('z.zip', buf.getvalue()), 'python')

    def test_validate_rejects_path_traversal(self, tmp_path):
        from core.file_handler import FileHandler
        from utils.exceptions import FileValidationError
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('../evil.py', 'x = 1')
        with pytest.raises(FileValidationError):
            FileHandler().validate_zip_file(buf.getvalue(), 'evil.zip')

    def test_validate_rejects_absolute_path(self, tmp_path):
        from core.file_handler import FileHandler
        from utils.exceptions import FileValidationError
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('/etc/passwd.py', 'x = 1')
        with pytest.raises(FileValidationError):
            FileHandler().validate_zip_file(buf.getvalue(), 'abs.zip')

    def test_validate_rejects_corrupt(self, tmp_path):
        from core.file_handler import FileHandler
        from utils.exceptions import FileValidationError
        with pytest.raises(FileValidationError):
            FileHandler().validate_zip_file(b'PK\x03\x04not-a-real-zip', 'bad.zip')

    def test_extract_corrupt_zip_raises(self, tmp_path):
        from core.file_handler import FileHandler
        data = b'PK\x03\x04garbage-not-a-real-zip'
        with pytest.raises(Exception):
            FileHandler().extract_zip(FakeUpload('bad.zip', data), 'python')

    def test_extract_too_large_raises(self, tmp_path, monkeypatch):
        from core import file_handler as fhmod
        from utils.exceptions import FileValidationError
        monkeypatch.setattr(fhmod.config, 'MAX_ZIP_SIZE_MB', 0.000001)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('a.py', 'x = 1' * 1000)
        with pytest.raises(FileValidationError):
            fhmod.FileHandler().extract_zip(FakeUpload('big.zip', buf.getvalue()), 'python')

    def test_read_file_utf8(self, tmp_path):
        from core.file_handler import FileHandler
        f = tmp_path / 'code.py'
        f.write_text('x = 1', encoding='utf-8')
        assert FileHandler().read_file(str(f)) == 'x = 1'

    def test_get_extension_for_language(self, tmp_path):
        from core.file_handler import FileHandler
        handler = FileHandler()
        assert handler.get_extension_for_language('python') == 'py'
        assert handler.get_extension_for_language('c++') == 'cpp'


# ---------------------------------------------------------------------------
# AnalysisPipeline — cache + llm client properties
# ---------------------------------------------------------------------------

class TestPipelineProperties:
    def test_cache_property_without_use_cache(self):
        pipeline = AnalysisPipeline('python', use_cache=False)
        assert pipeline.cache is None

    def test_cache_setter(self):
        pipeline = AnalysisPipeline('python')
        sentinel = object()
        pipeline.cache = sentinel
        assert pipeline.cache is sentinel

    def test_llm_client_without_api_key(self):
        pipeline = AnalysisPipeline('python', api_key=None)
        assert pipeline.llm_client is None

    def test_llm_client_with_api_key(self):
        with patch('core.llm_client.MaritacaClient') as fake:
            pipeline = AnalysisPipeline('python', api_key='KEY123')
            client = pipeline.llm_client
            fake.assert_called_once_with(api_key='KEY123', model=pipeline.model)
            assert client is fake.return_value

    def test_file_handler_lazy(self):
        pipeline = AnalysisPipeline('python')
        assert pipeline._file_handler is None
        assert pipeline.file_handler is not None  # lazy init via property