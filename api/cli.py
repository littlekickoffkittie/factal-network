"""
Command-line interface for FractalChain.
"""

import argparse
import asyncio
import sys
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.blockchain import Blockchain
from core.transaction import Transaction
from core.crypto import KeyPair
from consensus.fractal_math import FractalConfig
from consensus.miner import Miner
from consensus.verification import HybridVerifier
from consensus.difficulty import DifficultyAdjustment
from economic.staking import StakingSystem
from network.p2p import P2PNode
from api.rpc_server import RPCServer
from utils.config import Config


class FractalChainCLI:
    """Command-line interface for FractalChain."""

    def __init__(self):
        """Initialize CLI."""
        self.config = Config()
        self.blockchain = None
        self.miner = None
        self.verifier = None
        self.staking = None
        self.p2p_node = None
        self.keypair = None

    def init_components(self):
        """Initialize blockchain components."""
        # Load configuration
        db_path = self.config.get_db_path()

        # Initialize blockchain
        self.blockchain = Blockchain(db_path)

        # Initialize fractal config
        fractal_cfg = FractalConfig(
            max_iterations=self.config.get('fractal.max_iterations'),
            escape_radius=self.config.get('fractal.escape_radius'),
            grid_size=self.config.get('fractal.grid_size'),
            target_dimension=self.config.get('fractal.target_dimension'),
            epsilon=self.config.get('fractal.epsilon')
        )

        # Initialize verifier
        deepseek_key = self.config.get('verification.deepseek_api_key')
        self.verifier = HybridVerifier(fractal_cfg, deepseek_key)

        # Initialize staking
        staking_cfg = self.config.get_staking_config()
        self.staking = StakingSystem(
            min_stake_amount=staking_cfg['min_stake_amount'],
            min_lock_period=staking_cfg['min_lock_period'],
            annual_return_rate=staking_cfg['annual_return_rate'],
            slash_percentage=staking_cfg['slash_percentage']
        )

    def create_wallet(self, args):
        """Create a new wallet."""
        keypair = KeyPair()
        address = keypair.get_address()

        # Save to keystore
        keystore_path = Path(self.config.get_keystore_path())
        wallet_file = keystore_path / f"{address}.json"

        wallet_data = {
            'address': address,
            'public_key': keypair.export_public_key(),
            'private_key': keypair.export_private_key()
        }

        with open(wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=2)

        print(f"Created new wallet:")
        print(f"  Address: {address}")
        print(f"  Saved to: {wallet_file}")
        print(f"\nWARNING: Keep your private key secure!")

    def get_balance(self, args):
        """Get balance for an address."""
        self.init_components()

        balance = self.blockchain.get_balance(args.address)
        print(f"Balance for {args.address}: {balance} FRC")

    def send_transaction(self, args):
        """Send a transaction."""
        self.init_components()

        # Load wallet
        keystore_path = Path(self.config.get_keystore_path())
        wallet_file = keystore_path / f"{args.from_address}.json"

        if not wallet_file.exists():
            print(f"Error: Wallet not found for {args.from_address}")
            return

        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)

        # Create keypair
        keypair = KeyPair.from_private_key_hex(wallet_data['private_key'])

        # Check balance
        balance = self.blockchain.get_balance(args.from_address)
        required = args.amount + args.fee

        if balance < required:
            print(f"Error: Insufficient balance ({balance} < {required})")
            return

        # Create transaction
        tx = Transaction(
            sender=args.from_address,
            recipient=args.to_address,
            amount=args.amount,
            fee=args.fee,
            timestamp=time.time()
        )

        tx.sign(keypair)

        # Add to blockchain
        if self.blockchain.add_transaction(tx):
            print(f"Transaction sent successfully!")
            print(f"  TX Hash: {tx.tx_hash}")
            print(f"  Amount: {args.amount} FRC")
            print(f"  Fee: {args.fee} FRC")
        else:
            print("Error: Transaction rejected")

    def get_blockchain_info(self, args):
        """Get blockchain information."""
        self.init_components()

        latest_block = self.blockchain.get_latest_block()
        difficulty_target, header_bits = self.blockchain.get_difficulty()

        print("Blockchain Information:")
        print(f"  Chain Length: {self.blockchain.get_chain_length()}")
        print(f"  Latest Block: {latest_block.block_hash if latest_block else 'N/A'}")
        print(f"  Latest Index: {latest_block.index if latest_block else 0}")
        print(f"  Difficulty Target: {difficulty_target}")
        print(f"  Header Difficulty: {header_bits} bits")
        print(f"  Block Reward: {self.blockchain.get_block_reward()} FRC")

    def get_block(self, args):
        """Get block information."""
        self.init_components()

        if args.hash:
            block = self.blockchain.get_block_by_hash(args.hash)
        else:
            block = self.blockchain.get_block_by_index(args.index)

        if block:
            print(json.dumps(block.to_dict(), indent=2))
        else:
            print("Block not found")

    def mine(self, args):
        """Start mining."""
        self.init_components()

        # Load wallet
        keystore_path = Path(self.config.get_keystore_path())
        wallet_file = keystore_path / f"{args.address}.json"

        if not wallet_file.exists():
            print(f"Error: Wallet not found for {args.address}")
            return

        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)

        keypair = KeyPair.from_private_key_hex(wallet_data['private_key'])

        # Create fractal config
        fractal_cfg = FractalConfig(
            max_iterations=self.config.get('fractal.max_iterations'),
            escape_radius=self.config.get('fractal.escape_radius'),
            grid_size=self.config.get('fractal.grid_size'),
            target_dimension=self.config.get('fractal.target_dimension'),
            epsilon=self.config.get('fractal.epsilon')
        )

        # Create miner
        miner = Miner(self.blockchain, keypair, fractal_cfg)

        print(f"Mining with address: {args.address}")
        print(f"Max iterations: {args.iterations}")

        # Mine block
        def progress_callback(attempts, status):
            if attempts % 100 == 0:
                print(f"  [{attempts}] {status}")

        block = miner.mine_block(
            max_iterations=args.iterations,
            progress_callback=progress_callback
        )

        if block:
            # Verify and add
            previous_block = self.blockchain.get_latest_block()
            is_valid, message, _ = self.verifier.verify_block(block, previous_block)

            if is_valid:
                self.blockchain.add_block(block)
                print(f"\nBlock mined successfully!")
                print(f"  Block Index: {block.index}")
                print(f"  Block Hash: {block.block_hash}")
                print(f"  Dimension: {block.fractal_proof.fractal_dimension:.6f}")
                print(f"  Reward: {self.blockchain.get_block_reward()} FRC")
            else:
                print(f"\nMined invalid block: {message}")
        else:
            print("\nMining stopped or failed")

    def stake(self, args):
        """Create a stake."""
        self.init_components()

        current_block = self.blockchain.get_chain_length()
        success, message = self.staking.create_stake(
            args.address,
            args.amount,
            args.lock_period,
            current_block
        )

        if success:
            print(f"Staking successful: {message}")
        else:
            print(f"Staking failed: {message}")

    def get_stake_info(self, args):
        """Get staking information."""
        self.init_components()

        positions = self.staking.get_stake_positions(args.address)

        print(f"Stake positions for {args.address}:")
        for i, pos in enumerate(positions):
            print(f"\n  Position {i}:")
            print(f"    Amount: {pos.amount} FRC")
            print(f"    Status: {pos.status}")
            print(f"    Unlock Block: {pos.unlock_block}")
            print(f"    Rewards: {pos.rewards_earned} FRC")

    def start_node(self, args):
        """Start a full node."""
        self.init_components()

        # Get network config
        net_cfg = self.config.get_network_config()

        # Create P2P node
        self.p2p_node = P2PNode(
            host=net_cfg['host'],
            port=net_cfg['port'],
            blockchain=self.blockchain,
            verifier=self.verifier,
            bootstrap_peers=net_cfg['bootstrap_peers']
        )

        # Create RPC server if enabled
        rpc_server = None
        if self.config.get('api.enabled'):
            api_cfg = self.config.get_api_config()
            rpc_server = RPCServer(
                blockchain=self.blockchain,
                verifier=self.verifier,
                staking=self.staking,
                p2p_node=self.p2p_node,
                host=api_cfg['host'],
                port=api_cfg['port']
            )

        async def run_node():
            """Run the node."""
            # Start P2P node
            await self.p2p_node.start()

            # Start RPC server in background
            if rpc_server:
                import threading
                rpc_thread = threading.Thread(target=rpc_server.start)
                rpc_thread.daemon = True
                rpc_thread.start()

            print(f"Node started:")
            print(f"  P2P: {net_cfg['host']}:{net_cfg['port']}")
            if rpc_server:
                print(f"  RPC: {api_cfg['host']}:{api_cfg['port']}")

            # Keep running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
                await self.p2p_node.stop()

        # Run
        asyncio.run(run_node())

    def run(self):
        """Run the CLI."""
        parser = argparse.ArgumentParser(description='FractalChain CLI')
        subparsers = parser.add_subparsers(dest='command', help='Command to execute')

        # Wallet commands
        wallet_parser = subparsers.add_parser('wallet', help='Wallet commands')
        wallet_sub = wallet_parser.add_subparsers(dest='wallet_command')

        wallet_sub.add_parser('create', help='Create new wallet')

        balance_parser = wallet_sub.add_parser('balance', help='Get balance')
        balance_parser.add_argument('address', help='Wallet address')

        send_parser = wallet_sub.add_parser('send', help='Send transaction')
        send_parser.add_argument('from_address', help='Sender address')
        send_parser.add_argument('to_address', help='Recipient address')
        send_parser.add_argument('amount', type=float, help='Amount to send')
        send_parser.add_argument('--fee', type=float, default=0.0001, help='Transaction fee')

        # Blockchain commands
        chain_parser = subparsers.add_parser('chain', help='Blockchain commands')
        chain_sub = chain_parser.add_subparsers(dest='chain_command')

        chain_sub.add_parser('info', help='Get blockchain info')

        block_parser = chain_sub.add_parser('block', help='Get block')
        block_group = block_parser.add_mutually_exclusive_group(required=True)
        block_group.add_argument('--hash', help='Block hash')
        block_group.add_argument('--index', type=int, help='Block index')

        # Mining commands
        mine_parser = subparsers.add_parser('mine', help='Mine a block')
        mine_parser.add_argument('address', help='Miner address')
        mine_parser.add_argument('--iterations', type=int, default=10000, help='Max iterations')

        # Staking commands
        stake_parser = subparsers.add_parser('stake', help='Staking commands')
        stake_sub = stake_parser.add_subparsers(dest='stake_command')

        create_stake_parser = stake_sub.add_parser('create', help='Create stake')
        create_stake_parser.add_argument('address', help='Staker address')
        create_stake_parser.add_argument('amount', type=float, help='Amount to stake')
        create_stake_parser.add_argument('lock_period', type=int, help='Lock period (blocks)')

        info_stake_parser = stake_sub.add_parser('info', help='Get stake info')
        info_stake_parser.add_argument('address', help='Staker address')

        # Node commands
        node_parser = subparsers.add_parser('node', help='Start full node')

        # Parse arguments
        args = parser.parse_args()

        # Route to handler
        if args.command == 'wallet':
            if args.wallet_command == 'create':
                self.create_wallet(args)
            elif args.wallet_command == 'balance':
                self.get_balance(args)
            elif args.wallet_command == 'send':
                self.send_transaction(args)

        elif args.command == 'chain':
            if args.chain_command == 'info':
                self.get_blockchain_info(args)
            elif args.chain_command == 'block':
                self.get_block(args)

        elif args.command == 'mine':
            self.mine(args)

        elif args.command == 'stake':
            if args.stake_command == 'create':
                self.stake(args)
            elif args.stake_command == 'info':
                self.get_stake_info(args)

        elif args.command == 'node':
            self.start_node(args)

        else:
            parser.print_help()


if __name__ == '__main__':
    cli = FractalChainCLI()
    cli.run()
