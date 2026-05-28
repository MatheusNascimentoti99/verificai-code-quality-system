"""
LLM service for VerificAI Backend - Direct LLM API integration with global locking
"""

import os
import json
import re
import httpx
import asyncio
import time
import datetime
from typing import Dict, List, Any, Optional
from fastapi import HTTPException, status

# Use relative import for robustness
try:
    from ..core.config import settings
except ImportError:
    from app.core.config import settings

class LLMService:
    """Service for direct LLM API integration supporting Gemini and OpenRouter (OpenAI-compatible)"""

    def __init__(self):
        # Use settings from config.py
        self.api_key = settings.OPENROUTER_API_KEY or settings.GEMINI_API_KEY
        self.provider = "openrouter" if settings.OPENROUTER_API_KEY else "gemini"
        
        # Base URLs
        if self.provider == "openrouter":
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
            self.primary_model = settings.OPENROUTER_MODEL
        else:
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
            self.primary_model = settings.MODEL if "gemini" in settings.MODEL else "gemini-1.5-flash"
            
        self.fallback_model = "gemini-1.5-pro" if self.provider == "gemini" else "anthropic/claude-3-haiku"
        
        # Lock global para serializar completamente todas as solicitações LLM
        self._global_lock = asyncio.Lock()
        
        print(f"=== LLMService: Inicializado com Provedor [{self.provider}] e Modelo [{self.primary_model}] ===")

    async def analyze_code(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Send prompt to LLM - legacy name for compatibility"""
        return await self.send_prompt(prompt, **kwargs)

    async def send_prompt(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Send prompt directly to LLM API with fallback logic and global serialization"""

        # BLOQUEO GLOBAL
        async with self._global_lock:
            try:
                return await self._execute_llm_request(prompt, **kwargs)
            except Exception as e:
                print(f"Error in LLMService: {str(e)}")
                raise

    async def _execute_llm_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Execute the actual LLM request with fallback logic"""
        
        max_output_tokens = kwargs.get("max_tokens", 32000)
        temperature = kwargs.get("temperature", 0.7)

        if self.provider == "openrouter":
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://verificai.com",
                "X-Title": "VerificAI"
            }
            payload = {
                "model": self.primary_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_output_tokens,
                "temperature": temperature
            }
        else:
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_output_tokens, "temperature": temperature},
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            }

        max_retries = 2
        base_delay = 2

        # Try primary model
        primary_result = await self._try_model(prompt, self.primary_model, headers, payload, max_retries, base_delay)

        if primary_result:
            return self._process_successful_response(primary_result["result"], primary_result["model"])
        
        # Try fallback
        fallback_model = self.fallback_model
        if self.provider == "openrouter":
            payload["model"] = fallback_model
        
        fallback_result = await self._try_model(prompt, fallback_model, headers, payload, max_retries, base_delay)

        if fallback_result:
            return self._process_successful_response(fallback_result["result"], fallback_result["model"])
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de IA indisponível. Por favor, tente novamente em instantes."
        )

    async def _try_model(self, prompt, model, headers, payload, max_retries, base_delay):
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    await asyncio.sleep(base_delay * (2 ** attempt))

                url = self.base_url
                if self.provider == "gemini":
                    url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"

                async with httpx.AsyncClient(timeout=180.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code == 200:
                        return {"result": response.json(), "model": model}
                    elif response.status_code == 429:
                        await asyncio.sleep(base_delay * 5)
                    elif response.status_code == 503:
                        pass
            except Exception as e:
                print(f"Error trying model {model}: {e}")
            
        return None

    def _process_successful_response(self, result: Dict, model: str) -> Dict[str, Any]:
        response_text = ""
        if "choices" in result and len(result["choices"]) > 0:
            response_text = result["choices"][0]["message"].get("content", "")
        elif "candidates" in result and len(result["candidates"]) > 0:
            response_text = result["candidates"][0]["content"]["parts"][0].get("text", "")

        return {
            "text": response_text,
            "model": model,
            "usage": result.get("usage", result.get("usageMetadata", {}))
        }

# Export instance for shared use
llm_service = LLMService()