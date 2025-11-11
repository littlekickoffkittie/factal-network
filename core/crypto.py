"""
Cryptographic utilities for FractalChain.
Provides SHA-256 hashing, ECDSA signatures, and key management.
"""

import hashlib
import json
from typing import Any, Dict, Tuple
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigencode_string, sigdecode_string
import binascii


class CryptoUtils:
    """Cryptographic utility functions for FractalChain."""

    @staticmethod
    def sha256(data: str) -> str:
        """
        Compute SHA-256 hash of data.

        Args:
            data: String data to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    @staticmethod
    def sha256_bytes(data: bytes) -> str:
        """
        Compute SHA-256 hash of bytes.

        Args:
            data: Bytes data to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def double_sha256(data: str) -> str:
        """
        Compute double SHA-256 hash (Bitcoin-style).

        Args:
            data: String data to hash

        Returns:
            Hexadecimal hash string
        """
        first_hash = hashlib.sha256(data.encode('utf-8')).digest()
        return hashlib.sha256(first_hash).hexdigest()

    @staticmethod
    def hash_object(obj: Any) -> str:
        """
        Hash a JSON-serializable object.

        Args:
            obj: Object to hash

        Returns:
            Hexadecimal hash string
        """
        json_str = json.dumps(obj, sort_keys=True, separators=(',', ':'))
        return CryptoUtils.sha256(json_str)


class KeyPair:
    """ECDSA key pair for signing and verification."""

    def __init__(self, private_key: SigningKey = None):
        """
        Initialize key pair.

        Args:
            private_key: Existing private key, or None to generate new
        """
        if private_key is None:
            self.private_key = SigningKey.generate(curve=SECP256k1)
        else:
            self.private_key = private_key

        self.public_key = self.private_key.get_verifying_key()

    def get_address(self) -> str:
        """
        Get address derived from public key.

        Returns:
            Hexadecimal address string
        """
        pubkey_bytes = self.public_key.to_string()
        hash1 = hashlib.sha256(pubkey_bytes).digest()
        hash2 = hashlib.new('ripemd160', hash1).digest()
        return binascii.hexlify(hash2).decode('utf-8')

    def sign(self, message: str) -> str:
        """
        Sign a message with private key.

        Args:
            message: Message to sign

        Returns:
            Hexadecimal signature string
        """
        message_hash = hashlib.sha256(message.encode('utf-8')).digest()
        signature = self.private_key.sign_digest(
            message_hash,
            sigencode=sigencode_string
        )
        return binascii.hexlify(signature).decode('utf-8')

    @staticmethod
    def verify(message: str, signature: str, address: str, public_key_hex: str) -> bool:
        """
        Verify a signature.

        Args:
            message: Original message
            signature: Signature to verify
            address: Expected address
            public_key_hex: Public key in hex format

        Returns:
            True if signature is valid
        """
        try:
            # Reconstruct public key
            public_key_bytes = binascii.unhexlify(public_key_hex)
            public_key = VerifyingKey.from_string(public_key_bytes, curve=SECP256k1)

            # Verify address matches public key
            pubkey_bytes = public_key.to_string()
            hash1 = hashlib.sha256(pubkey_bytes).digest()
            hash2 = hashlib.new('ripemd160', hash1).digest()
            derived_address = binascii.hexlify(hash2).decode('utf-8')

            if derived_address != address:
                return False

            # Verify signature
            message_hash = hashlib.sha256(message.encode('utf-8')).digest()
            signature_bytes = binascii.unhexlify(signature)

            return public_key.verify_digest(
                signature_bytes,
                message_hash,
                sigdecode=sigdecode_string
            )
        except Exception:
            return False

    def export_private_key(self) -> str:
        """Export private key as hex string."""
        return binascii.hexlify(self.private_key.to_string()).decode('utf-8')

    def export_public_key(self) -> str:
        """Export public key as hex string."""
        return binascii.hexlify(self.public_key.to_string()).decode('utf-8')

    @staticmethod
    def from_private_key_hex(private_key_hex: str) -> 'KeyPair':
        """
        Load key pair from hex private key.

        Args:
            private_key_hex: Private key in hex format

        Returns:
            KeyPair instance
        """
        private_key_bytes = binascii.unhexlify(private_key_hex)
        private_key = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
        return KeyPair(private_key)
