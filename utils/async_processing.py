"""
Async processing for I/O operations and batch processing.
Provides asynchronous execution for improved performance.
"""

import asyncio
import concurrent.futures
from typing import List, Any, Callable, Optional, Dict
from functools import wraps
import time
from concurrent.futures import ThreadPoolExecutor

from utils.logger import get_logger
from utils.performance import track_performance

logger = get_logger(__name__)


class AsyncProcessor:
    """
    Processor for async I/O operations.
    Executes tasks concurrently for improved performance.
    """
    
    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._loop = None
        self._max_workers = max_workers
    
    async def run_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Run function asynchronously.
        
        Args:
            func: Function to run
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args, **kwargs)
    
    async def run_batch_async(self, func: Callable, items: List[Any], 
                               max_concurrent: int = 10) -> List[Any]:
        """
        Run function on multiple items concurrently.
        
        Args:
            func: Function to run on each item
            items: List of items
            max_concurrent: Maximum concurrent tasks
            
        Returns:
            List of results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(item):
            async with semaphore:
                return await self.run_async(func, item)
        
        tasks = [run_with_semaphore(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing item {i}: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    def shutdown(self):
        """Shutdown executor."""
        self._executor.shutdown(wait=True)


class BatchProcessor:
    """
    Batch processing for large datasets.
    Processes items in batches to optimize memory and performance.
    """
    
    def __init__(self, batch_size: int = 100, max_workers: int = 4):
        self._batch_size = batch_size
        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    @track_performance('batch.process')
    def process_batch(self, func: Callable, items: List[Any],
                      progress_callback: Callable = None) -> List[Any]:
        """
        Process items in batches.
        
        Args:
            func: Function to apply to each item
            items: List of items to process
            progress_callback: Callback for progress updates (current, total)
            
        Returns:
            List of results
        """
        total_items = len(items)
        results = []
        
        for i in range(0, total_items, self._batch_size):
            batch = items[i:i + self._batch_size]
            batch_results = self._process_batch(func, batch)
            results.extend(batch_results)
            
            if progress_callback:
                progress_callback(min(i + self._batch_size, total_items), total_items)
        
        return results
    
    def _process_batch(self, func: Callable, batch: List[Any]) -> List[Any]:
        """Process a single batch."""
        futures = []
        
        for item in batch:
            future = self._executor.submit(func, item)
            futures.append(future)
        
        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                results.append(None)
        
        return results
    
    async def process_batch_async(self, func: Callable, items: List[Any],
                                   progress_callback: Callable = None) -> List[Any]:
        """
        Process items in batches asynchronously.
        
        Args:
            func: Async function to apply to each item
            items: List of items to process
            progress_callback: Callback for progress updates
            
        Returns:
            List of results
        """
        processor = AsyncProcessor(self._max_workers)
        
        total_items = len(items)
        results = []
        
        for i in range(0, total_items, self._batch_size):
            batch = items[i:i + self._batch_size]
            batch_results = await processor.run_batch_async(func, batch)
            results.extend(batch_results)
            
            if progress_callback:
                progress_callback(min(i + self._batch_size, total_items), total_items)
        
        return results
    
    def shutdown(self):
        """Shutdown executor."""
        self._executor.shutdown(wait=True)


class ChunkedProcessor:
    """
    Process large files in chunks.
    Useful for processing large ZIP files or datasets.
    """
    
    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB default
        self._chunk_size = chunk_size
    
    def process_file_chunks(self, file_obj: Any, process_func: Callable) -> List[Any]:
        """
        Process file in chunks.
        
        Args:
            file_obj: File object
            process_func: Function to process each chunk
            
        Returns:
            List of processed results
        """
        chunk_num = 0
        results = []
        
        while True:
            chunk = file_obj.read(self._chunk_size)
            if not chunk:
                break
            
            try:
                result = process_func(chunk, chunk_num)
                results.append(result)
                chunk_num += 1
            except Exception as e:
                logger.error(f"Error processing chunk {chunk_num}: {e}")
                results.append(None)
        
        return results
    
    async def process_file_async(self, file_obj: Any, process_func: Callable) -> List[Any]:
        """Process file chunks asynchronously."""
        processor = AsyncProcessor()
        
        chunks = []
        while True:
            chunk = file_obj.read(self._chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
        
        results = await processor.run_batch_async(
            lambda c: process_func(c),
            chunks
        )
        
        return results


def async_task(func: Callable) -> Callable:
    """
    Decorator to make function async.
    
    Usage:
        @async_task
        def long_running_operation():
            return expensive_calculation()
        
        # Run asynchronously
        result = await long_running_operation()
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    
    return wrapper


def batch_process(batch_size: int = 100) -> Callable:
    """
    Decorator to automatically batch process large lists.
    
    Usage:
        @batch_process(batch_size=50)
        def process_item(item):
            return transform(item)
        
        # Automatically batches items
        results = process_item(large_list)
    """
    def decorator(func: Callable) -> Callable:
        processor = BatchProcessor(batch_size=batch_size)
        
        @wraps(func)
        def wrapper(items: List[Any], *args, **kwargs) -> List[Any]:
            return processor.process_batch(
                lambda item: func(item, *args, **kwargs),
                items
            )
        
        return wrapper
    
    return decorator


_global_async_processor: Optional[AsyncProcessor] = None
_global_batch_processor: Optional[BatchProcessor] = None


def get_async_processor(max_workers: int = 4) -> AsyncProcessor:
    """Get global async processor instance."""
    global _global_async_processor
    if _global_async_processor is None:
        _global_async_processor = AsyncProcessor(max_workers=max_workers)
    return _global_async_processor


def get_batch_processor(batch_size: int = 100, max_workers: int = 4) -> BatchProcessor:
    """Get global batch processor instance."""
    global _global_batch_processor
    if _global_batch_processor is None:
        _global_batch_processor = BatchProcessor(
            batch_size=batch_size,
            max_workers=max_workers
        )
    return _global_batch_processor


def run_in_executor(func: Callable, *args, **kwargs) -> Any:
    """
    Run function in thread pool executor.
    
    Args:
        func: Function to run
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
    """
    processor = get_async_processor()
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        processor.run_async(func, *args, **kwargs)
    )