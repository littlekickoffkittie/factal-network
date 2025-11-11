"""
Block implementation for FractalChain.
"""

import time
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from .transaction import Transaction
from .merkle import compute_merkle_root
from .crypto import CryptoUtils


@dataclass
class FractalProof:
    """Proof of work data for a block."""

    nonce: int
    fractal_seed: str
    solution_point_real: float
    solution_point_imag: float
    fractal_dimension: float
    fractal_data_hash: str
    timestamp: float

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'nonce': self.nonce,
            'fractal_seed': self.fractal_seed,
            'solution_point_real': self.solution_point_real,
            'solution_point_imag': self.solution_point_imag,
            'fractal_dimension': self.fractal_dimension,
            'fractal_data_hash': self.fractal_data_hash,
            'timestamp': self.timestamp,
        }

    @staticmethod
    def from_dict(data: Dict) -> 'FractalProof':
        """Create from dictionary."""
        return FractalProof(
            nonce=data['nonce'],
            fractal_seed=data['fractal_seed'],
            solution_point_real=data['solution_point_real'],
            solution_point_imag=data['solution_point_imag'],
            fractal_dimension=data['fractal_dimension'],
            fractal_data_hash=data['fractal_data_hash'],
            timestamp=data['timestamp'],
        )

    def get_solution_point(self) -> complex:
        """Get solution point as complex number."""
        return complex(self.solution_point_real, self.solution_point_imag)


@dataclass
class Block:
    """Represents a block in FractalChain."""

    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    miner_address: str
    fractal_proof: Optional[FractalProof] = None
    merkle_root: str = ""
    block_hash: str = ""
    difficulty_target: float = 1.5
    header_difficulty_bits: int = 16

    def __post_init__(self):
        """Calculate derived fields."""
        if not self.merkle_root:
            self.merkle_root = self.calculate_merkle_root()
        if not self.block_hash and self.fractal_proof:
            self.block_hash = self.calculate_hash()

    def calculate_merkle_root(self) -> str:
        """
        Calculate Merkle root of transactions.

        Returns:
            Merkle root hash
        """
        if not self.transactions:
            return CryptoUtils.sha256("")

        tx_hashes = [tx.tx_hash for tx in self.transactions]
        return compute_merkle_root(tx_hashes)

    def calculate_header_hash(self) -> str:
        """
        Calculate block header hash (for pre-filter).

        Returns:
            Header hash
        """
        header_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'miner_address': self.miner_address,
        }

        if self.fractal_proof:
            header_data['nonce'] = self.fractal_proof.nonce

        return CryptoUtils.hash_object(header_data)

    def calculate_hash(self) -> str:
        """
        Calculate complete block hash.

        Returns:
            Block hash
        """
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'miner_address': self.miner_address,
        }

        if self.fractal_proof:
            block_data['fractal_proof'] = self.fractal_proof.to_dict()

        return CryptoUtils.hash_object(block_data)

    def to_dict(self) -> Dict:
        """
        Convert block to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'miner_address': self.miner_address,
            'fractal_proof': self.fractal_proof.to_dict() if self.fractal_proof else None,
            'merkle_root': self.merkle_root,
            'block_hash': self.block_hash,
            'difficulty_target': self.difficulty_target,
            'header_difficulty_bits': self.header_difficulty_bits,
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Block':
        """
        Create block from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Block instance
        """
        transactions = [Transaction.from_dict(tx) for tx in data['transactions']]

        fractal_proof = None
        if data.get('fractal_proof'):
            fractal_proof = FractalProof.from_dict(data['fractal_proof'])

        return Block(
            index=data['index'],
            timestamp=data['timestamp'],
            transactions=transactions,
            previous_hash=data['previous_hash'],
            miner_address=data['miner_address'],
            fractal_proof=fractal_proof,
            merkle_root=data.get('merkle_root', ''),
            block_hash=data.get('block_hash', ''),
            difficulty_target=data.get('difficulty_target', 1.5),
            header_difficulty_bits=data.get('header_difficulty_bits', 16),
        )

    @staticmethod
    def create_genesis_block() -> 'Block':
        """
        Create the genesis block.

        Returns:
            Genesis block
        """
        genesis_tx = Transaction(
            sender="GENESIS",
            recipient="GENESIS",
            amount=0.0,
            fee=0.0,
            timestamp=1640000000.0,  # Fixed timestamp for genesis
            signature="genesis",
            public_key="",
        )

        genesis_block = Block(
            index=0,
            timestamp=1640000000.0,
            transactions=[genesis_tx],
            previous_hash="0" * 64,
            miner_address="GENESIS",
        )

        # Genesis block doesn't need fractal proof
        genesis_block.merkle_root = genesis_block.calculate_merkle_root()
        genesis_block.block_hash = genesis_block.calculate_hash()

        return genesis_block

    def get_total_fees(self) -> float:
        """
        Calculate total transaction fees in block.

        Returns:
            Total fees
        """
        return sum(tx.fee for tx in self.transactions if tx.sender != "COINBASE")

    def is_valid(self, previous_block: Optional['Block'] = None) -> bool:
        """
        Validate block structure.

        Args:
            previous_block: Previous block for validation

        Returns:
            True if block is valid
        """
        # Genesis block
        if self.index == 0:
            return self.previous_hash == "0" * 64

        # Check previous hash
        if previous_block and self.previous_hash != previous_block.block_hash:
            return False

        # Check index
        if previous_block and self.index != previous_block.index + 1:
            return False

        # Check merkle root
        if self.merkle_root != self.calculate_merkle_root():
            return False

        # Check transactions
        for tx in self.transactions:
            if not tx.is_valid():
                return False

        # Check coinbase transaction
        coinbase_txs = [tx for tx in self.transactions if tx.sender == "COINBASE"]
        if len(coinbase_txs) != 1:
            return False

        # Block hash should match calculated hash
        if self.block_hash != self.calculate_hash():
            return False

        return True
