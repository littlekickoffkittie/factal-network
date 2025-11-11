"""
Tests for fractal mathematics components.
"""

import pytest
import numpy as np
from consensus.fractal_math import (
    FractalConfig, JuliaSetGenerator, BoxCountingDimension, FractalProofOfWork
)


class TestJuliaSetGenerator:
    """Tests for Julia set generation."""

    def test_seed_to_c_parameter(self):
        """Test conversion of seed to c parameter."""
        gen = JuliaSetGenerator()
        seed = "0" * 64

        c = gen.generate_c_from_seed(seed)

        assert isinstance(c, complex)
        assert -1 <= c.real <= 1
        assert -1 <= c.imag <= 1

    def test_julia_set_computation(self):
        """Test Julia set computation."""
        gen = JuliaSetGenerator()
        c = complex(0.0, 0.0)

        iterations = gen.compute_julia_set(c)

        assert iterations.shape == (128, 128)
        assert iterations.dtype == int
        assert np.all(iterations >= 0)
        assert np.all(iterations <= 256)

    def test_fractal_bitmap_generation(self):
        """Test fractal bitmap generation."""
        gen = JuliaSetGenerator()
        c = complex(-0.7, 0.27)

        bitmap = gen.generate_fractal_bitmap(c)

        assert bitmap.shape == (128, 128)
        assert np.all((bitmap == 0) | (bitmap == 1))
        assert np.any(bitmap == 1)  # Should have some fractal points

    def test_different_c_values(self):
        """Test Julia sets with different c values."""
        gen = JuliaSetGenerator()

        c_values = [
            complex(0, 0),
            complex(-0.7, 0.27),
            complex(0.285, 0.01),
            complex(-0.4, 0.6)
        ]

        for c in c_values:
            bitmap = gen.generate_fractal_bitmap(c)
            assert bitmap.shape == (128, 128)


class TestBoxCountingDimension:
    """Tests for box-counting dimension calculation."""

    def test_count_boxes(self):
        """Test box counting."""
        counter = BoxCountingDimension()

        # Create simple test bitmap
        bitmap = np.zeros((128, 128), dtype=int)
        bitmap[50:80, 50:80] = 1

        count = counter.count_boxes(bitmap, 1.0)
        assert count > 0

    def test_dimension_calculation(self):
        """Test dimension calculation."""
        counter = BoxCountingDimension()

        # Create fractal-like pattern
        bitmap = np.zeros((128, 128), dtype=int)
        bitmap[::2, ::2] = 1  # Checkerboard pattern

        dimension, r_squared, data_points = counter.calculate_dimension(bitmap)

        assert 0 <= dimension <= 3
        assert 0 <= r_squared <= 1
        assert len(data_points) > 0

    def test_empty_bitmap(self):
        """Test with empty bitmap."""
        counter = BoxCountingDimension()

        bitmap = np.zeros((128, 128), dtype=int)

        dimension, r_squared, data_points = counter.calculate_dimension(bitmap)

        assert dimension == 0.0

    def test_full_bitmap(self):
        """Test with full bitmap."""
        counter = BoxCountingDimension()

        bitmap = np.ones((128, 128), dtype=int)

        dimension, r_squared, data_points = counter.calculate_dimension(bitmap)

        assert dimension > 0


class TestFractalProofOfWork:
    """Tests for FractalPoW system."""

    def test_fractal_seed_generation(self):
        """Test fractal seed generation."""
        fpow = FractalProofOfWork()

        seed = fpow.generate_fractal_seed(
            "prev_hash_123",
            "miner_address_abc",
            12345
        )

        assert isinstance(seed, str)
        assert len(seed) == 64  # SHA-256 hex

    def test_deterministic_seed(self):
        """Test that seed generation is deterministic."""
        fpow = FractalProofOfWork()

        seed1 = fpow.generate_fractal_seed("prev", "miner", 100)
        seed2 = fpow.generate_fractal_seed("prev", "miner", 100)

        assert seed1 == seed2

    def test_different_nonce_different_seed(self):
        """Test that different nonces produce different seeds."""
        fpow = FractalProofOfWork()

        seed1 = fpow.generate_fractal_seed("prev", "miner", 100)
        seed2 = fpow.generate_fractal_seed("prev", "miner", 101)

        assert seed1 != seed2

    def test_header_hash_verification(self):
        """Test header hash verification."""
        fpow = FractalProofOfWork()

        # Hash with 4 leading zero hex chars (16 bits)
        valid_hash = "0000" + "a" * 60
        assert fpow.verify_header_hash(valid_hash, 16)

        # Hash without enough leading zeros
        invalid_hash = "000a" + "a" * 60
        assert not fpow.verify_header_hash(invalid_hash, 16)

    def test_search_point_generation(self):
        """Test search point generation."""
        fpow = FractalProofOfWork()

        seed = "test_seed_123"
        points = fpow._generate_search_points(seed, 10)

        assert len(points) == 10
        assert all(isinstance(p, complex) for p in points)

        # Should be deterministic
        points2 = fpow._generate_search_points(seed, 10)
        assert points == points2

    def test_solution_verification(self):
        """Test solution verification."""
        fpow = FractalProofOfWork()

        # Generate a seed and find solution
        seed = fpow.generate_fractal_seed("prev", "miner", 1)
        c = fpow.julia_gen.generate_c_from_seed(seed)

        # Generate fractal at origin
        bitmap = fpow.julia_gen.generate_fractal_bitmap(c, complex(0, 0))
        dimension, r_squared, _ = fpow.box_counter.calculate_dimension(bitmap)

        # Verify with appropriate tolerance
        is_valid = fpow.verify_solution(
            seed,
            complex(0, 0),
            dimension,
            target_dimension=dimension,
            epsilon=0.01
        )

        assert is_valid


class TestFractalConfig:
    """Tests for fractal configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FractalConfig()

        assert config.max_iterations == 256
        assert config.escape_radius == 2.0
        assert config.grid_size == 128
        assert config.target_dimension == 1.5
        assert config.epsilon == 0.001
        assert len(config.box_sizes) == 8

    def test_custom_config(self):
        """Test custom configuration."""
        config = FractalConfig(
            max_iterations=512,
            grid_size=256,
            target_dimension=1.8
        )

        assert config.max_iterations == 512
        assert config.grid_size == 256
        assert config.target_dimension == 1.8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
