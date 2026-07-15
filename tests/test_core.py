"""
Test core modules.
"""

import pytest
import numpy as np


class TestPlagiarismAnalyzer:
    """Test main analyzer class."""
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        from core.analyzer import PlagiarismAnalyzer
        
        analyzer = PlagiarismAnalyzer(language='python', max_workers=2)
        
        assert analyzer.language == 'python'
        assert analyzer.max_workers == 2
        assert analyzer.ast_parser is not None
        assert analyzer.metrics is not None
    
    def test_build_matrix(self):
        """Test similarity matrix building."""
        from core.analyzer import PlagiarismAnalyzer
        
        analyzer = PlagiarismAnalyzer(language='python', max_workers=1)
        
        files = ['a.py', 'b.py', 'c.py']
        similarities = [
            ('a.py', 'b.py', 0.9),
            ('a.py', 'c.py', 0.3),
            ('b.py', 'c.py', 0.5)
        ]
        
        matrix = analyzer._build_matrix(files, similarities)
        
        assert matrix.shape == (3, 3)
        assert matrix[0, 0] == 1.0  # Diagonal
        assert matrix[0, 1] == 0.9
        assert matrix[1, 0] == 0.9  # Symmetric
        assert matrix[0, 2] == 0.3
    
    def test_get_suspicious_pairs(self):
        """Test filtering suspicious pairs."""
        from core.analyzer import PlagiarismAnalyzer
        
        analyzer = PlagiarismAnalyzer(language='python', max_workers=1)
        
        similarities = [
            ('a.py', 'b.py', 0.95),
            ('a.py', 'c.py', 0.6),
            ('b.py', 'c.py', 0.3)
        ]
        
        # With threshold 0.7
        suspicious = analyzer.get_suspicious_pairs(similarities, threshold=0.7)
        
        assert len(suspicious) == 1
        assert suspicious[0] == ('a.py', 'b.py', 0.95)
        
        # With threshold 0.5
        suspicious = analyzer.get_suspicious_pairs(similarities, threshold=0.5)
        
        assert len(suspicious) == 2


class TestMaritacaClient:
    """Test Maritaca API client."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        from core.llm_client import MaritacaClient
        
        client = MaritacaClient(
            api_key="test-key",
            model="sabiazinho-4",
            timeout=10
        )
        
        assert client.model == "sabiazinho-4"
        assert client.max_retries == 3
        assert client.rate_limiter is not None
    
    def test_system_prompt(self):
        """Test system prompt generation."""
        from core.llm_client import MaritacaClient
        
        client = MaritacaClient(api_key="test-key")
        prompt = client._get_system_prompt()
        
        assert "Niklaus" in prompt
        assert "plágio" in prompt.lower()
    
    def test_user_prompt_building(self):
        """Test user prompt building."""
        from core.llm_client import MaritacaClient
        
        client = MaritacaClient(api_key="test-key")
        prompt = client._build_user_prompt(
            code1="def foo(): pass",
            code2="def bar(): pass",
            file1="a.py",
            file2="b.py",
            textual_similarity=0.8,
            ast_similarity=0.9,
            plagiarism_type="COPIA_DIRETA",
            confidence=0.95
        )
        
        assert "a.py" in prompt
        assert "b.py" in prompt
        assert "80.0%" in prompt  # 0.8 formatted
        assert "90.0%" in prompt  # 0.9 formatted
        assert "COPIA_DIRETA" in prompt


class TestRateLimiter:
    """Test rate limiter."""

    @pytest.mark.slow
    def test_rate_limiter_basic(self):
        """Test basic rate limiting (slow: sleeps ~1s)."""
        from core.llm_client import RateLimiter
        
        limiter = RateLimiter(calls_per_minute=60)  # 1 call per second
        
        import time
        start = time.time()
        
        # Should allow immediate first call
        limiter.wait()
        elapsed1 = time.time() - start
        assert elapsed1 < 0.1
        
        # Second call should wait
        limiter.wait()
        elapsed2 = time.time() - start
        assert elapsed2 >= 0.9  # Should have waited ~1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])