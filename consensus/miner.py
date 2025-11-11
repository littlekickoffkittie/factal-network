"""
Mining implementation for FractalChain.
Implements the complete FractalPoW mining loop.
"""

import time
import logging
from typing import Optional, Callable
from ..core.block import Block, FractalProof
from ..core.transaction import Transaction
from ..core.blockchain import Blockchain
from ..core.crypto import CryptoUtils, KeyPair
from .fractal_math import FractalProofOfWork, FractalConfig
import numpy as np


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Miner:
    """
    FractalChain miner implementation.
    """

    def __init__(
        self,
        blockchain: Blockchain,
        keypair: KeyPair,
        fractal_config: FractalConfig = None
    ):
        """
        Initialize miner.

        Args:
            blockchain: Blockchain instance
            keypair: Miner's key pair
            fractal_config: Fractal configuration
        """
        self.blockchain = blockchain
        self.keypair = keypair
        self.miner_address = keypair.get_address()
        self.fractal_pow = FractalProofOfWork(fractal_config or FractalConfig())
        self.is_mining = False
        self.hashrate = 0.0
        self.blocks_mined = 0

    def mine_block(
        self,
        max_iterations: int = 10000,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Optional[Block]:
        """
        Mine a new block using FractalPoW.

        Args:
            max_iterations: Maximum mining iterations
            progress_callback: Optional callback for progress updates

        Returns:
            Mined block or None
        """
        self.is_mining = True
        start_time = time.time()

        try:
            # Get pending transactions
            transactions = self.blockchain.get_pending_transactions(max_count=100)

            # Create coinbase transaction
            block_reward = self.blockchain.get_block_reward()
            total_fees = sum(tx.fee for tx in transactions)
            coinbase = Transaction.create_coinbase(
                self.miner_address,
                block_reward + total_fees,
                self.blockchain.get_chain_length()
            )

            # Add coinbase as first transaction
            transactions = [coinbase] + transactions

            # Get blockchain state
            latest_block = self.blockchain.get_latest_block()
            previous_hash = latest_block.block_hash if latest_block else "0" * 64
            block_index = latest_block.index + 1 if latest_block else 0
            difficulty_target, header_difficulty = self.blockchain.get_difficulty()

            # Create candidate block
            candidate_block = Block(
                index=block_index,
                timestamp=time.time(),
                transactions=transactions,
                previous_hash=previous_hash,
                miner_address=self.miner_address,
                difficulty_target=difficulty_target,
                header_difficulty_bits=header_difficulty,
            )

            candidate_block.merkle_root = candidate_block.calculate_merkle_root()

            logger.info(f"Mining block {block_index} with {len(transactions)} transactions")
            logger.info(f"Target dimension: {difficulty_target}, Header difficulty: {header_difficulty} bits")

            # Mining loop
            nonce = 0
            attempts = 0

            while self.is_mining and attempts < max_iterations:
                nonce += 1
                attempts += 1

                # Generate fractal seed
                fractal_seed = self.fractal_pow.generate_fractal_seed(
                    previous_hash,
                    self.miner_address,
                    nonce
                )

                # Update candidate block timestamp
                candidate_block.timestamp = time.time()

                # Calculate header hash for pre-filter
                temp_proof = FractalProof(
                    nonce=nonce,
                    fractal_seed=fractal_seed,
                    solution_point_real=0.0,
                    solution_point_imag=0.0,
                    fractal_dimension=0.0,
                    fractal_data_hash="",
                    timestamp=candidate_block.timestamp
                )
                candidate_block.fractal_proof = temp_proof
                header_hash = candidate_block.calculate_header_hash()

                # Pre-filter: check header hash
                if not self.fractal_pow.verify_header_hash(header_hash, header_difficulty):
                    if attempts % 1000 == 0 and progress_callback:
                        progress_callback(attempts, "Searching for valid header...")
                    continue

                logger.info(f"Found valid header at nonce {nonce}! Computing fractal...")

                # Find fractal solution
                solution = self.fractal_pow.find_fractal_solution(
                    fractal_seed,
                    target_dimension=difficulty_target,
                    epsilon=self.fractal_pow.config.epsilon,
                    max_attempts=100
                )

                if solution:
                    solution_point, dimension, bitmap = solution

                    # Calculate fractal data hash
                    fractal_data_hash = CryptoUtils.sha256_bytes(bitmap.tobytes())

                    # Create complete proof
                    fractal_proof = FractalProof(
                        nonce=nonce,
                        fractal_seed=fractal_seed,
                        solution_point_real=solution_point.real,
                        solution_point_imag=solution_point.imag,
                        fractal_dimension=dimension,
                        fractal_data_hash=fractal_data_hash,
                        timestamp=time.time()
                    )

                    candidate_block.fractal_proof = fractal_proof
                    candidate_block.block_hash = candidate_block.calculate_hash()

                    # Calculate hashrate
                    elapsed = time.time() - start_time
                    self.hashrate = attempts / elapsed if elapsed > 0 else 0

                    logger.info(f"Block mined successfully!")
                    logger.info(f"Nonce: {nonce}")
                    logger.info(f"Dimension: {dimension:.6f}")
                    logger.info(f"Attempts: {attempts}")
                    logger.info(f"Time: {elapsed:.2f}s")
                    logger.info(f"Hashrate: {self.hashrate:.2f} attempts/s")

                    self.blocks_mined += 1
                    return candidate_block

                if attempts % 100 == 0 and progress_callback:
                    progress_callback(attempts, f"Testing nonce {nonce}...")

            logger.info(f"Mining stopped after {attempts} attempts")
            return None

        except Exception as e:
            logger.error(f"Mining error: {e}")
            return None

        finally:
            self.is_mining = False

    def stop_mining(self) -> None:
        """Stop the mining process."""
        self.is_mining = False
        logger.info("Mining stopped by user")

    def get_hashrate(self) -> float:
        """
        Get current mining hashrate.

        Returns:
            Hashrate in attempts per second
        """
        return self.hashrate

    def get_mining_stats(self) -> dict:
        """
        Get mining statistics.

        Returns:
            Dictionary of mining stats
        """
        return {
            'is_mining': self.is_mining,
            'hashrate': self.hashrate,
            'blocks_mined': self.blocks_mined,
            'miner_address': self.miner_address,
            'balance': self.blockchain.get_balance(self.miner_address)
        }


class MiningPool:
    """
    Simple mining pool implementation for collaborative mining.
    """

    def __init__(self, pool_address: str):
        """
        Initialize mining pool.

        Args:
            pool_address: Pool's payout address
        """
        self.pool_address = pool_address
        self.miners: dict = {}  # address -> contribution
        self.total_shares = 0

    def add_share(self, miner_address: str, difficulty: float) -> None:
        """
        Add a mining share from a miner.

        Args:
            miner_address: Miner's address
            difficulty: Difficulty of the share
        """
        if miner_address not in self.miners:
            self.miners[miner_address] = 0.0

        self.miners[miner_address] += difficulty
        self.total_shares += difficulty

    def distribute_reward(self, block_reward: float) -> dict:
        """
        Distribute block reward to miners based on shares.

        Args:
            block_reward: Total reward to distribute

        Returns:
            Dictionary of address -> payout amount
        """
        if self.total_shares == 0:
            return {}

        payouts = {}

        for miner_address, shares in self.miners.items():
            proportion = shares / self.total_shares
            payout = block_reward * proportion
            payouts[miner_address] = payout

        # Reset shares
        self.miners.clear()
        self.total_shares = 0

        return payouts

    def get_pool_stats(self) -> dict:
        """
        Get mining pool statistics.

        Returns:
            Dictionary of pool stats
        """
        return {
            'pool_address': self.pool_address,
            'total_miners': len(self.miners),
            'total_shares': self.total_shares,
            'miners': self.miners.copy()
        }
