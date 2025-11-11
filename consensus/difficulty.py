"""
Difficulty adjustment algorithm for FractalChain.
Maintains consistent block time through dynamic difficulty targeting.
"""

import logging
from typing import List, Tuple
from ..core.block import Block


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DifficultyAdjustment:
    """
    Manages mining difficulty adjustment based on block times.
    """

    def __init__(
        self,
        target_block_time: float = 600.0,  # 10 minutes like Bitcoin
        adjustment_interval: int = 2016,  # Adjust every 2016 blocks
        max_adjustment_factor: float = 4.0
    ):
        """
        Initialize difficulty adjustment system.

        Args:
            target_block_time: Target time between blocks in seconds
            adjustment_interval: Number of blocks between adjustments
            max_adjustment_factor: Maximum difficulty change per adjustment
        """
        self.target_block_time = target_block_time
        self.adjustment_interval = adjustment_interval
        self.max_adjustment_factor = max_adjustment_factor

    def should_adjust_difficulty(self, block_height: int) -> bool:
        """
        Check if difficulty should be adjusted at this block height.

        Args:
            block_height: Current block height

        Returns:
            True if adjustment is needed
        """
        return block_height > 0 and block_height % self.adjustment_interval == 0

    def calculate_new_difficulty(
        self,
        recent_blocks: List[Block],
        current_difficulty: float,
        current_header_bits: int
    ) -> Tuple[float, int]:
        """
        Calculate new difficulty based on recent block times.

        Args:
            recent_blocks: List of recent blocks (should be adjustment_interval blocks)
            current_difficulty: Current fractal dimension target
            current_header_bits: Current header difficulty bits

        Returns:
            Tuple of (new_fractal_target, new_header_bits)
        """
        if len(recent_blocks) < 2:
            return current_difficulty, current_header_bits

        # Calculate actual time taken for recent blocks
        first_block = recent_blocks[0]
        last_block = recent_blocks[-1]
        actual_time = last_block.timestamp - first_block.timestamp

        # Calculate expected time
        expected_time = self.target_block_time * (len(recent_blocks) - 1)

        # Calculate time ratio
        time_ratio = actual_time / expected_time if expected_time > 0 else 1.0

        # Limit adjustment to prevent wild swings
        adjustment_factor = min(max(time_ratio, 1.0 / self.max_adjustment_factor), self.max_adjustment_factor)

        logger.info(f"Difficulty adjustment: actual_time={actual_time:.2f}s, expected_time={expected_time:.2f}s")
        logger.info(f"Time ratio: {time_ratio:.4f}, adjustment factor: {adjustment_factor:.4f}")

        # Adjust fractal dimension target
        # If blocks are too fast, make target harder (further from typical values)
        # If blocks are too slow, make target easier (closer to typical values)
        new_fractal_target = self._adjust_fractal_target(
            current_difficulty,
            adjustment_factor
        )

        # Adjust header difficulty bits
        new_header_bits = self._adjust_header_bits(
            current_header_bits,
            adjustment_factor
        )

        logger.info(f"New difficulty: fractal_target={new_fractal_target:.6f}, header_bits={new_header_bits}")

        return new_fractal_target, new_header_bits

    def _adjust_fractal_target(self, current_target: float, adjustment_factor: float) -> float:
        """
        Adjust fractal dimension target.

        Args:
            current_target: Current target dimension
            adjustment_factor: Adjustment factor (>1 = make easier, <1 = make harder)

        Returns:
            New target dimension
        """
        # Typical Julia set dimensions range from ~1.0 to ~2.0
        # Target of 1.5 is medium difficulty
        # Moving away from 1.5 makes it harder

        baseline = 1.5
        deviation = current_target - baseline

        if adjustment_factor > 1.0:
            # Make easier - move target closer to baseline
            new_deviation = deviation / adjustment_factor
        else:
            # Make harder - move target further from baseline
            new_deviation = deviation * (1.0 / adjustment_factor)

        new_target = baseline + new_deviation

        # Clamp to reasonable range
        new_target = max(1.0, min(2.0, new_target))

        return round(new_target, 6)

    def _adjust_header_bits(self, current_bits: int, adjustment_factor: float) -> int:
        """
        Adjust header hash difficulty bits.

        Args:
            current_bits: Current difficulty bits
            adjustment_factor: Adjustment factor (>1 = make easier, <1 = make harder)

        Returns:
            New difficulty bits
        """
        if adjustment_factor > 1.0:
            # Make easier - decrease bits
            new_bits = int(current_bits / adjustment_factor)
        else:
            # Make harder - increase bits
            new_bits = int(current_bits * (1.0 / adjustment_factor))

        # Clamp to reasonable range (4 to 32 bits)
        new_bits = max(4, min(32, new_bits))

        return new_bits

    def estimate_hashrate(self, recent_blocks: List[Block]) -> float:
        """
        Estimate network hashrate from recent blocks.

        Args:
            recent_blocks: Recent blocks to analyze

        Returns:
            Estimated hashrate (attempts per second)
        """
        if len(recent_blocks) < 2:
            return 0.0

        first_block = recent_blocks[0]
        last_block = recent_blocks[-1]

        time_span = last_block.timestamp - first_block.timestamp
        if time_span <= 0:
            return 0.0

        # Estimate based on difficulty and time
        # This is a rough estimate
        average_attempts = self._estimate_attempts_for_difficulty(
            last_block.difficulty_target,
            last_block.header_difficulty_bits
        )

        blocks_mined = len(recent_blocks) - 1
        total_attempts = average_attempts * blocks_mined

        hashrate = total_attempts / time_span

        return hashrate

    def _estimate_attempts_for_difficulty(
        self,
        fractal_target: float,
        header_bits: int
    ) -> float:
        """
        Estimate average attempts needed for given difficulty.

        Args:
            fractal_target: Fractal dimension target
            header_bits: Header difficulty bits

        Returns:
            Estimated attempts
        """
        # Header pre-filter probability
        header_probability = 1.0 / (2 ** header_bits)

        # Fractal dimension matching probability (rough estimate)
        # Epsilon of 0.001 gives ~0.002 range (±0.001)
        # Dimension space is roughly 0-2, so probability ~0.001
        fractal_probability = 0.001

        # Combined probability
        combined_probability = header_probability * fractal_probability

        # Average attempts = 1 / probability
        average_attempts = 1.0 / combined_probability if combined_probability > 0 else 1000000

        return average_attempts

    def get_difficulty_stats(self, recent_blocks: List[Block]) -> dict:
        """
        Get difficulty statistics.

        Args:
            recent_blocks: Recent blocks to analyze

        Returns:
            Dictionary of difficulty stats
        """
        if not recent_blocks:
            return {
                'current_fractal_target': 1.5,
                'current_header_bits': 16,
                'estimated_hashrate': 0.0,
                'average_block_time': 0.0,
                'blocks_until_adjustment': 0
            }

        latest_block = recent_blocks[-1]

        # Calculate average block time
        if len(recent_blocks) >= 2:
            time_span = recent_blocks[-1].timestamp - recent_blocks[0].timestamp
            average_block_time = time_span / (len(recent_blocks) - 1)
        else:
            average_block_time = 0.0

        # Estimate hashrate
        hashrate = self.estimate_hashrate(recent_blocks[-100:] if len(recent_blocks) > 100 else recent_blocks)

        # Blocks until next adjustment
        blocks_until_adjustment = self.adjustment_interval - (latest_block.index % self.adjustment_interval)

        return {
            'current_fractal_target': latest_block.difficulty_target,
            'current_header_bits': latest_block.header_difficulty_bits,
            'estimated_hashrate': hashrate,
            'average_block_time': average_block_time,
            'blocks_until_adjustment': blocks_until_adjustment,
            'block_height': latest_block.index
        }
