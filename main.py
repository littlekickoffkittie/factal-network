#!/usr/bin/env python3
"""
FractalChain - Main Entry Point
A cryptocurrency powered by fractal mathematics.
"""

import asyncio
import argparse
import signal
import sys
import logging
from pathlib import Path

from core.blockchain import Blockchain
from core.crypto import KeyPair
from consensus.fractal_math import FractalConfig
from consensus.miner import Miner
from consensus.verification import HybridVerifier
from consensus.difficulty import DifficultyAdjustment
from economic.staking import StakingSystem
from network.p2p import P2PNode
from api.rpc_server import RPCServer
from api.web_explorer import BlockExplorer
from utils.config import Config


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FractalChainNode:
    """
    Main FractalChain node combining all components.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize FractalChain node.

        Args:
            config_path: Path to configuration file
        """
        self.config = Config(config_path)
        self.running = False

        # Core components
        self.blockchain = None
        self.verifier = None
        self.staking = None
        self.miner = None
        self.p2p_node = None
        self.rpc_server = None
        self.web_explorer = None
        self.difficulty_adjuster = None

    def initialize_components(self):
        """Initialize all node components."""
        logger.info("Initializing FractalChain node...")

        # Create data directory
        self.config.create_data_directory()

        # Initialize blockchain
        db_path = self.config.get_db_path()
        logger.info(f"Database: {db_path}")
        self.blockchain = Blockchain(db_path)

        # Initialize fractal config
        fractal_cfg_dict = self.config.get_fractal_config()
        fractal_cfg = FractalConfig(
            max_iterations=fractal_cfg_dict['max_iterations'],
            escape_radius=fractal_cfg_dict['escape_radius'],
            grid_size=fractal_cfg_dict['grid_size'],
            target_dimension=fractal_cfg_dict['target_dimension'],
            epsilon=fractal_cfg_dict['epsilon']
        )

        # Initialize verifier
        deepseek_key = self.config.get('verification.deepseek_api_key')
        self.verifier = HybridVerifier(fractal_cfg, deepseek_key)

        # Initialize difficulty adjuster
        blockchain_cfg = self.config.get_blockchain_config()
        self.difficulty_adjuster = DifficultyAdjustment(
            target_block_time=blockchain_cfg['block_time_target'],
            adjustment_interval=blockchain_cfg['difficulty_adjustment_interval']
        )

        # Initialize staking
        staking_cfg = self.config.get_staking_config()
        if staking_cfg['enabled']:
            self.staking = StakingSystem(
                min_stake_amount=staking_cfg['min_stake_amount'],
                min_lock_period=staking_cfg['min_lock_period'],
                annual_return_rate=staking_cfg['annual_return_rate'],
                slash_percentage=staking_cfg['slash_percentage']
            )
            logger.info("Staking system enabled")

        # Initialize miner if enabled
        mining_cfg = self.config.get_mining_config()
        if mining_cfg['enabled']:
            # Load or create miner wallet
            keystore_path = Path(self.config.get_keystore_path())
            miner_wallet = keystore_path / "miner.json"

            if miner_wallet.exists():
                import json
                with open(miner_wallet, 'r') as f:
                    wallet_data = json.load(f)
                keypair = KeyPair.from_private_key_hex(wallet_data['private_key'])
            else:
                logger.info("Creating new miner wallet...")
                keypair = KeyPair()
                import json
                miner_wallet.parent.mkdir(parents=True, exist_ok=True)
                with open(miner_wallet, 'w') as f:
                    json.dump({
                        'address': keypair.get_address(),
                        'private_key': keypair.export_private_key(),
                        'public_key': keypair.export_public_key()
                    }, f, indent=2)
                logger.info(f"Miner wallet created: {keypair.get_address()}")

            self.miner = Miner(self.blockchain, keypair, fractal_cfg)
            logger.info(f"Mining enabled with address: {keypair.get_address()}")

        logger.info(f"Blockchain initialized: {self.blockchain.get_chain_length()} blocks")

    async def start(self):
        """Start the FractalChain node."""
        self.initialize_components()
        self.running = True

        # Start P2P node
        net_cfg = self.config.get_network_config()
        self.p2p_node = P2PNode(
            host=net_cfg['host'],
            port=net_cfg['port'],
            blockchain=self.blockchain,
            verifier=self.verifier,
            bootstrap_peers=net_cfg['bootstrap_peers']
        )

        logger.info(f"Starting P2P node on {net_cfg['host']}:{net_cfg['port']}")
        await self.p2p_node.start()

        # Start RPC server if enabled
        if self.config.get('api.enabled'):
            api_cfg = self.config.get_api_config()
            self.rpc_server = RPCServer(
                blockchain=self.blockchain,
                verifier=self.verifier,
                staking=self.staking,
                miner=self.miner,
                p2p_node=self.p2p_node,
                host=api_cfg['host'],
                port=api_cfg['port']
            )

            # Start RPC server in background
            import threading
            rpc_thread = threading.Thread(target=self.rpc_server.start)
            rpc_thread.daemon = True
            rpc_thread.start()

            logger.info(f"RPC API started on {api_cfg['host']}:{api_cfg['port']}")

        # Start web explorer if enabled
        if self.config.get('web.enabled'):
            web_cfg = self.config.get('web').get('web', {'host': '0.0.0.0', 'port': 8080})
            self.web_explorer = BlockExplorer(
                blockchain=self.blockchain,
                staking=self.staking,
                p2p_node=self.p2p_node,
                host=web_cfg['host'],
                port=web_cfg['port']
            )

            # Start web explorer in background
            import threading
            web_thread = threading.Thread(target=self.web_explorer.start)
            web_thread.daemon = True
            web_thread.start()

            logger.info(f"Web explorer started on http://{web_cfg['host']}:{web_cfg['port']}")

        # Start mining loop if enabled
        if self.miner:
            asyncio.create_task(self._mining_loop())

        logger.info("=" * 60)
        logger.info("FractalChain node is running!")
        logger.info("=" * 60)
        logger.info(f"Network: {self.config.get('network.network_type')}")
        logger.info(f"Chain length: {self.blockchain.get_chain_length()}")
        logger.info(f"P2P Port: {net_cfg['port']}")
        if self.config.get('api.enabled'):
            logger.info(f"RPC API: http://{api_cfg['host']}:{api_cfg['port']}")
        if self.config.get('web.enabled'):
            logger.info(f"Explorer: http://{web_cfg['host']}:{web_cfg['port']}")
        logger.info("=" * 60)

        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)

                # Periodic difficulty adjustment
                if self.difficulty_adjuster.should_adjust_difficulty(
                    self.blockchain.get_chain_length()
                ):
                    await self._adjust_difficulty()

        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await self.stop()

    async def _mining_loop(self):
        """Background mining loop."""
        logger.info("Mining loop started")

        while self.running:
            try:
                block = self.miner.mine_block(max_iterations=10000)

                if block:
                    # Verify block
                    previous_block = self.blockchain.get_latest_block()
                    is_valid, message, _ = self.verifier.verify_block(block, previous_block)

                    if is_valid:
                        # Add to blockchain
                        if self.blockchain.add_block(block):
                            logger.info(f"✓ Mined block {block.index}!")

                            # Broadcast to network
                            if self.p2p_node:
                                await self.p2p_node.broadcast_block(block)
                        else:
                            logger.error("Failed to add mined block to chain")
                    else:
                        logger.error(f"Mined invalid block: {message}")

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Mining error: {e}")
                await asyncio.sleep(5)

    async def _adjust_difficulty(self):
        """Adjust mining difficulty."""
        logger.info("Adjusting difficulty...")

        chain_length = self.blockchain.get_chain_length()
        interval = self.difficulty_adjuster.adjustment_interval

        # Get recent blocks
        start_index = max(0, chain_length - interval)
        recent_blocks = []

        for i in range(start_index, chain_length):
            block = self.blockchain.get_block_by_index(i)
            if block:
                recent_blocks.append(block)

        if len(recent_blocks) >= 2:
            current_difficulty, current_header_bits = self.blockchain.get_difficulty()

            new_difficulty, new_header_bits = self.difficulty_adjuster.calculate_new_difficulty(
                recent_blocks,
                current_difficulty,
                current_header_bits
            )

            logger.info(f"Difficulty adjusted: {current_difficulty:.6f} → {new_difficulty:.6f}")
            logger.info(f"Header bits adjusted: {current_header_bits} → {new_header_bits}")

    async def stop(self):
        """Stop the node."""
        self.running = False

        # Stop mining
        if self.miner:
            self.miner.stop_mining()

        # Stop P2P node
        if self.p2p_node:
            await self.p2p_node.stop()

        logger.info("Node stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='FractalChain Node')
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file',
        default='fractalchain.conf'
    )
    parser.add_argument(
        '--network',
        type=str,
        choices=['mainnet', 'testnet', 'devnet'],
        help='Network type',
        default='mainnet'
    )
    parser.add_argument(
        '--mine',
        action='store_true',
        help='Enable mining'
    )
    parser.add_argument(
        '--port',
        type=int,
        help='P2P port'
    )

    args = parser.parse_args()

    # Create config
    config = Config(args.config)

    # Override with command line arguments
    if args.network:
        config.set('network.network_type', args.network)

    if args.mine:
        config.set('mining.enabled', True)

    if args.port:
        config.set('network.port', args.port)

    # Save config
    config.save()

    # Create and start node
    node = FractalChainNode(args.config)

    # Handle signals
    def signal_handler(sig, frame):
        logger.info("\nReceived interrupt signal")
        asyncio.create_task(node.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run node
    try:
        asyncio.run(node.start())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == '__main__':
    main()
