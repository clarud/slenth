"""
LLM Service - Unified interface for OpenAI and Anthropic models.

Provides methods for:
- Chat completions
- Streaming responses
- Token counting
- Error handling and retries
- Cost tracking
"""

import logging
from enum import Enum
from typing import Any, Dict, Generator, List, Optional

import anthropic
import openai
import tiktoken
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


class LLMService:
    """Service for interacting with LLM providers."""

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize LLM service.

        Args:
            provider: LLM provider to use (openai or anthropic). If None, uses config default.
        """
        self.provider = LLMProvider(provider or getattr(settings, "llm_provider", "openai"))
        self.model = getattr(settings, "llm_model", None) or (
            settings.openai_model if self.provider == LLMProvider.OPENAI else settings.anthropic_model
        )

        if self.provider == LLMProvider.OPENAI:
            # Native OpenAI
            self.client = openai.OpenAI(api_key=getattr(settings, "openai_api_key", None))
            try:
                self.encoding = tiktoken.encoding_for_model(self.model)
            except Exception:
                self.encoding = None
        elif self.provider == LLMProvider.ANTHROPIC:
            # Native Anthropic
            self.client = anthropic.Anthropic(api_key=getattr(settings, "anthropic_api_key", None))
            self.encoding = None  # Anthropic uses different tokenization
        elif self.provider == LLMProvider.GROQ:
            # Groq via OpenAI-compatible endpoint
            self.client = openai.OpenAI(
                api_key=getattr(settings, "groq_api_key", None),
                base_url="https://api.groq.com/openai/v1",
            )
            try:
                self.encoding = tiktoken.encoding_for_model(self.model)
            except Exception:
                self.encoding = None
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    @staticmethod
    def _messages_to_input(messages: List[Dict[str, str]]) -> str:
        """Flatten chat messages to a single prompt string for Responses API.
        Prefers the latest user message; falls back to simple role: content join.
        """
        if not messages:
            return ""
        # Try latest user content
        for msg in reversed(messages):
            if msg.get("role") == "user" and msg.get("content"):
                return str(msg["content"])  # type: ignore
        # Fallback: join all
        parts = []
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            parts.append(f"{role}: {content}")
        return "\n".join(parts)

        self.total_input_tokens = 0
        self.total_output_tokens = 0

        logger.info(f"Initialized LLMService with provider: {self.provider}, model: {self.model}")

    @retry(
        retry=retry_if_exception_type(
            (openai.RateLimitError, openai.APITimeoutError, anthropic.RateLimitError)
        ),
        wait=wait_exponential(multiplier=1, min=4, max=120),
        stop=stop_after_attempt(5),
    )
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response
            response_format: Optional format specification (e.g., {"type": "json_object"})

        Returns:
            Generated text response
        """
        try:
            if self.provider == LLMProvider.GROQ:
                # Prefer Responses API when using Groq (per provider docs)
                input_text = self._messages_to_input(messages)
                resp = self.client.responses.create(
                    model=self.model,
                    input=input_text,
                )
                # usage fields may differ; guard counters
                try:
                    self.total_input_tokens += getattr(resp, "usage", {}).get("input_tokens", 0)
                    self.total_output_tokens += getattr(resp, "usage", {}).get("output_tokens", 0)
                except Exception:
                    pass
                return getattr(resp, "output_text", "")

            if self.provider == LLMProvider.OPENAI:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                if response_format:
                    kwargs["response_format"] = response_format
                response = self.client.chat.completions.create(**kwargs)
                try:
                    self.total_input_tokens += response.usage.prompt_tokens
                    self.total_output_tokens += response.usage.completion_tokens
                except Exception:
                    pass
                return response.choices[0].message.content

            elif self.provider == LLMProvider.ANTHROPIC:
                # Convert messages to Anthropic format
                system_message = None
                anthropic_messages = []

                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        anthropic_messages.append(
                            {"role": msg["role"], "content": msg["content"]}
                        )

                kwargs = {
                    "model": self.model,
                    "messages": anthropic_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens or 4096,
                }
                if system_message:
                    kwargs["system"] = system_message

                response = self.client.messages.create(**kwargs)

                self.total_input_tokens += response.usage.input_tokens
                self.total_output_tokens += response.usage.output_tokens

                content = response.content[0].text
                logger.debug(
                    f"Anthropic completion: {response.usage.input_tokens} in, "
                    f"{response.usage.output_tokens} out"
                )
                return content

        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise

    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """
        Generate streaming chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Yields:
            Text chunks as they arrive
        """
        try:
            if self.provider == LLMProvider.GROQ:
                # Responses API has no true streaming; return one-shot
                yield self.chat_completion(messages, temperature=temperature, max_tokens=max_tokens)
                return

            if self.provider == LLMProvider.OPENAI:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens

                stream = self.client.chat.completions.create(**kwargs)

                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            elif self.provider == LLMProvider.ANTHROPIC:
                # Convert messages
                system_message = None
                anthropic_messages = []

                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        anthropic_messages.append(
                            {"role": msg["role"], "content": msg["content"]}
                        )

                kwargs = {
                    "model": self.model,
                    "messages": anthropic_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens or 4096,
                    "stream": True,
                }
                if system_message:
                    kwargs["system"] = system_message

                with self.client.messages.stream(**kwargs) as stream:
                    for text in stream.text_stream:
                        yield text

        except Exception as e:
            logger.error(f"Error in streaming completion: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Input text

        Returns:
            Token count
        """
        if self.provider == LLMProvider.OPENAI and self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Rough estimate for Anthropic: ~4 chars per token
            return len(text) // 4

    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count tokens in message list.

        Args:
            messages: List of message dicts

        Returns:
            Total token count
        """
        total = 0
        for message in messages:
            total += self.count_tokens(message.get("content", ""))
            total += 4  # Overhead per message
        return total + 2  # Base overhead

    def get_token_stats(self) -> Dict[str, int]:
        """
        Get token usage statistics.

        Returns:
            Dict with input and output token counts
        """
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
        }

    def estimate_cost(self) -> float:
        """
        Estimate total cost based on token usage.

        Returns:
            Estimated cost in USD
        """
        if self.provider == LLMProvider.OPENAI:
            if "gpt-4" in self.model:
                # GPT-4 Turbo pricing
                input_cost = (self.total_input_tokens / 1_000_000) * 10.0
                output_cost = (self.total_output_tokens / 1_000_000) * 30.0
            else:
                # GPT-3.5 Turbo pricing
                input_cost = (self.total_input_tokens / 1_000_000) * 0.5
                output_cost = (self.total_output_tokens / 1_000_000) * 1.5
            return input_cost + output_cost

        elif self.provider == LLMProvider.ANTHROPIC:
            # Claude 3 Opus pricing
            if "opus" in self.model:
                input_cost = (self.total_input_tokens / 1_000_000) * 15.0
                output_cost = (self.total_output_tokens / 1_000_000) * 75.0
            # Claude 3 Sonnet pricing
            else:
                input_cost = (self.total_input_tokens / 1_000_000) * 3.0
                output_cost = (self.total_output_tokens / 1_000_000) * 15.0
            return input_cost + output_cost

        return 0.0

    def reset_stats(self) -> None:
        """Reset token counters."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        logger.info("Reset LLM stats")
