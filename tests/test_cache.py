"""
Tests for caching module.
"""

import pytest
import time
from utils.cache import LRUCache, FractalCache, BlockCache


class TestLRUCache:
    """Test LRU cache implementation."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = LRUCache(max_size=10)
        assert cache.max_size == 10
        assert len(cache.cache) == 0

    def test_cache_put_get(self):
        """Test putting and getting values."""
        cache = LRUCache(max_size=10)
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss(self):
        """Test cache miss."""
        cache = LRUCache(max_size=10)
        assert cache.get("nonexistent") is None
        assert cache.misses == 1

    def test_cache_hit(self):
        """Test cache hit."""
        cache = LRUCache(max_size=10)
        cache.put("key1", "value1")
        cache.get("key1")
        assert cache.hits == 1

    def test_cache_eviction(self):
        """Test cache eviction on max size."""
        cache = LRUCache(max_size=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        cache.put("key4", "value4")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_cache_lru_order(self):
        """Test LRU ordering."""
        cache = LRUCache(max_size=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Access key1 to make it recent
        cache.get("key1")

        # Add key4, should evict key2 (least recently used)
        cache.put("key4", "value4")

        assert cache.get("key2") is None
        assert cache.get("key1") == "value1"

    def test_cache_ttl(self):
        """Test TTL expiration."""
        cache = LRUCache(max_size=10, ttl=1)  # 1 second TTL

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_cache_update(self):
        """Test updating existing key."""
        cache = LRUCache(max_size=10)

        cache.put("key1", "value1")
        cache.put("key1", "value2")  # Update

        assert cache.get("key1") == "value2"
        assert len(cache.cache) == 1

    def test_cache_delete(self):
        """Test deleting key."""
        cache = LRUCache(max_size=10)

        cache.put("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_cache_clear(self):
        """Test clearing cache."""
        cache = LRUCache(max_size=10)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.clear()

        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = LRUCache(max_size=10)

        cache.put("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()

        assert stats['size'] == 1
        assert stats['max_size'] == 10
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 50.0


class TestFractalCache:
    """Test fractal-specific cache."""

    def test_fractal_cache_initialization(self):
        """Test fractal cache initialization."""
        cache = FractalCache(max_size=100)
        assert cache.cache.max_size == 100

    def test_fractal_cache_put_get(self):
        """Test caching fractal results."""
        cache = FractalCache(max_size=100)

        seed = "test_seed"
        c = complex(0.5, 0.5)
        center = complex(0, 0)
        bitmap = [[1, 0], [0, 1]]
        dimension = 1.5

        cache.put_fractal(seed, c, center, bitmap, dimension)
        result = cache.get_fractal(seed, c, center)

        assert result is not None
        assert result[0] == bitmap
        assert result[1] == dimension

    def test_fractal_cache_miss(self):
        """Test fractal cache miss."""
        cache = FractalCache(max_size=100)

        result = cache.get_fractal("nonexistent", complex(0, 0), complex(0, 0))
        assert result is None

    def test_fractal_cache_stats(self):
        """Test fractal cache statistics."""
        cache = FractalCache(max_size=100)

        cache.put_fractal("seed1", complex(0, 0), complex(0, 0), [[1]], 1.5)
        stats = cache.get_stats()

        assert stats['size'] == 1


class TestBlockCache:
    """Test blockchain-specific cache."""

    def test_block_cache_initialization(self):
        """Test block cache initialization."""
        cache = BlockCache(max_blocks=100)
        assert cache.block_cache.max_size == 100

    def test_block_cache_put_get(self):
        """Test caching blocks."""
        cache = BlockCache(max_blocks=100)

        block_hash = "a" * 64
        block_data = {"index": 1, "hash": block_hash}

        cache.put_block(block_hash, block_data)
        result = cache.get_block(block_hash)

        assert result == block_data

    def test_transaction_cache(self):
        """Test caching transactions."""
        cache = BlockCache(max_blocks=100)

        tx_hash = "b" * 64
        tx_data = {"from": "addr1", "to": "addr2", "amount": 10}

        cache.put_transaction(tx_hash, tx_data)
        result = cache.get_transaction(tx_hash)

        assert result == tx_data

    def test_balance_cache(self):
        """Test caching balances."""
        cache = BlockCache(max_blocks=100)

        address = "c" * 40
        balance = 100.5

        cache.put_balance(address, balance)
        result = cache.get_balance(address)

        assert result == balance

    def test_balance_invalidation(self):
        """Test invalidating cached balance."""
        cache = BlockCache(max_blocks=100)

        address = "c" * 40
        cache.put_balance(address, 100.0)
        cache.invalidate_balance(address)

        assert cache.get_balance(address) is None

    def test_balance_cache_ttl(self):
        """Test balance cache TTL."""
        cache = BlockCache(max_blocks=100)

        address = "d" * 40
        cache.put_balance(address, 100.0)

        # Balances have 60s TTL - should still be there
        assert cache.get_balance(address) == 100.0

    def test_block_cache_stats(self):
        """Test block cache statistics."""
        cache = BlockCache(max_blocks=100)

        cache.put_block("a" * 64, {"data": "block1"})
        cache.put_transaction("b" * 64, {"data": "tx1"})
        cache.put_balance("c" * 40, 100.0)

        stats = cache.get_stats()

        assert 'blocks' in stats
        assert 'transactions' in stats
        assert 'balances' in stats
        assert stats['blocks']['size'] == 1
        assert stats['transactions']['size'] == 1
        assert stats['balances']['size'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
