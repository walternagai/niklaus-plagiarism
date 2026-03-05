"""
Compressor for analysis results.
Reduces memory usage and storage for large analysis datasets.
"""

import json
import zlib
import gzip
import base64
from typing import Any, Dict, Optional
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class ResultCompressor:
    """
    Compresses and decompresses analysis results.
    Reduces memory footprint and storage requirements.
    """
    
    def __init__(self, compression_level: int = 6):
        """
        Initialize compressor.
        
        Args:
            compression_level: Compression level (1-9, higher = better compression but slower)
        """
        self.compression_level = compression_level
    
    def compress(self, data: Dict[str, Any]) -> bytes:
        """
        Compress analysis results.
        
        Args:
            data: Dictionary with analysis results
            
        Returns:
            Compressed bytes
        """
        try:
            serialized = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            compressed = zlib.compress(
                serialized.encode('utf-8'),
                level=self.compression_level
            )
            
            original_size = len(serialized.encode('utf-8'))
            compressed_size = len(compressed)
            ratio = (1 - compressed_size / original_size) * 100
            
            logger.debug(
                f"Compressed result: {original_size} -> {compressed_size} bytes "
                f"({ratio:.1f}% reduction)"
            )
            
            return compressed
        except Exception as e:
            logger.error(f"Compression error: {e}")
            raise
    
    def decompress(self, data: bytes) -> Dict[str, Any]:
        """
        Decompress analysis results.
        
        Args:
            data: Compressed bytes
            
        Returns:
            Decompressed dictionary
        """
        try:
            decompressed = zlib.decompress(data)
            return json.loads(decompressed.decode('utf-8'))
        except Exception as e:
            logger.error(f"Decompression error: {e}")
            raise
    
    def compress_to_base64(self, data: Dict[str, Any]) -> str:
        """
        Compress and encode to base64 string.
        
        Args:
            data: Dictionary with analysis results
            
        Returns:
            Base64-encoded compressed string
        """
        compressed = self.compress(data)
        return base64.b64encode(compressed).decode('utf-8')
    
    def decompress_from_base64(self, data: str) -> Dict[str, Any]:
        """
        Decompress from base64 string.
        
        Args:
            data: Base64-encoded compressed string
            
        Returns:
            Decompressed dictionary
        """
        compressed = base64.b64decode(data.encode('utf-8'))
        return self.decompress(compressed)
    
    def compress_file(self, input_path: str, output_path: str) -> int:
        """
        Compress file using gzip.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
            
        Returns:
            Compression ratio percentage
        """
        try:
            with open(input_path, 'rb') as f_in:
                with gzip.open(output_path, 'wb', compresslevel=self.compression_level) as f_out:
                    f_out.writelines(f_in)
            
            original_size = Path(input_path).stat().st_size
            compressed_size = Path(output_path).stat().st_size
            ratio = (1 - compressed_size / original_size) * 100
            
            logger.debug(
                f"Compressed file: {original_size} -> {compressed_size} bytes "
                f"({ratio:.1f}% reduction)"
            )
            
            return int(ratio)
        except Exception as e:
            logger.error(f"File compression error: {e}")
            raise
    
    def decompress_file(self, input_path: str, output_path: str):
        """
        Decompress gzip file.
        
        Args:
            input_path: Path to compressed file
            output_path: Path to output file
        """
        try:
            with gzip.open(input_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            logger.debug(f"Decompressed file: {input_path} -> {output_path}")
        except Exception as e:
            logger.error(f"File decompression error: {e}")
            raise


class ChunkedCompressor:
    """
    Compresses large results in chunks.
    Useful for streaming compression of very large datasets.
    """
    
    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB default
        self._compressor = ResultCompressor()
        self._chunk_size = chunk_size
    
    def compress_chunks(self, data: Dict[str, Any]) -> list:
        """
        Compress data in chunks.
        
        Args:
            data: Large dictionary to compress
            
        Returns:
            List of compressed chunks
        """
        serialized = json.dumps(data, separators=(',', ':')).encode('utf-8')
        chunks = []
        
        for i in range(0, len(serialized), self._chunk_size):
            chunk = serialized[i:i + self._chunk_size]
            compressed_chunk = zlib.compress(chunk, level=6)
            chunks.append(compressed_chunk)
        
        return chunks
    
    def decompress_chunks(self, chunks: list) -> Dict[str, Any]:
        """
        Decompress data from chunks.
        
        Args:
            chunks: List of compressed chunks
            
        Returns:
            Decompressed dictionary
        """
        decompressed_parts = []
        
        for chunk in chunks:
            decompressed = zlib.decompress(chunk)
            decompressed_parts.append(decompressed)
        
        full_data = b''.join(decompressed_parts)
        return json.loads(full_data.decode('utf-8'))


class CompressionStats:
    """
    Statistics for compression operations.
    """
    
    def __init__(self):
        self._stats: Dict[str, Dict[str, int]] = {}
    
    def record(self, operation: str, original_size: int, compressed_size: int):
        """Record compression statistics."""
        if operation not in self._stats:
            self._stats[operation] = {
                'total_original': 0,
                'total_compressed': 0,
                'count': 0
            }
        
        self._stats[operation]['total_original'] += original_size
        self._stats[operation]['total_compressed'] += compressed_size
        self._stats[operation]['count'] += 1
    
    def get_stats(self, operation: str = None) -> Dict[str, Any]:
        """Get compression statistics."""
        if operation:
            return self._stats.get(operation, {})
        
        return {
            op: {
                **stats,
                'ratio': (1 - stats['total_compressed'] / stats['total_original']) * 100
                         if stats['total_original'] > 0 else 0
            }
            for op, stats in self._stats.items()
        }
    
    def get_total_savings(self) -> Dict[str, int]:
        """Calculate total space saved."""
        total_original = sum(s['total_original'] for s in self._stats.values())
        total_compressed = sum(s['total_compressed'] for s in self._stats.values())
        
        return {
            'original_bytes': total_original,
            'compressed_bytes': total_compressed,
            'saved_bytes': total_original - total_compressed,
            'savings_percentage': (1 - total_compressed / total_original) * 100
                                  if total_original > 0 else 0
        }


_global_compression_stats: Optional[CompressionStats] = None


def get_compression_stats() -> CompressionStats:
    """Get global compression statistics instance."""
    global _global_compression_stats
    if _global_compression_stats is None:
        _global_compression_stats = CompressionStats()
    return _global_compression_stats


def compress_result(data: Dict[str, Any], level: int = 6) -> bytes:
    """Quick function to compress analysis result."""
    compressor = ResultCompressor(compression_level=level)
    compressed = compressor.compress(data)
    
    stats = get_compression_stats()
    original_size = len(json.dumps(data).encode('utf-8'))
    stats.record('result', original_size, len(compressed))
    
    return compressed


def decompress_result(data: bytes) -> Dict[str, Any]:
    """Quick function to decompress analysis result."""
    compressor = ResultCompressor()
    return compressor.decompress(data)