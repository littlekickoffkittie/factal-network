"""
P2P networking implementation for FractalChain.
Handles node discovery, peer management, and message propagation.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Set, Callable
from .protocol import (
    NetworkMessage, MessageType, PeerInfo, MessageValidator,
    RateLimiter, ProtocolVersion
)
from ..core.block import Block
from ..core.transaction import Transaction
from ..core.blockchain import Blockchain
from ..consensus.verification import HybridVerifier


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class P2PNode:
    """
    P2P network node for FractalChain.
    Manages peer connections and message propagation.
    """

    def __init__(
        self,
        host: str,
        port: int,
        blockchain: Blockchain,
        verifier: HybridVerifier,
        bootstrap_peers: List[str] = None
    ):
        """
        Initialize P2P node.

        Args:
            host: Node host address
            port: Node port
            blockchain: Blockchain instance
            verifier: Block verifier
            bootstrap_peers: List of bootstrap peer addresses
        """
        self.host = host
        self.port = port
        self.blockchain = blockchain
        self.verifier = verifier
        self.node_id = str(uuid.uuid4())

        # Peer management
        self.peers: Dict[str, PeerInfo] = {}
        self.peer_connections: Dict[str, asyncio.StreamWriter] = {}
        self.bootstrap_peers = bootstrap_peers or []

        # Message handling
        self.message_validator = MessageValidator()
        self.rate_limiter = RateLimiter()
        self.seen_messages: Set[str] = set()
        self.message_handlers: Dict[str, Callable] = {}

        # Server
        self.server: Optional[asyncio.Server] = None
        self.running = False

        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'blocks_received': 0,
            'transactions_received': 0,
            'connections': 0
        }

        self._register_message_handlers()

    def _register_message_handlers(self) -> None:
        """Register message handlers."""
        self.message_handlers = {
            MessageType.HELLO.value: self._handle_hello,
            MessageType.GET_PEERS.value: self._handle_get_peers,
            MessageType.PEERS.value: self._handle_peers,
            MessageType.NEW_BLOCK.value: self._handle_new_block,
            MessageType.BLOCK_ANNOUNCEMENT.value: self._handle_block_announcement,
            MessageType.NEW_TRANSACTION.value: self._handle_new_transaction,
            MessageType.GET_CHAIN_INFO.value: self._handle_get_chain_info,
            MessageType.CHAIN_INFO.value: self._handle_chain_info,
            MessageType.GET_BLOCKS.value: self._handle_get_blocks,
            MessageType.BLOCKS.value: self._handle_blocks,
            MessageType.PING.value: self._handle_ping,
            MessageType.PONG.value: self._handle_pong,
        }

    async def start(self) -> None:
        """Start the P2P node."""
        self.running = True

        # Start server
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )

        logger.info(f"P2P node started on {self.host}:{self.port}")
        logger.info(f"Node ID: {self.node_id}")

        # Connect to bootstrap peers
        await self._connect_to_bootstrap_peers()

        # Start background tasks
        asyncio.create_task(self._peer_discovery_loop())
        asyncio.create_task(self._peer_maintenance_loop())
        asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the P2P node."""
        self.running = False

        # Close all peer connections
        for writer in self.peer_connections.values():
            writer.close()
            await writer.wait_closed()

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("P2P node stopped")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """
        Handle incoming client connection.

        Args:
            reader: Stream reader
            writer: Stream writer
        """
        peer_address = writer.get_extra_info('peername')
        logger.info(f"New connection from {peer_address}")

        self.stats['connections'] += 1

        try:
            while self.running:
                # Read message length (4 bytes)
                length_bytes = await reader.readexactly(4)
                message_length = int.from_bytes(length_bytes, 'big')

                # Check message size
                if message_length > MessageValidator.MAX_MESSAGE_SIZE:
                    logger.warning(f"Message too large from {peer_address}")
                    break

                # Read message data
                message_data = await reader.readexactly(message_length)
                message_json = message_data.decode('utf-8')

                # Process message
                await self._process_message(message_json, writer)

        except asyncio.IncompleteReadError:
            logger.info(f"Connection closed by {peer_address}")
        except Exception as e:
            logger.error(f"Error handling client {peer_address}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self.stats['connections'] -= 1

    async def _process_message(
        self,
        message_json: str,
        writer: asyncio.StreamWriter
    ) -> None:
        """
        Process incoming message.

        Args:
            message_json: Message JSON string
            writer: Stream writer for responses
        """
        try:
            # Parse message
            message = NetworkMessage.from_json(message_json)

            # Validate message
            if not self.message_validator.validate_message(message):
                logger.warning("Invalid message received")
                return

            # Check rate limit
            if not self.rate_limiter.check_rate_limit(message.sender_id, len(message_json)):
                logger.warning(f"Rate limit exceeded for {message.sender_id}")
                return

            # Check for duplicates
            if message.msg_id in self.seen_messages:
                return

            self.seen_messages.add(message.msg_id)
            self.stats['messages_received'] += 1

            # Handle message
            handler = self.message_handlers.get(message.msg_type)
            if handler:
                await handler(message, writer)
            else:
                logger.warning(f"Unknown message type: {message.msg_type}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _handle_hello(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle HELLO message."""
        payload = message.payload

        peer_info = PeerInfo(
            node_id=payload['node_id'],
            host=payload['host'],
            port=payload['port'],
            protocol_version=payload['protocol_version'],
            chain_height=payload['chain_height'],
            last_seen=time.time()
        )

        # Check protocol compatibility
        if not ProtocolVersion.is_compatible(peer_info.protocol_version):
            logger.warning(f"Incompatible protocol version from {peer_info.node_id}")
            return

        # Add peer
        self.peers[peer_info.node_id] = peer_info
        self.peer_connections[peer_info.node_id] = writer

        logger.info(f"Added peer {peer_info.node_id} at {peer_info.get_address()}")

        # Send our info
        response = NetworkMessage.create(
            MessageType.HELLO,
            {
                'node_id': self.node_id,
                'host': self.host,
                'port': self.port,
                'protocol_version': ProtocolVersion.to_string(),
                'chain_height': self.blockchain.get_chain_length()
            },
            self.node_id
        )

        await self._send_message(writer, response)

    async def _handle_get_peers(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle GET_PEERS message."""
        peer_list = [peer.to_dict() for peer in self.peers.values()]

        response = NetworkMessage.create(
            MessageType.PEERS,
            {'peers': peer_list},
            self.node_id
        )

        await self._send_message(writer, response)

    async def _handle_peers(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle PEERS message."""
        peers_data = message.payload.get('peers', [])

        for peer_data in peers_data:
            peer_info = PeerInfo.from_dict(peer_data)

            if peer_info.node_id not in self.peers and peer_info.node_id != self.node_id:
                # Try to connect to new peer
                asyncio.create_task(self._connect_to_peer(peer_info.host, peer_info.port))

    async def _handle_new_block(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle NEW_BLOCK message."""
        block_data = message.payload.get('block_data')

        if not block_data:
            return

        try:
            block = Block.from_dict(block_data)

            # Quick verification
            if not self.verifier.quick_verify(block):
                logger.warning(f"Block {block.index} failed quick verification")
                return

            # Full verification
            previous_block = self.blockchain.get_block_by_hash(block.previous_hash)
            is_valid, error_msg, _ = self.verifier.verify_block(block, previous_block)

            if is_valid:
                # Add to blockchain
                if self.blockchain.add_block(block):
                    logger.info(f"Added block {block.index} from network")
                    self.stats['blocks_received'] += 1

                    # Propagate to other peers
                    await self.broadcast_block(block, exclude=[message.sender_id])
            else:
                logger.warning(f"Block {block.index} verification failed: {error_msg}")

        except Exception as e:
            logger.error(f"Error processing new block: {e}")

    async def _handle_block_announcement(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle BLOCK_ANNOUNCEMENT message."""
        block_hash = message.payload.get('block_hash')
        block_index = message.payload.get('block_index')

        # Check if we already have this block
        existing_block = self.blockchain.get_block_by_hash(block_hash)

        if not existing_block:
            # Request full block
            request = NetworkMessage.create(
                MessageType.GET_BLOCKS,
                {'start_index': block_index, 'count': 1},
                self.node_id
            )
            await self._send_message(writer, request)

    async def _handle_new_transaction(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle NEW_TRANSACTION message."""
        tx_data = message.payload.get('transaction_data')

        if not tx_data:
            return

        try:
            transaction = Transaction.from_dict(tx_data)

            # Add to mempool
            if self.blockchain.add_transaction(transaction):
                logger.info(f"Added transaction {transaction.tx_hash} from network")
                self.stats['transactions_received'] += 1

                # Propagate to other peers
                await self.broadcast_transaction(transaction, exclude=[message.sender_id])

        except Exception as e:
            logger.error(f"Error processing new transaction: {e}")

    async def _handle_get_chain_info(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle GET_CHAIN_INFO message."""
        latest_block = self.blockchain.get_latest_block()

        response = NetworkMessage.create(
            MessageType.CHAIN_INFO,
            {
                'chain_height': self.blockchain.get_chain_length(),
                'latest_block_hash': latest_block.block_hash if latest_block else "",
                'latest_block_index': latest_block.index if latest_block else 0
            },
            self.node_id
        )

        await self._send_message(writer, response)

    async def _handle_chain_info(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle CHAIN_INFO message."""
        chain_height = message.payload.get('chain_height', 0)
        our_height = self.blockchain.get_chain_length()

        # If peer has longer chain, sync
        if chain_height > our_height:
            logger.info(f"Peer has longer chain ({chain_height} vs {our_height}), syncing...")
            await self._sync_from_peer(writer, our_height, chain_height)

    async def _handle_get_blocks(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle GET_BLOCKS message."""
        start_index = message.payload.get('start_index', 0)
        count = message.payload.get('count', 10)

        blocks_data = []

        for i in range(start_index, min(start_index + count, self.blockchain.get_chain_length())):
            block = self.blockchain.get_block_by_index(i)
            if block:
                blocks_data.append(block.to_dict())

        response = NetworkMessage.create(
            MessageType.BLOCKS,
            {'blocks': blocks_data},
            self.node_id
        )

        await self._send_message(writer, response)

    async def _handle_blocks(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle BLOCKS message."""
        blocks_data = message.payload.get('blocks', [])

        for block_data in blocks_data:
            try:
                block = Block.from_dict(block_data)
                previous_block = self.blockchain.get_block_by_hash(block.previous_hash)

                is_valid, error_msg, _ = self.verifier.verify_block(block, previous_block)

                if is_valid:
                    self.blockchain.add_block(block)
                    logger.info(f"Synced block {block.index}")

            except Exception as e:
                logger.error(f"Error syncing block: {e}")

    async def _handle_ping(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle PING message."""
        response = NetworkMessage.create(
            MessageType.PONG,
            {'timestamp': time.time()},
            self.node_id
        )
        await self._send_message(writer, response)

    async def _handle_pong(self, message: NetworkMessage, writer: asyncio.StreamWriter) -> None:
        """Handle PONG message."""
        # Update peer last seen
        if message.sender_id in self.peers:
            self.peers[message.sender_id].last_seen = time.time()

    async def _send_message(
        self,
        writer: asyncio.StreamWriter,
        message: NetworkMessage
    ) -> bool:
        """
        Send message to peer.

        Args:
            writer: Stream writer
            message: Message to send

        Returns:
            True if successful
        """
        try:
            message_json = message.to_json()
            message_bytes = message_json.encode('utf-8')

            # Send length prefix
            length_bytes = len(message_bytes).to_bytes(4, 'big')
            writer.write(length_bytes)
            writer.write(message_bytes)

            await writer.drain()

            self.stats['messages_sent'] += 1
            return True

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def broadcast_block(self, block: Block, exclude: List[str] = None) -> None:
        """
        Broadcast block to all peers.

        Args:
            block: Block to broadcast
            exclude: Node IDs to exclude
        """
        exclude = exclude or []

        message = NetworkMessage.create(
            MessageType.NEW_BLOCK,
            {'block_data': block.to_dict()},
            self.node_id
        )

        for node_id, writer in self.peer_connections.items():
            if node_id not in exclude:
                await self._send_message(writer, message)

    async def broadcast_transaction(
        self,
        transaction: Transaction,
        exclude: List[str] = None
    ) -> None:
        """
        Broadcast transaction to all peers.

        Args:
            transaction: Transaction to broadcast
            exclude: Node IDs to exclude
        """
        exclude = exclude or []

        message = NetworkMessage.create(
            MessageType.NEW_TRANSACTION,
            {'transaction_data': transaction.to_dict()},
            self.node_id
        )

        for node_id, writer in self.peer_connections.items():
            if node_id not in exclude:
                await self._send_message(writer, message)

    async def _connect_to_bootstrap_peers(self) -> None:
        """Connect to bootstrap peers."""
        for peer_address in self.bootstrap_peers:
            try:
                host, port = peer_address.split(':')
                await self._connect_to_peer(host, int(port))
            except Exception as e:
                logger.error(f"Error connecting to bootstrap peer {peer_address}: {e}")

    async def _connect_to_peer(self, host: str, port: int) -> bool:
        """
        Connect to a peer.

        Args:
            host: Peer host
            port: Peer port

        Returns:
            True if successful
        """
        try:
            reader, writer = await asyncio.open_connection(host, port)

            # Send HELLO
            hello = NetworkMessage.create(
                MessageType.HELLO,
                {
                    'node_id': self.node_id,
                    'host': self.host,
                    'port': self.port,
                    'protocol_version': ProtocolVersion.to_string(),
                    'chain_height': self.blockchain.get_chain_length()
                },
                self.node_id
            )

            await self._send_message(writer, hello)

            # Start handling messages from this peer
            asyncio.create_task(self._handle_client(reader, writer))

            logger.info(f"Connected to peer at {host}:{port}")
            return True

        except Exception as e:
            logger.error(f"Error connecting to {host}:{port}: {e}")
            return False

    async def _sync_from_peer(
        self,
        writer: asyncio.StreamWriter,
        start_index: int,
        end_index: int
    ) -> None:
        """Sync blocks from peer."""
        batch_size = 100

        for i in range(start_index, end_index, batch_size):
            request = NetworkMessage.create(
                MessageType.GET_BLOCKS,
                {'start_index': i, 'count': batch_size},
                self.node_id
            )
            await self._send_message(writer, request)
            await asyncio.sleep(0.1)  # Rate limiting

    async def _peer_discovery_loop(self) -> None:
        """Periodically discover new peers."""
        while self.running:
            await asyncio.sleep(60)  # Every minute

            # Request peers from connected peers
            for writer in self.peer_connections.values():
                request = NetworkMessage.create(
                    MessageType.GET_PEERS,
                    {},
                    self.node_id
                )
                await self._send_message(writer, request)

    async def _peer_maintenance_loop(self) -> None:
        """Maintain peer connections."""
        while self.running:
            await asyncio.sleep(30)  # Every 30 seconds

            current_time = time.time()

            # Remove stale peers
            stale_peers = [
                node_id for node_id, peer in self.peers.items()
                if current_time - peer.last_seen > 300  # 5 minutes
            ]

            for node_id in stale_peers:
                logger.info(f"Removing stale peer {node_id}")
                self.peers.pop(node_id, None)
                writer = self.peer_connections.pop(node_id, None)
                if writer:
                    writer.close()
                    await writer.wait_closed()

            # Ping active peers
            for node_id, writer in self.peer_connections.items():
                ping = NetworkMessage.create(
                    MessageType.PING,
                    {},
                    self.node_id
                )
                await self._send_message(writer, ping)

    async def _cleanup_loop(self) -> None:
        """Clean up old seen messages."""
        while self.running:
            await asyncio.sleep(300)  # Every 5 minutes
            self.seen_messages.clear()

    def get_stats(self) -> dict:
        """Get network statistics."""
        return {
            **self.stats,
            'peer_count': len(self.peers),
            'node_id': self.node_id,
            'address': f"{self.host}:{self.port}"
        }
