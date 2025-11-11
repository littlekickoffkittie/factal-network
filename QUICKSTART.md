# FractalChain Quick Start Guide

Get FractalChain running in 5 minutes!

## Prerequisites

- Python 3.9+
- 4GB RAM minimum
- Internet connection

## Step 1: Install

```bash
# Clone or extract FractalChain
cd fractalchain

# Run installation
chmod +x install.sh
./install.sh
```

Or use make:

```bash
make install
```

## Step 2: Create Wallet

```bash
# Activate virtual environment
source venv/bin/activate

# Create wallet
python3 -m api.cli wallet create
```

Save your wallet address and keep the private key secure!

## Step 3: Start Node

### Option A: Basic Node

```bash
python3 main.py
```

### Option B: Mining Node

```bash
python3 main.py --mine
```

### Option C: Using Make

```bash
make run          # Basic node
make mine         # Mining node
```

### Option D: Docker

```bash
docker-compose up -d
```

## Step 4: Explore

### Web Interface

Open http://localhost:8080 in your browser to:
- View blocks
- See fractal visualizations
- Explore transactions

### RPC API

```bash
# Get blockchain info
curl -X POST http://localhost:8545 -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "method": "getBlockchainInfo",
  "params": [],
  "id": 1
}'
```

### CLI Commands

```bash
# Get blockchain info
python3 -m api.cli chain info

# Get your balance
python3 -m api.cli wallet balance YOUR_ADDRESS

# Mine a block
python3 -m api.cli mine YOUR_ADDRESS
```

## Common Tasks

### Send Transaction

```bash
python3 -m api.cli wallet send FROM_ADDRESS TO_ADDRESS AMOUNT --fee 0.0001
```

### Stake Tokens

```bash
# Stake 100 FRC for 1000 blocks
python3 -m api.cli stake create YOUR_ADDRESS 100 1000

# Check stake status
python3 -m api.cli stake info YOUR_ADDRESS
```

### View Block

```bash
# By index
python3 -m api.cli chain block --index 1

# By hash
python3 -m api.cli chain block --hash BLOCK_HASH
```

## Testnet

To run on testnet:

```bash
python3 main.py --network testnet --port 18333
```

## Troubleshooting

### Port Already in Use

Change the port in `fractalchain.conf`:

```json
{
  "network": {
    "port": 9333
  }
}
```

### Mining Too Slow

Reduce difficulty or increase iterations:

```bash
python3 -m api.cli mine YOUR_ADDRESS --iterations 50000
```

### Can't Connect to Peers

Add bootstrap peers in `fractalchain.conf`:

```json
{
  "network": {
    "bootstrap_peers": [
      "seed1.fractalchain.io:8333",
      "seed2.fractalchain.io:8333"
    ]
  }
}
```

## Next Steps

- Read the full [README.md](README.md)
- Join our Discord community
- Explore the [API documentation](docs/API.md)
- Check out the [architecture guide](docs/ARCHITECTURE.md)

## Need Help?

- GitHub Issues: https://github.com/fractalchain/fractalchain/issues
- Discord: https://discord.gg/fractalchain
- Documentation: [docs/](docs/)

Happy mining! 🌀
