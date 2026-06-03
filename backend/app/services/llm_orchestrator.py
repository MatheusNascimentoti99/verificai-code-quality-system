"""
LLM orchestration: save prompts/responses, call LLM and extract structured results.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schemas.llm import StructuredAnalysisOutput
from app.models.prompt import GeneralCriteria
from app.services.llm_service import LLMService


class LLMOrchestrator:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service

    def _save_latest_prompt(self, final_prompt: str, request_data: Any, current_user: Any, total_files_processed: int) -> None:
        try:
            prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
            prompts_dir.mkdir(exist_ok=True)
            latest_prompt_path = prompts_dir / "latest_prompt.txt"

            with open(latest_prompt_path, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write(f"LTIMO PROMPT ENVIADO PARA LLM - {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"TAMANHO TOTAL: {len(final_prompt)} caracteres\n")
                f.write(f"ARQUIVOS PROCESSADOS: {total_files_processed}\n")
                f.write(f"CRITRIOS: {len(request_data.criteria_ids)}\n")
                f.write(f"USURIO: {current_user.username} (ID: {current_user.id})\n\n")
                f.write("=" * 80 + "\n")
                f.write("CONTEDO COMPLETO DO PROMPT:\n")
                f.write("=" * 80 + "\n\n")
                f.write(final_prompt)
                f.write("\n\n" + "=" * 80 + "\n")
                f.write("FIM DO PROMPT\n")
                f.write("=" * 80 + "\n")
        except Exception as save_error:
            print(f"DEBUG: Erro ao salvar prompt em arquivo: {save_error}")

    def _save_latest_response(self, llm_response_content: str) -> None:
        try:
            prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
            prompts_dir.mkdir(exist_ok=True)
            latest_response_path = prompts_dir / "latest_response.txt"

            with open(latest_response_path, "w", encoding="utf-8") as f:
                f.write(llm_response_content)
        except Exception as save_error:
            print(f"DEBUG: Erro ao salvar resposta em arquivo: {save_error}")

    def _extract_criteria_results(
        self,
        llm_response_content: str,
        structured_response: dict,
        selected_criteria: List[GeneralCriteria],
        criteria_ids: List[str],
    ) -> dict:
        try:
            # Reuse the extraction logic from the previous implementation
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

            if not llm_response_content:
                return {"criteria_results": {}, "raw_response": "", "structured_response": structured_response}

            import re

            criteria_results = {}

            if "#FIM_ANALISE_CRITERIO#" in llm_response_content:
                blocks = re.split(r'#FIM_ANALISE_CRITERIO#', llm_response_content)
                for block in blocks:
                    match = re.search(r'##\s*Crit[ée]rio\s*(\d+(?:\.\d+)*)\s*[:\-]?\s*(.+?)\n(.*?)$', block, re.DOTALL)
                    if match:
                        crit_id = match.group(1)
                        crit_name = match.group(2).strip()
                        crit_content = match.group(3).strip()

                        criteria_results[f"criteria_{crit_id}"] = {
                            "name": crit_name,
                            "content": crit_content,
                        }

            if not criteria_results or len(criteria_results) < len(criteria_ids):
                criteria_pattern = r'##\s*Crit[ée]rio\s*(\d+(?:\.\d+)*)\s*[:\-]?\s*(.+?)\n(.*?)(?=\s*##\s*Crit[ée]rio\s*\d+|\s*##\s*(?:Resultado|Recomendações)\s*(?:Geral|)|#FIM_ANALISE_CRITERIO#|#FIM#|$)'
                matches = re.findall(criteria_pattern, llm_response_content, re.DOTALL)

                for match in matches:
                    crit_id = match[0]
                    if f"criteria_{crit_id}" not in criteria_results:
                        criteria_results[f"criteria_{crit_id}"] = {
                            "name": match[1].strip(),
                            "content": match[2].strip(),
                        }

            return {
                "criteria_results": criteria_results,
                "raw_response": llm_response_content.strip(),
                "structured_response": structured_response,
            }
        except Exception as extract_error:
            print(f"ERROR: Extraction failed: {extract_error}")
            return {
                "criteria_results": {},
                "raw_response": llm_response_content,
                "structured_response": structured_response,
            }

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

        self._save_latest_prompt(final_prompt, request_data, current_user, total_files_processed)

        forced_max_tokens = 32000

        try:
            llm_response = await self.llm_service.send_prompt(
                final_prompt,
                temperature=request_data.temperature,
                max_tokens=forced_max_tokens,
                response_model=StructuredAnalysisOutput,
            )
        except Exception as llm_error:
            print(f"ERROR: LLM service failed: {llm_error}")
            import traceback

            traceback.print_exc()
            raise

        llm_response_content = llm_response.get("response", llm_response.get("text", ""))
        structured_response = getattr(llm_response, "structured_content", {}) or {}
        self._save_latest_response(llm_response_content)

        extracted_content = self._extract_criteria_results(
            llm_response_content=llm_response_content,
            structured_response=structured_response,
            selected_criteria=selected_criteria,
            criteria_ids=criteria_ids,
        )

        return extracted_content, llm_response
