"""
Tests for validation module.
"""

import pytest
from utils.validation import Validator, ValidationError, RateLimiter


class TestValidator:
    """Test validation functions."""

    def test_validate_address_valid(self):
        """Test valid address validation."""
        valid_address = "a" * 40
        is_valid, error = Validator.validate_address(valid_address)
        assert is_valid
        assert error is None

    def test_validate_address_special(self):
        """Test special addresses."""
        is_valid, error = Validator.validate_address("COINBASE")
        assert is_valid

        is_valid, error = Validator.validate_address("GENESIS")
        assert is_valid

    def test_validate_address_invalid(self):
        """Test invalid address validation."""
        is_valid, error = Validator.validate_address("invalid")
        assert not is_valid
        assert error is not None

    def test_validate_hash_valid(self):
        """Test valid hash validation."""
        valid_hash = "a" * 64
        is_valid, error = Validator.validate_hash(valid_hash)
        assert is_valid
        assert error is None

    def test_validate_hash_invalid(self):
        """Test invalid hash validation."""
        is_valid, error = Validator.validate_hash("toolong" * 20)
        assert not is_valid

    def test_validate_amount_valid(self):
        """Test valid amount validation."""
        is_valid, error = Validator.validate_amount(100.5)
        assert is_valid
        assert error is None

    def test_validate_amount_negative(self):
        """Test negative amount validation."""
        is_valid, error = Validator.validate_amount(-10)
        assert not is_valid

    def test_validate_amount_zero(self):
        """Test zero amount validation."""
        is_valid, error = Validator.validate_amount(0, allow_zero=True)
        assert is_valid

        is_valid, error = Validator.validate_amount(0, allow_zero=False)
        assert not is_valid

    def test_validate_amount_too_large(self):
        """Test amount exceeding maximum."""
        is_valid, error = Validator.validate_amount(30000000)
        assert not is_valid

    def test_validate_amount_precision(self):
        """Test amount precision validation."""
        is_valid, error = Validator.validate_amount(0.123456789)
        assert not is_valid  # Too many decimal places

        is_valid, error = Validator.validate_amount(0.12345678)
        assert is_valid  # Exactly 8 decimal places

    def test_validate_fee_valid(self):
        """Test valid fee validation."""
        is_valid, error = Validator.validate_fee(0.01)
        assert is_valid

    def test_validate_fee_negative(self):
        """Test negative fee validation."""
        is_valid, error = Validator.validate_fee(-1)
        assert not is_valid

    def test_validate_timestamp_valid(self):
        """Test valid timestamp validation."""
        import time
        current = time.time()
        is_valid, error = Validator.validate_timestamp(current)
        assert is_valid

    def test_validate_timestamp_future(self):
        """Test future timestamp validation."""
        import time
        future = time.time() + 10000
        is_valid, error = Validator.validate_timestamp(future)
        assert not is_valid

    def test_validate_port_valid(self):
        """Test valid port validation."""
        is_valid, error = Validator.validate_port(8333)
        assert is_valid

    def test_validate_port_invalid(self):
        """Test invalid port validation."""
        is_valid, error = Validator.validate_port(100)
        assert not is_valid

        is_valid, error = Validator.validate_port(70000)
        assert not is_valid

    def test_validate_ip_valid(self):
        """Test valid IP validation."""
        is_valid, error = Validator.validate_ip("192.168.1.1")
        assert is_valid

        is_valid, error = Validator.validate_ip("0.0.0.0")
        assert is_valid

    def test_validate_ip_invalid(self):
        """Test invalid IP validation."""
        is_valid, error = Validator.validate_ip("256.1.1.1")
        assert not is_valid

        is_valid, error = Validator.validate_ip("invalid")
        assert not is_valid

    def test_sanitize_string(self):
        """Test string sanitization."""
        dirty = "Hello\x00World\x01"
        clean = Validator.sanitize_string(dirty)
        assert "\x00" not in clean
        assert "\x01" not in clean

    def test_sanitize_string_length(self):
        """Test string length limiting."""
        long_string = "a" * 20000
        clean = Validator.sanitize_string(long_string, max_length=100)
        assert len(clean) == 100

    def test_validate_difficulty(self):
        """Test difficulty validation."""
        is_valid, error = Validator.validate_difficulty(1.5, 0.001)
        assert is_valid

        is_valid, error = Validator.validate_difficulty(-1, 0.001)
        assert not is_valid

        is_valid, error = Validator.validate_difficulty(1.5, 0)
        assert not is_valid

    def test_validate_nonce(self):
        """Test nonce validation."""
        is_valid, error = Validator.validate_nonce(12345)
        assert is_valid

        is_valid, error = Validator.validate_nonce(-1)
        assert not is_valid


class TestRateLimiter:
    """Test rate limiting."""

    def test_rate_limiter_allow(self):
        """Test rate limiter allows requests."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        for i in range(5):
            assert limiter.is_allowed("test_user")

    def test_rate_limiter_block(self):
        """Test rate limiter blocks excess requests."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        for i in range(3):
            assert limiter.is_allowed("test_user")

        # 4th request should be blocked
        assert not limiter.is_allowed("test_user")

    def test_rate_limiter_different_users(self):
        """Test rate limiter tracks different users separately."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        assert limiter.is_allowed("user1")
        assert limiter.is_allowed("user1")
        assert not limiter.is_allowed("user1")

        # Different user should be allowed
        assert limiter.is_allowed("user2")

    def test_rate_limiter_remaining(self):
        """Test remaining requests count."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        assert limiter.get_remaining("test_user") == 5

        limiter.is_allowed("test_user")
        assert limiter.get_remaining("test_user") == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
