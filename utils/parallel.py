"""
Parallel processing utilities for Niklaus plagiarism detector.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Any, Tuple
import time

from utils.exceptions import ParallelProcessingError
from utils.logger import get_logger

logger = get_logger(__name__)


class ParallelComparator:
    """Execute comparisons in parallel using ThreadPoolExecutor."""
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize parallel comparator.
        
        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers
    
    def compare_all_pairs(
        self,
        contents: List[str],
        compare_func: Callable[[str, str], float],
        progress_callback: Callable[[int, int], None] = None
    ) -> List[Tuple[int, int, float]]:
        """
        Compare all pairs of files in parallel.
        
        Args:
            contents: List of file contents
            compare_func: Function that takes (content1, content2) and returns similarity
            progress_callback: Optional callback(completed, total)
        
        Returns:
            List of (i, j, similarity) tuples
        
        Raises:
            ParallelProcessingError: If processing fails
        """
        n = len(contents)
        total_pairs = n * (n - 1) // 2
        results = []
        completed = 0
        
        logger.info(f"Starting parallel comparison of {total_pairs} pairs with {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            # Submit all tasks
            for i in range(n):
                for j in range(i + 1, n):
                    future = executor.submit(compare_func, contents[i], contents[j])
                    futures[future] = (i, j)
            
            # Collect results
            for future in as_completed(futures):
                i, j = futures[future]
                try:
                    similarity = future.result()
                    results.append((i, j, similarity))
                    completed += 1
                    
                    if progress_callback and completed % 10 == 0:
                        progress_callback(completed, total_pairs)
                        
                except Exception as e:
                    logger.error(f"Comparison failed for pair ({i}, {j}): {e}")
                    # Add zero similarity for failed comparisons
                    results.append((i, j, 0.0))
        
        logger.info(f"Parallel comparison completed: {completed}/{total_pairs} pairs")
        return results
    
    def analyze_parallel(
        self,
        tasks: List[Tuple[Callable, tuple]],
        progress_callback: Callable[[int, int], None] = None
    ) -> List[Any]:
        """
        Execute arbitrary tasks in parallel.
        
        Args:
            tasks: List of (function, args_tuple)
            progress_callback: Optional callback(completed, total)
        
        Returns:
            List of results in order
        
        Raises:
            ParallelProcessingError: If any task fails
        """
        total = len(tasks)
        completed = 0
        results = [None] * total
        
        logger.info(f"Starting parallel execution of {total} tasks")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(func, *args): idx
                for idx, (func, args) in enumerate(tasks)
            }
            
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                    completed += 1
                    
                    if progress_callback and completed % 10 == 0:
                        progress_callback(completed, total)
                        
                except Exception as e:
                    logger.error(f"Task {idx} failed: {e}")
                    raise ParallelProcessingError(
                        f"Task {idx} failed: {str(e)}",
                        task_id=idx,
                        original_error=e
                    )
        
        logger.info(f"Parallel execution completed: {completed}/{total} tasks")
        return results
    
    def map_parallel(
        self,
        func: Callable,
        items: List[Any],
        progress_callback: Callable[[int, int], None] = None
    ) -> List[Any]:
        """
        Apply function to each item in parallel.
        
        Args:
            func: Function to apply
            items: List of items
            progress_callback: Optional callback(completed, total)
        
        Returns:
            List of results
        """
        tasks = [(func, (item,)) for item in items]
        return self.analyze_parallel(tasks, progress_callback)


class RateLimiter:
    """Thread-safe rate limiter."""
    
    def __init__(self, calls_per_second: float):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum calls per second
        """
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0
        self._lock = None  # Will be created in first call
    
    def wait(self) -> None:
        """Wait if necessary to respect rate limit."""
        import threading
        
        if self._lock is None:
            self._lock = threading.Lock()
        
        with self._lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time
            
            if time_since_last_call < self.min_interval:
                sleep_time = self.min_interval - time_since_last_call
                time.sleep(sleep_time)
            
            self.last_call_time = time.time()


class BatchProcessor:
    """Process items in batches."""
    
    def __init__(self, batch_size: int = 10):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of items per batch
        """
        self.batch_size = batch_size
    
    def process_in_batches(
        self,
        items: List[Any],
        process_func: Callable[[List[Any]], List[Any]],
        progress_callback: Callable[[int, int], None] = None
    ) -> List[Any]:
        """
        Process items in batches.
        
        Args:
            items: Items to process
            process_func: Function that processes a batch and returns results
            progress_callback: Optional callback(completed, total)
        
        Returns:
            List of all results
        """
        total = len(items)
        results = []
        
        for i in range(0, total, self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = process_func(batch)
            results.extend(batch_results)
            
            if progress_callback:
                completed = min(i + self.batch_size, total)
                progress_callback(completed, total)
        
        return results