"""
Monitoring and metrics collection for FractalChain.
Tracks node performance, network stats, and blockchain metrics.
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import deque
import json


@dataclass
class NodeMetrics:
    """Comprehensive node metrics."""

    # System metrics
    start_time: float = field(default_factory=time.time)
    uptime_seconds: float = 0.0

    # Blockchain metrics
    chain_length: int = 0
    total_transactions: int = 0
    pending_transactions: int = 0
    total_difficulty: float = 0.0
    average_block_time: float = 0.0

    # Mining metrics
    blocks_mined: int = 0
    hashes_computed: int = 0
    mining_hashrate: float = 0.0  # hashes per second
    last_block_time: float = 0.0

    # Network metrics
    connected_peers: int = 0
    total_peers_seen: int = 0
    blocks_received: int = 0
    blocks_sent: int = 0
    transactions_received: int = 0
    transactions_sent: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0

    # Staking metrics
    total_staked: float = 0.0
    staking_positions: int = 0
    total_rewards_paid: float = 0.0

    # Performance metrics
    avg_verification_time: float = 0.0
    avg_mining_time: float = 0.0
    avg_sync_time: float = 0.0

    # Error metrics
    verification_failures: int = 0
    network_errors: int = 0
    database_errors: int = 0

    def update_uptime(self):
        """Update uptime counter."""
        self.uptime_seconds = time.time() - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        self.update_uptime()
        return asdict(self)


class MetricsCollector:
    """Collects and aggregates metrics over time."""

    def __init__(self, window_size: int = 3600):
        """
        Initialize metrics collector.

        Args:
            window_size: Size of rolling window in seconds
        """
        self.window_size = window_size
        self.metrics = NodeMetrics()
        self.lock = threading.Lock()

        # Time-series data (timestamp, value)
        self.block_times: deque = deque(maxlen=2016)  # Last 2016 blocks
        self.hashrate_samples: deque = deque(maxlen=60)  # Last 60 samples
        self.peer_count_history: deque = deque(maxlen=1440)  # Last 24 hours (1 min intervals)

        # Performance tracking
        self.verification_times: deque = deque(maxlen=1000)
        self.mining_times: deque = deque(maxlen=100)

    def record_block_mined(self, block_time: float = None):
        """
        Record a newly mined block.

        Args:
            block_time: Block timestamp (defaults to current time)
        """
        with self.lock:
            self.metrics.blocks_mined += 1
            self.metrics.chain_length += 1

            block_time = block_time or time.time()
            self.metrics.last_block_time = block_time

            if len(self.block_times) > 0:
                time_diff = block_time - self.block_times[-1]
                self.block_times.append(block_time)

                # Calculate average block time
                if len(self.block_times) > 1:
                    diffs = [
                        self.block_times[i] - self.block_times[i-1]
                        for i in range(1, len(self.block_times))
                    ]
                    self.metrics.average_block_time = sum(diffs) / len(diffs)
            else:
                self.block_times.append(block_time)

    def record_block_received(self):
        """Record a block received from network."""
        with self.lock:
            self.metrics.blocks_received += 1
            self.metrics.chain_length += 1

    def record_block_sent(self):
        """Record a block sent to network."""
        with self.lock:
            self.metrics.blocks_sent += 1

    def record_transaction(self, is_pending: bool = True):
        """
        Record a transaction.

        Args:
            is_pending: Whether transaction is pending or confirmed
        """
        with self.lock:
            self.metrics.total_transactions += 1
            if is_pending:
                self.metrics.pending_transactions += 1

    def confirm_transactions(self, count: int):
        """
        Record confirmed transactions.

        Args:
            count: Number of transactions confirmed
        """
        with self.lock:
            self.metrics.pending_transactions = max(0, self.metrics.pending_transactions - count)

    def record_hash_computation(self, count: int = 1):
        """
        Record hash computations for mining.

        Args:
            count: Number of hashes computed
        """
        with self.lock:
            self.metrics.hashes_computed += count

            # Sample hashrate every second
            self.hashrate_samples.append((time.time(), count))

            # Calculate hashrate from recent samples
            if len(self.hashrate_samples) > 1:
                time_window = self.hashrate_samples[-1][0] - self.hashrate_samples[0][0]
                if time_window > 0:
                    total_hashes = sum(count for _, count in self.hashrate_samples)
                    self.metrics.mining_hashrate = total_hashes / time_window

    def record_peer_connection(self, connected: bool = True):
        """
        Record peer connection/disconnection.

        Args:
            connected: Whether peer connected (True) or disconnected (False)
        """
        with self.lock:
            if connected:
                self.metrics.connected_peers += 1
                self.metrics.total_peers_seen += 1
            else:
                self.metrics.connected_peers = max(0, self.metrics.connected_peers - 1)

    def record_network_traffic(self, bytes_sent: int = 0, bytes_received: int = 0):
        """
        Record network traffic.

        Args:
            bytes_sent: Bytes sent
            bytes_received: Bytes received
        """
        with self.lock:
            self.metrics.bytes_sent += bytes_sent
            self.metrics.bytes_received += bytes_received

    def record_verification(self, duration: float, success: bool = True):
        """
        Record block verification.

        Args:
            duration: Verification duration in seconds
            success: Whether verification succeeded
        """
        with self.lock:
            self.verification_times.append(duration)

            if len(self.verification_times) > 0:
                self.metrics.avg_verification_time = sum(self.verification_times) / len(self.verification_times)

            if not success:
                self.metrics.verification_failures += 1

    def record_mining_attempt(self, duration: float):
        """
        Record mining attempt.

        Args:
            duration: Mining duration in seconds
        """
        with self.lock:
            self.mining_times.append(duration)

            if len(self.mining_times) > 0:
                self.metrics.avg_mining_time = sum(self.mining_times) / len(self.mining_times)

    def record_stake(self, amount: float):
        """
        Record new stake.

        Args:
            amount: Amount staked
        """
        with self.lock:
            self.metrics.total_staked += amount
            self.metrics.staking_positions += 1

    def record_unstake(self, amount: float):
        """
        Record unstake.

        Args:
            amount: Amount unstaked
        """
        with self.lock:
            self.metrics.total_staked = max(0, self.metrics.total_staked - amount)
            self.metrics.staking_positions = max(0, self.metrics.staking_positions - 1)

    def record_reward(self, amount: float):
        """
        Record reward payment.

        Args:
            amount: Reward amount
        """
        with self.lock:
            self.metrics.total_rewards_paid += amount

    def record_error(self, error_type: str):
        """
        Record error occurrence.

        Args:
            error_type: Type of error (network, verification, database)
        """
        with self.lock:
            if error_type == "network":
                self.metrics.network_errors += 1
            elif error_type == "verification":
                self.metrics.verification_failures += 1
            elif error_type == "database":
                self.metrics.database_errors += 1

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics snapshot.

        Returns:
            Dictionary of current metrics
        """
        with self.lock:
            return self.metrics.to_dict()

    def get_summary(self) -> str:
        """
        Get human-readable metrics summary.

        Returns:
            Formatted metrics string
        """
        metrics = self.get_metrics()

        summary = f"""
FractalChain Node Metrics
========================
Uptime: {metrics['uptime_seconds'] / 3600:.2f} hours

Blockchain:
  Chain Length: {metrics['chain_length']}
  Total Transactions: {metrics['total_transactions']}
  Pending Transactions: {metrics['pending_transactions']}
  Average Block Time: {metrics['average_block_time']:.2f}s

Mining:
  Blocks Mined: {metrics['blocks_mined']}
  Total Hashes: {metrics['hashes_computed']}
  Hashrate: {metrics['mining_hashrate']:.2f} H/s
  Avg Mining Time: {metrics['avg_mining_time']:.2f}s

Network:
  Connected Peers: {metrics['connected_peers']}
  Total Peers Seen: {metrics['total_peers_seen']}
  Blocks Received: {metrics['blocks_received']}
  Blocks Sent: {metrics['blocks_sent']}
  Data Sent: {metrics['bytes_sent'] / 1024 / 1024:.2f} MB
  Data Received: {metrics['bytes_received'] / 1024 / 1024:.2f} MB

Staking:
  Total Staked: {metrics['total_staked']:.2f}
  Positions: {metrics['staking_positions']}
  Rewards Paid: {metrics['total_rewards_paid']:.2f}

Performance:
  Avg Verification: {metrics['avg_verification_time']:.4f}s

Errors:
  Verification Failures: {metrics['verification_failures']}
  Network Errors: {metrics['network_errors']}
  Database Errors: {metrics['database_errors']}
"""
        return summary

    def export_metrics(self, filepath: str):
        """
        Export metrics to JSON file.

        Args:
            filepath: Path to export file
        """
        metrics = self.get_metrics()

        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)

    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.metrics = NodeMetrics()
            self.block_times.clear()
            self.hashrate_samples.clear()
            self.peer_count_history.clear()
            self.verification_times.clear()
            self.mining_times.clear()


# Global metrics instance
_global_metrics = None
_metrics_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """
    Get global metrics collector instance.

    Returns:
        Global MetricsCollector instance
    """
    global _global_metrics

    with _metrics_lock:
        if _global_metrics is None:
            _global_metrics = MetricsCollector()

    return _global_metrics
