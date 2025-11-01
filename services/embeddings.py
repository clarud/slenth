"""
Embedding Service - Generate embeddings using OpenAI API.

Provides methods for:
- Single text embedding
- Batch embedding generation
- Rate limiting and retry logic
- Cost tracking
"""

import logging
import time
from typing import List, Optional

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.embedding_dim = settings.embedding_dim
        self.batch_size = settings.embedding_batch_size
        self.total_tokens = 0
        logger.info(f"Initialized EmbeddingService with model: {self.model}")

    @retry(
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
    )
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding")
                return [0.0] * self.embedding_dim

            response = self.client.embeddings.create(input=text, model=self.model)

            embedding = response.data[0].embedding
            self.total_tokens += response.usage.total_tokens

            logger.debug(
                f"Generated embedding for text of length {len(text)} ({response.usage.total_tokens} tokens)"
            )
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
    )
    def embed_batch(
        self, texts: List[str], show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of input texts
            show_progress: Whether to log progress

        Returns:
            List of embedding vectors
        """
        if not texts:
            logger.warning("Empty text list provided for batch embedding")
            return []

        embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1

            # Filter out empty texts
            valid_batch = [t if t and t.strip() else " " for t in batch]

            try:
                response = self.client.embeddings.create(
                    input=valid_batch, model=self.model
                )

                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                self.total_tokens += response.usage.total_tokens

                if show_progress:
                    logger.info(
                        f"Processed batch {batch_num}/{total_batches} "
                        f"({len(batch)} texts, {response.usage.total_tokens} tokens)"
                    )

            except Exception as e:
                logger.error(f"Error in batch {batch_num}: {e}")
                # Return zero vectors for failed batch
                embeddings.extend([[0.0] * self.embedding_dim] * len(batch))

            # Rate limiting: small delay between batches
            if i + self.batch_size < len(texts):
                time.sleep(0.1)

        logger.info(
            f"Generated {len(embeddings)} embeddings using {self.total_tokens} total tokens"
        )
        return embeddings

    def get_total_tokens(self) -> int:
        """
        Get total tokens used across all embedding calls.

        Returns:
            Total token count
        """
        return self.total_tokens

    def estimate_cost(self) -> float:
        """
        Estimate total cost based on tokens used.

        Returns:
            Estimated cost in USD
        """
        # text-embedding-3-large pricing: $0.00013 per 1K tokens
        cost_per_1k = 0.00013
        return (self.total_tokens / 1000) * cost_per_1k

    def reset_stats(self) -> None:
        """Reset token counter."""
        self.total_tokens = 0
        logger.info("Reset embedding stats")
