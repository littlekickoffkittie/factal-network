"""
Tests for core blockchain components.
"""

import pytest
import time
from core.block import Block, FractalProof
from core.transaction import Transaction
from core.blockchain import Blockchain
from core.crypto import KeyPair, CryptoUtils
from core.merkle import MerkleTree, compute_merkle_root


class TestCrypto:
    """Tests for cryptographic utilities."""

    def test_sha256_hash(self):
        """Test SHA-256 hashing."""
        data = "test data"
        hash1 = CryptoUtils.sha256(data)
        hash2 = CryptoUtils.sha256(data)

        assert hash1 == hash2
        assert len(hash1) == 64  # Hex string

    def test_keypair_generation(self):
        """Test key pair generation."""
        keypair = KeyPair()

        assert keypair.private_key is not None
        assert keypair.public_key is not None

        address = keypair.get_address()
        assert len(address) == 40  # RIPEMD160 hex

    def test_signature_verification(self):
        """Test signature creation and verification."""
        keypair = KeyPair()
        message = "test message"

        signature = keypair.sign(message)
        assert len(signature) > 0

        # Verify with correct data
        is_valid = KeyPair.verify(
            message,
            signature,
            keypair.get_address(),
            keypair.export_public_key()
        )
        assert is_valid

        # Verify with wrong message
        is_valid = KeyPair.verify(
            "wrong message",
            signature,
            keypair.get_address(),
            keypair.export_public_key()
        )
        assert not is_valid

    def test_keypair_export_import(self):
        """Test key pair export and import."""
        keypair1 = KeyPair()
        private_key_hex = keypair1.export_private_key()

        keypair2 = KeyPair.from_private_key_hex(private_key_hex)

        assert keypair1.get_address() == keypair2.get_address()
        assert keypair1.export_public_key() == keypair2.export_public_key()


class TestMerkleTree:
    """Tests for Merkle tree."""

    def test_merkle_tree_creation(self):
        """Test Merkle tree creation."""
        transactions = ["tx1", "tx2", "tx3", "tx4"]
        tree = MerkleTree(transactions)

        assert tree.get_root() is not None
        assert len(tree.get_root()) == 64

    def test_merkle_proof(self):
        """Test Merkle proof generation and verification."""
        transactions = ["tx1", "tx2", "tx3", "tx4"]
        tree = MerkleTree(transactions)

        # Get proof for first transaction
        proof = tree.get_proof("tx1")
        assert proof is not None

        # Verify proof
        is_valid = MerkleTree.verify_proof("tx1", tree.get_root(), proof)
        assert is_valid

    def test_merkle_tree_deterministic(self):
        """Test that Merkle tree is deterministic."""
        transactions = ["tx1", "tx2", "tx3"]

        tree1 = MerkleTree(transactions)
        tree2 = MerkleTree(transactions)

        assert tree1.get_root() == tree2.get_root()

    def test_merkle_tree_odd_count(self):
        """Test Merkle tree with odd number of transactions."""
        transactions = ["tx1", "tx2", "tx3"]
        tree = MerkleTree(transactions)

        assert tree.get_root() is not None


class TestTransaction:
    """Tests for transactions."""

    def test_transaction_creation(self):
        """Test transaction creation."""
        tx = Transaction(
            sender="alice",
            recipient="bob",
            amount=10.0,
            fee=0.1,
            timestamp=time.time()
        )

        assert tx.sender == "alice"
        assert tx.recipient == "bob"
        assert tx.amount == 10.0
        assert tx.tx_hash is not None

    def test_transaction_signing(self):
        """Test transaction signing."""
        keypair = KeyPair()

        tx = Transaction(
            sender=keypair.get_address(),
            recipient="bob",
            amount=10.0,
            fee=0.1,
            timestamp=time.time()
        )

        tx.sign(keypair)

        assert tx.signature != ""
        assert tx.public_key != ""
        assert tx.verify_signature()

    def test_transaction_validation(self):
        """Test transaction validation."""
        keypair = KeyPair()

        # Valid transaction
        tx = Transaction(
            sender=keypair.get_address(),
            recipient="bob",
            amount=10.0,
            fee=0.1,
            timestamp=time.time()
        )
        tx.sign(keypair)

        assert tx.is_valid()

        # Invalid (negative amount)
        tx_invalid = Transaction(
            sender=keypair.get_address(),
            recipient="bob",
            amount=-10.0,
            fee=0.1,
            timestamp=time.time()
        )

        assert not tx_invalid.is_valid()

    def test_coinbase_transaction(self):
        """Test coinbase transaction."""
        tx = Transaction.create_coinbase("miner_address", 50.0, 1)

        assert tx.sender == "COINBASE"
        assert tx.recipient == "miner_address"
        assert tx.amount == 50.0
        assert tx.is_valid()


