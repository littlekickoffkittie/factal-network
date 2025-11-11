"""
Caching system for FractalChain.
Provides LRU cache for expensive fractal computations and blockchain queries.
"""

import time
import threading
import hashlib
import pickle
from typing import Any, Optional, Callable, Dict, Tuple
from collections import OrderedDict
from functools import wraps


class LRUCache:
    """Thread-safe LRU (Least Recently Used) cache."""

    def __init__(self, max_size: int = 1000, ttl: Optional[int] = None):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items in cache
            ttl: Time-to-live in seconds (None for no expiration)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None

            # Check TTL
            if self.ttl is not None:
                timestamp = self.timestamps.get(key, 0)
                if time.time() - timestamp > self.ttl:
                    # Expired
                    del self.cache[key]
                    del self.timestamps[key]
                    self.misses += 1
                    return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]

    def put(self, key: str, value: Any) -> None:
        """
        Put value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            # Update existing key
            if key in self.cache:
                self.cache.move_to_end(key)
                self.cache[key] = value
                self.timestamps[key] = time.time()
                return

            # Add new key
            self.cache[key] = value
            self.timestamps[key] = time.time()

            # Evict oldest if over max size
            if len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]

    def delete(self, key: str) -> None:
        """
        Delete key from cache.

        Args:
            key: Cache key
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary of cache stats
        """
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0

            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'ttl': self.ttl
            }


class FractalCache:
    """Specialized cache for fractal computations."""

    def __init__(self, max_size: int = 500):
        """
        Initialize fractal cache.

        Args:
            max_size: Maximum number of cached fractals
        """
        self.cache = LRUCache(max_size=max_size, ttl=3600)  # 1 hour TTL

    def _generate_key(self, seed: str, c: complex, center: complex) -> str:
        """
        Generate cache key for fractal computation.

        Args:
            seed: Fractal seed
            c: Julia set parameter
            center: Center point

        Returns:
            Cache key
        """
        data = f"{seed}:{c.real}:{c.imag}:{center.real}:{center.imag}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def get_fractal(
        self,
        seed: str,
        c: complex,
        center: complex
    ) -> Optional[Tuple[Any, float]]:
        """
        Get cached fractal bitmap and dimension.

        Args:
            seed: Fractal seed
            c: Julia set parameter
            center: Center point

        Returns:
            Tuple of (bitmap, dimension) or None
        """
        key = self._generate_key(seed, c, center)
        return self.cache.get(key)

    def put_fractal(
        self,
        seed: str,
        c: complex,
        center: complex,
        bitmap: Any,
        dimension: float
    ) -> None:
        """
        Cache fractal bitmap and dimension.

        Args:
            seed: Fractal seed
            c: Julia set parameter
            center: Center point
            bitmap: Fractal bitmap
            dimension: Computed dimension
        """
        key = self._generate_key(seed, c, center)
        self.cache.put(key, (bitmap, dimension))

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()


class BlockCache:
    """Specialized cache for blockchain data."""

    def __init__(self, max_blocks: int = 2016):
        """
        Initialize block cache.

        Args:
            max_blocks: Maximum number of cached blocks
        """
        self.block_cache = LRUCache(max_size=max_blocks)
        self.tx_cache = LRUCache(max_size=max_blocks * 100)  # More transactions
        self.balance_cache = LRUCache(max_size=10000, ttl=60)  # 1 min TTL for balances

    def get_block(self, block_hash: str) -> Optional[Any]:
        """
        Get cached block.

        Args:
            block_hash: Block hash

        Returns:
            Block object or None
        """
        return self.block_cache.get(block_hash)

    def put_block(self, block_hash: str, block: Any) -> None:
        """
        Cache block.

        Args:
            block_hash: Block hash
            block: Block object
        """
        self.block_cache.put(block_hash, block)

    def get_transaction(self, tx_hash: str) -> Optional[Any]:
        """
        Get cached transaction.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction object or None
        """
        return self.tx_cache.get(tx_hash)

    def put_transaction(self, tx_hash: str, transaction: Any) -> None:
        """
        Cache transaction.

        Args:
            tx_hash: Transaction hash
            transaction: Transaction object
        """
        self.tx_cache.put(tx_hash, transaction)

    def get_balance(self, address: str) -> Optional[float]:
        """
        Get cached balance.

        Args:
            address: Account address

        Returns:
            Balance or None
        """
        return self.balance_cache.get(address)

    def put_balance(self, address: str, balance: float) -> None:
        """
        Cache balance.

        Args:
            address: Account address
            balance: Account balance
        """
        self.balance_cache.put(address, balance)

    def invalidate_balance(self, address: str) -> None:
        """
        Invalidate cached balance.

        Args:
            address: Account address
        """
        self.balance_cache.delete(address)

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get all cache statistics."""
        return {
            'blocks': self.block_cache.get_stats(),
            'transactions': self.tx_cache.get_stats(),
            'balances': self.balance_cache.get_stats()
        }


def cached(cache_instance: LRUCache, key_func: Optional[Callable] = None):
    """
    Decorator for caching function results.

    Args:
        cache_instance: Cache instance to use
        key_func: Optional function to generate cache key from args

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: hash arguments
                key_data = pickle.dumps((args, sorted(kwargs.items())))
                cache_key = hashlib.sha256(key_data).hexdigest()[:16]

            # Try to get from cache
            result = cache_instance.get(cache_key)
            if result is not None:
                return result

            # Compute and cache result
            result = func(*args, **kwargs)
            cache_instance.put(cache_key, result)
            return result

        return wrapper
    return decorator


# Global cache instances
_fractal_cache = None
_block_cache = None
_cache_lock = threading.Lock()


def get_fractal_cache() -> FractalCache:
    """
    Get global fractal cache instance.

    Returns:
        Global FractalCache instance
    """
    global _fractal_cache

    with _cache_lock:
        if _fractal_cache is None:
            _fractal_cache = FractalCache()

    return _fractal_cache


def get_block_cache() -> BlockCache:
    """
    Get global block cache instance.

    Returns:
        Global BlockCache instance
    """
    global _block_cache

    with _cache_lock:
        if _block_cache is None:
            _block_cache = BlockCache()

    return _block_cache
