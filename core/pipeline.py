"""
Integration layer to connect new modular architecture with legacy app.py.
This provides a smooth transition path while maintaining backward compatibility.
"""

from typing import List, Dict, Any, Callable, Optional, Tuple
import time
import numpy as np

from utils.lazy_loader import LazyModule
from utils.performance import track_performance, PerformanceContext, get_performance_metrics
from utils.config import config
from utils.logger import get_logger
from utils.exceptions import NiklausError, FileValidationError, AnalysisCancelledError

logger = get_logger(__name__)

analyzer_module = LazyModule('core.analyzer')
file_handler_module = LazyModule('core.file_handler')
llm_module = LazyModule('core.llm_client')
persistence_module = LazyModule('core.persistence')
comparison_module = LazyModule('core.comparison')


class AnalysisPipeline:
    """
    Unified analysis pipeline that coordinates all analysis steps.
    Provides both parallel execution and progress tracking.
    """
    
    def __init__(
        self,
        language: str,
        api_key: Optional[str] = None,
        model: str = None,
        max_workers: int = None,
        use_cache: bool = True
    ):
        """
        Initialize analysis pipeline.
        
        Args:
            language: Programming language
            api_key: Maritaca API key (optional if only doing textual analysis)
            model: Maritaca model name
            max_workers: Number of parallel workers
            use_cache: Whether to use disk cache
        """
        self.language = language
        self.api_key = api_key
        self.model = model or config.MARITACA_MODEL
        self.max_workers = max_workers or config.PARALLEL_WORKERS
        self.use_cache = use_cache
        
        self._analyzer = None
        self._file_handler = None
        self._cache = None
        self._llm_client = None
        
        logger.info(f"Initialized AnalysisPipeline for {language} with {self.max_workers} workers")
    
    @property
    def analyzer(self):
        if self._analyzer is None:
            PlagiarismAnalyzer = analyzer_module.PlagiarismAnalyzer
            self._analyzer = PlagiarismAnalyzer(self.language, self.max_workers)
        return self._analyzer
    
    @property
    def file_handler(self):
        if self._file_handler is None:
            FileHandler = file_handler_module.FileHandler
            self._file_handler = FileHandler()
        return self._file_handler
    
    @property
    def cache(self):
        if self._cache is None and self.use_cache:
            AnalysisCache = persistence_module.AnalysisCache
            self._cache = AnalysisCache()
        return self._cache

    @cache.setter
    def cache(self, value):
        self._cache = value
    
    @property
    def llm_client(self):
        if self._llm_client is None and self.api_key:
            MaritacaClient = llm_module.MaritacaClient
            self._llm_client = MaritacaClient(
                api_key=self.api_key,
                model=self.model
            )
        return self._llm_client
    
    @track_performance('pipeline.run_full_analysis')
    def run_full_analysis(
        self,
        files: List[str],
        contents: List[str],
        threshold: float = 0.7,
        enable_ai: bool = True,
        progress_callback: Callable[[str, int, int], None] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Run complete plagiarism analysis pipeline.
        
        Args:
            files: List of filenames
            contents: List of file contents
            threshold: Similarity threshold
            enable_ai: Whether to run AI analysis
            progress_callback: Callback(stage, current, total)
        
        Returns:
            Complete analysis results
        
        Raises:
            NiklausError: If analysis fails
        """
        start_time = time.time()
        logger.info(f"Starting full analysis of {len(files)} files")
        
        try:
            self._raise_if_cancelled(cancel_check)
            # Check cache first
            if self.cache:
                cached = self.cache.load(files, threshold, contents=contents, language=self.language)
                if cached:
                    logger.info("Analysis loaded from cache")
                    if progress_callback:
                        progress_callback("cache", 1, 1)
                    return cached
            
            # Stage 1: Core analysis (textual + AST + metrics + clustering)
            if progress_callback:
                progress_callback("analysis", 0, 4)
            
            def analysis_progress(current, total, message=""):
                if progress_callback:
                    progress_callback("analysis", current, total)
            
            results = self.analyzer.analyze_files(
                files, contents, threshold, 
                progress_callback=analysis_progress,
                cancel_check=cancel_check
            )
            self._raise_if_cancelled(cancel_check)
            
            if progress_callback:
                progress_callback("analysis", 1, 4)
            
            # Stage 2: Build similarity matrix
            if progress_callback:
                progress_callback("matrix", 0, 1)
            
            similarity_matrix = results['similarity_matrix']
            
            if progress_callback:
                progress_callback("matrix", 1, 1)
            
            # Stage 3: Get suspicious pairs
            suspicious_pairs = self.analyzer.get_suspicious_pairs(
                results['textual_similarities'], 
                threshold
            )
            self._raise_if_cancelled(cancel_check)
            
            # Calculate similarity statistics
            textual_sims = results['textual_similarities']
            if textual_sims:
                similarities = [sim for _, _, sim in textual_sims]
                avg_similarity = sum(similarities) / len(similarities)
                max_similarity = max(similarities)
            else:
                avg_similarity = 0.0
                max_similarity = 0.0
            
            # Convert suspicious_pairs to pairwise_results format
            pairwise_results = [
                {
                    'file1': file1,
                    'file2': file2,
                    'similarity': sim,
                    'is_suspicious': sim >= threshold
                }
                for file1, file2, sim in textual_sims
            ]
            
            # Stage 4: AI analysis (if enabled and API key provided)
            ai_analyses = {}
            if enable_ai and self.llm_client and suspicious_pairs:
                if progress_callback:
                    progress_callback("ai", 0, len(suspicious_pairs))
                
                ai_analyses = self._run_ai_analysis(
                    files, contents, suspicious_pairs, results,
                    progress_callback,
                    cancel_check=cancel_check
                )
                
                if progress_callback:
                    progress_callback("ai", len(suspicious_pairs), len(suspicious_pairs))
            
            # Compile final results
            final_results = {
                'files': files,
                'files_content': contents,
                'language': self.language,
                'threshold': threshold,
                'textual_similarities': results['textual_similarities'],
                'ast_similarities': results['ast_similarities'],
                'metrics': results['metrics'],
                'similarity_matrix': similarity_matrix.tolist(),  # Convert numpy to list
                'cluster_data': results['cluster_data'],
                'patterns': results['patterns'],
                'ai_analyses': ai_analyses,
                'suspicious_pairs': suspicious_pairs,
                'pairwise_results': pairwise_results,
                'average_similarity': avg_similarity,
                'max_similarity': max_similarity,
                'analysis_time': time.time() - start_time
            }
            
            # Save to cache
            if self.cache:
                self.cache.save(files, threshold, final_results, contents=contents, language=self.language)
            
            logger.info(f"Analysis completed in {final_results['analysis_time']:.2f}s")
            return final_results
        except AnalysisCancelledError:
            logger.info("Analysis cancelled by user")
            raise
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise NiklausError(f"Analysis pipeline failed: {str(e)}")

    @staticmethod
    def _raise_if_cancelled(cancel_check: Optional[Callable[[], bool]]) -> None:
        if cancel_check and cancel_check():
            raise AnalysisCancelledError("Analysis cancelled by user")
    
    def _run_ai_analysis(
        self,
        files: List[str],
        contents: List[str],
        suspicious_pairs: List[Tuple[str, str, float]],
        analysis_results: Dict,
        progress_callback: Callable = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Dict[str, str]:
        """
        Run AI analysis for suspicious pairs in parallel.
        
        Args:
            files: List of filenames
            contents: List of file contents
            suspicious_pairs: List of (file1, file2, similarity) tuples
            analysis_results: Results from core analysis
            progress_callback: Progress callback
        
        Returns:
            Dictionary mapping "file1_file2" to AI analysis
        """
        ai_analyses = {}
        completed = 0

        file_to_idx = {f: i for i, f in enumerate(files)}
        
        # Create lookup for AST similarities
        ast_sim_map = {
            (f1, f2): sim for f1, f2, sim in analysis_results['ast_similarities']
        }
        
        # Create lookup for patterns
        patterns_map = analysis_results.get('patterns', {})
        
        for file1, file2, textual_sim in suspicious_pairs:
            self._raise_if_cancelled(cancel_check)
            try:
                # Get indices
                idx1 = file_to_idx[file1]
                idx2 = file_to_idx[file2]
                
                # Get AST similarity
                ast_sim = ast_sim_map.get(
                    (file1, file2), 
                    ast_sim_map.get((file2, file1), 0.0)
                )
                
                # Get pattern
                pattern_key = f"{file1}_{file2}"
                pattern = patterns_map.get(pattern_key, {})
                
                plagiarism_type = pattern.get('plagiarism_type', 'UNKNOWN')
                confidence = pattern.get('confidence', 0.5)
                
                # Call Maritaca API
                analysis = self.llm_client.analyze_plagiarism(
                    code1=contents[idx1],
                    code2=contents[idx2],
                    file1=file1,
                    file2=file2,
                    textual_similarity=textual_sim,
                    ast_similarity=ast_sim,
                    plagiarism_type=plagiarism_type,
                    confidence=confidence
                )
                
                ai_analyses[pattern_key] = analysis
                completed += 1
                
                if progress_callback:
                    progress_callback("ai", completed, len(suspicious_pairs))
                
            except Exception as e:
                logger.error(f"AI analysis failed for {file1} vs {file2}: {e}")
                ai_analyses[f"{file1}_{file2}"] = f"Error: {str(e)}"
        
        return ai_analyses
    
    def run_textual_only(
        self,
        files: List[str],
        contents: List[str],
        threshold: float = 0.7,
        progress_callback: Callable = None
    ) -> Dict[str, Any]:
        """
        Run textual analysis only (no AST, metrics, or AI).
        Fastest option for basic similarity detection.
        
        Args:
            files: List of filenames
            contents: List of file contents
            threshold: Similarity threshold
            progress_callback: Progress callback
        
        Returns:
            Basic analysis results
        """
        logger.info(f"Running textual-only analysis for {len(files)} files")
        
        # Calculate textual similarities in parallel
        textual_sims = self.analyzer._calculate_textual_similarities(
            files, contents, progress_callback
        )
        
        # Build matrix
        similarity_matrix = self.analyzer._build_matrix(files, textual_sims)
        
        # Get suspicious pairs
        suspicious_pairs = self.analyzer.get_suspicious_pairs(textual_sims, threshold)
        
        return {
            'files': files,
            'textual_similarities': textual_sims,
            'similarity_matrix': similarity_matrix.tolist(),
            'suspicious_pairs': suspicious_pairs,
            'threshold': threshold
        }
    
    def get_performance_stats(self, file_count: int) -> Dict[str, Any]:
        """
        Estimate performance metrics for given file count.
        
        Args:
            file_count: Number of files to analyze
        
        Returns:
            Performance estimates
        """
        # Number of comparisons
        comparisons = file_count * (file_count - 1) // 2
        
        # Estimated times (based on benchmarks)
        # - Textual comparison: ~5ms per pair
        # - AST parsing: ~20ms per pair  
        # - Metrics: ~10ms per file
        # - AI analysis: ~2s per pair
        
        textual_time = comparisons * 0.005 / self.max_workers
        ast_time = comparisons * 0.020 / self.max_workers
        metrics_time = file_count * 0.010 / self.max_workers
        
        # Serial operations
        matrix_time = comparisons * 0.001
        cluster_time = file_count * 0.001
        
        return {
            'files': file_count,
            'comparisons': comparisons,
            'estimated_textual_time': textual_time,
            'estimated_ast_time': ast_time,
            'estimated_metrics_time': metrics_time,
            'estimated_total_time': textual_time + ast_time + metrics_time + matrix_time + cluster_time,
            'parallel_workers': self.max_workers,
            'speedup_factor': self.max_workers
        }


class LegacyAdapter:
    """
    Adapter to make new modular architecture compatible with legacy app.py.
    Provides drop-in replacement for existing functions.
    """
    
    @staticmethod
    def extract_zip(zip_file, language: str):
        """
        Drop-in replacement for legacy ZIP extraction.
        
        Args:
            zip_file: Streamlit UploadedFile
            language: Programming language
        
        Returns:
            Tuple of (files, contents, extract_path)
        """
        file_handler_cls = file_handler_module.FileHandler
        handler = file_handler_cls()
        return handler.extract_zip(zip_file, language)
    
    @staticmethod
    def comparate_files(code1: str, code2: str, language: str = 'python') -> float:
        """
        Drop-in replacement for legacy file comparison.
        
        Args:
            code1: First code
            code2: Second code
            language: Programming language
        
        Returns:
            Similarity score
        """
        compare_files_fn = comparison_module.compare_files
        return compare_files_fn(code1, code2, language)
    
    @staticmethod
    def create_similarity_matrix(
        files: List[str],
        textual_sims: List[Tuple[str, str, float]]
    ) -> List[List[float]]:
        """
        Convert textual similarities to matrix format.
        
        Args:
            files: List of filenames
            textual_sims: List of (file1, file2, similarity) tuples
        
        Returns:
            2D similarity matrix
        """
        from core.analyzer import PlagiarismAnalyzer
        analyzer = PlagiarismAnalyzer('python', max_workers=1)
        return analyzer._build_matrix(files, textual_sims).tolist()


def compare_performance(file_counts: List[int] = [10, 20, 50, 100]) -> Dict[str, Any]:
    """
    Compare sequential vs parallel performance estimates.
    
    Args:
        file_counts: List of file counts to benchmark
    
    Returns:
        Performance comparison data
    """
    results = []
    
    for count in file_counts:
        # Sequential (workers=1)
        pipeline_seq = AnalysisPipeline('python', max_workers=1)
        stats_seq = pipeline_seq.get_performance_stats(count)
        
        # Parallel (workers=4)
        pipeline_par = AnalysisPipeline('python', max_workers=4)
        stats_par = pipeline_par.get_performance_stats(count)
        
        results.append({
            'files': count,
            'comparisons': stats_seq['comparisons'],
            'sequential_time': stats_seq['estimated_total_time'],
            'parallel_time': stats_par['estimated_total_time'],
            'speedup': stats_seq['estimated_total_time'] / stats_par['estimated_total_time']
        })
    
    return {
        'comparison': results,
        'speedup_avg': sum(r['speedup'] for r in results) / len(results)
    }