class TestBlock:
    """Tests for blocks."""

    def test_genesis_block(self):
        """Test genesis block creation."""
        genesis = Block.create_genesis_block()

        assert genesis.index == 0
        assert genesis.previous_hash == "0" * 64
        assert len(genesis.transactions) == 1
        assert genesis.transactions[0].sender == "GENESIS"

    def test_block_hash_calculation(self):
        """Test block hash calculation."""
        block = Block(
            index=1,
            timestamp=time.time(),
            transactions=[],
            previous_hash="prev_hash",
            miner_address="miner"
        )

        hash1 = block.calculate_hash()
        hash2 = block.calculate_hash()

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_block_with_transactions(self):
        """Test block with transactions."""
        tx1 = Transaction.create_coinbase("miner", 50.0, 1)

        block = Block(
            index=1,
            timestamp=time.time(),
            transactions=[tx1],
            previous_hash="prev_hash",
            miner_address="miner"
        )

        assert len(block.transactions) == 1
        assert block.merkle_root is not None

    def test_block_validation(self):
        """Test block validation."""
        genesis = Block.create_genesis_block()
        assert genesis.is_valid()

        # Create next block
        tx = Transaction.create_coinbase("miner", 50.0, 1)

        block = Block(
            index=1,
            timestamp=time.time(),
            transactions=[tx],
            previous_hash=genesis.block_hash,
            miner_address="miner"
        )
        block.block_hash = block.calculate_hash()

        assert block.is_valid(genesis)


class TestBlockchain:
    """Tests for blockchain."""

    def test_blockchain_initialization(self):
        """Test blockchain initialization."""
        blockchain = Blockchain(":memory:")

        assert blockchain.get_chain_length() == 1
        assert blockchain.get_latest_block().index == 0

    def test_add_block(self):
        """Test adding blocks."""
        blockchain = Blockchain(":memory:")

        # Create and add block
        tx = Transaction.create_coinbase("miner", 50.0, 1)

        block = Block(
            index=1,
            timestamp=time.time(),
            transactions=[tx],
            previous_hash=blockchain.get_latest_block().block_hash,
            miner_address="miner"
        )
        block.block_hash = block.calculate_hash()

        assert blockchain.add_block(block)
        assert blockchain.get_chain_length() == 2

    def test_get_balance(self):
        """Test balance retrieval."""
        blockchain = Blockchain(":memory:")

        # Initially zero
        assert blockchain.get_balance("alice") == 0.0

        # Add block with transaction to alice
        tx = Transaction.create_coinbase("alice", 50.0, 1)

        block = Block(
            index=1,
            timestamp=time.time(),
            transactions=[tx],
            previous_hash=blockchain.get_latest_block().block_hash,
            miner_address="miner"
        )
        block.block_hash = block.calculate_hash()

        blockchain.add_block(block)

        assert blockchain.get_balance("alice") == 50.0

    def test_add_transaction(self):
        """Test adding transactions."""
        blockchain = Blockchain(":memory:")

        keypair = KeyPair()
        address = keypair.get_address()

        # Give address some balance
        coinbase = Transaction.create_coinbase(address, 100.0, 1)
        block = Block(
            index=1,
            timestamp=time.time(),
            transactions=[coinbase],
            previous_hash=blockchain.get_latest_block().block_hash,
            miner_address="miner"
        )
        block.block_hash = block.calculate_hash()
        blockchain.add_block(block)

        # Create transaction
        tx = Transaction(
            sender=address,
            recipient="bob",
            amount=10.0,
            fee=0.1,
            timestamp=time.time()
        )
        tx.sign(keypair)

        assert blockchain.add_transaction(tx)
        assert len(blockchain.pending_transactions) == 1

    def test_block_reward_halving(self):
        """Test block reward halving."""
        blockchain = Blockchain(":memory:")

        # Initial reward
        reward1 = blockchain.get_block_reward()
        assert reward1 == 50.0

        # Simulate reaching halving point
        blockchain.chain = [Block.create_genesis_block()] * 210001

        reward2 = blockchain.get_block_reward()
        assert reward2 == 25.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
