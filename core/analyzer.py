"""
Main analysis orchestrator for Niklaus plagiarism detector.
"""

from typing import List, Dict, Any, Tuple, Optional, Callable
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

from analyzer import ASTParser, CodeMetrics, ClusterDetector, PlagiarismPatternDetector
from core.comparison import compare_files
from utils.parallel import ParallelComparator
from utils.exceptions import AnalysisError
from utils.logger import get_logger

logger = get_logger(__name__)


class PlagiarismAnalyzer:
    """Orchestrates all plagiarism analysis operations."""
    
    def __init__(self, language: str, max_workers: int = None):
        """
        Initialize analyzer.
        
        Args:
            language: Programming language
            max_workers: Maximum number of parallel workers
        """
        from utils.config import config
        
        self.language = language
        self.max_workers = max_workers or config.PARALLEL_WORKERS
        
        # Initialize analyzers
        self.ast_parser = ASTParser()
        self.metrics = CodeMetrics()
        self.cluster_detector = ClusterDetector()
        self.pattern_detector = PlagiarismPatternDetector()
        self.parallel = ParallelComparator(max_workers=self.max_workers)
        
        logger.info(f"Initialized PlagiarismAnalyzer for {language} with {self.max_workers} workers")
    
    def analyze_files(
        self,
        files: List[str],
        contents: List[str],
        threshold: float = 0.7,
        progress_callback: Callable[[int, int, str], None] = None
    ) -> Dict[str, Any]:
        """
        Perform complete analysis on file set.
        
        Args:
            files: List of filenames
            contents: List of file contents
            threshold: Similarity threshold
            progress_callback: Optional callback(completed, total, message)
        
        Returns:
            Complete analysis results
        
        Raises:
            AnalysisError: If analysis fails
        """
        try:
            logger.info(f"Starting analysis of {len(files)} files")
            
            # 1. Textual similarity (parallel)
            logger.info("Calculating textual similarities...")
            if progress_callback:
                progress_callback(0, len(files), "Calculando similaridade textual...")
            
            textual_sims = self._calculate_textual_similarities(
                files, contents, progress_callback
            )
            
            # 2. AST similarity (parallel)
            logger.info("Calculating AST similarities...")
            if progress_callback:
                progress_callback(0, len(files), "Calculando similaridade estrutural...")
            
            ast_sims = self._calculate_ast_similarities(
                files, contents, progress_callback
            )
            
            # 3. Code metrics (parallel)
            logger.info("Calculating code metrics...")
            if progress_callback:
                progress_callback(0, len(files), "Calculando métricas de código...")
            
            metrics = self._calculate_metrics(contents, progress_callback)
            
            # 4. Build similarity matrix
            logger.info("Building similarity matrix...")
            similarity_matrix = self._build_matrix(files, textual_sims)
            
            # 5. Cluster detection
            logger.info("Detecting clusters...")
            if progress_callback:
                progress_callback(0, 1, "Detectando clusters...")
            
            cluster_data = self.cluster_detector.analyze_clusters(
                similarity_matrix, files, min_similarity=threshold
            )
            
            # 6. Pattern detection for pairs above threshold
            logger.info("Detecting plagiarism patterns...")
            patterns = self._detect_patterns(
                files, contents, textual_sims, ast_sims, threshold
            )
            
            result = {
                'textual_similarities': textual_sims,
                'ast_similarities': ast_sims,
                'metrics': metrics,
                'similarity_matrix': similarity_matrix,
                'cluster_data': cluster_data,
                'patterns': patterns,
                'files': files,
                'language': self.language,
                'threshold': threshold
            }
            
            logger.info("Analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise AnalysisError(
                f"Failed to analyze files: {str(e)}",
                file1=files[0] if files else None,
                file2=files[1] if len(files) > 1 else None
            )
    
    def _calculate_textual_similarities(
        self,
        files: List[str],
        contents: List[str],
        progress_callback: Callable = None
    ) -> List[Tuple[str, str, float]]:
        """
        Calculate textual similarities in parallel.
        
        Args:
            files: List of filenames
            contents: List of file contents
            progress_callback: Optional progress callback
        
        Returns:
            List of (file1, file2, similarity) tuples
        """
        n = len(contents)
        total_pairs = n * (n - 1) // 2
        completed = 0
        
        results = []
        
        def compare_wrapper(content1, content2):
            return compare_files(content1, content2, self.language)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for i in range(n):
                for j in range(i + 1, n):
                    future = executor.submit(compare_wrapper, contents[i], contents[j])
                    futures[future] = (i, j)
            
            for future in as_completed(futures):
                i, j = futures[future]
                try:
                    similarity = future.result()
                    results.append((files[i], files[j], similarity))
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(completed, total_pairs, f"Comparando {files[i]} vs {files[j]}")
                        
                except Exception as e:
                    logger.error(f"Error comparing {files[i]} and {files[j]}: {e}")
                    results.append((files[i], files[j], 0.0))
        
        return results
    
    def _calculate_ast_similarities(
        self,
        files: List[str],
        contents: List[str],
        progress_callback: Callable = None
    ) -> List[Tuple[str, str, float]]:
        """
        Calculate AST similarities in parallel.
        
        Args:
            files: List of filenames
            contents: List of file contents
            progress_callback: Optional progress callback
        
        Returns:
            List of (file1, file2, similarity) tuples
        """
        n = len(contents)
        total_pairs = n * (n - 1) // 2
        completed = 0
        
        results = []
        
        def ast_compare(content1, content2):
            return self.ast_parser.structural_similarity(content1, content2, self.language.lower())
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for i in range(n):
                for j in range(i + 1, n):
                    future = executor.submit(ast_compare, contents[i], contents[j])
                    futures[future] = (i, j)
            
            for future in as_completed(futures):
                i, j = futures[future]
                try:
                    similarity = future.result()
                    results.append((files[i], files[j], similarity))
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(completed, total_pairs, f"AST {files[i]} vs {files[j]}")
                        
                except Exception as e:
                    logger.error(f"Error in AST comparison {files[i]} and {files[j]}: {e}")
                    results.append((files[i], files[j], 0.0))
        
        return results
    
    def _calculate_metrics(
        self,
        contents: List[str],
        progress_callback: Callable = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate code metrics for each file in parallel.
        
        Args:
            contents: List of file contents
            progress_callback: Optional progress callback
        
        Returns:
            List of metric dictionaries
        """
        total = len(contents)
        completed = 0
        
        def calculate_single_metrics(content: str) -> Dict[str, Any]:
            metrics = self.metrics.calculate_all_metrics(content, self.language.lower())
            return {
                'loc': metrics['loc']['code'],
                'cyclomatic': metrics['cyclomatic_complexity'],
                'functions': metrics['function_count'],
                'nesting': metrics['max_nesting_depth'],
                'maintainability': metrics['maintainability_index']
            }
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(calculate_single_metrics, content): i
                for i, content in enumerate(contents)
            }
            
            for future in as_completed(futures):
                i = futures[future]
                try:
                    metrics = future.result()
                    results.append((i, metrics))
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(completed, total, f"Métricas arquivo {i+1}")
                        
                except Exception as e:
                    logger.error(f"Error calculating metrics for file {i}: {e}")
                    results.append((i, {}))
        
        # Sort by original order
        results.sort(key=lambda x: x[0])
        return [metrics for _, metrics in results]
    
    def _build_matrix(
        self,
        files: List[str],
        similarities: List[Tuple[str, str, float]]
    ) -> np.ndarray:
        """
        Build similarity matrix from similarity list.
        
        Args:
            files: List of filenames
            similarities: List of (file1, file2, similarity) tuples
        
        Returns:
            NxN similarity matrix
        """
        n = len(files)
        matrix = np.eye(n)  # Diagonal is 1.0
        
        # Create file index mapping
        file_idx = {f: i for i, f in enumerate(files)}
        
        for file1, file2, sim in similarities:
            i = file_idx.get(file1)
            j = file_idx.get(file2)
            
            if i is not None and j is not None:
                matrix[i, j] = sim
                matrix[j, i] = sim
        
        return matrix
    
    def _detect_patterns(
        self,
        files: List[str],
        contents: List[str],
        textual_sims: List[Tuple[str, str, float]],
        ast_sims: List[Tuple[str, str, float]],
        threshold: float
    ) -> Dict[str, Dict[str, Any]]:
        """
        Detect plagiarism patterns for pairs above threshold.
        
        Args:
            files: List of filenames
            contents: List of file contents
            textual_sims: Textual similarities
            ast_sims: AST similarities
            threshold: Similarity threshold
        
        Returns:
            Dictionary mapping "file1_file2" to pattern analysis
        """
        patterns = {}
        
        # Create lookup for AST similarities
        ast_sim_map = {
            (f1, f2): sim for f1, f2, sim in ast_sims
        }
        
        for file1, file2, textual_sim in textual_sims:
            if textual_sim < threshold:
                continue
            
            try:
                # Get file indices
                idx1 = files.index(file1)
                idx2 = files.index(file2)
                
                # Get AST similarity
                ast_sim = ast_sim_map.get((file1, file2), 
                                          ast_sim_map.get((file2, file1), 0.0))
                
                # Calculate metrics comparison
                metrics1 = self.metrics.calculate_all_metrics(
                    contents[idx1], self.language.lower()
                )
                metrics2 = self.metrics.calculate_all_metrics(
                    contents[idx2], self.language.lower()
                )
                metrics_comp = self.metrics.compare_metrics(metrics1, metrics2)
                
                # Pattern detection
                pattern = self.pattern_detector.comprehensive_analysis(
                    contents[idx1],
                    contents[idx2],
                    textual_sim,
                    ast_sim,
                    metrics_comp
                )
                
                patterns[f"{file1}_{file2}"] = pattern
                
            except Exception as e:
                logger.error(f"Pattern detection failed for {file1} vs {file2}: {e}")
        
        return patterns
    
    def get_suspicious_pairs(
        self,
        textual_sims: List[Tuple[str, str, float]],
        threshold: float
    ) -> List[Tuple[str, str, float]]:
        """
        Get pairs with similarity above threshold.
        
        Args:
            textual_sims: List of similarities
            threshold: Similarity threshold
        
        Returns:
            List of suspicious pairs sorted by similarity
        """
        suspicious = [
            (f1, f2, sim) 
            for f1, f2, sim in textual_sims 
            if sim >= threshold
        ]
        
        # Sort by similarity descending
        suspicious.sort(key=lambda x: x[2], reverse=True)
        
        return suspicious