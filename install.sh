#!/bin/bash
# Installation script for FractalChain

set -e

echo "================================"
echo "  FractalChain Installation"
echo "================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.9 or higher is required"
    exit 1
fi

echo "✓ Python $python_version detected"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Install FractalChain
echo ""
echo "Installing FractalChain..."
pip install -e .

# Create data directories
echo ""
echo "Creating data directories..."
mkdir -p ~/.fractalchain/mainnet
mkdir -p ~/.fractalchain/testnet
mkdir -p ~/.fractalchain/devnet

echo "✓ Data directories created"

# Create default config
echo ""
echo "Creating default configuration..."
if [ ! -f "fractalchain.conf" ]; then
    python3 -c "from utils.config import Config; c = Config(); c.save()"
    echo "✓ Configuration file created: fractalchain.conf"
else
    echo "✓ Configuration file already exists"
fi

# Run tests
echo ""
echo "Running tests..."
pytest tests/ -v

echo ""
echo "================================"
echo "  Installation Complete!"
echo "================================"
echo ""
echo "To get started:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Create a wallet: python3 -m api.cli wallet create"
echo "  3. Start a node: python3 main.py"
echo "  4. Or use CLI: python3 -m api.cli --help"
echo ""
echo "For more information, see README.md"
echo ""
