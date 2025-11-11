"""
Web-based block explorer for FractalChain.
Provides visualization of blocks, fractals, and network statistics.
"""

import io
import base64
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ..core.blockchain import Blockchain
from ..consensus.fractal_math import JuliaSetGenerator, FractalConfig
from ..economic.staking import StakingSystem
from ..network.p2p import P2PNode


class BlockExplorer:
    """
    Web-based block explorer for FractalChain.
    """

    def __init__(
        self,
        blockchain: Blockchain,
        staking: StakingSystem = None,
        p2p_node: P2PNode = None,
        host: str = "0.0.0.0",
        port: int = 8080
    ):
        """
        Initialize block explorer.

        Args:
            blockchain: Blockchain instance
            staking: Staking system
            p2p_node: P2P node
            host: Server host
            port: Server port
        """
        self.blockchain = blockchain
        self.staking = staking
        self.p2p_node = p2p_node
        self.host = host
        self.port = port

        # Fractal generator for visualization
        self.fractal_gen = JuliaSetGenerator(FractalConfig())

        # Create FastAPI app
        self.app = FastAPI(title="FractalChain Explorer", version="1.0.0")

        # Add CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register API routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Serve main page."""
            return self._get_explorer_html()

        @self.app.get("/api/stats")
        async def get_stats():
            """Get blockchain statistics."""
            latest_block = self.blockchain.get_latest_block()
            difficulty_target, header_bits = self.blockchain.get_difficulty()

            stats = {
                "chain_length": self.blockchain.get_chain_length(),
                "latest_block_hash": latest_block.block_hash if latest_block else "",
                "latest_block_index": latest_block.index if latest_block else 0,
                "difficulty_target": difficulty_target,
                "header_difficulty_bits": header_bits,
                "block_reward": self.blockchain.get_block_reward(),
                "pending_transactions": len(self.blockchain.pending_transactions)
            }

            if self.staking:
                stats["staking"] = self.staking.get_statistics()

            if self.p2p_node:
                stats["network"] = self.p2p_node.get_stats()

            return stats

        @self.app.get("/api/blocks")
        async def get_blocks(start: int = 0, count: int = 10):
            """Get recent blocks."""
            blocks = []
            chain_length = self.blockchain.get_chain_length()

            start_index = max(0, min(start, chain_length - 1))
            end_index = min(start_index + count, chain_length)

            for i in range(start_index, end_index):
                block = self.blockchain.get_block_by_index(i)
                if block:
                    blocks.append({
                        "index": block.index,
                        "hash": block.block_hash,
                        "timestamp": block.timestamp,
                        "miner": block.miner_address,
                        "transactions": len(block.transactions),
                        "dimension": block.fractal_proof.fractal_dimension if block.fractal_proof else None
                    })

            return blocks

        @self.app.get("/api/block/{block_id}")
        async def get_block(block_id: str):
            """Get block details."""
            # Try as hash first
            block = self.blockchain.get_block_by_hash(block_id)

            # Try as index
            if not block:
                try:
                    index = int(block_id)
                    block = self.blockchain.get_block_by_index(index)
                except ValueError:
                    pass

            if not block:
                raise HTTPException(status_code=404, detail="Block not found")

            return block.to_dict()

        @self.app.get("/api/fractal/{block_id}")
        async def get_fractal_image(block_id: str):
            """Get fractal visualization for a block."""
            # Get block
            block = self.blockchain.get_block_by_hash(block_id)

            if not block:
                try:
                    index = int(block_id)
                    block = self.blockchain.get_block_by_index(index)
                except ValueError:
                    pass

            if not block or not block.fractal_proof:
                raise HTTPException(status_code=404, detail="Block or fractal not found")

            # Generate fractal
            c = self.fractal_gen.generate_c_from_seed(block.fractal_proof.fractal_seed)
            solution_point = block.fractal_proof.get_solution_point()

            iterations = self.fractal_gen.compute_julia_set(c, solution_point)

            # Create visualization
            plt.figure(figsize=(8, 8))
            plt.imshow(iterations, cmap='hot', interpolation='bilinear')
            plt.colorbar(label='Iterations to escape')
            plt.title(f'Julia Set - Block {block.index}\nDimension: {block.fractal_proof.fractal_dimension:.6f}')
            plt.xlabel('Real')
            plt.ylabel('Imaginary')

            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            # Encode as base64
            image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

            return {
                "image": f"data:image/png;base64,{image_base64}",
                "dimension": block.fractal_proof.fractal_dimension,
                "seed": block.fractal_proof.fractal_seed
            }

        @self.app.get("/api/transaction/{tx_hash}")
        async def get_transaction(tx_hash: str):
            """Get transaction details."""
            for block in self.blockchain.chain:
                for tx in block.transactions:
                    if tx.tx_hash == tx_hash:
                        return {
                            **tx.to_dict(),
                            "block_index": block.index,
                            "block_hash": block.block_hash,
                            "confirmations": self.blockchain.get_chain_length() - block.index
                        }

            raise HTTPException(status_code=404, detail="Transaction not found")

        @self.app.get("/api/address/{address}")
        async def get_address_info(address: str):
            """Get address information."""
            balance = self.blockchain.get_balance(address)

            # Get transactions
            transactions = []
            for block in self.blockchain.chain:
                for tx in block.transactions:
                    if tx.sender == address or tx.recipient == address:
                        transactions.append({
                            "tx_hash": tx.tx_hash,
                            "block_index": block.index,
                            "timestamp": tx.timestamp,
                            "amount": tx.amount,
                            "fee": tx.fee,
                            "type": "sent" if tx.sender == address else "received"
                        })

            # Get stake info
            stake_info = None
            if self.staking:
                positions = self.staking.get_stake_positions(address)
                stake_info = {
                    "total_staked": self.staking.get_total_staked_by_address(address),
                    "staking_power": self.staking.get_staking_power(address),
                    "positions": [pos.to_dict() for pos in positions]
                }

            return {
                "address": address,
                "balance": balance,
                "transaction_count": len(transactions),
                "transactions": sorted(transactions, key=lambda x: x['timestamp'], reverse=True)[:10],
                "stake_info": stake_info
            }

    def _get_explorer_html(self) -> str:
        """Get explorer HTML."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FractalChain Explorer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .header h1 {
            font-size: 2.5em;
            color: #667eea;
            margin-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .stat-card h3 { color: #667eea; margin-bottom: 10px; }
        .stat-card .value { font-size: 2em; font-weight: bold; color: #333; }
        .blocks-section {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .blocks-section h2 { color: #667eea; margin-bottom: 20px; }
        .block-item {
            border-left: 4px solid #667eea;
            padding: 15px;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .block-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        .block-item h4 { color: #333; margin-bottom: 5px; }
        .block-item p { color: #666; font-size: 0.9em; }
        .fractal-viewer {
            margin-top: 20px;
            text-align: center;
        }
        .fractal-viewer img {
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .loading { text-align: center; padding: 50px; color: white; font-size: 1.2em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌀 FractalChain Explorer</h1>
            <p>Blockchain powered by fractal mathematics</p>
        </div>

        <div class="stats-grid" id="stats-grid">
            <div class="loading">Loading statistics...</div>
        </div>

        <div class="blocks-section">
            <h2>Recent Blocks</h2>
            <div id="blocks-list">
                <div class="loading">Loading blocks...</div>
            </div>
        </div>

        <div id="fractal-viewer" class="fractal-viewer" style="display: none;">
            <h2>Fractal Visualization</h2>
            <div id="fractal-content"></div>
        </div>
    </div>

    <script>
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();

                const statsHtml = `
                    <div class="stat-card">
                        <h3>Chain Length</h3>
                        <div class="value">${stats.chain_length}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Block Reward</h3>
                        <div class="value">${stats.block_reward.toFixed(2)} FRC</div>
                    </div>
                    <div class="stat-card">
                        <h3>Pending TXs</h3>
                        <div class="value">${stats.pending_transactions}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Difficulty</h3>
                        <div class="value">${stats.difficulty_target.toFixed(3)}</div>
                    </div>
                `;

                document.getElementById('stats-grid').innerHTML = statsHtml;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        async function loadBlocks() {
            try {
                const response = await fetch('/api/blocks?start=0&count=10');
                const blocks = await response.json();

                const blocksHtml = blocks.reverse().map(block => `
                    <div class="block-item" onclick="viewFractal('${block.hash}')">
                        <h4>Block #${block.index}</h4>
                        <p>Hash: ${block.hash.substring(0, 16)}...</p>
                        <p>Miner: ${block.miner.substring(0, 16)}...</p>
                        <p>Transactions: ${block.transactions}</p>
                        ${block.dimension ? `<p>Dimension: ${block.dimension.toFixed(6)}</p>` : ''}
                        <p>Time: ${new Date(block.timestamp * 1000).toLocaleString()}</p>
                    </div>
                `).join('');

                document.getElementById('blocks-list').innerHTML = blocksHtml;
            } catch (error) {
                console.error('Error loading blocks:', error);
            }
        }

        async function viewFractal(blockHash) {
            const viewer = document.getElementById('fractal-viewer');
            const content = document.getElementById('fractal-content');

            viewer.style.display = 'block';
            content.innerHTML = '<div class="loading">Loading fractal...</div>';

            try {
                const response = await fetch(`/api/fractal/${blockHash}`);
                const data = await response.json();

                content.innerHTML = `
                    <img src="${data.image}" alt="Julia Set Fractal">
                    <p>Dimension: ${data.dimension.toFixed(6)}</p>
                    <p>Seed: ${data.seed.substring(0, 32)}...</p>
                `;
            } catch (error) {
                content.innerHTML = '<p style="color: red;">Error loading fractal</p>';
                console.error('Error loading fractal:', error);
            }
        }

        // Initial load
        loadStats();
        loadBlocks();

        // Auto-refresh every 30 seconds
        setInterval(() => {
            loadStats();
            loadBlocks();
        }, 30000);
    </script>
</body>
</html>
        """

    def start(self) -> None:
        """Start the block explorer."""
        print(f"Starting block explorer on http://{self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)


# For testing
if __name__ == "__main__":
    from ..core.blockchain import Blockchain

    blockchain = Blockchain(":memory:")
    explorer = BlockExplorer(blockchain)
    explorer.start()
