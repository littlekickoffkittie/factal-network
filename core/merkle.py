"""
Merkle tree implementation for transaction hashing.
Provides efficient verification of transaction inclusion.
"""

import hashlib
from typing import List, Optional, Tuple
from math import ceil, log2


class MerkleTree:
    """
    Merkle tree for efficient transaction verification.
    """

    def __init__(self, transactions: List[str]):
        """
        Build Merkle tree from transaction hashes.

        Args:
            transactions: List of transaction hashes
        """
        if not transactions:
            raise ValueError("Cannot create Merkle tree with no transactions")

        self.transactions = transactions
        self.tree: List[List[str]] = []
        self.root = self._build_tree()

    def _hash_pair(self, left: str, right: str) -> str:
        """
        Hash a pair of nodes.

        Args:
            left: Left node hash
            right: Right node hash

        Returns:
            Combined hash
        """
        combined = left + right
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def _build_tree(self) -> str:
        """
        Build the Merkle tree.

        Returns:
            Root hash
        """
        current_level = self.transactions.copy()
        self.tree.append(current_level)

        while len(current_level) > 1:
            next_level = []

            # Process pairs
            for i in range(0, len(current_level), 2):
                left = current_level[i]

                # If odd number of nodes, duplicate the last one
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = current_level[i]

                parent_hash = self._hash_pair(left, right)
                next_level.append(parent_hash)

            self.tree.append(next_level)
            current_level = next_level

        return current_level[0]

    def get_root(self) -> str:
        """Get the Merkle root hash."""
        return self.root

    def get_proof(self, transaction_hash: str) -> Optional[List[Tuple[str, str]]]:
        """
        Get Merkle proof for a transaction.

        Args:
            transaction_hash: Transaction hash to prove

        Returns:
            List of (hash, position) tuples forming the proof path,
            or None if transaction not found
        """
        try:
            index = self.transactions.index(transaction_hash)
        except ValueError:
            return None

        proof = []
        current_index = index

        # Traverse up the tree
        for level in range(len(self.tree) - 1):
            current_level = self.tree[level]

            # Determine sibling
            if current_index % 2 == 0:
                # Current node is left child
                if current_index + 1 < len(current_level):
                    sibling = current_level[current_index + 1]
                    position = 'right'
                else:
                    sibling = current_level[current_index]
                    position = 'right'
            else:
                # Current node is right child
                sibling = current_level[current_index - 1]
                position = 'left'

            proof.append((sibling, position))
            current_index = current_index // 2

        return proof

    @staticmethod
    def verify_proof(
        transaction_hash: str,
        merkle_root: str,
        proof: List[Tuple[str, str]]
    ) -> bool:
        """
        Verify a Merkle proof.

        Args:
            transaction_hash: Transaction hash to verify
            merkle_root: Expected Merkle root
            proof: Proof path from get_proof()

        Returns:
            True if proof is valid
        """
        current_hash = transaction_hash

        for sibling_hash, position in proof:
            if position == 'left':
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash

            current_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()

        return current_hash == merkle_root

    def get_tree_height(self) -> int:
        """Get the height of the Merkle tree."""
        return len(self.tree)

    def get_level(self, level: int) -> List[str]:
        """
        Get all hashes at a specific level.

        Args:
            level: Tree level (0 = leaves)

        Returns:
            List of hashes at that level
        """
        if level < 0 or level >= len(self.tree):
            raise ValueError(f"Invalid level {level}")
        return self.tree[level]


def compute_merkle_root(transaction_hashes: List[str]) -> str:
    """
    Compute Merkle root from transaction hashes.

    Args:
        transaction_hashes: List of transaction hashes

    Returns:
        Merkle root hash
    """
    if not transaction_hashes:
        return hashlib.sha256(b'').hexdigest()

    tree = MerkleTree(transaction_hashes)
    return tree.get_root()
