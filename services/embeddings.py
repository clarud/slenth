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

from config import settings

# OpenAI client (default provider)
import openai
try:
    import groq  # type: ignore
except Exception:  # pragma: no cover
    groq = None
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.provider = getattr(settings, "embeddings_provider", "openai").lower()
        self.model = settings.embedding_model
        self.embedding_dim = settings.embedding_dimension
        self.batch_size = settings.embedding_batch_size
        if self.provider == "openai":
            self.client = openai.OpenAI(api_key=settings.openai_api_key)
        elif self.provider == "groq":
            if groq is None:
                logger.warning("groq package not installed; embeddings will return zero vectors.")
                self.client = None
            else:
                # Placeholder init; actual embeddings support depends on Groq API
                self.client = groq.Groq(api_key=getattr(settings, "groq_api_key", None))
        else:
            logger.warning(f"Unknown embeddings provider '{self.provider}', defaulting to zero vectors.")
            self.client = None
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

            if self.provider == "openai" and self.client is not None:
                response = self.client.embeddings.create(input=text, model=self.model)
                embedding = response.data[0].embedding
                self.total_tokens += getattr(response, "usage", {}).get("total_tokens", 0)
                logger.debug(
                    f"Generated embedding for text of length {len(text)}"
                )
                return embedding

            # Fallback for unsupported providers
            logger.warning(f"Embeddings provider '{self.provider}' not fully implemented; returning zeros.")
            return [0.0] * self.embedding_dim

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
                if self.provider == "openai" and self.client is not None:
                    response = self.client.embeddings.create(
                        input=valid_batch, model=self.model
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    embeddings.extend(batch_embeddings)
                    self.total_tokens += getattr(response, "usage", {}).get("total_tokens", 0)
                else:
                    # Fallback zeros for unsupported providers
                    embeddings.extend([[0.0] * self.embedding_dim] * len(batch))

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
