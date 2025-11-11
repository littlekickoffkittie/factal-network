"""
Configuration management for FractalChain.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Configuration manager for FractalChain."""

    DEFAULT_CONFIG = {
        # Network settings
        'network': {
            'host': '0.0.0.0',
            'port': 8333,
            'bootstrap_peers': [],
            'max_peers': 50,
            'network_type': 'mainnet'  # mainnet, testnet, devnet
        },

        # Blockchain settings
        'blockchain': {
            'db_path': 'fractalchain.db',
            'block_time_target': 600,  # 10 minutes
            'difficulty_adjustment_interval': 2016,
            'max_block_size': 1048576,  # 1 MB
            'genesis_timestamp': 1640000000.0
        },

        # Mining settings
        'mining': {
            'enabled': False,
            'threads': 1,
            'max_iterations': 10000
        },

        # Fractal PoW settings
        'fractal': {
            'max_iterations': 256,
            'escape_radius': 2.0,
            'grid_size': 128,
            'target_dimension': 1.5,
            'epsilon': 0.001,
            'header_difficulty_bits': 16
        },

        # Staking settings
        'staking': {
            'enabled': True,
            'min_stake_amount': 100.0,
            'min_lock_period': 1000,
            'annual_return_rate': 0.05,
            'slash_percentage': 0.10
        },

        # API settings
        'api': {
            'enabled': True,
            'host': '0.0.0.0',
            'port': 8545,
            'cors_origins': ['*']
        },

        # Web interface settings
        'web': {
            'enabled': True,
            'host': '0.0.0.0',
            'port': 8080
        },

        # Verification settings
        'verification': {
            'use_ai_audit': False,
            'deepseek_api_key': None,
            'deepseek_api_url': 'https://api.deepseek.com/v1/chat/completions'
        },

        # Logging settings
        'logging': {
            'level': 'INFO',
            'file': 'fractalchain.log',
            'max_size': 10485760,  # 10 MB
            'backup_count': 5
        },

        # Wallet settings
        'wallet': {
            'keystore_path': 'keystore',
            'default_fee': 0.0001
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config file (JSON)
        """
        self.config_path = config_path or 'fractalchain.conf'
        self.config = self.DEFAULT_CONFIG.copy()

        # Load config from file if exists
        if os.path.exists(self.config_path):
            self.load()

    def load(self) -> None:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                loaded_config = json.load(f)

            # Deep merge with defaults
            self._deep_merge(self.config, loaded_config)

        except Exception as e:
            print(f"Error loading config: {e}")

    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)

        except Exception as e:
            print(f"Error saving config: {e}")

    def _deep_merge(self, base: Dict, update: Dict) -> None:
        """
        Deep merge update dict into base dict.

        Args:
            base: Base dictionary to merge into
            update: Dictionary with updates
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated key path (e.g., 'network.port')
            default: Default value if not found

        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value by dot-separated path.

        Args:
            key_path: Dot-separated key path
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def get_network_config(self) -> Dict:
        """Get network configuration."""
        return self.config['network']

    def get_blockchain_config(self) -> Dict:
        """Get blockchain configuration."""
        return self.config['blockchain']

    def get_mining_config(self) -> Dict:
        """Get mining configuration."""
        return self.config['mining']

    def get_fractal_config(self) -> Dict:
        """Get fractal PoW configuration."""
        return self.config['fractal']

    def get_staking_config(self) -> Dict:
        """Get staking configuration."""
        return self.config['staking']

    def get_api_config(self) -> Dict:
        """Get API configuration."""
        return self.config['api']

    def is_mainnet(self) -> bool:
        """Check if running on mainnet."""
        return self.get('network.network_type') == 'mainnet'

    def is_testnet(self) -> bool:
        """Check if running on testnet."""
        return self.get('network.network_type') == 'testnet'

    def create_data_directory(self) -> Path:
        """
        Create and return data directory.

        Returns:
            Path to data directory
        """
        network_type = self.get('network.network_type')
        data_dir = Path.home() / '.fractalchain' / network_type

        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def get_db_path(self) -> str:
        """Get full database path."""
        data_dir = self.create_data_directory()
        return str(data_dir / self.get('blockchain.db_path'))

    def get_keystore_path(self) -> str:
        """Get full keystore path."""
        data_dir = self.create_data_directory()
        keystore_dir = data_dir / self.get('wallet.keystore_path')
        keystore_dir.mkdir(exist_ok=True)
        return str(keystore_dir)

    def get_log_path(self) -> str:
        """Get full log file path."""
        data_dir = self.create_data_directory()
        return str(data_dir / self.get('logging.file'))

    def to_dict(self) -> Dict:
        """Get configuration as dictionary."""
        return self.config.copy()

    def __repr__(self) -> str:
        """String representation."""
        return f"Config(path='{self.config_path}', network='{self.get('network.network_type')}')"
