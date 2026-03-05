"""
Test utilities module.
"""

import pytest
from utils.config import Config, config
from utils.exceptions import (
    NiklausError,
    FileValidationError,
    ZipExtractionError,
    MaritacaAPIError,
    AnalysisError,
    CacheError
)
from utils.logger import get_logger


class TestConfig:
    """Test configuration module."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        assert config.MARITACA_MODEL == "sabiazinho-4"
        assert config.MARITACA_TIMEOUT == 30
        assert config.MAX_ZIP_SIZE_MB == 50
        assert config.PARALLEL_WORKERS == 4
        assert config.DEFAULT_THRESHOLD == 0.7
    
    def test_config_from_env(self):
        """Test configuration from environment variables."""
        import os
        os.environ['PARALLEL_WORKERS'] = '8'
        
        custom_config = Config.from_env()
        assert custom_config.PARALLEL_WORKERS == 8
        
        # Clean up
        del os.environ['PARALLEL_WORKERS']
    
    def test_language_extensions(self):
        """Test language extensions mapping."""
        assert config.LANGUAGE_EXTENSIONS is not None
        assert config.LANGUAGE_EXTENSIONS['Python'] == 'py'
        assert config.LANGUAGE_EXTENSIONS['JavaScript'] == 'js'
        assert len(config.LANGUAGE_EXTENSIONS) == 9


class TestExceptions:
    """Test custom exceptions."""
    
    def test_base_exception(self):
        """Test base NiklausError exception."""
        with pytest.raises(NiklausError):
            raise NiklausError("Test error")
    
    def test_file_validation_error(self):
        """Test FileValidationError with filename."""
        error = FileValidationError("Invalid file", filename="test.py")
        assert error.filename == "test.py"
        assert "Invalid file" in str(error)
    
    def test_maritaca_api_error(self):
        """Test MaritacaAPIError with status code."""
        error = MaritacaAPIError("API failed", status_code=500)
        assert error.status_code == 500
        assert "API failed" in str(error)
    
    def test_analysis_error(self):
        """Test AnalysisError with files."""
        error = AnalysisError("Analysis failed", file1="a.py", file2="b.py")
        assert error.file1 == "a.py"
        assert error.file2 == "b.py"


class TestLogger:
    """Test logging module."""
    
    def test_get_logger(self):
        """Test logger creation."""
        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"
    
    def test_logger_with_file(self, tmp_path):
        """Test logger with file output."""
        log_file = tmp_path / "test.log"
        logger = get_logger("test_file", log_file=str(log_file))
        
        logger.info("Test message")
        
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content


class TestComparison:
    """Test comparison utilities."""
    
    def test_remove_comments_python(self):
        """Test removing Python comments."""
        from core.comparison import remove_blank_spaces_and_comments
        
        code = '''# Comment
def foo():
    """Docstring"""
    return 42  # inline
'''
        result = remove_blank_spaces_and_comments(code, 'python')
        assert '#' not in result
        assert '"""' not in result
    
    def test_remove_comments_c(self):
        """Test removing C-style comments."""
        from core.comparison import remove_blank_spaces_and_comments
        
        code = '''/* multi
line comment */
int x = 5; // inline
'''
        result = remove_blank_spaces_and_comments(code, 'c')
        assert '/*' not in result
        assert '// inline' not in result
    
    def test_calculate_similarity_identical(self):
        """Test similarity of identical code."""
        from core.comparison import calculate_similarity
        
        code = "def foo(): return 42"
        similarity = calculate_similarity(code, code)
        
        assert similarity >= 0.99
    
    def test_calculate_similarity_different(self):
        """Test similarity of different code."""
        from core.comparison import calculate_similarity
        
        code1 = "def foo(): return 42"
        code2 = "def bar(): print('hello')"
        similarity = calculate_similarity(code1, code2)
        
        assert similarity < 0.5
    
    def test_compare_files(self):
        """Test file comparison."""
        from core.comparison import compare_files
        
        code1 = "def add(a, b): return a + b"
        code2 = "def add(x, y): return x + y"
        
        similarity = compare_files(code1, code2, 'python')
        assert similarity > 0.7  # Should be similar despite variable renaming


