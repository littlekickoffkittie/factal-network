# FractalChain 🌀

**A revolutionary cryptocurrency powered by fractal mathematics**

FractalChain implements a novel Proof-of-Work consensus mechanism based on Julia set fractals and box-counting dimension calculations, creating a unique and mathematically beautiful blockchain.

## 🌟 Key Features

- **Fractal Proof-of-Work (FractalPoW)**: Novel consensus algorithm using Julia set generation and box-counting dimension
- **Trustless Verification**: Deterministic fractal dimension calculation ensures verifiable consensus
- **Optional AI Audit**: DeepSeek API integration for additional fraud detection
- **Staking System**: Stake tokens to earn rewards and participate in network security
- **P2P Networking**: Robust peer-to-peer network with DoS protection
- **JSON-RPC API**: Full-featured API for wallet and blockchain operations
- **Web Explorer**: Beautiful block explorer with fractal visualization
- **CLI Tools**: Comprehensive command-line interface

## 🔬 How FractalPoW Works

FractalPoW combines cryptographic hashing with fractal mathematics:

1. **Header Pre-filter**: SHA-256 hash must have N leading zero bits
2. **Fractal Seed**: `seed = SHA-256(prev_hash + miner_address + nonce)`
3. **Julia Set Generation**: Generate Julia set fractal from seed
4. **Box-Counting**: Calculate fractal dimension using box-counting algorithm
5. **Difficulty Match**: `|dimension - target| < epsilon`

This creates a two-stage PoW system that is both computationally challenging and mathematically verifiable.

## 📋 Requirements

- Python 3.9 or higher
- 4GB+ RAM (8GB recommended for mining)
- 10GB+ disk space for blockchain data
- Linux, macOS, or Windows with WSL

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/fractalchain/fractalchain.git
cd fractalchain

# Run installation script
chmod +x install.sh
./install.sh

# Activate virtual environment
source venv/bin/activate
```

### Create a Wallet

```bash
python3 -m api.cli wallet create
```

### Start a Node

```bash
# Start a full node
python3 main.py

# Start with mining enabled
python3 main.py --mine

# Start on testnet
python3 main.py --network testnet --port 18333
```

### CLI Commands

```bash
# Get blockchain info
python3 -m api.cli chain info

# Get wallet balance
python3 -m api.cli wallet balance <address>

# Send transaction
python3 -m api.cli wallet send <from> <to> <amount>

# Mine a block
python3 -m api.cli mine <address> --iterations 10000

# Stake tokens
python3 -m api.cli stake create <address> <amount> <lock_period>

# Get stake info
python3 -m api.cli stake info <address>
```

## 📊 Architecture

```
fractalchain/
├── core/                    # Core blockchain components
│   ├── block.py            # Block data structures
│   ├── blockchain.py       # Chain management
│   ├── crypto.py           # Cryptographic utilities
│   ├── merkle.py           # Merkle tree implementation
│   └── transaction.py      # Transaction handling
├── consensus/              # Consensus mechanism
│   ├── fractal_math.py     # Fractal mathematics
│   ├── miner.py            # Mining implementation
│   ├── verification.py     # Block verification
│   └── difficulty.py       # Difficulty adjustment
├── network/                # P2P networking
│   ├── p2p.py              # P2P node implementation
│   └── protocol.py         # Network protocol
├── economic/               # Economic model
│   └── staking.py          # Staking system
├── api/                    # APIs and interfaces
│   ├── rpc_server.py       # JSON-RPC API
│   ├── cli.py              # CLI interface
│   └── web_explorer.py     # Web block explorer
├── utils/                  # Utilities
│   └── config.py           # Configuration management
└── tests/                  # Test suite
```

## 🔧 Configuration

Edit `fractalchain.conf` to customize your node:

```json
{
  "network": {
    "host": "0.0.0.0",
    "port": 8333,
    "bootstrap_peers": [],
    "network_type": "mainnet"
  },
  "fractal": {
    "max_iterations": 256,
    "escape_radius": 2.0,
    "grid_size": 128,
    "target_dimension": 1.5,
    "epsilon": 0.001
  },
  "mining": {
    "enabled": false,
    "threads": 1
  },
  "api": {
    "enabled": true,
    "port": 8545
  },
  "web": {
    "enabled": true,
    "port": 8080
  }
}
```

## 🌐 JSON-RPC API

The RPC server runs on port 8545 by default:

```bash
# Example API calls
curl -X POST http://localhost:8545 -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "method": "getBlockchainInfo",
  "params": [],
  "id": 1
}'

curl -X POST http://localhost:8545 -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "method": "getBalance",
  "params": ["<address>"],
  "id": 1
}'
```

### Available RPC Methods

- `getBlockchainInfo` - Get blockchain statistics
- `getBlock` - Get block by hash or index
- `getBalance` - Get address balance
- `getTransaction` - Get transaction details
- `sendTransaction` - Send a transaction
- `startMining` / `stopMining` - Control mining
- `stake` - Create stake position
- `getStakePositions` - Get stake information
- `getPeerInfo` - Get connected peers

## 🎨 Web Explorer

Access the block explorer at `http://localhost:8080` to:

- View recent blocks and transactions
- Visualize Julia set fractals for each block
- Explore addresses and balances
- Monitor network statistics

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_fractal.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## 🔒 Security Considerations

- **Private Key Security**: Store private keys securely, never commit to version control
- **Network Security**: Use firewall rules to protect RPC/API ports
- **Staking**: Validators who submit invalid blocks will be slashed
- **DoS Protection**: Rate limiting is enabled on P2P connections

## 📈 Performance

### Mining Performance

- Average block time: 10 minutes (configurable)
- Fractal computation: ~100-1000 attempts/second (CPU dependent)
- Memory usage: ~2GB during mining

### Network Performance

- Transaction throughput: ~10-20 TPS
- Block propagation: <5 seconds globally
- P2P connections: Support for 50+ peers

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🔗 Resources

- **Documentation**: [docs/](docs/)
- **GitHub**: https://github.com/fractalchain/fractalchain
- **Discord**: https://discord.gg/fractalchain
- **Twitter**: @fractalchain

## 🎯 Roadmap

- [x] Core blockchain implementation
- [x] FractalPoW consensus
- [x] P2P networking
- [x] Staking system
- [x] Web explorer
- [ ] Mobile wallet
- [ ] Smart contracts
- [ ] Lightning Network integration
- [ ] Hardware wallet support

## ⚠️ Disclaimer

FractalChain is experimental software. Use at your own risk. Do not use for production or financial purposes without thorough testing and security audits.

## 🙏 Acknowledgments

- Inspired by Bitcoin's proof-of-work
- Julia set mathematics from Mandelbrot's research
- Box-counting dimension algorithm from fractal geometry
- Community feedback and contributions

---

**Built with ❤️ and Mathematics**

For questions or support, open an issue on GitHub or join our Discord community.
