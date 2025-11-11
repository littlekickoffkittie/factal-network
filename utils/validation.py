"""
Input validation and sanitization for FractalChain.
Provides security checks and data validation.
"""

import re
from typing import Any, Optional, Tuple
from decimal import Decimal, InvalidOperation


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class Validator:
    """Comprehensive input validation for blockchain operations."""

    # Address format: 40 hex characters (derived from RIPEMD-160)
    ADDRESS_PATTERN = re.compile(r'^[0-9a-f]{40}$', re.IGNORECASE)

    # Hash format: 64 hex characters (SHA-256)
    HASH_PATTERN = re.compile(r'^[0-9a-f]{64}$', re.IGNORECASE)

    # Signature format: variable length hex
    SIGNATURE_PATTERN = re.compile(r'^[0-9a-f]+$', re.IGNORECASE)

    # Maximum values for safety
    MAX_AMOUNT = Decimal('21000000')  # Total supply limit
    MIN_AMOUNT = Decimal('0.00000001')  # Minimum transaction amount (1 satoshi equivalent)
    MAX_FEE = Decimal('1000')  # Maximum reasonable fee
    MIN_FEE = Decimal('0')  # Minimum fee (free transactions allowed)

    MAX_STRING_LENGTH = 10000
    MAX_ARRAY_LENGTH = 10000

    @staticmethod
    def validate_address(address: str) -> Tuple[bool, Optional[str]]:
        """
        Validate blockchain address format.

        Args:
            address: Address string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(address, str):
            return False, "Address must be a string"

        # Special addresses
        if address in ["COINBASE", "GENESIS"]:
            return True, None

        if not Validator.ADDRESS_PATTERN.match(address):
            return False, "Invalid address format (must be 40 hex characters)"

        return True, None

    @staticmethod
    def validate_hash(hash_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate hash format.

        Args:
            hash_str: Hash string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(hash_str, str):
            return False, "Hash must be a string"

        if not Validator.HASH_PATTERN.match(hash_str):
            return False, "Invalid hash format (must be 64 hex characters)"

        return True, None

    @staticmethod
    def validate_signature(signature: str) -> Tuple[bool, Optional[str]]:
        """
        Validate signature format.

        Args:
            signature: Signature string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(signature, str):
            return False, "Signature must be a string"

        if len(signature) < 64 or len(signature) > 512:
            return False, "Signature length out of range"

        if not Validator.SIGNATURE_PATTERN.match(signature):
            return False, "Invalid signature format (must be hex)"

        return True, None

    @staticmethod
    def validate_amount(amount: float, allow_zero: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate transaction amount.

        Args:
            amount: Amount to validate
            allow_zero: Whether to allow zero amounts

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            amount_dec = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            return False, "Amount must be a valid number"

        if not allow_zero and amount_dec <= 0:
            return False, "Amount must be positive"

        if amount_dec < 0:
            return False, "Amount cannot be negative"

        if amount_dec < Validator.MIN_AMOUNT and amount_dec != 0:
            return False, f"Amount below minimum ({Validator.MIN_AMOUNT})"

        if amount_dec > Validator.MAX_AMOUNT:
            return False, f"Amount exceeds maximum ({Validator.MAX_AMOUNT})"

        # Check precision (max 8 decimal places)
        if amount_dec.as_tuple().exponent < -8:
            return False, "Amount has too many decimal places (max 8)"

        return True, None

    @staticmethod
    def validate_fee(fee: float) -> Tuple[bool, Optional[str]]:
        """
        Validate transaction fee.

        Args:
            fee: Fee to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            fee_dec = Decimal(str(fee))
        except (InvalidOperation, ValueError):
            return False, "Fee must be a valid number"

        if fee_dec < Validator.MIN_FEE:
            return False, "Fee cannot be negative"

        if fee_dec > Validator.MAX_FEE:
            return False, f"Fee exceeds maximum ({Validator.MAX_FEE})"

        return True, None

    @staticmethod
    def validate_timestamp(timestamp: float, max_drift: float = 7200) -> Tuple[bool, Optional[str]]:
        """
        Validate timestamp (not too far in future).

        Args:
            timestamp: Unix timestamp to validate
            max_drift: Maximum future drift allowed (seconds)

        Returns:
            Tuple of (is_valid, error_message)
        """
        import time

        if not isinstance(timestamp, (int, float)):
            return False, "Timestamp must be a number"

        if timestamp < 0:
            return False, "Timestamp cannot be negative"

        current_time = time.time()
        if timestamp > current_time + max_drift:
            return False, f"Timestamp too far in future (max drift: {max_drift}s)"

        # Check if timestamp is reasonable (after year 2020)
        if timestamp < 1577836800:  # Jan 1, 2020
            return False, "Timestamp too old"

        return True, None

    @staticmethod
    def validate_port(port: int) -> Tuple[bool, Optional[str]]:
        """
        Validate network port number.

        Args:
            port: Port number to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(port, int):
            return False, "Port must be an integer"

        if port < 1024 or port > 65535:
            return False, "Port must be between 1024 and 65535"

        return True, None

    @staticmethod
    def validate_ip(ip: str) -> Tuple[bool, Optional[str]]:
        """
        Validate IP address.

        Args:
            ip: IP address to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(ip, str):
            return False, "IP must be a string"

        # Allow special values
        if ip in ["0.0.0.0", "localhost", "127.0.0.1"]:
            return True, None

        # Basic IPv4 validation
        parts = ip.split('.')
        if len(parts) != 4:
            return False, "Invalid IPv4 format"

        for part in parts:
            try:
                num = int(part)
                if num < 0 or num > 255:
                    return False, "IPv4 octet out of range (0-255)"
            except ValueError:
                return False, "IPv4 octet must be a number"

        return True, None

    @staticmethod
    def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize string input.

        Args:
            value: String to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            value = str(value)

        # Remove control characters except newlines and tabs
        value = ''.join(char for char in value if char.isprintable() or char in '\n\t')

        # Limit length
        max_len = max_length or Validator.MAX_STRING_LENGTH
        if len(value) > max_len:
            value = value[:max_len]

        return value

    @staticmethod
    def validate_difficulty(target: float, epsilon: float) -> Tuple[bool, Optional[str]]:
        """
        Validate difficulty parameters.

        Args:
            target: Target fractal dimension
            epsilon: Tolerance value

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(target, (int, float)):
            return False, "Target must be a number"

        if target < 0 or target > 3:
            return False, "Target dimension out of range (0-3)"

        if not isinstance(epsilon, (int, float)):
            return False, "Epsilon must be a number"

        if epsilon <= 0 or epsilon > 1:
            return False, "Epsilon out of range (0-1)"

        return True, None

    @staticmethod
    def validate_block_index(index: int, chain_length: int) -> Tuple[bool, Optional[str]]:
        """
        Validate block index.

        Args:
            index: Block index to validate
            chain_length: Current blockchain length

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(index, int):
            return False, "Block index must be an integer"

        if index < 0:
            return False, "Block index cannot be negative"

        if index >= chain_length:
            return False, f"Block index out of range (max: {chain_length - 1})"

        return True, None

    @staticmethod
    def validate_nonce(nonce: int) -> Tuple[bool, Optional[str]]:
        """
        Validate mining nonce.

        Args:
            nonce: Nonce value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(nonce, int):
            return False, "Nonce must be an integer"

        if nonce < 0:
            return False, "Nonce cannot be negative"

        if nonce > 2**64:
            return False, "Nonce too large"

        return True, None


class RateLimiter:
    """Simple rate limiter for API and network requests."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict = {}  # {identifier: [(timestamp, count)]}

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed.

        Args:
            identifier: Unique identifier (IP, address, etc.)

        Returns:
            True if request is allowed
        """
        import time

        current_time = time.time()

        # Clean old entries
        if identifier in self.requests:
            self.requests[identifier] = [
                (ts, count) for ts, count in self.requests[identifier]
                if current_time - ts < self.window_seconds
            ]
        else:
            self.requests[identifier] = []

        # Count recent requests
        total_requests = sum(count for _, count in self.requests[identifier])

        if total_requests >= self.max_requests:
            return False

        # Add this request
        self.requests[identifier].append((current_time, 1))
        return True

    def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests for identifier.

        Args:
            identifier: Unique identifier

        Returns:
            Number of remaining requests
        """
        import time

        current_time = time.time()

        if identifier not in self.requests:
            return self.max_requests

        # Count recent requests
        total_requests = sum(
            count for ts, count in self.requests[identifier]
            if current_time - ts < self.window_seconds
        )

        return max(0, self.max_requests - total_requests)
