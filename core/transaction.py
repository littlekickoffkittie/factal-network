"""
Transaction implementation for FractalChain.
"""

import time
import json
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from .crypto import CryptoUtils


@dataclass
class Transaction:
    """Represents a transaction in FractalChain."""

    sender: str  # Address
    recipient: str  # Address
    amount: float
    fee: float
    timestamp: float
    signature: str = ""
    public_key: str = ""
    tx_hash: str = ""

    def __post_init__(self):
        """Calculate transaction hash if not provided."""
        if not self.tx_hash:
            self.tx_hash = self.calculate_hash()

    def to_dict(self, include_signature: bool = True) -> Dict:
        """
        Convert transaction to dictionary.

        Args:
            include_signature: Whether to include signature

        Returns:
            Dictionary representation
        """
        data = {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp,
        }

        if include_signature:
            data['signature'] = self.signature
            data['public_key'] = self.public_key

        return data

    def calculate_hash(self) -> str:
        """
        Calculate transaction hash (excluding signature).

        Returns:
            Transaction hash
        """
        data = self.to_dict(include_signature=False)
        return CryptoUtils.hash_object(data)

    def sign(self, keypair) -> None:
        """
        Sign the transaction.

        Args:
            keypair: KeyPair instance for signing
        """
        message = json.dumps(self.to_dict(include_signature=False), sort_keys=True)
        self.signature = keypair.sign(message)
        self.public_key = keypair.export_public_key()
        self.tx_hash = self.calculate_hash()

    def verify_signature(self) -> bool:
        """
        Verify transaction signature.

        Returns:
            True if signature is valid
        """
        if not self.signature or not self.public_key:
            return False

        message = json.dumps(self.to_dict(include_signature=False), sort_keys=True)

        from .crypto import KeyPair
        return KeyPair.verify(message, self.signature, self.sender, self.public_key)

    def is_valid(self) -> bool:
        """
        Validate transaction.

        Returns:
            True if transaction is valid
        """
        # Check basic validity
        if self.amount <= 0:
            return False

        if self.fee < 0:
            return False

        # Coinbase transactions (mining rewards) don't need signature
        if self.sender == "COINBASE":
            return True

        # Verify signature
        return self.verify_signature()

    @staticmethod
    def create_coinbase(miner_address: str, block_reward: float, block_height: int) -> 'Transaction':
        """
        Create a coinbase transaction (mining reward).

        Args:
            miner_address: Address receiving the reward
            block_reward: Amount of reward
            block_height: Height of the block

        Returns:
            Coinbase transaction
        """
        return Transaction(
            sender="COINBASE",
            recipient=miner_address,
            amount=block_reward,
            fee=0.0,
            timestamp=time.time(),
            signature=f"coinbase_block_{block_height}",
            public_key="",
        )

    @staticmethod
    def from_dict(data: Dict) -> 'Transaction':
        """
        Create transaction from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Transaction instance
        """
        return Transaction(
            sender=data['sender'],
            recipient=data['recipient'],
            amount=data['amount'],
            fee=data['fee'],
            timestamp=data['timestamp'],
            signature=data.get('signature', ''),
            public_key=data.get('public_key', ''),
            tx_hash=data.get('tx_hash', '')
        )
