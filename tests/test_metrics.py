"""
Tests for metrics collection module.
"""

import pytest
import time
from utils.metrics import MetricsCollector, NodeMetrics


class TestNodeMetrics:
    """Test NodeMetrics dataclass."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = NodeMetrics()
        assert metrics.chain_length == 0
        assert metrics.blocks_mined == 0
        assert metrics.connected_peers == 0

    def test_metrics_update_uptime(self):
        """Test uptime update."""
        metrics = NodeMetrics()
        time.sleep(0.1)
        metrics.update_uptime()
        assert metrics.uptime_seconds > 0

    def test_metrics_to_dict(self):
        """Test metrics to dictionary conversion."""
        metrics = NodeMetrics()
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert 'chain_length' in metrics_dict
        assert 'blocks_mined' in metrics_dict


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_collector_initialization(self):
        """Test collector initialization."""
        collector = MetricsCollector()
        assert collector.metrics.chain_length == 0
        assert len(collector.block_times) == 0

    def test_record_block_mined(self):
        """Test recording mined blocks."""
        collector = MetricsCollector()
        collector.record_block_mined()
        assert collector.metrics.blocks_mined == 1
        assert collector.metrics.chain_length == 1

    def test_record_multiple_blocks(self):
        """Test recording multiple blocks."""
        collector = MetricsCollector()

        for i in range(10):
            collector.record_block_mined(time.time() + i * 10)

        assert collector.metrics.blocks_mined == 10
        assert len(collector.block_times) == 10
        assert collector.metrics.average_block_time > 0

    def test_record_block_received(self):
        """Test recording received blocks."""
        collector = MetricsCollector()
        collector.record_block_received()
        assert collector.metrics.blocks_received == 1

    def test_record_transaction(self):
        """Test recording transactions."""
        collector = MetricsCollector()
        collector.record_transaction(is_pending=True)
        assert collector.metrics.total_transactions == 1
        assert collector.metrics.pending_transactions == 1

    def test_confirm_transactions(self):
        """Test confirming transactions."""
        collector = MetricsCollector()
        collector.record_transaction(is_pending=True)
        collector.record_transaction(is_pending=True)
        collector.confirm_transactions(1)
        assert collector.metrics.pending_transactions == 1

    def test_record_hash_computation(self):
        """Test recording hash computations."""
        collector = MetricsCollector()
        collector.record_hash_computation(1000)
        assert collector.metrics.hashes_computed == 1000

    def test_hashrate_calculation(self):
        """Test hashrate calculation."""
        collector = MetricsCollector()

        # Record some hashes over time
        for i in range(5):
            collector.record_hash_computation(1000)
            time.sleep(0.01)

        assert collector.metrics.mining_hashrate > 0

    def test_record_peer_connection(self):
        """Test recording peer connections."""
        collector = MetricsCollector()
        collector.record_peer_connection(connected=True)
        assert collector.metrics.connected_peers == 1
        assert collector.metrics.total_peers_seen == 1

    def test_record_peer_disconnection(self):
        """Test recording peer disconnections."""
        collector = MetricsCollector()
        collector.record_peer_connection(connected=True)
        collector.record_peer_connection(connected=False)
        assert collector.metrics.connected_peers == 0

    def test_record_network_traffic(self):
        """Test recording network traffic."""
        collector = MetricsCollector()
        collector.record_network_traffic(bytes_sent=1000, bytes_received=2000)
        assert collector.metrics.bytes_sent == 1000
        assert collector.metrics.bytes_received == 2000

    def test_record_verification(self):
        """Test recording verifications."""
        collector = MetricsCollector()
        collector.record_verification(duration=0.5, success=True)
        assert collector.metrics.avg_verification_time == 0.5

    def test_record_verification_failure(self):
        """Test recording verification failures."""
        collector = MetricsCollector()
        collector.record_verification(duration=0.5, success=False)
        assert collector.metrics.verification_failures == 1

    def test_record_mining_attempt(self):
        """Test recording mining attempts."""
        collector = MetricsCollector()
        collector.record_mining_attempt(duration=2.5)
        assert collector.metrics.avg_mining_time == 2.5

    def test_record_stake(self):
        """Test recording stakes."""
        collector = MetricsCollector()
        collector.record_stake(amount=100.0)
        assert collector.metrics.total_staked == 100.0
        assert collector.metrics.staking_positions == 1

    def test_record_unstake(self):
        """Test recording unstakes."""
        collector = MetricsCollector()
        collector.record_stake(amount=100.0)
        collector.record_unstake(amount=50.0)
        assert collector.metrics.total_staked == 50.0

    def test_record_reward(self):
        """Test recording rewards."""
        collector = MetricsCollector()
        collector.record_reward(amount=10.0)
        assert collector.metrics.total_rewards_paid == 10.0

    def test_record_error(self):
        """Test recording errors."""
        collector = MetricsCollector()
        collector.record_error("network")
        collector.record_error("verification")
        collector.record_error("database")

        assert collector.metrics.network_errors == 1
        assert collector.metrics.verification_failures == 1
        assert collector.metrics.database_errors == 1

    def test_get_metrics(self):
        """Test getting metrics snapshot."""
        collector = MetricsCollector()
        collector.record_block_mined()
        metrics = collector.get_metrics()
        assert isinstance(metrics, dict)
        assert metrics['blocks_mined'] == 1

    def test_get_summary(self):
        """Test getting metrics summary."""
        collector = MetricsCollector()
        collector.record_block_mined()
        summary = collector.get_summary()
        assert isinstance(summary, str)
        assert 'FractalChain Node Metrics' in summary

    def test_reset(self):
        """Test resetting metrics."""
        collector = MetricsCollector()
        collector.record_block_mined()
        collector.reset()
        assert collector.metrics.blocks_mined == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
