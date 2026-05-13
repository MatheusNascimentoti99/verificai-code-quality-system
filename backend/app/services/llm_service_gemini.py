"""
LLM service for VerificAI Backend - Google Gemini API integration
"""

import os
import json
import re
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import HTTPException, status

class GeminiLLMService:
    """Service for direct LLM API integration using Google Gemini with fallback"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

    async def _send_to_model(self, model_name: str, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Send request to a specific Gemini model"""
        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "candidateCount": 1,
                "responseMimeType": "text/plain"
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
        }

        url = f"{self.base_url}/models/{model_name}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutos
            response = await client.post(
                url,
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                return {"error": True, "status_code": response.status_code, "text": response.text}

            result = response.json()

            # Extract the text from Gemini response
            response_text = ""
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        response_text = parts[0]["text"]

            # Extract usage information if available
            usage_info = {}
            if "usageMetadata" in result:
                usage_metadata = result["usageMetadata"]
                usage_info = {
                    "promptTokens": usage_metadata.get("promptTokenCount", 0),
                    "candidatesTokens": usage_metadata.get("candidatesTokenCount", 0),
                    "totalTokens": usage_metadata.get("totalTokenCount", 0)
                }

            return {
                "success": True,
                "response": response_text,
                "model": model_name,
                "usage": usage_info,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def send_prompt(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Send prompt directly to Gemini API with fallback logic"""
        # Default parameters
        max_tokens = kwargs.get("max_tokens", 4000)
        temperature = kwargs.get("temperature", 0.7)

        # List of models to try in order of preference (baseado nos modelos realmente disponíveis)
        # Usar Gemini Pro primeiro, depois Flash como fallback
        models_to_try = [
            "gemini-2.5-pro",                      # Latest Pro model (prioridade)
            "gemini-2.5-pro-preview-03-25",       # Pro Preview
            "gemini-2.5-pro-preview-06-05",       # Pro Preview
            "gemini-2.0-pro-exp",                 # Pro Experimental
            "gemini-2.5-flash",                    # Flash como fallback
            "gemini-2.0-flash",                    # Stable Flash 2.0
            "gemini-flash-latest",                 # Latest Flash (alias)
            "gemini-2.0-flash-lite",               # Flash Lite version
            "gemini-2.5-flash-preview-05-20",      # Preview Flash
            "gemini-2.5-flash-lite-preview-06-17", # Flash Lite Preview
            "gemini-2.0-flash-001",                # Flash 001
            "gemini-1.5-flash",                    # Try to find correct name
            "gemini-1.5-pro"                       # Try to find correct name
        ]

        last_error = None

        for model_name in models_to_try:
            try:
                print(f"Tentando modelo: {model_name}")
                result = await self._send_to_model(model_name, prompt, max_tokens, temperature)

                if result.get("error"):
                    error_text = result.get("text", f"HTTP {result.get('status_code')}")
                    last_error = f"Gemini API ({model_name}) error: {error_text}"
                    print(f"Falha com {model_name}: {error_text}")
                    continue

                response_text = result.get("response", "")

                print(f"=== GEMINI API SUCCESS ({model_name}) ===")
                print(f"Response text length: {len(response_text)}")
                print(f"Response preview: {response_text[:200]}...")
                print(f"Usage: {result.get('usage', {})}")
                print(f"=== END GEMINI API RESPONSE ===")

                if not response_text:
                    print(f"WARNING: No response text from {model_name}")
                    continue

                return {
                    "success": True,
                    "response": response_text,
                    "model": model_name,
                    "usage": result.get("usage", {}),
                    "timestamp": result.get("timestamp", datetime.utcnow().isoformat())
                }

            except httpx.TimeoutException:
                last_error = f"Timeout com {model_name}"
                print(f"Timeout: {last_error}")
                continue
            except Exception as e:
                last_error = f"Exception com {model_name}: {str(e)}"
                print(f"Exception: {last_error}")
                continue

        # If all models failed
        error_message = f"Todos os modelos Gemini falharam. Último erro: {last_error}"
        print(f"ERROR FINAL: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Gemini API unavailable: {error_message}"
        )

    async def send_prompt_with_end_detection(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Send prompt to Gemini with end marker detection (#FIM)"""

        # Add instruction to include end marker (only if not already present)
        if "#FIM" not in prompt:
            enhanced_prompt = prompt + "\n\nIMPORTANTE: Ao finalizar sua resposta, inclua exatamente '#FIM' para indicar que a análise está completa."
        else:
            enhanced_prompt = prompt

        # Use the regular send_prompt method
        result = await self.send_prompt(enhanced_prompt, **kwargs)

        # Check for end marker
        response_text = result.get("response", "")

        if "#FIM" not in response_text:
            print("WARNING: End marker #FIM not found in Gemini response")
            result["end_marker_detected"] = False
        else:
            # Remove the end marker from the response
            response_text = response_text.replace("#FIM", "").strip()
            result["response"] = response_text
            result["end_marker_detected"] = True
            print("SUCCESS: End marker #FIM detected and removed from Gemini response")

        return result

    def extract_markdown_content(self, response: str) -> Dict[str, str]:
        """Extract content from markdown code blocks in Gemini response"""
        print(f"=== GEMINI EXTRACT_MARKDOWN_CONTENT CALLED ===")
        print(f"Response type: {type(response)}")
        print(f"Response length: {len(response)}")
        print(f"Response first 200 chars: {response[:200]}")
        print(f"=== END GEMINI EXTRACT_MARKDOWN_CONTENT CALL ===")

        import logging
        logger = logging.getLogger(__name__)

        # Debug: Log the raw response
        logger.info(f"=== DEBUG GEMINI RAW RESPONSE ===")
        logger.info(f"Response length: {len(response)}")
        logger.info(f"Response preview: {response[:800]}")
        logger.info(f"=== END GEMINI RAW RESPONSE ===")

        print(f"=== DEBUG GEMINI RAW RESPONSE ===")
        print(f"Response length: {len(response)}")
        print(f"Response preview: {response[:800]}")
        print(f"=== END GEMINI RAW RESPONSE ===")

        # Pattern to match markdown code blocks
        pattern = r'```(?:markdown|md)?\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)

        # Use the content from code blocks if found, otherwise use entire response
        content = matches[0] if matches else response

        print(f"=== DEBUG GEMINI EXTRACTED CONTENT ===")
        print(f"Content from code blocks: {bool(matches)}")
        print(f"Content length: {len(content)}")
        print(f"Content preview: {content[:800]}")
        print(f"=== END GEMINI EXTRACTED CONTENT ===")

        # Extract individual criteria from the content
        criteria_results = {}

        # Check if this is a single criterion response (simpler pattern first)
        single_criterion_pattern = r'##\s*Crit[ée]rio\s*(\d+(?:\.\d+)*)\s*[:\-]?\s*(.+?)\n(.*?)(?=\n##\s*(?:Resultado|Recomendações)\s*(?:Geral|)|\Z|$)'
        single_matches = re.findall(single_criterion_pattern, content, re.DOTALL)

        print(f"=== DEBUG GEMINI SINGLE CRITERION CHECK ===")
        print(f"Single criterion matches: {len(single_matches)}")
        print(f"=== END GEMINI SINGLE CRITERION CHECK ===")

        if single_matches and len(single_matches) == 1:
            # This appears to be a single criterion response
            criteria_num, criteria_name, criteria_content = single_matches[0]
            print(f"Gemini Processing single criterion: num={criteria_num}, name={criteria_name[:50]}...")
            criteria_results[f"criteria_{criteria_num}"] = {
                "name": criteria_name.strip(),
                "content": criteria_content.strip()
            }
        else:
            # Look for multiple criteria sections (original logic)
            criteria_pattern = r'##\s*Crit[ée]rio\s*(\d+(?:\.\d+)*)\s*[:\-]?\s*(.+?)\n(.*?)(?=\n##\s*Crit[ée]rio\s*\d+|\n##\s*(?:Resultado|Recomendações)\s*(?:Geral|)|$)'
            criteria_matches = re.findall(criteria_pattern, content, re.DOTALL)

            print(f"=== DEBUG GEMINI CRITERIA EXTRACTION ===")
            print(f"Criteria pattern: {criteria_pattern}")
            print(f"Criteria matches found: {len(criteria_matches)}")
            print(f"Criteria matches: {criteria_matches}")
            print(f"=== END GEMINI CRITERIA EXTRACTION ===")

            # Also try a more flexible pattern
            if not criteria_matches:
                flexible_pattern = r'##\s*Crit[ée]rio\s*(\d+(?:\.\d+)*)\s*[:\-]?\s*(.+?)\n(.*?)(?=\n##\s*Crit[ée]rio\s*\d+|\n##\s*(?:Resultado|Recomendações)\s*(?:Geral|)|\Z|$)'
                flexible_matches = re.findall(flexible_pattern, content, re.DOTALL)
                print(f"Gemini Flexible pattern matches: {flexible_matches}")
                criteria_matches = flexible_matches

            for i, match in enumerate(criteria_matches):
                # Handle different match lengths (3, 4, or 5 groups due to regex capturing)
                if len(match) >= 3:
                    criteria_num, criteria_name, criteria_content = match[0], match[1], match[2]
                else:
                    continue  # Skip invalid matches
                print(f"Gemini Processing criteria {i+1}: num={criteria_num}, name={criteria_name[:50]}...")
                criteria_results[f"criteria_{criteria_num}"] = {
                    "name": criteria_name.strip(),
                    "content": criteria_content.strip()
                }

        print(f"Gemini Final criteria_results: {criteria_results}")

        return {
            "criteria_results": criteria_results,
            "raw_response": response.strip()
        }

# Global instance for Gemini
gemini_llm_service = GeminiLLMService()