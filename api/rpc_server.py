"""
JSON-RPC API server for FractalChain.
Provides programmatic access to blockchain functionality.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from ..core.blockchain import Blockchain
from ..core.transaction import Transaction
from ..core.crypto import KeyPair
from ..consensus.miner import Miner
from ..consensus.verification import HybridVerifier
from ..economic.staking import StakingSystem
from ..network.p2p import P2PNode


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RPCRequest(BaseModel):
    """JSON-RPC request model."""
    jsonrpc: str = "2.0"
    method: str
    params: Any = []
    id: Optional[int] = None


class RPCResponse(BaseModel):
    """JSON-RPC response model."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict] = None
    id: Optional[int] = None


class RPCServer:
    """
    JSON-RPC server for FractalChain.
    """

    def __init__(
        self,
        blockchain: Blockchain,
        verifier: HybridVerifier,
        staking: StakingSystem,
        miner: Optional[Miner] = None,
        p2p_node: Optional[P2PNode] = None,
        host: str = "0.0.0.0",
        port: int = 8545
    ):
        """
        Initialize RPC server.

        Args:
            blockchain: Blockchain instance
            verifier: Block verifier
            staking: Staking system
            miner: Miner instance
            p2p_node: P2P node
            host: Server host
            port: Server port
        """
        self.blockchain = blockchain
        self.verifier = verifier
        self.staking = staking
        self.miner = miner
        self.p2p_node = p2p_node
        self.host = host
        self.port = port

        # Create FastAPI app
        self.app = FastAPI(title="FractalChain RPC API", version="1.0.0")

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register API routes."""

        @self.app.post("/")
        async def handle_rpc(request: RPCRequest) -> RPCResponse:
            """Handle JSON-RPC request."""
            try:
                method = request.method
                params = request.params if isinstance(request.params, list) else [request.params]

                # Route to handler
                handler = getattr(self, f"rpc_{method}", None)

                if handler is None:
                    return RPCResponse(
                        error={"code": -32601, "message": "Method not found"},
                        id=request.id
                    )

                result = handler(*params)

                return RPCResponse(result=result, id=request.id)

            except Exception as e:
                logger.error(f"RPC error: {e}")
                return RPCResponse(
                    error={"code": -32603, "message": str(e)},
                    id=request.id
                )

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "ok", "chain_height": self.blockchain.get_chain_length()}

    # Blockchain methods

    def rpc_getBlockchainInfo(self) -> Dict:
        """Get blockchain information."""
        latest_block = self.blockchain.get_latest_block()
        difficulty_target, header_bits = self.blockchain.get_difficulty()

        return {
            "chain_length": self.blockchain.get_chain_length(),
            "latest_block_hash": latest_block.block_hash if latest_block else "",
            "latest_block_index": latest_block.index if latest_block else 0,
            "difficulty_target": difficulty_target,
            "header_difficulty_bits": header_bits,
            "block_reward": self.blockchain.get_block_reward()
        }

    def rpc_getBlock(self, block_hash: str = None, block_index: int = None) -> Optional[Dict]:
        """Get block by hash or index."""
        if block_hash:
            block = self.blockchain.get_block_by_hash(block_hash)
        elif block_index is not None:
            block = self.blockchain.get_block_by_index(block_index)
        else:
            block = self.blockchain.get_latest_block()

        return block.to_dict() if block else None

    def rpc_getBalance(self, address: str) -> float:
        """Get balance for an address."""
        return self.blockchain.get_balance(address)

    def rpc_getTransaction(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction by hash."""
        # Search through blocks
        for block in self.blockchain.chain:
            for tx in block.transactions:
                if tx.tx_hash == tx_hash:
                    return tx.to_dict()
        return None

    def rpc_getPendingTransactions(self) -> List[Dict]:
        """Get pending transactions."""
        return [tx.to_dict() for tx in self.blockchain.pending_transactions]

    # Transaction methods

    def rpc_sendTransaction(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        fee: float = 0.0001,
        private_key_hex: str = None
    ) -> Dict:
        """
        Send a transaction.

        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Amount to send
            fee: Transaction fee
            private_key_hex: Private key (hex)

        Returns:
            Transaction info
        """
        try:
            # Create transaction
            tx = Transaction(
                sender=from_address,
                recipient=to_address,
                amount=amount,
                fee=fee,
                timestamp=time.time()
            )

            # Sign if private key provided
            if private_key_hex:
                keypair = KeyPair.from_private_key_hex(private_key_hex)
                tx.sign(keypair)

            # Add to blockchain
            if self.blockchain.add_transaction(tx):
                # Broadcast to network
                if self.p2p_node:
                    import asyncio
                    asyncio.create_task(self.p2p_node.broadcast_transaction(tx))

                return {
                    "success": True,
                    "tx_hash": tx.tx_hash,
                    "message": "Transaction added to mempool"
                }
            else:
                return {
                    "success": False,
                    "message": "Transaction rejected"
                }

        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    # Mining methods

    def rpc_startMining(self) -> Dict:
        """Start mining."""
        if not self.miner:
            return {"success": False, "message": "Miner not configured"}

        if self.miner.is_mining:
            return {"success": False, "message": "Already mining"}

        import asyncio
        asyncio.create_task(self._mine_loop())

        return {"success": True, "message": "Mining started"}

    def rpc_stopMining(self) -> Dict:
        """Stop mining."""
        if not self.miner:
            return {"success": False, "message": "Miner not configured"}

        self.miner.stop_mining()
        return {"success": True, "message": "Mining stopped"}

    def rpc_getMiningInfo(self) -> Dict:
        """Get mining information."""
        if not self.miner:
            return {"error": "Miner not configured"}

        return self.miner.get_mining_stats()

    async def _mine_loop(self) -> None:
        """Background mining loop."""
        while self.miner.is_mining:
            block = self.miner.mine_block(max_iterations=10000)

            if block:
                # Verify and add block
                previous_block = self.blockchain.get_latest_block()
                is_valid, message, _ = self.verifier.verify_block(block, previous_block)

                if is_valid:
                    self.blockchain.add_block(block)

                    # Broadcast to network
                    if self.p2p_node:
                        await self.p2p_node.broadcast_block(block)

                    logger.info(f"Mined and added block {block.index}")
                else:
                    logger.error(f"Mined invalid block: {message}")

    # Staking methods

    def rpc_stake(
        self,
        address: str,
        amount: float,
        lock_period: int
    ) -> Dict:
        """Create a stake."""
        current_block = self.blockchain.get_chain_length()
        success, message = self.staking.create_stake(address, amount, lock_period, current_block)

        return {"success": success, "message": message}

    def rpc_getStakePositions(self, address: str) -> List[Dict]:
        """Get stake positions for an address."""
        positions = self.staking.get_stake_positions(address)
        return [pos.to_dict() for pos in positions]

    def rpc_withdrawStake(self, address: str, stake_index: int) -> Dict:
        """Withdraw a stake."""
        current_block = self.blockchain.get_chain_length()

        # Initiate withdrawal
        success, message = self.staking.initiate_withdrawal(address, stake_index, current_block)

        if not success:
            return {"success": False, "message": message}

        # Complete withdrawal
        success, amount, message = self.staking.complete_withdrawal(address, stake_index)

        return {"success": success, "amount": amount, "message": message}

    def rpc_getStakingInfo(self) -> Dict:
        """Get staking statistics."""
        return self.staking.get_statistics()

    # Network methods

    def rpc_getPeerInfo(self) -> List[Dict]:
        """Get connected peers."""
        if not self.p2p_node:
            return []

        return [peer.to_dict() for peer in self.p2p_node.peers.values()]

    def rpc_getNetworkInfo(self) -> Dict:
        """Get network information."""
        if not self.p2p_node:
            return {"error": "P2P node not configured"}

        return self.p2p_node.get_stats()

    # Wallet methods

    def rpc_createWallet(self) -> Dict:
        """Create a new wallet."""
        keypair = KeyPair()

        return {
            "address": keypair.get_address(),
            "public_key": keypair.export_public_key(),
            "private_key": keypair.export_private_key()
        }

    def rpc_getAddressFromPrivateKey(self, private_key_hex: str) -> Dict:
        """Get address from private key."""
        try:
            keypair = KeyPair.from_private_key_hex(private_key_hex)

            return {
                "address": keypair.get_address(),
                "public_key": keypair.export_public_key()
            }
        except Exception as e:
            return {"error": str(e)}

    def start(self) -> None:
        """Start the RPC server."""
        logger.info(f"Starting RPC server on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)


# For testing
if __name__ == "__main__":
    import time
    from ..core.blockchain import Blockchain
    from ..consensus.verification import HybridVerifier
    from ..economic.staking import StakingSystem

    blockchain = Blockchain(":memory:")
    verifier = HybridVerifier()
    staking = StakingSystem()

    server = RPCServer(blockchain, verifier, staking)
    server.start()
