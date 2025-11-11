"""
Staking system for FractalChain.
Allows token holders to stake coins and earn rewards.
"""

import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class StakePosition:
    """Represents a staking position."""

    address: str
    amount: float
    start_time: float
    lock_period: int  # in blocks
    unlock_block: int
    rewards_earned: float = 0.0
    status: str = "active"  # active, unlocking, withdrawn

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'StakePosition':
        """Create from dictionary."""
        return StakePosition(**data)


@dataclass
class ValidatorSlash:
    """Record of a validator being slashed."""

    address: str
    block_index: int
    slash_amount: float
    reason: str
    timestamp: float

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class StakingSystem:
    """
    Manages staking positions and rewards distribution.
    """

    def __init__(
        self,
        min_stake_amount: float = 100.0,
        min_lock_period: int = 1000,  # blocks
        annual_return_rate: float = 0.05,  # 5% APR
        slash_percentage: float = 0.10  # 10% slash for fraud
    ):
        """
        Initialize staking system.

        Args:
            min_stake_amount: Minimum amount to stake
            min_lock_period: Minimum lock period in blocks
            annual_return_rate: Annual percentage return
            slash_percentage: Percentage to slash for fraud
        """
        self.min_stake_amount = min_stake_amount
        self.min_lock_period = min_lock_period
        self.annual_return_rate = annual_return_rate
        self.slash_percentage = slash_percentage

        self.stakes: Dict[str, List[StakePosition]] = {}
        self.total_staked = 0.0
        self.slash_history: List[ValidatorSlash] = []

        # Blocks per year (assuming 10 minute block time)
        self.blocks_per_year = 365 * 24 * 6

    def create_stake(
        self,
        address: str,
        amount: float,
        lock_period: int,
        current_block: int
    ) -> Tuple[bool, str]:
        """
        Create a new stake position.

        Args:
            address: Staker address
            amount: Amount to stake
            lock_period: Lock period in blocks
            current_block: Current block height

        Returns:
            Tuple of (success, message)
        """
        # Validate amount
        if amount < self.min_stake_amount:
            return False, f"Minimum stake is {self.min_stake_amount}"

        # Validate lock period
        if lock_period < self.min_lock_period:
            return False, f"Minimum lock period is {self.min_lock_period} blocks"

        # Create stake position
        stake = StakePosition(
            address=address,
            amount=amount,
            start_time=time.time(),
            lock_period=lock_period,
            unlock_block=current_block + lock_period
        )

        # Add to stakes
        if address not in self.stakes:
            self.stakes[address] = []

        self.stakes[address].append(stake)
        self.total_staked += amount

        return True, f"Staked {amount} tokens for {lock_period} blocks"

    def calculate_rewards(
        self,
        stake: StakePosition,
        current_block: int
    ) -> float:
        """
        Calculate rewards for a stake position.

        Args:
            stake: Stake position
            current_block: Current block height

        Returns:
            Rewards amount
        """
        if stake.status != "active":
            return 0.0

        # Calculate blocks elapsed
        blocks_elapsed = min(
            current_block - (stake.unlock_block - stake.lock_period),
            stake.lock_period
        )

        if blocks_elapsed <= 0:
            return 0.0

        # Calculate rewards based on APR
        years_elapsed = blocks_elapsed / self.blocks_per_year
        rewards = stake.amount * self.annual_return_rate * years_elapsed

        return rewards

    def update_rewards(self, current_block: int) -> None:
        """
        Update rewards for all active stakes.

        Args:
            current_block: Current block height
        """
        for address, positions in self.stakes.items():
            for stake in positions:
                if stake.status == "active":
                    stake.rewards_earned = self.calculate_rewards(stake, current_block)

    def initiate_withdrawal(
        self,
        address: str,
        stake_index: int,
        current_block: int
    ) -> Tuple[bool, str]:
        """
        Initiate withdrawal of a stake.

        Args:
            address: Staker address
            stake_index: Index of stake position
            current_block: Current block height

        Returns:
            Tuple of (success, message)
        """
        if address not in self.stakes:
            return False, "No stakes found"

        if stake_index >= len(self.stakes[address]):
            return False, "Invalid stake index"

        stake = self.stakes[address][stake_index]

        if stake.status != "active":
            return False, "Stake not active"

        if current_block < stake.unlock_block:
            return False, f"Stake locked until block {stake.unlock_block}"

        # Update rewards
        stake.rewards_earned = self.calculate_rewards(stake, current_block)
        stake.status = "unlocking"

        return True, f"Initiated withdrawal of {stake.amount + stake.rewards_earned} tokens"

    def complete_withdrawal(
        self,
        address: str,
        stake_index: int
    ) -> Tuple[bool, float, str]:
        """
        Complete withdrawal of a stake.

        Args:
            address: Staker address
            stake_index: Index of stake position

        Returns:
            Tuple of (success, amount, message)
        """
        if address not in self.stakes:
            return False, 0.0, "No stakes found"

        if stake_index >= len(self.stakes[address]):
            return False, 0.0, "Invalid stake index"

        stake = self.stakes[address][stake_index]

        if stake.status != "unlocking":
            return False, 0.0, "Stake not in unlocking state"

        # Calculate total withdrawal
        total_amount = stake.amount + stake.rewards_earned

        # Update state
        stake.status = "withdrawn"
        self.total_staked -= stake.amount

        return True, total_amount, f"Withdrew {total_amount} tokens"

    def slash_validator(
        self,
        address: str,
        block_index: int,
        reason: str
    ) -> Tuple[bool, float, str]:
        """
        Slash a validator for fraud or invalid blocks.

        Args:
            address: Validator address
            block_index: Block where fraud occurred
            reason: Reason for slashing

        Returns:
            Tuple of (success, slashed_amount, message)
        """
        if address not in self.stakes:
            return False, 0.0, "No stakes found for validator"

        total_slashed = 0.0

        # Slash all active stakes
        for stake in self.stakes[address]:
            if stake.status == "active":
                slash_amount = stake.amount * self.slash_percentage
                stake.amount -= slash_amount
                total_slashed += slash_amount

                # If stake falls below minimum, deactivate
                if stake.amount < self.min_stake_amount:
                    stake.status = "slashed"
                    self.total_staked -= stake.amount

        # Record slash
        slash_record = ValidatorSlash(
            address=address,
            block_index=block_index,
            slash_amount=total_slashed,
            reason=reason,
            timestamp=time.time()
        )
        self.slash_history.append(slash_record)

        return True, total_slashed, f"Slashed {total_slashed} tokens from {address}"

    def get_stake_positions(self, address: str) -> List[StakePosition]:
        """
        Get all stake positions for an address.

        Args:
            address: Staker address

        Returns:
            List of stake positions
        """
        return self.stakes.get(address, [])

    def get_total_staked_by_address(self, address: str) -> float:
        """
        Get total amount staked by an address.

        Args:
            address: Staker address

        Returns:
            Total staked amount
        """
        total = 0.0
        for stake in self.stakes.get(address, []):
            if stake.status == "active":
                total += stake.amount
        return total

    def get_staking_power(self, address: str) -> float:
        """
        Get staking power (weighted by amount and duration).

        Args:
            address: Staker address

        Returns:
            Staking power
        """
        power = 0.0

        for stake in self.stakes.get(address, []):
            if stake.status == "active":
                # Weight by lock period (longer = more power)
                duration_multiplier = 1.0 + (stake.lock_period / self.blocks_per_year)
                power += stake.amount * duration_multiplier

        return power

    def get_top_stakers(self, count: int = 10) -> List[Tuple[str, float]]:
        """
        Get top stakers by staking power.

        Args:
            count: Number of top stakers to return

        Returns:
            List of (address, staking_power) tuples
        """
        staker_powers = []

        for address in self.stakes.keys():
            power = self.get_staking_power(address)
            if power > 0:
                staker_powers.append((address, power))

        staker_powers.sort(key=lambda x: x[1], reverse=True)
        return staker_powers[:count]

    def get_statistics(self) -> Dict:
        """
        Get staking statistics.

        Returns:
            Dictionary of statistics
        """
        active_stakes = sum(
            len([s for s in positions if s.status == "active"])
            for positions in self.stakes.values()
        )

        total_stakers = len([
            addr for addr, positions in self.stakes.items()
            if any(s.status == "active" for s in positions)
        ])

        return {
            'total_staked': self.total_staked,
            'active_stakes': active_stakes,
            'total_stakers': total_stakers,
            'min_stake_amount': self.min_stake_amount,
            'annual_return_rate': self.annual_return_rate,
            'total_slashed': sum(s.slash_amount for s in self.slash_history)
        }

    def save_state(self, filepath: str) -> None:
        """Save staking state to file."""
        state = {
            'stakes': {
                addr: [stake.to_dict() for stake in positions]
                for addr, positions in self.stakes.items()
            },
            'total_staked': self.total_staked,
            'slash_history': [slash.to_dict() for slash in self.slash_history]
        }

        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self, filepath: str) -> None:
        """Load staking state from file."""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)

            self.stakes = {
                addr: [StakePosition.from_dict(stake) for stake in positions]
                for addr, positions in state['stakes'].items()
            }
            self.total_staked = state['total_staked']
            self.slash_history = [
                ValidatorSlash(**slash) for slash in state['slash_history']
            ]

        except FileNotFoundError:
            pass  # Start with empty state
