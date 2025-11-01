"""
Groq LLM Service for fast inference

Uses Groq API with OpenAI-compatible interface
"""

import os
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class GroqLLMService:
    """Groq LLM service using OpenAI client"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq LLM service
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        # Initialize OpenAI client with Groq base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Default model - Using current Groq models (as of Nov 2024)
        # Options: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768
        self.default_model = "llama-3.3-70b-versatile"  # Latest Llama model
        
        logger.info(f"Groq LLM service initialized with model: {self.default_model}")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        model: Optional[str] = None
    ) -> str:
        """
        Generate text using Groq LLM
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            model: Model to use (defaults to default_model)
            
        Returns:
            Generated text
        """
        try:
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            generated_text = response.choices[0].message.content
            
            logger.debug(f"Generated {len(generated_text)} characters")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise
    
    def generate_sync(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        model: Optional[str] = None
    ) -> str:
        """
        Synchronous version of generate (for non-async contexts)
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            model: Model to use (defaults to default_model)
            
        Returns:
            Generated text
        """
        try:
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            generated_text = response.choices[0].message.content
            
            logger.debug(f"Generated {len(generated_text)} characters")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise


# Convenience function for quick usage
def get_groq_service(api_key: Optional[str] = None) -> GroqLLMService:
    """
    Get Groq LLM service instance
    
    Args:
        api_key: Optional API key (uses env var if not provided)
        
    Returns:
        GroqLLMService instance
    """
    return GroqLLMService(api_key=api_key)
