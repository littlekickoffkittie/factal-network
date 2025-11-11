"""
Network protocol definitions for FractalChain P2P communication.
"""

import json
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict


class MessageType(Enum):
    """Network message types."""

    # Handshake and discovery
    HELLO = "hello"
    GET_PEERS = "get_peers"
    PEERS = "peers"

    # Blockchain sync
    GET_BLOCKS = "get_blocks"
    BLOCKS = "blocks"
    GET_BLOCK_HEADERS = "get_block_headers"
    BLOCK_HEADERS = "block_headers"

    # Block propagation
    NEW_BLOCK = "new_block"
    BLOCK_ANNOUNCEMENT = "block_announcement"

    # Transaction propagation
    NEW_TRANSACTION = "new_transaction"
    GET_MEMPOOL = "get_mempool"
    MEMPOOL = "mempool"

    # Chain state
    GET_CHAIN_INFO = "get_chain_info"
    CHAIN_INFO = "chain_info"

    # Ping/Pong
    PING = "ping"
    PONG = "pong"

    # Error
    ERROR = "error"


@dataclass
class NetworkMessage:
    """Standard network message format."""

    msg_type: str
    payload: Dict[str, Any]
    msg_id: str = ""
    timestamp: float = 0.0
    sender_id: str = ""

    def to_json(self) -> str:
        """
        Serialize message to JSON.

        Returns:
            JSON string
        """
        data = {
            'msg_type': self.msg_type,
            'payload': self.payload,
            'msg_id': self.msg_id,
            'timestamp': self.timestamp,
            'sender_id': self.sender_id
        }
        return json.dumps(data)

    @staticmethod
    def from_json(json_str: str) -> 'NetworkMessage':
        """
        Deserialize message from JSON.

        Args:
            json_str: JSON string

        Returns:
            NetworkMessage instance
        """
        data = json.loads(json_str)
        return NetworkMessage(
            msg_type=data['msg_type'],
            payload=data['payload'],
            msg_id=data.get('msg_id', ''),
            timestamp=data.get('timestamp', 0.0),
            sender_id=data.get('sender_id', '')
        )

    @staticmethod
    def create(
        msg_type: MessageType,
        payload: Dict[str, Any],
        sender_id: str = ""
    ) -> 'NetworkMessage':
        """
        Create a new network message.

        Args:
            msg_type: Message type
            payload: Message payload
            sender_id: Sender node ID

        Returns:
            NetworkMessage instance
        """
        import time
        import uuid

        return NetworkMessage(
            msg_type=msg_type.value,
            payload=payload,
            msg_id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender_id=sender_id
        )


class ProtocolVersion:
    """Protocol version information."""

    MAJOR = 1
    MINOR = 0
    PATCH = 0

    @classmethod
    def to_string(cls) -> str:
        """Get version string."""
        return f"{cls.MAJOR}.{cls.MINOR}.{cls.PATCH}"

    @classmethod
    def to_int(cls) -> int:
        """Get version as integer for comparison."""
        return cls.MAJOR * 1000000 + cls.MINOR * 1000 + cls.PATCH

    @classmethod
    def is_compatible(cls, other_version_str: str) -> bool:
        """
        Check if another version is compatible.

        Args:
            other_version_str: Other version string (e.g., "1.0.0")

        Returns:
            True if compatible
        """
        try:
            parts = other_version_str.split('.')
            other_major = int(parts[0])
            return other_major == cls.MAJOR
        except:
            return False


@dataclass
class PeerInfo:
    """Information about a peer node."""

    node_id: str
    host: str
    port: int
    protocol_version: str
    chain_height: int
    last_seen: float
    reputation: float = 1.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'PeerInfo':
        """Create from dictionary."""
        return PeerInfo(**data)

    def get_address(self) -> str:
        """Get peer address as host:port."""
        return f"{self.host}:{self.port}"


class MessageValidator:
    """Validates network messages."""

    MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_PAYLOAD_ITEMS = 1000

    @staticmethod
    def validate_message(message: NetworkMessage) -> bool:
        """
        Validate a network message.

        Args:
            message: Message to validate

        Returns:
            True if valid
        """
        # Check message type
        try:
            MessageType(message.msg_type)
        except ValueError:
            return False

        # Check payload
        if not isinstance(message.payload, dict):
            return False

        # Check size constraints
        json_str = message.to_json()
        if len(json_str) > MessageValidator.MAX_MESSAGE_SIZE:
            return False

        return True

    @staticmethod
    def validate_block_message(payload: Dict) -> bool:
        """
        Validate block message payload.

        Args:
            payload: Message payload

        Returns:
            True if valid
        """
        required_fields = ['block_data']
        return all(field in payload for field in required_fields)

    @staticmethod
    def validate_transaction_message(payload: Dict) -> bool:
        """
        Validate transaction message payload.

        Args:
            payload: Message payload

        Returns:
            True if valid
        """
        required_fields = ['transaction_data']
        return all(field in payload for field in required_fields)


class RateLimiter:
    """Rate limiting for DOS protection."""

    def __init__(
        self,
        max_messages_per_second: int = 10,
        max_bytes_per_second: int = 1024 * 1024
    ):
        """
        Initialize rate limiter.

        Args:
            max_messages_per_second: Maximum messages per second
            max_bytes_per_second: Maximum bytes per second
        """
        self.max_messages_per_second = max_messages_per_second
        self.max_bytes_per_second = max_bytes_per_second
        self.message_counts: Dict[str, list] = {}
        self.byte_counts: Dict[str, list] = {}

    def check_rate_limit(self, peer_id: str, message_size: int) -> bool:
        """
        Check if peer is within rate limits.

        Args:
            peer_id: Peer identifier
            message_size: Size of message in bytes

        Returns:
            True if within limits
        """
        import time
        current_time = time.time()

        # Initialize peer records
        if peer_id not in self.message_counts:
            self.message_counts[peer_id] = []
            self.byte_counts[peer_id] = []

        # Clean old entries (older than 1 second)
        self.message_counts[peer_id] = [
            t for t in self.message_counts[peer_id]
            if current_time - t < 1.0
        ]
        self.byte_counts[peer_id] = [
            (t, s) for t, s in self.byte_counts[peer_id]
            if current_time - t < 1.0
        ]

        # Check message rate
        if len(self.message_counts[peer_id]) >= self.max_messages_per_second:
            return False

        # Check byte rate
        total_bytes = sum(s for _, s in self.byte_counts[peer_id])
        if total_bytes + message_size > self.max_bytes_per_second:
            return False

        # Update counts
        self.message_counts[peer_id].append(current_time)
        self.byte_counts[peer_id].append((current_time, message_size))

        return True

    def reset_peer(self, peer_id: str) -> None:
        """Reset rate limits for a peer."""
        self.message_counts.pop(peer_id, None)
        self.byte_counts.pop(peer_id, None)
