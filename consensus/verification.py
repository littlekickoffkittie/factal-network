"""
Block verification system for FractalChain.
Includes fractal dimension verification and optional DeepSeek API audit.
"""

import logging
import requests
import json
from typing import Optional, Tuple, Dict
from ..core.block import Block
from ..core.crypto import CryptoUtils
from .fractal_math import FractalProofOfWork, FractalConfig


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlockVerifier:
    """
    Verifies blocks using FractalPoW and optional AI audit.
    """

    def __init__(self, fractal_config: FractalConfig = None):
        """
        Initialize block verifier.

        Args:
            fractal_config: Fractal configuration
        """
        self.fractal_pow = FractalProofOfWork(fractal_config or FractalConfig())
        self.config = fractal_config or FractalConfig()

    def verify_block(self, block: Block, previous_block: Optional[Block] = None) -> Tuple[bool, str]:
        """
        Complete block verification.

        Args:
            block: Block to verify
            previous_block: Previous block for validation

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Step 1: Basic block structure validation
        if not block.is_valid(previous_block):
            return False, "Block structure is invalid"

        # Genesis block doesn't need PoW verification
        if block.index == 0:
            return True, "Genesis block verified"

        # Step 2: Verify fractal proof exists
        if not block.fractal_proof:
            return False, "Block missing fractal proof"

        # Step 3: Verify header hash (pre-filter)
        header_hash = block.calculate_header_hash()
        if not self.fractal_pow.verify_header_hash(header_hash, block.header_difficulty_bits):
            return False, f"Header hash does not meet difficulty requirement"

        # Step 4: Verify fractal seed generation
        expected_seed = self.fractal_pow.generate_fractal_seed(
            block.previous_hash,
            block.miner_address,
            block.fractal_proof.nonce
        )

        if expected_seed != block.fractal_proof.fractal_seed:
            return False, "Fractal seed mismatch"

        # Step 5: Verify fractal dimension
        solution_point = block.fractal_proof.get_solution_point()

        is_valid = self.fractal_pow.verify_solution(
            block.fractal_proof.fractal_seed,
            solution_point,
            block.fractal_proof.fractal_dimension,
            target_dimension=block.difficulty_target,
            epsilon=self.config.epsilon
        )

        if not is_valid:
            return False, "Fractal dimension does not match target"

        logger.info(f"Block {block.index} verified successfully")
        return True, "Block verified"

    def quick_verify(self, block: Block) -> bool:
        """
        Quick verification using only header hash.
        Used for rapid block propagation filtering.

        Args:
            block: Block to verify

        Returns:
            True if block passes quick verification
        """
        if block.index == 0:
            return True

        if not block.fractal_proof:
            return False

        header_hash = block.calculate_header_hash()
        return self.fractal_pow.verify_header_hash(header_hash, block.header_difficulty_bits)


class DeepSeekVerifier:
    """
    Optional AI-based verification using DeepSeek API.
    Provides additional fraud detection layer.
    """

    def __init__(self, api_key: Optional[str] = None, api_url: str = "https://api.deepseek.com/v1/chat/completions"):
        """
        Initialize DeepSeek verifier.

        Args:
            api_key: DeepSeek API key
            api_url: API endpoint URL
        """
        self.api_key = api_key
        self.api_url = api_url
        self.enabled = api_key is not None
        self.request_count = 0
        self.max_requests_per_hour = 100

    def generate_verification_prompt(self, block: Block) -> str:
        """
        Generate deterministic verification prompt from block data.

        Args:
            block: Block to verify

        Returns:
            Verification prompt
        """
        if not block.fractal_proof:
            return ""

        prompt = f"""Verify the following FractalChain block using mathematical analysis:

Block Index: {block.index}
Previous Hash: {block.previous_hash}
Miner Address: {block.miner_address}
Timestamp: {block.timestamp}

Fractal Proof Parameters:
- Nonce: {block.fractal_proof.nonce}
- Fractal Seed: {block.fractal_proof.fractal_seed}
- Solution Point: {block.fractal_proof.solution_point_real:.10f} + {block.fractal_proof.solution_point_imag:.10f}i
- Calculated Dimension: {block.fractal_proof.fractal_dimension:.10f}
- Target Dimension: {block.difficulty_target:.10f}
- Tolerance: 0.001
- Fractal Data Hash: {block.fractal_proof.fractal_data_hash}

