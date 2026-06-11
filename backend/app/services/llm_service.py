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
import logging
from typing import Dict, List, Any, Optional, Type
from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError
from app.schemas.llm import BaseResponseModel

logger = logging.getLogger(__name__)

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
                    
        # Lock global para serializar completamente todas as solicitações LLM
        self._global_lock = asyncio.Lock()
        
        print(f"=== LLMService: Inicializado com Provedor [{self.provider}] e Modelo [{self.primary_model}] ===")

    async def analyze_code(self, prompt: str, **kwargs) -> "LLMResponse":
        """Send prompt to LLM - legacy name for compatibility"""
        return await self.send_prompt(prompt, **kwargs)

    async def send_prompt(self, prompt: str, **kwargs) -> "LLMResponse":
        """Send prompt directly to LLM API with fallback logic and global serialization"""

        # BLOQUEO GLOBAL
        async with self._global_lock:
            return await self._execute_llm_request(prompt, **kwargs)

    async def _execute_llm_request(self, prompt: str, **kwargs) -> "LLMResponse":
        """Execute the actual LLM request with fallback logic"""
        
        max_output_tokens = kwargs.get("max_tokens", 32000)
        temperature = kwargs.get("temperature", 0.7)
        response_model = kwargs.get("response_model")

        if self.provider == "openrouter":
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://verificai.com",
                "X-Title": "VerificAI"
            }
            payload = {
                "model": self.primary_model,
                "messages": [{"role": "user", "content": self._build_structured_prompt(prompt, response_model)}],
                "max_tokens": max_output_tokens,
                "temperature": temperature,
                "response_format": response_model.get_response_schema(),
                "structured_outputs": True
            }
        else:
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": max_output_tokens,
                    "temperature": temperature,
                    **({
                        "_responseJsonSchema": response_model.get_response_schema(),
                        "responseMimeType": "application/json"
                    } if response_model else {})
                },
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
            return self._process_successful_response(primary_result["result"], primary_result["model"], response_model)
        
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

    def _process_successful_response(self, result: Dict, model: str, response_model: Optional[Type[BaseModel]] = None) -> "LLMResponse":
        response_text = ""
        if "choices" in result and len(result["choices"]) > 0:
            response_text = result["choices"][0]["message"].get("content", "")
        elif "candidates" in result and len(result["candidates"]) > 0:
            response_text = result["candidates"][0]["content"]["parts"][0].get("text", "")

        structured_content = self._parse_structured_content(response_text, response_model)

        return LLMResponse(
            content=response_text,
            model=model,
            usage=result.get("usage", result.get("usageMetadata", {})),
            structured_content=structured_content,
        )

    def _build_structured_prompt(self, prompt: str, response_model: Optional[Type[BaseModel]]) -> str:
        """Append a JSON schema hint when structured output is requested."""
        if response_model is None:
            return prompt

        schema_builder = getattr(response_model, "model_json_schema", None) or getattr(response_model, "schema", None)
        schema_text = json.dumps(schema_builder(), ensure_ascii=False, indent=2)
        return (
            f"{prompt}\n\n"
            "Return only valid JSON that matches the following schema exactly. "
            "Do not use markdown fences or add extra commentary.\n"
            f"JSON schema:\n{schema_text}"
        )

    def _parse_structured_content(self, content: str, response_model: Optional[Type[BaseModel]]) -> Dict[str, Any]:
        """Parse structured JSON content when available."""
        if response_model is None:
            return {}

        raw_content = content.strip()
        if raw_content.startswith("```"):
            raw_content = raw_content.strip("`")
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()

        try:
            parsed = json.loads(raw_content)
            validator = getattr(response_model, "model_validate", None)
            if validator is not None:
                validated = validator(parsed)
                dumper = getattr(validated, "model_dump", None) or getattr(validated, "dict", None)
                return dumper()

            validated = response_model.parse_obj(parsed)
            return validated.dict()
        except (json.JSONDecodeError, ValidationError) as exc:
            print(f"Error parsing structured LLM response: {exc}")
            return {}


class LLMResponse:
    """Compatibility wrapper for LLM responses."""

    def __init__(self, content: str, tokens_used: int = 0, model: str = "", usage: Dict[str, Any] = None, structured_content: Optional[Dict[str, Any]] = None):
        self.content = content
        self.tokens_used = tokens_used
        self.model = model
        self.usage = usage or {}
        self.structured_content = structured_content or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "text": self.content,
            "response": self.content,
            "model": self.model,
            "usage": self.usage,
            "structured_content": self.structured_content,
            "tokens_used": self.tokens_used,
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def keys(self):
        return self.to_dict().keys()

    def items(self):
        return self.to_dict().items()

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        return key in self.to_dict()

    def __len__(self) -> int:
        return len(self.content)

# Export instance for shared use
llm_service = LLMService()