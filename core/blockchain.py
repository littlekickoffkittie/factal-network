"""
Blockchain implementation for FractalChain.
"""

import json
import sqlite3
import time
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from .block import Block
from .transaction import Transaction
from .crypto import CryptoUtils


class Blockchain:
    """
    Main blockchain data structure.
    Manages chain state, validation, and persistence.
    """

    def __init__(self, db_path: str = "fractalchain.db"):
        """
        Initialize blockchain.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.balances: Dict[str, float] = {}
        self.utxo: Dict[str, List[Transaction]] = {}  # Unspent transaction outputs

        # Initialize database
        self._init_database()

        # Load chain from database
        self._load_chain()

        # Create genesis block if needed
        if len(self.chain) == 0:
            genesis = Block.create_genesis_block()
            self.add_block(genesis)

    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Blocks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocks (
                block_hash TEXT PRIMARY KEY,
                index INTEGER UNIQUE NOT NULL,
                timestamp REAL NOT NULL,
                previous_hash TEXT NOT NULL,
                miner_address TEXT NOT NULL,
                merkle_root TEXT NOT NULL,
                difficulty_target REAL NOT NULL,
                header_difficulty_bits INTEGER NOT NULL,
                block_data TEXT NOT NULL
            )
        ''')

        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                tx_hash TEXT PRIMARY KEY,
                block_hash TEXT NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                amount REAL NOT NULL,
                fee REAL NOT NULL,
                timestamp REAL NOT NULL,
                tx_data TEXT NOT NULL,
                FOREIGN KEY (block_hash) REFERENCES blocks(block_hash)
            )
        ''')

        # Balances table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balances (
                address TEXT PRIMARY KEY,
                balance REAL NOT NULL
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_block_index ON blocks(index)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_sender ON transactions(sender)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_recipient ON transactions(recipient)')

        conn.commit()
        conn.close()

    def _load_chain(self) -> None:
        """Load blockchain from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT block_data FROM blocks ORDER BY index ASC')
        rows = cursor.fetchall()

        for row in rows:
            block_data = json.loads(row[0])
            block = Block.from_dict(block_data)
            self.chain.append(block)

        # Load balances
        cursor.execute('SELECT address, balance FROM balances')
        balance_rows = cursor.fetchall()

        for address, balance in balance_rows:
            self.balances[address] = balance

        conn.close()

    def _save_block(self, block: Block) -> None:
        """
        Save block to database.

        Args:
            block: Block to save
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        block_data_json = json.dumps(block.to_dict())

        cursor.execute('''
            INSERT OR REPLACE INTO blocks
            (block_hash, index, timestamp, previous_hash, miner_address,
             merkle_root, difficulty_target, header_difficulty_bits, block_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            block.block_hash,
            block.index,
            block.timestamp,
            block.previous_hash,
            block.miner_address,
            block.merkle_root,
            block.difficulty_target,
            block.header_difficulty_bits,
            block_data_json
        ))

        # Save transactions
        for tx in block.transactions:
            tx_data_json = json.dumps(tx.to_dict())

            cursor.execute('''
                INSERT OR REPLACE INTO transactions
                (tx_hash, block_hash, sender, recipient, amount, fee, timestamp, tx_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tx.tx_hash,
                block.block_hash,
                tx.sender,
                tx.recipient,
                tx.amount,
                tx.fee,
                tx.timestamp,
                tx_data_json
            ))

        conn.commit()
        conn.close()

    def _update_balances(self, block: Block) -> None:
        """
        Update account balances based on block transactions.

        Args:
            block: Block containing transactions
        """
        for tx in block.transactions:
            # Deduct from sender (except coinbase)
            if tx.sender != "COINBASE" and tx.sender != "GENESIS":
                if tx.sender not in self.balances:
                    self.balances[tx.sender] = 0.0
                self.balances[tx.sender] -= (tx.amount + tx.fee)

            # Add to recipient
            if tx.recipient not in self.balances:
                self.balances[tx.recipient] = 0.0
            self.balances[tx.recipient] += tx.amount

        # Save balances to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for address, balance in self.balances.items():
            cursor.execute('''
                INSERT OR REPLACE INTO balances (address, balance)
                VALUES (?, ?)
            ''', (address, balance))

        conn.commit()
        conn.close()

    def add_block(self, block: Block) -> bool:
        """
        Add a block to the chain.

        Args:
            block: Block to add

        Returns:
            True if block was added successfully
        """
        # Validate block
        previous_block = self.get_latest_block() if len(self.chain) > 0 else None

        if not block.is_valid(previous_block):
            return False

        # Add to chain
        self.chain.append(block)

        # Update balances
        self._update_balances(block)

        # Save to database
        self._save_block(block)

        # Remove transactions from pending pool
        tx_hashes = {tx.tx_hash for tx in block.transactions}
        self.pending_transactions = [
            tx for tx in self.pending_transactions
            if tx.tx_hash not in tx_hashes
        ]

        return True

    def get_latest_block(self) -> Optional[Block]:
        """
        Get the most recent block.

        Returns:
            Latest block or None
        """
        return self.chain[-1] if self.chain else None

    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """
        Get block by hash.

        Args:
            block_hash: Block hash to search for

        Returns:
            Block or None
        """
        for block in self.chain:
            if block.block_hash == block_hash:
                return block
        return None

    def get_block_by_index(self, index: int) -> Optional[Block]:
        """
        Get block by index.

        Args:
            index: Block index

        Returns:
            Block or None
        """
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None

    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Add transaction to pending pool.

        Args:
            transaction: Transaction to add

        Returns:
            True if transaction was added
        """
        # Validate transaction
        if not transaction.is_valid():
            return False

        # Check if sender has sufficient balance (except coinbase)
        if transaction.sender != "COINBASE":
            sender_balance = self.get_balance(transaction.sender)
            required = transaction.amount + transaction.fee

            if sender_balance < required:
                return False

        # Check for duplicate
        if any(tx.tx_hash == transaction.tx_hash for tx in self.pending_transactions):
            return False

        self.pending_transactions.append(transaction)
        return True

    def get_balance(self, address: str) -> float:
        """
        Get balance for an address.

        Args:
            address: Address to query

        Returns:
            Balance
        """
        # Start with confirmed balance
        balance = self.balances.get(address, 0.0)

        # Subtract pending outgoing transactions
        for tx in self.pending_transactions:
            if tx.sender == address:
                balance -= (tx.amount + tx.fee)

        return balance

    def get_pending_transactions(self, max_count: int = 100) -> List[Transaction]:
        """
        Get pending transactions for mining.

        Args:
            max_count: Maximum number of transactions

        Returns:
            List of pending transactions
        """
        # Sort by fee (highest first)
        sorted_txs = sorted(
            self.pending_transactions,
            key=lambda tx: tx.fee,
            reverse=True
        )

        return sorted_txs[:max_count]

    def is_valid_chain(self) -> bool:
        """
        Validate the entire blockchain.

        Returns:
            True if chain is valid
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if not current_block.is_valid(previous_block):
                return False

        return True

    def get_chain_length(self) -> int:
        """Get the length of the blockchain."""
        return len(self.chain)

    def get_difficulty(self) -> Tuple[float, int]:
        """
        Get current mining difficulty.

        Returns:
            Tuple of (fractal_dimension_target, header_difficulty_bits)
        """
        latest_block = self.get_latest_block()
        if latest_block:
            return latest_block.difficulty_target, latest_block.header_difficulty_bits

        # Default difficulty
        return 1.5, 16

    def get_block_reward(self) -> float:
        """
        Calculate current block reward.
        Implements halving every 210,000 blocks (like Bitcoin).

        Returns:
            Block reward amount
        """
        height = self.get_chain_length()
        halvings = height // 210000

        initial_reward = 50.0
        reward = initial_reward / (2 ** halvings)

        return max(reward, 0.00000001)  # Minimum reward