class TestFileHandler:
    """Test file handler module."""
    
    def test_get_extension_for_language(self):
        """Test language to extension mapping."""
        from core.file_handler import FileHandler
        
        handler = FileHandler()
        
        assert handler.get_extension_for_language('Python') == 'py'
        assert handler.get_extension_for_language('JavaScript') == 'js'
    
    def test_detect_language_from_extension(self):
        """Test extension to language mapping."""
        from core.file_handler import FileHandler
        
        handler = FileHandler()
        
        assert handler.detect_language_from_extension('.py') == 'Python'
        assert handler.detect_language_from_extension('js') == 'JavaScript'
    
    def test_unsupported_language(self):
        """Test unsupported language error."""
        from core.file_handler import FileHandler
        from utils.exceptions import LanguageDetectionError
        
        handler = FileHandler()
        
        with pytest.raises(LanguageDetectionError):
            handler.get_extension_for_language('UnsupportedLang')
    
    def test_validate_zip_size(self, tmp_path):
        """Test ZIP file size validation."""
        from core.file_handler import FileHandler
        from utils.exceptions import FileValidationError
        
        handler = FileHandler(max_size_mb=1)  # 1MB limit
        
        # Create a small valid ZIP
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('test.py', 'print("hello")')
        
        zip_bytes = zip_buffer.getvalue()
        
        # Should not raise for valid ZIP
        handler.validate_zip_file(zip_bytes, 'test.zip')
    
    def test_get_file_stats(self):
        """Test file statistics calculation."""
        from core.file_handler import FileHandler
        
        handler = FileHandler()
        
        files = ['a.py', 'b.py']
        contents = ['line1\nline2\nline3', 'line1\nline2']
        
        stats = handler.get_file_stats(files, contents)
        
        assert stats['file_count'] == 2
        assert stats['total_lines'] == 5
        assert stats['avg_lines'] == 2.5


class TestPersistence:
    """Test persistence module."""
    
    def test_analysis_cache_save_load(self, tmp_path):
        """Test cache save and load."""
        from core.persistence import AnalysisCache
        
        cache = AnalysisCache(cache_dir=str(tmp_path))
        
        files = ['a.py', 'b.py']
        data = {'test': 'data', 'value': 42}
        
        # Save
        cache_path = cache.save(files, threshold=0.7, analysis_data=data)
        assert cache_path.exists()
        
        # Load
        loaded = cache.load(files, threshold=0.7)
        assert loaded == data
    
    def test_analysis_cache_expired(self, tmp_path):
        """Test cache expiry."""
        from core.persistence import AnalysisCache
        
        cache = AnalysisCache(cache_dir=str(tmp_path))
        
        files = ['a.py']
        data = {'test': 'data'}
        
        cache.save(files, threshold=0.7, analysis_data=data)
        
        # Load with 0 hour expiry (immediate expiry)
        loaded = cache.load(files, threshold=0.7, max_age_hours=0)
        
        assert loaded is None
    
    def test_cache_clear(self, tmp_path):
        """Test cache clearing."""
        from core.persistence import AnalysisCache
        
        cache = AnalysisCache(cache_dir=str(tmp_path))
        
        files = ['a.py']
        data = {'test': 'data'}
        
        cache.save(files, threshold=0.7, analysis_data=data)
        
        removed = cache.clear_all_cache()
        assert removed == 1

    def test_analysis_cache_uses_content_signature(self, tmp_path):
        """Cache key must differ for same filenames with different content."""
        from core.persistence import AnalysisCache

        cache = AnalysisCache(cache_dir=str(tmp_path))

        files = ['a.py', 'b.py']
        contents_v1 = ['print(1)', 'print(2)']
        contents_v2 = ['print(10)', 'print(20)']

        cache.save(files, threshold=0.7, analysis_data={'version': 1}, contents=contents_v1, language='Python')

        loaded_v1 = cache.load(files, threshold=0.7, contents=contents_v1, language='Python')
        loaded_v2 = cache.load(files, threshold=0.7, contents=contents_v2, language='Python')

        assert loaded_v1 == {'version': 1}
        assert loaded_v2 is None
    
    def test_session_manager(self, tmp_path):
        """Test session manager."""
        from core.persistence import SessionManager
        
        session_file = tmp_path / "session.json"
        manager = SessionManager(session_file=str(session_file))
        
        data = {'user': 'test', 'settings': {'theme': 'dark'}}
        
        # Save
        manager.save_session(data)
        assert session_file.exists()
        
        # Load
        loaded = manager.load_session()
        assert loaded['user'] == 'test'
        
        # Clear
        manager.clear_session()
        assert not session_file.exists()


class TestParallel:
    """Test parallel processing module."""
    
    def test_compare_all_pairs(self):
        """Test parallel pair comparison."""
        from utils.parallel import ParallelComparator
        
        comparator = ParallelComparator(max_workers=2)
        
        contents = ["abc", "abd", "xyz"]
        
        def simple_compare(c1, c2):
            # Dummy comparison based on character overlap
            return len(set(c1) & set(c2)) / max(len(set(c1)), len(set(c2)))
        
        results = comparator.compare_all_pairs(contents, simple_compare)
        
        # Should have 3 pairs (3 choose 2)
        assert len(results) == 3
        
        # Each result should be (i, j, similarity)
        for i, j, sim in results:
            assert 0 <= i < len(contents)
            assert 0 <= j < len(contents)
            assert 0.0 <= sim <= 1.0
    
    def test_map_parallel(self):
        """Test parallel mapping."""
        from utils.parallel import ParallelComparator
        
        comparator = ParallelComparator(max_workers=2)
        
        items = [1, 2, 3, 4, 5]
        
        def double(x):
            return x * 2
        
        results = comparator.map_parallel(double, items)
        
        assert results == [2, 4, 6, 8, 10]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
