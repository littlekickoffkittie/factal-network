#!/usr/bin/env python3
"""
FractalChain Monitoring Dashboard
Real-time monitoring and metrics display for FractalChain nodes.
"""

import time
import sys
import requests
from datetime import datetime
from typing import Dict, Any


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def clear_screen():
    """Clear terminal screen."""
    print('\033[2J\033[H', end='')


def print_header(title: str):
    """Print section header."""
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print()


def print_metric(label: str, value: Any, color: str = Colors.CYAN):
    """Print a metric with label and value."""
    print(f"{Colors.BOLD}{label}:{Colors.ENDC} {color}{value}{Colors.ENDC}")


def format_bytes(bytes_count: int) -> str:
    """Format bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def get_rpc_data(endpoint: str, method: str, params: list = None) -> Dict[str, Any]:
    """
    Fetch data from RPC server.

    Args:
        endpoint: RPC endpoint URL
        method: RPC method name
        params: Method parameters

    Returns:
        RPC response data
    """
    try:
        response = requests.post(
            endpoint,
            json={
                "jsonrpc": "2.0",
                "method": method,
                "params": params or [],
                "id": 1
            },
            timeout=5
        )
        response.raise_for_status()
        return response.json().get('result', {})
    except Exception as e:
        return {'error': str(e)}


def display_dashboard(endpoint: str = "http://localhost:8545"):
    """
    Display monitoring dashboard.

    Args:
        endpoint: RPC endpoint URL
    """
    clear_screen()

    # Header
    print_header("FractalChain Node Monitor")
    print(f"{Colors.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
    print(f"{Colors.CYAN}Endpoint: {endpoint}{Colors.ENDC}")
    print()

    # Get blockchain info
    blockchain_info = get_rpc_data(endpoint, "getBlockchainInfo")

    if 'error' in blockchain_info:
        print(f"{Colors.RED}✗ Cannot connect to RPC server{Colors.ENDC}")
        print(f"{Colors.RED}Error: {blockchain_info['error']}{Colors.ENDC}")
        return

    # Blockchain Section
    print(f"{Colors.HEADER}{Colors.BOLD}BLOCKCHAIN{Colors.ENDC}")
    print_metric("  Chain Length", blockchain_info.get('chain_length', 0), Colors.GREEN)
    print_metric("  Total Transactions", blockchain_info.get('total_transactions', 0))
    print_metric("  Pending Transactions", blockchain_info.get('pending_transactions', 0))
    print_metric("  Current Difficulty", f"{blockchain_info.get('current_difficulty', 0):.6f}")
    print()

    # Mining Section
    if blockchain_info.get('mining_enabled'):
        print(f"{Colors.HEADER}{Colors.BOLD}MINING{Colors.ENDC}")
        print_metric("  Status", "ACTIVE", Colors.GREEN)
        print_metric("  Blocks Mined", blockchain_info.get('blocks_mined', 0))
        hashrate = blockchain_info.get('hashrate', 0)
        print_metric("  Hashrate", f"{hashrate:.2f} H/s")
        print()

    # Network Section
    peer_info = get_rpc_data(endpoint, "getPeerInfo")
    print(f"{Colors.HEADER}{Colors.BOLD}NETWORK{Colors.ENDC}")
    print_metric("  Connected Peers", len(peer_info) if isinstance(peer_info, list) else 0)

    if isinstance(peer_info, list) and len(peer_info) > 0:
        print(f"  {Colors.BOLD}Peer List:{Colors.ENDC}")
        for peer in peer_info[:5]:  # Show first 5 peers
            print(f"    • {peer.get('address', 'unknown')} - {peer.get('state', 'unknown')}")

    print()

    # Staking Section (if available)
    print(f"{Colors.HEADER}{Colors.BOLD}STAKING{Colors.ENDC}")
    print_metric("  Total Staked", f"{blockchain_info.get('total_staked', 0):.2f}")
    print_metric("  Staking Positions", blockchain_info.get('staking_positions', 0))
    print()

    # Performance Section
    print(f"{Colors.HEADER}{Colors.BOLD}PERFORMANCE{Colors.ENDC}")
    avg_verify = blockchain_info.get('avg_verification_time', 0)
    print_metric("  Avg Verification Time", f"{avg_verify * 1000:.2f}ms")

    uptime = blockchain_info.get('uptime', 0)
    print_metric("  Uptime", format_duration(uptime), Colors.GREEN)
    print()

    # Footer
    print(f"{Colors.CYAN}Press Ctrl+C to exit{Colors.ENDC}")


def main():
    """Main monitoring loop."""
    import argparse

    parser = argparse.ArgumentParser(description='FractalChain Node Monitor')
    parser.add_argument(
        '--endpoint',
        type=str,
        default='http://localhost:8545',
        help='RPC endpoint URL'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=2,
        help='Update interval in seconds'
    )

    args = parser.parse_args()

    print(f"{Colors.GREEN}Starting FractalChain Monitor...{Colors.ENDC}")
    time.sleep(1)

    try:
        while True:
            display_dashboard(args.endpoint)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitor stopped{Colors.ENDC}")
        sys.exit(0)


if __name__ == '__main__':
    main()
