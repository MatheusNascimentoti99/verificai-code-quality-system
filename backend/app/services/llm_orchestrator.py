"""
LLM orchestration: save prompts/responses, call LLM and extract structured results.
"""
import json
import time
from datetime import datetime
from typing import Any, List

from app.schemas.llm import StructuredAnalysisOutput
from app.models.prompt import GeneralCriteria
from app.services.llm_service import LLMService
from app.providers.storage import StorageProvider

class LLMOrchestrator:
    def __init__(self, llm_service: LLMService, storage_provider: StorageProvider):
        self.llm_service = llm_service
        self.storage_provider = storage_provider

    async def _save_latest_prompt(self, final_prompt: str, request_data: Any, current_user: Any, total_files_processed: int) -> None:
        try:
            content = '\n'.join([f"Último prompt para análise geral - {datetime.now().isoformat()}",
                            f"Usuário: {current_user.username} (ID: {current_user.id})",
                            f"Análise: {getattr(request_data, 'analysis_name', 'N/A')}",
                            f"Arquivos processados: {total_files_processed}",
                            "\nConteúdo do prompt:\n",
                            final_prompt])
            filename = f"latest_general_analysis_prompt_{current_user.id}.txt"
            if self.storage_provider:
                await self.storage_provider.upload_bytes(
                    user_id=current_user.id,
                    file_id=f"general_analysis_{int(time.time())}",
                    original_name=filename,
                    relative_path=None,
                    content=content.encode('utf-8'),
                    content_type="text/plain",
                )
        except Exception as save_error:
            print(f"DEBUG: Erro ao salvar prompt em arquivo: {save_error}")

    async def _save_latest_response(self, llm_response_content: str, current_user: Any) -> None:
        try:
            await self.storage_provider.upload_bytes(
                user_id=current_user.id,
                file_id=f"general_analysis_response_{int(time.time())}",
                original_name=f"latest_general_analysis_response_{int(time.time())}.txt",
                relative_path=None,
                content=llm_response_content.encode('utf-8'),
                content_type="text/plain",
            )
        except Exception as save_error:
            print(f"DEBUG: Erro ao salvar resposta em arquivo: {save_error}")

    def _extract_criteria_results(
        self,
        llm_response_content: str,
        selected_criteria: List[GeneralCriteria],
        criteria_ids: List[str],
    ) -> dict:
        # Reuse the extraction logic from the previous implementation
        # Remove ``` json and ``` if present    
        if llm_response_content.startswith("```"):
            llm_response_content = llm_response_content[len("```json"):].strip()
        if llm_response_content.endswith("```"):
            llm_response_content = llm_response_content[:-len("```")].strip()
        structured_response = json.loads(llm_response_content)
        
        
        if structured_response.get("criteria_results"):
            criteria_results = {}
            for item in structured_response.get("criteria_results", []):
                if not isinstance(item, dict):
                    continue
                criterion_id = item.get("id")
                if criterion_id is None:
                    continue
                criterion = next((c for c in selected_criteria if c.id == criterion_id), None)
                criteria_results[f"criteria_{criterion_id}"] = {
                    "name": criterion.text if criterion else f"Critério {criterion_id}",
                    "content": (
                        f"**Status:** {item.get('status', 'Análise requerida')}\n"
                        f"**Confiança:** {item.get('confidence', 0.0):.2f}\n\n"
                        f"### Análise:\n{item.get('assessment', '')}\n\n"
                        f"### Evidências:\n" + "\n".join(f"- {evidence}" for evidence in item.get('evidence', [])) +
                        ("\n\n### Recomendações:\n" + "\n".join(f"- {recommendation}" for recommendation in item.get('recommendations', [])) if item.get('recommendations') else "")
                    ).strip()
                }
            
            return {
                "criteria_results": criteria_results,
                "raw_response": llm_response_content.strip(),
                "structured_response": structured_response,
            }
        raise ValueError("Structured response does not contain 'criteria_results' or is not in expected format")
        

    async def analyze(
        self,
        final_prompt: str,
        request_data: Any,
        current_user: Any,
        selected_criteria: List[GeneralCriteria],
        criteria_ids: List[str],
        total_files_processed: int,
        modified_prompt: str,
    ) -> tuple[dict, dict]:
        """Send prompt to LLM, persist prompt/response and extract results."""
        if not self.llm_service:
            raise RuntimeError("LLM service dependency not provided")

        await self._save_latest_prompt(final_prompt, request_data, current_user, total_files_processed)

        forced_max_tokens = 32000

        try:
            llm_response = await self.llm_service.send_prompt(
                final_prompt,
                temperature=request_data.temperature,
                max_tokens=forced_max_tokens,
                response_model=StructuredAnalysisOutput,
            )
            self._save_latest_response(llm_response.get("response", llm_response.get("text", "")), current_user)
        except Exception as llm_error:
            await self._save_latest_response(f"Error during LLM call: {str(llm_error)}", current_user)
            import traceback
            traceback.print_exc()
            raise

        llm_response_content = llm_response.get("response", llm_response.get("text", ""))

        extracted_content = self._extract_criteria_results(
            llm_response_content=llm_response_content,
            selected_criteria=selected_criteria,
            criteria_ids=criteria_ids,
        )

        return extracted_content, llm_response