Verification Tasks:
1. Confirm that the fractal seed = SHA256(previous_hash + miner_address + nonce)
2. Verify that |calculated_dimension - target_dimension| < tolerance
3. Check for any mathematical inconsistencies or fraud indicators
4. Validate that the fractal_data_hash is consistent with expected Julia set parameters

Respond with a JSON object containing:
{{
    "seed_valid": true/false,
    "dimension_valid": true/false,
    "fraud_score": 0.0-1.0,
    "fraud_indicators": [],
    "overall_valid": true/false,
    "confidence": 0.0-1.0,
    "notes": "detailed analysis"
}}
"""
        return prompt

    def verify_with_api(self, block: Block) -> Optional[Dict]:
        """
        Verify block using DeepSeek API.

        Args:
            block: Block to verify

        Returns:
            Verification result dictionary or None
        """
        if not self.enabled:
            logger.warning("DeepSeek verification disabled (no API key)")
            return None

        # Rate limiting
        if self.request_count >= self.max_requests_per_hour:
            logger.warning("DeepSeek API rate limit reached")
            return None

        try:
            prompt = self.generate_verification_prompt(block)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a mathematical verification system for blockchain consensus. Analyze the provided data and respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.0,
                "max_tokens": 1000
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            self.request_count += 1

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']

                # Parse JSON response
                verification_result = json.loads(content)
                return verification_result
            else:
                logger.error(f"DeepSeek API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"DeepSeek verification error: {e}")
            return None

    def analyze_fraud_score(self, verification_result: Dict) -> Tuple[bool, float]:
        """
        Analyze DeepSeek verification result for fraud.

        Args:
            verification_result: Result from verify_with_api

        Returns:
            Tuple of (is_suspicious, fraud_score)
        """
        fraud_score = verification_result.get('fraud_score', 0.0)
        overall_valid = verification_result.get('overall_valid', True)
        confidence = verification_result.get('confidence', 0.0)

        # Consider block suspicious if:
        # - Fraud score > 0.5
        # - Overall not valid
        # - Low confidence in validation
        is_suspicious = (
            fraud_score > 0.5 or
            not overall_valid or
            confidence < 0.7
        )

        return is_suspicious, fraud_score


class HybridVerifier:
    """
    Combines trustless fractal verification with optional AI audit.
    """

    def __init__(
        self,
        fractal_config: FractalConfig = None,
        deepseek_api_key: Optional[str] = None
    ):
        """
        Initialize hybrid verifier.

        Args:
            fractal_config: Fractal configuration
            deepseek_api_key: Optional DeepSeek API key
        """
        self.block_verifier = BlockVerifier(fractal_config)
        self.deepseek_verifier = DeepSeekVerifier(deepseek_api_key)

    def verify_block(
        self,
        block: Block,
        previous_block: Optional[Block] = None,
        use_ai_audit: bool = False
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verify block with optional AI audit.

        Args:
            block: Block to verify
            previous_block: Previous block
            use_ai_audit: Whether to use DeepSeek audit

        Returns:
            Tuple of (is_valid, message, ai_result)
        """
        # Primary verification (trustless)
        is_valid, message = self.block_verifier.verify_block(block, previous_block)

        if not is_valid:
            return False, message, None

        # Optional AI audit
        ai_result = None
        if use_ai_audit and self.deepseek_verifier.enabled:
            logger.info("Performing DeepSeek AI audit...")
            ai_result = self.deepseek_verifier.verify_with_api(block)

            if ai_result:
                is_suspicious, fraud_score = self.deepseek_verifier.analyze_fraud_score(ai_result)

                if is_suspicious:
                    logger.warning(f"Block {block.index} flagged as suspicious (fraud score: {fraud_score})")
                    message += f" | AI flagged as suspicious (fraud: {fraud_score})"

        return is_valid, message, ai_result

    def quick_verify(self, block: Block) -> bool:
        """Quick verification using header hash only."""
        return self.block_verifier.quick_verify(block)
