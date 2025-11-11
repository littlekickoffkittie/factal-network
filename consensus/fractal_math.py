"""
Fractal mathematics engine for FractalChain.
Implements Julia set generation and box-counting dimension calculation.
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass
import hashlib
from scipy import stats


@dataclass
class FractalConfig:
    """Configuration for fractal generation and analysis."""

    # Julia set parameters
    max_iterations: int = 256
    escape_radius: float = 2.0
    grid_size: int = 128

    # Box-counting parameters
    box_sizes: List[float] = None
    region_size: float = 2.0  # 2x2 complex units

    # Difficulty parameters
    target_dimension: float = 1.5
    epsilon: float = 0.001  # Tolerance for dimension matching

    def __post_init__(self):
        """Initialize default box sizes if not provided."""
        if self.box_sizes is None:
            # 8 discrete box sizes from 1 to 1/128
            self.box_sizes = [1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125]


class JuliaSetGenerator:
    """
    Generates Julia sets for the FractalPoW algorithm.
    Uses the function f(z) = z² + c.
    """

    def __init__(self, config: FractalConfig = None):
        """
        Initialize Julia set generator.

        Args:
            config: Fractal configuration parameters
        """
        self.config = config or FractalConfig()

    def generate_c_from_seed(self, seed: str) -> complex:
        """
        Generate Julia set parameter c from a seed hash.

        Args:
            seed: Hexadecimal seed string

        Returns:
            Complex parameter c
        """
        # Use first 16 hex chars for real part, next 16 for imaginary
        if len(seed) < 32:
            seed = seed.ljust(32, '0')

        real_hex = seed[:16]
        imag_hex = seed[16:32]

        # Convert to integers and normalize to [-1, 1]
        real_int = int(real_hex, 16)
        imag_int = int(imag_hex, 16)

        max_val = 2**64
        real_part = (real_int / max_val) * 2 - 1
        imag_part = (imag_int / max_val) * 2 - 1

        return complex(real_part, imag_part)

    def compute_julia_set(
        self,
        c: complex,
        center: complex = 0 + 0j,
        region_size: float = None
    ) -> np.ndarray:
        """
        Compute Julia set for parameter c.

        Args:
            c: Julia set parameter
            center: Center of the region to compute
            region_size: Size of the region (defaults to config)

        Returns:
            2D array of iteration counts
        """
        if region_size is None:
            region_size = self.config.region_size

        # Create grid
        grid_size = self.config.grid_size
        half_size = region_size / 2

        x = np.linspace(
            center.real - half_size,
            center.real + half_size,
            grid_size
        )
        y = np.linspace(
            center.imag - half_size,
            center.imag + half_size,
            grid_size
        )

        X, Y = np.meshgrid(x, y)
        Z = X + 1j * Y

        # Initialize iteration count array
        iterations = np.zeros(Z.shape, dtype=int)
        mask = np.ones(Z.shape, dtype=bool)

        # Iterate Julia set function
        Z_iter = Z.copy()
        for i in range(self.config.max_iterations):
            # Compute z² + c
            Z_iter[mask] = Z_iter[mask]**2 + c

            # Check for escape
            escaped = np.abs(Z_iter) > self.config.escape_radius
            newly_escaped = escaped & mask

            iterations[newly_escaped] = i
            mask[escaped] = False

            if not mask.any():
                break

        # Points that never escaped get max iterations
        iterations[mask] = self.config.max_iterations

        return iterations

    def generate_fractal_bitmap(
        self,
        c: complex,
        center: complex = 0 + 0j
    ) -> np.ndarray:
        """
        Generate binary fractal bitmap (in set = 1, not in set = 0).

        Args:
            c: Julia set parameter
            center: Center of the region

        Returns:
            Binary 2D array
        """
        iterations = self.compute_julia_set(c, center)

        # Points in the set are those that didn't escape
        in_set = (iterations == self.config.max_iterations).astype(int)

        return in_set


class BoxCountingDimension:
    """
    Calculates fractal dimension using box-counting method.
    """

    def __init__(self, config: FractalConfig = None):
        """
        Initialize box-counting calculator.

        Args:
            config: Fractal configuration parameters
        """
        self.config = config or FractalConfig()

    def count_boxes(self, bitmap: np.ndarray, box_size: float) -> int:
        """
        Count boxes containing fractal at given box size.

        Args:
            bitmap: Binary fractal bitmap
            box_size: Size of boxes to use

        Returns:
            Number of boxes containing the fractal
        """
        grid_size = bitmap.shape[0]
        region_size = self.config.region_size

        # Calculate number of boxes along each dimension
        boxes_per_side = int(region_size / box_size)

        if boxes_per_side <= 0 or boxes_per_side > grid_size:
            boxes_per_side = grid_size

        # Calculate pixels per box
        pixels_per_box = grid_size // boxes_per_side

        if pixels_per_box <= 0:
            return np.sum(bitmap > 0)

        count = 0

        # Scan through boxes
        for i in range(boxes_per_side):
            for j in range(boxes_per_side):
                # Get box region
                row_start = i * pixels_per_box
                row_end = min((i + 1) * pixels_per_box, grid_size)
                col_start = j * pixels_per_box
                col_end = min((j + 1) * pixels_per_box, grid_size)

                box_region = bitmap[row_start:row_end, col_start:col_end]

                # Check if box contains any fractal points
                if np.any(box_region > 0):
                    count += 1

        return count

    def calculate_dimension(self, bitmap: np.ndarray) -> Tuple[float, float, List[Tuple[float, int]]]:
        """
        Calculate box-counting dimension using OLS regression.

        Args:
            bitmap: Binary fractal bitmap

        Returns:
            Tuple of (dimension, r_squared, data_points)
        """
        log_scales = []
        log_counts = []
        data_points = []

        for box_size in self.config.box_sizes:
            count = self.count_boxes(bitmap, box_size)

            if count > 0:
                log_scale = np.log(1.0 / box_size)
                log_count = np.log(count)

                log_scales.append(log_scale)
                log_counts.append(log_count)
                data_points.append((box_size, count))

        if len(log_scales) < 2:
            return 0.0, 0.0, data_points

        # Perform linear regression
        log_scales = np.array(log_scales)
        log_counts = np.array(log_counts)

        slope, intercept, r_value, p_value, std_err = stats.linregress(
            log_scales, log_counts
        )

        # The slope is the fractal dimension
        dimension = slope
        r_squared = r_value ** 2

        return dimension, r_squared, data_points


class FractalProofOfWork:
    """
    Complete FractalPoW implementation combining Julia set and box-counting.
    """

    def __init__(self, config: FractalConfig = None):
        """
        Initialize FractalPoW system.

        Args:
            config: Fractal configuration parameters
        """
        self.config = config or FractalConfig()
        self.julia_gen = JuliaSetGenerator(self.config)
        self.box_counter = BoxCountingDimension(self.config)

    def generate_fractal_seed(
        self,
        prev_hash: str,
        miner_address: str,
        nonce: int
    ) -> str:
        """
        Generate fractal seed from block data.

        Args:
            prev_hash: Previous block hash
            miner_address: Miner's address
            nonce: Mining nonce

        Returns:
            Hexadecimal seed string
        """
        data = f"{prev_hash}{miner_address}{nonce}"
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def verify_header_hash(self, header_hash: str, difficulty_bits: int = 16) -> bool:
        """
        Quick pre-filter: check if first N bits are zero.

        Args:
            header_hash: Block header hash
            difficulty_bits: Number of leading zero bits required

        Returns:
            True if header passes pre-filter
        """
        # Convert hex to binary
        hash_int = int(header_hash, 16)

        # Check leading zeros
        leading_zeros = (hash_int.bit_length() == 256 - difficulty_bits or
                        hash_int < (1 << (256 - difficulty_bits)))

        # Simpler check: first difficulty_bits/4 hex chars are zero
        hex_zeros = difficulty_bits // 4
        return header_hash[:hex_zeros] == '0' * hex_zeros

    def find_fractal_solution(
        self,
        seed: str,
        target_dimension: float = None,
        epsilon: float = None,
        max_attempts: int = 100
    ) -> Optional[Tuple[complex, float, np.ndarray]]:
        """
        Search for fractal solution matching target dimension.

        Args:
            seed: Fractal seed
            target_dimension: Target dimension (defaults to config)
            epsilon: Tolerance (defaults to config)
            max_attempts: Maximum search attempts

        Returns:
            Tuple of (solution_point, actual_dimension, bitmap) or None
        """
        if target_dimension is None:
            target_dimension = self.config.target_dimension
        if epsilon is None:
            epsilon = self.config.epsilon

        # Generate c parameter from seed
        c = self.julia_gen.generate_c_from_seed(seed)

        # Search different center points in the complex plane
        search_points = self._generate_search_points(seed, max_attempts)

        for center in search_points:
            # Generate fractal bitmap
            bitmap = self.julia_gen.generate_fractal_bitmap(c, center)

            # Calculate dimension
            dimension, r_squared, _ = self.box_counter.calculate_dimension(bitmap)

            # Check if dimension matches target
            if abs(dimension - target_dimension) < epsilon and r_squared > 0.95:
                return center, dimension, bitmap

        return None

    def _generate_search_points(
        self,
        seed: str,
        count: int
    ) -> List[complex]:
        """
        Generate deterministic search points from seed.

        Args:
            seed: Seed string
            count: Number of points to generate

        Returns:
            List of complex search points
        """
        points = []
        current_seed = seed

        for i in range(count):
            # Generate deterministic point from seed
            current_seed = hashlib.sha256(
                f"{current_seed}{i}".encode('utf-8')
            ).hexdigest()

            # Extract real and imaginary parts
            real_hex = current_seed[:16]
            imag_hex = current_seed[16:32]

            real_int = int(real_hex, 16)
            imag_int = int(imag_hex, 16)

            max_val = 2**64

            # Map to search region (typically near origin)
            real_part = (real_int / max_val) * 2 - 1
            imag_part = (imag_int / max_val) * 2 - 1

            points.append(complex(real_part, imag_part))

        return points

    def verify_solution(
        self,
        seed: str,
        solution_point: complex,
        claimed_dimension: float,
        target_dimension: float = None,
        epsilon: float = None
    ) -> bool:
        """
        Verify a fractal PoW solution.

        Args:
            seed: Fractal seed
            solution_point: Claimed solution point
            claimed_dimension: Claimed dimension value
            target_dimension: Target dimension (defaults to config)
            epsilon: Tolerance (defaults to config)

        Returns:
            True if solution is valid
        """
        if target_dimension is None:
            target_dimension = self.config.target_dimension
        if epsilon is None:
            epsilon = self.config.epsilon

        # Generate c parameter from seed
        c = self.julia_gen.generate_c_from_seed(seed)

        # Generate fractal at solution point
        bitmap = self.julia_gen.generate_fractal_bitmap(c, solution_point)

        # Calculate dimension
        dimension, r_squared, _ = self.box_counter.calculate_dimension(bitmap)

        # Verify dimension matches target
        dimension_match = abs(dimension - target_dimension) < epsilon
        quality_check = r_squared > 0.95
        claim_accurate = abs(dimension - claimed_dimension) < 0.0001

        return dimension_match and quality_check and claim_accurate
