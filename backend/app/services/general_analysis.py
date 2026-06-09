"""
Service for general analysis workflows.
"""

import json
import os
import time
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.analysis import Analysis, AnalysisStatus
from app.models.code_entry import CodeEntry
from app.models.prompt import Prompt, PromptType, GeneralCriteria, GeneralAnalysisResult as GeneralAnalysisResultModel
from app.models.uploaded_file import UploadedFile, FileStatus
from app.models.user import User
from app.schemas.analysis import AnalysisCreate
from app.schemas.general_analysis import AnalyzeSelectedRequest
from app.services.analysis import AnalysisService
from app.services.llm_service import LLMService
from app.services.prompt import PromptService
from app.providers.storage import StorageProvider
from app.services.file_processor import FileProcessorService
from app.services.llm_orchestrator import LLMOrchestrator

class GeneralAnalysisService:
    """Encapsulates general analysis use cases."""

    def __init__(
        self,
        db: Session,
        prompt_service: Optional[PromptService] = None,
        storage_provider: Optional[StorageProvider] = None,
        llm_service: Optional[LLMService] = None,
        file_processor: Optional[FileProcessorService] = None,
        llm_orchestrator: Optional[LLMOrchestrator] = None,
    ):
        self.db = db
        self.analysis_service = AnalysisService(db)
        self.prompt_service = prompt_service
        self.storage_provider = storage_provider
        self.llm_service = llm_service
        self.file_processor = file_processor
        self.llm_orchestrator = llm_orchestrator

    def create_general_analysis(self, request_data, current_user: User) -> Analysis:
        """Create the analysis and keep prompt setup in one place."""
        general_prompt = self._ensure_general_prompt(current_user, request_data.criteria)

        analysis_data = AnalysisCreate(
            name=request_data.name,
            description=request_data.description,
            prompt_id=general_prompt.id,
            file_paths=request_data.file_paths,
            configuration={
                "llm_provider": request_data.llm_provider,
                "temperature": request_data.temperature,
                "max_tokens": request_data.max_tokens,
                "criteria": request_data.criteria,
                "analysis_type": "general",
            },
        )

        return self.analysis_service.create_analysis(
            current_user.id,
            analysis_data.model_dump(),
            current_user.is_admin,
        )

    def get_general_analysis_result(self, analysis_id: int, current_user: User):
        """Return a general analysis response shaped for the API."""
        analysis = self.analysis_service.get_analysis_by_id(analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", str(analysis_id))

        if not current_user.is_admin and analysis.user_id != current_user.id:
            raise BusinessRuleError("Access denied")

        if not analysis.result:
            raise NotFoundError("Analysis result", str(analysis_id))

        return {
            "id": str(analysis.id),
            "analysis_type": "general",
            "timestamp": analysis.created_at,
            "overall_assessment": analysis.result.summary,
            "criteria_results": self._build_criteria_results(analysis.result.get_issues()),
            "token_usage": {
                "total_tokens": analysis.result.tokens_used or 0,
                "prompt_tokens": analysis.result.tokens_used or 0,
                "completion_tokens": 0,
            },
            "processing_time": float(analysis.result.processing_time or 0),
            "status": analysis.status.value if isinstance(analysis.status, AnalysisStatus) else str(analysis.status),
        }

    def get_user_criteria(self) -> List[GeneralCriteria]:
        """Return all active shared criteria."""
        return self.db.query(GeneralCriteria).filter(
            GeneralCriteria.is_active == True  # noqa: E712
        ).order_by(GeneralCriteria.order, GeneralCriteria.created_at).all()

    def create_criterion(self, user_id: int, text: str) -> GeneralCriteria:
        """Create a new criterion for the current user."""
        max_order = self.db.query(GeneralCriteria).filter(
            GeneralCriteria.user_id == user_id
        ).order_by(GeneralCriteria.order.desc()).first()

        next_order = (max_order.order + 1) if max_order else 0

        criterion = GeneralCriteria(
            user_id=user_id,
            text=text,
            is_active=True,
            order=next_order,
        )

        self.db.add(criterion)
        self.db.commit()
        self.db.refresh(criterion)
        return criterion

    def update_criterion(self, criteria_id: str, text: str) -> GeneralCriteria:
        """Update an existing criterion."""
        actual_id = self._parse_criteria_id(criteria_id)
        criterion = self.db.query(GeneralCriteria).filter(GeneralCriteria.id == actual_id).first()
        if not criterion:
            raise NotFoundError("Criterion", str(actual_id))

        criterion.text = text
        self.db.commit()
        self.db.refresh(criterion)
        return criterion

    def delete_criterion(self, criteria_id: str) -> None:
        """Delete a criterion."""
        actual_id = self._parse_criteria_id(criteria_id)
        criterion = self.db.query(GeneralCriteria).filter(GeneralCriteria.id == actual_id).first()
        if not criterion:
            raise NotFoundError("Criterion", str(actual_id))

        self.db.delete(criterion)
        self.db.commit()

    def get_latest_code_entry(self, user_id: int) -> Optional[CodeEntry]:
        """Get the latest active code entry for a user."""
        return self.db.query(CodeEntry).filter(
            CodeEntry.user_id == user_id,
            CodeEntry.is_active == True  # noqa: E712
        ).order_by(CodeEntry.created_at.desc()).first()

    def get_general_analysis_results(self, user_id: int) -> List[GeneralAnalysisResultModel]:
        """Get all general analysis results for a user."""
        return self.db.query(GeneralAnalysisResultModel).filter(
            GeneralAnalysisResultModel.user_id == user_id
        ).order_by(GeneralAnalysisResultModel.created_at.desc()).all()

    def get_general_analysis_result_by_id(self, result_id: int, user_id: int) -> Optional[GeneralAnalysisResultModel]:
        """Get a general analysis result by ID and owner."""
        return self.db.query(GeneralAnalysisResultModel).filter(
            GeneralAnalysisResultModel.id == result_id,
            GeneralAnalysisResultModel.user_id == user_id,
        ).first()

    async def analyze_selected_criteria(self, request_data: AnalyzeSelectedRequest, current_user: User) -> dict:
        """Analyze selected criteria and store the result."""
        if not self.prompt_service or not self.file_processor or not self.llm_orchestrator:
            raise RuntimeError("GeneralAnalysisService dependencies were not provided")

        general_prompt = self._get_general_prompt(self.prompt_service)
        selected_criteria = self.prompt_service.get_selected_criteria(request_data.criteria_ids)

        if not selected_criteria:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid criteria found",
            )

        modified_prompt = self.prompt_service.insert_criteria_into_prompt(general_prompt, selected_criteria)
        all_source_code, source_info, total_files_processed = await self.file_processor.build_source_bundle(
            request_data=request_data,
            current_user=current_user,
        )

        full_source_code = source_info + all_source_code
        final_prompt = modified_prompt.replace("[INSERIR CÓDIGO AQUI]", full_source_code)

        processing_start = time.time()

        # Delegate LLM call, saving and extraction to orchestrator
        try:
            extracted_content, llm_response = await self.llm_orchestrator.analyze(
                final_prompt=final_prompt,
                request_data=request_data,
                current_user=current_user,
                selected_criteria=selected_criteria,
                criteria_ids=request_data.criteria_ids,
                total_files_processed=total_files_processed,
                modified_prompt=modified_prompt,
            )
        except Exception as llm_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro na comunicacao com o servio de LLM: {str(llm_error)}",
            )

        processing_duration = time.time() - processing_start
        processing_time_str = f"{processing_duration:.2f}s"

        db_analysis_result = self._save_general_analysis_result(
            request_data=request_data,
            current_user=current_user,
            selected_criteria=selected_criteria,
            extracted_content=extracted_content,
            llm_response=llm_response,
            modified_prompt=modified_prompt,
            processing_time_str=processing_time_str,
        )

        return {
            "success": True,
            "analysis_name": request_data.analysis_name,
            "criteria_count": len(selected_criteria),
            "timestamp": llm_response.get("timestamp", datetime.utcnow().isoformat()),
            "model_used": llm_response.get("model", "unknown-model"),
            "usage": llm_response.get("usage", {}),
            "criteria_results": extracted_content.get("criteria_results", {}),
            "raw_response": extracted_content.get("raw_response", ""),
            "modified_prompt": modified_prompt,
            "file_paths": request_data.file_paths,
            "saved_to_db": True,
            "db_result_id": db_analysis_result.id if db_analysis_result else None,
        }

    def resolve_uploaded_file_path(self, file_path: str, user_id: int) -> str:
        """Resolve an uploaded file path to the actual storage locator."""
        try:
            storage = self.storage_provider
            if storage is None:
                return file_path

            def find_most_recent_existing(files_query):
                files = files_query.order_by(UploadedFile.created_at.desc()).all()
                for uploaded_file in files:
                    file_locator = uploaded_file.storage_path
                    if str(file_locator).startswith(("http://", "https://", "minio://")):
                        return uploaded_file, file_locator
                    if storage.path_exists(file_locator):
                        return uploaded_file, file_locator
                return None, None

            files_query = self.db.query(UploadedFile).filter(
                UploadedFile.relative_path == file_path,
                UploadedFile.user_id == user_id,
                UploadedFile.status == FileStatus.COMPLETED,
            )
            uploaded_file, full_disk_path = find_most_recent_existing(files_query)

            if not uploaded_file:
                files_query = self.db.query(UploadedFile).filter(
                    UploadedFile.original_name == file_path,
                    UploadedFile.user_id == user_id,
                    UploadedFile.status == FileStatus.COMPLETED,
                )
                uploaded_file, full_disk_path = find_most_recent_existing(files_query)

            if not uploaded_file:
                filename = file_path.split('/')[-1].split('\\')[-1]
                files_query = self.db.query(UploadedFile).filter(
                    UploadedFile.original_name == filename,
                    UploadedFile.user_id == user_id,
                    UploadedFile.status == FileStatus.COMPLETED,
                )
                uploaded_file, full_disk_path = find_most_recent_existing(files_query)

            if not uploaded_file:
                files_query = self.db.query(UploadedFile).filter(
                    UploadedFile.storage_path.like(f'%{file_path}%'),
                    UploadedFile.user_id == user_id,
                    UploadedFile.status == FileStatus.COMPLETED,
                )
                uploaded_file, full_disk_path = find_most_recent_existing(files_query)

            return full_disk_path if uploaded_file and full_disk_path else file_path
        except Exception:
            return file_path

    def get_analysis_result_payload(self, result_id: int, current_user: User) -> dict:
        """Return a specific result payload."""
        result = self.get_general_analysis_result_by_id(result_id, current_user.id)
        if not result:
            raise NotFoundError("Analysis result", str(result_id))

        return {
            "success": True,
            "result": {
                "id": result.id,
                "analysis_name": result.analysis_name,
                "criteria_count": result.criteria_count,
                "timestamp": result.created_at,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "file_paths": result.get_file_paths(),
                "criteria_results": result.get_criteria_results(),
                "raw_response": result.raw_response,
                "usage": result.get_usage(),
                "modified_prompt": result.modified_prompt,
            }
        }

    def get_analysis_results_payload(self, current_user: User) -> dict:
        """Return all result payloads for the current user."""
        results = self.get_general_analysis_results(current_user.id)
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "analysis_name": result.analysis_name,
                "criteria_count": result.criteria_count,
                "timestamp": result.created_at,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "file_paths": result.get_file_paths(),
                "criteria_results": result.get_criteria_results(),
                "raw_response": result.raw_response,
                "usage": result.get_usage(),
            })

        return {
            "success": True,
            "results": formatted_results,
            "total": len(formatted_results),
        }

    def _get_general_prompt(self, prompt_service) -> str:
        """Load the general prompt template, falling back to the default prompt."""
        try:
            general_prompt = prompt_service.get_general_prompt(4)
            if "[INSERIR CÓDIGO AQUI]" not in general_prompt:
                return prompt_service._get_default_general_prompt()
            return general_prompt
        except Exception:
            return prompt_service._get_default_general_prompt()

    async def _build_source_bundle(self, request_data: AnalyzeSelectedRequest, current_user: User) -> tuple[str, str, int]:
        """Collect source code from code entries or uploaded files."""
        all_source_code = ""
        source_info = ""
        total_files_processed = 0

        is_using_files = len(request_data.file_paths) > 0

        if not is_using_files and request_data.use_code_entry:
            code_entry = self._get_code_entry(request_data.code_entry_id, current_user.id)
            if not code_entry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nenhum código encontrado na tabela de colagem. Por favor, cole um código na página de colagem primeiro.",
                )

            all_source_code = code_entry.code_content or ""
            file_size = len(all_source_code)
            source_info = (
                f"\n\n{'='*60}\n"
                f"CÓDIGO COLADO: {code_entry.title}\n"
                f"DESCRIÇÃO: {code_entry.description or 'Sem descrição'}\n"
                f"LINGUAGEM: {code_entry.language or 'Não detectada'}\n"
                f"TAMANHO: {file_size} caracteres\n"
                f"LINHAS: {code_entry.lines_count}\n"
                f"CRIADO EM: {code_entry.created_at}\n"
                f"{'='*60}\n\n"
            )
            total_files_processed = 1
            return all_source_code, source_info, total_files_processed

        if not request_data.file_paths:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file paths provided")

        for source_file_path in request_data.file_paths:
            actual_file_path = source_file_path
            try:
                actual_file_path = self.resolve_uploaded_file_path(source_file_path, current_user.id)
                file_content = await self.storage_provider.read_text(actual_file_path)
                file_size = len(file_content)
                file_extension = source_file_path.split('.')[-1] if '.' in source_file_path else 'txt'

                source_info += f"\n\n{'='*60}\n"
                source_info += f"ARQUIVO: {source_file_path}\n"
                source_info += f"TAMANHO: {file_size} caracteres\n"
                source_info += f"TIPO: {file_extension.upper()}\n"
                source_info += f"{'='*60}\n\n"
                all_source_code += file_content
                total_files_processed += 1
            except Exception as file_error:
                print(f"❌ DEBUG: Error processing file {source_file_path} (actual: {actual_file_path}): {file_error}")
                continue

        if total_files_processed == 0:
            is_cloud = "render" in os.environ.get("HOSTNAME", "").lower() or "vercel" in os.environ.get("HOSTNAME", "").lower()
            detail_msg = "Nenhum código pôde ser lido para análise. O arquivo não existe no disco."
            if is_cloud:
                detail_msg += " Devido ao ambiente cloud (Render/Vercel), arquivos locais são perdidos após o restart. Por favor, remova caminhos antigos ou use a 'Colagem de Código'."
            else:
                file_previews = request_data.file_paths[:3] if request_data.file_paths else []
                detail_msg += f" Verifique se os diretórios {file_previews}... existem."

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail_msg)

        return all_source_code, source_info, total_files_processed

    def _get_code_entry(self, code_entry_id: Optional[str], user_id: int) -> Optional[CodeEntry]:
        """Get the code entry requested by the user or the latest active one."""
        if code_entry_id:
            return self.db.query(CodeEntry).filter(
                CodeEntry.id == code_entry_id,
                CodeEntry.user_id == user_id,
                CodeEntry.is_active == True,  # noqa: E712
            ).first()

        return self.db.query(CodeEntry).filter(
            CodeEntry.user_id == user_id,
            CodeEntry.is_active == True,  # noqa: E712
        ).order_by(CodeEntry.created_at.desc()).first()

    async def _save_latest_prompt(self, final_prompt: str, request_data: AnalyzeSelectedRequest, current_user: User, total_files_processed: int) -> None:
        """Persist the final prompt for debugging."""
        try:
            content = '\n'.join([f"Último prompt para análise geral - {datetime.now().isoformat()}",
                            f"Usuário: {current_user.username} (ID: {current_user.id})",
                            f"Análise: {request_data.analysis_name}",
                            f"Critérios: {', '.join(request_data.criteria_ids)}",
                            f"Arquivos processados: {total_files_processed}",
                            f"Tamanho do prompt: {len(final_prompt)} caracteres",
                            "\nConteúdo do prompt:\n",
                            final_prompt])
            filename = f"latest_general_analysis_prompt_{current_user.id}.txt"
            await self.storage_provider.upload_bytes(
                user_id=current_user.id,
                file_id=f"general_analysis_{int(time.time())}",
                original_name=filename,
                relative_path=filename,
                content=content.encode('utf-8'),
                content_type="text/plain",
            )
        except Exception as save_error:
            print(f"DEBUG: Erro ao salvar prompt em arquivo: {save_error}")

    async def _save_latest_response(self, llm_response_content: str) -> None:
        """Persist the raw LLM response for debugging."""
        try:
            content = '\n'.join([f"Última resposta da LLM - {datetime.now().isoformat()}",
                            f"Tamanho da resposta: {len(llm_response_content)} caracteres",
                            "\nConteúdo da resposta:\n",
                            llm_response_content])
            filename = f"latest_general_analysis_response.txt"
            await self.storage_provider.upload_bytes(
                user_id=0,
                file_id=f"general_analysis_response_{int(time.time())}",
                original_name=filename,
                relative_path=filename,
                content=content.encode('utf-8'),
                content_type="text/plain",
            )
        except Exception as save_error:
            print(f"DEBUG: Erro ao salvar resposta em arquivo: {save_error}")

    def _extract_criteria_results(
        self,
        llm_response_content: str,
        structured_response: dict,
        selected_criteria,
        criteria_ids: List[str],
    ) -> dict:
        """Extract the criteria results from a structured or free-form LLM response."""
        def normalize_structured_criteria_results(structured_data: dict) -> dict:
            criteria_results = {}
            for item in structured_data.get("criteria_results", []):
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
                        f"### Evidências:\n" + "\n".join(f"- {evidence}" for evidence in item.get("evidence", [])) +
                        ("\n\n### Recomendações:\n" + "\n".join(f"- {recommendation}" for recommendation in item.get("recommendations", [])) if item.get("recommendations") else "")
                    ).strip()
                }
            return criteria_results

        if structured_response.get("criteria_results"):
            return {
                "criteria_results": normalize_structured_criteria_results(structured_response),
                "raw_response": llm_response_content.strip(),
                "structured_response": structured_response,
            }

        if not llm_response_content:
            return {"criteria_results": {}, "raw_response": "", "structured_response": structured_response}

        try:
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

    def _save_general_analysis_result(
        self,
        request_data: AnalyzeSelectedRequest,
        current_user: User,
        selected_criteria,
        extracted_content: dict,
        llm_response: dict,
        modified_prompt: str,
        processing_time_str: str,
    ) -> Optional[GeneralAnalysisResultModel]:
        """Persist the analysis result to the database."""
        import traceback

        try:
            safe_analysis_name = request_data.analysis_name[:197] + "..." if len(request_data.analysis_name) > 200 else request_data.analysis_name

            db_analysis_result = GeneralAnalysisResultModel(
                analysis_name=safe_analysis_name,
                criteria_count=len(selected_criteria),
                user_id=current_user.id,
                criteria_results=extracted_content.get("criteria_results", {}),
                raw_response=extracted_content.get("raw_response", ""),
                model_used=llm_response.get("model", "claude-3-sonnet-20240229"),
                usage=llm_response.get("usage", {}),
                file_paths=json.dumps(request_data.file_paths),
                modified_prompt=modified_prompt,
                processing_time=processing_time_str,
            )

            self.db.add(db_analysis_result)
            self.db.flush()
            self.db.commit()
            self.db.commit()
            self.db.refresh(db_analysis_result)

            return db_analysis_result
        except Exception as db_error:
            print(f"CRITICAL ERROR: Database save failed: {str(db_error)}")
            traceback.print_exc()
            self.db.rollback()
            return None

    def _parse_criteria_id(self, criteria_id: str) -> int:
        """Extract the numeric criteria ID."""
        try:
            return int(criteria_id.replace("criteria_", ""))
        except ValueError as exc:
            raise BusinessRuleError("Invalid criteria ID format") from exc

    def _ensure_general_prompt(self, current_user: User, criteria: List[str]) -> Prompt:
        """Create or refresh the prompt template used by general analysis."""
        prompt = self.db.query(Prompt).filter(
            Prompt.prompt_type == PromptType.GENERAL,
            Prompt.user_id == current_user.id,
        ).first()

        prompt_content = self._build_prompt_content(criteria)

        if not prompt:
            prompt = Prompt(
                prompt_type=PromptType.GENERAL,
                name="General Analysis Prompt",
                content=prompt_content,
                user_id=current_user.id,
                version=1,
            )
            self.db.add(prompt)
            self.db.commit()
            self.db.refresh(prompt)
            return prompt

        prompt.content = prompt_content
        prompt.version += 1
        self.db.commit()
        self.db.refresh(prompt)
        return prompt

    def _build_prompt_content(self, criteria: List[str]) -> str:
        criteria_text = "\n".join([f"- {criterion}" for criterion in criteria])
        return f"""
You are a code quality expert. Analyze the provided code based on the following criteria:

{criteria_text}

For each criterion, provide:
1. A clear assessment of whether the code meets the criterion
2. Confidence level (0.0-1.0)
3. Specific evidence from the code
4. Recommendations for improvement if applicable

Provide your analysis in a structured format that includes:
- Overall assessment
- Individual criterion evaluations
- Code examples supporting your findings
- Actionable recommendations

Format your response in markdown.
""".strip()

    def _build_criteria_results(self, issues):
        """Map stored issues to the general-analysis response shape."""
        criteria_results = []

        for issue in issues or []:
            criteria_results.append({
                "criterion": issue.get("criterion", "Unknown"),
                "assessment": issue.get("assessment", ""),
                "status": issue.get("status", "unknown"),
                "confidence": issue.get("confidence", 0.0),
                "evidence": issue.get("evidence", []),
                "recommendations": issue.get("recommendations", []),
            })

        return criteria_results
    
    def get_latest_response(self, current_user: User) -> dict:
        """Get the latest LLM response for debugging purposes."""
        from app.models.prompt import GeneralAnalysisResult
        
        try:
            latest_result = self.db.query(GeneralAnalysisResult).filter(
                GeneralAnalysisResult.user_id == current_user.id
            ).order_by(GeneralAnalysisResult.created_at.desc()).first()

            if latest_result and latest_result.raw_response:
                usage_data = latest_result.get_usage() or {}
                token_usage = {
                    "total_tokens": usage_data.get("totalTokenCount", 0),
                    "prompt_tokens": usage_data.get("promptTokenCount", 0),
                    "completion_tokens": usage_data.get("candidatesTokenCount", 0),
                    # Include additional token data for completeness
                    "thoughts_tokens": usage_data.get("thoughtsTokenCount", 0)
                }
                return {
                    "response_content": latest_result.raw_response,
                    "file_exists": bool(latest_result.get_file_paths()),
                    "file_size": len(latest_result.raw_response) if latest_result.raw_response else 0,
                    "modified_time": latest_result.created_at.timestamp() if latest_result.created_at else None,
                    "message": "Resposta da LLM encontrada com sucesso.",
                    "token_usage": token_usage,
                }
            else:
                raise NotFoundError("LLM response", "latest for user")
        except Exception as e:
            raise e
    
    def get_latest_prompt(self, current_user: User) -> dict:
        """Get the latest prompt sent to the LLM for debugging purposes."""
        from app.models.prompt import GeneralAnalysisResult
        
        try:
            latest_result = self.db.query(GeneralAnalysisResult).filter(
                GeneralAnalysisResult.user_id == current_user.id
            ).order_by(GeneralAnalysisResult.created_at.desc()).first()
            if not latest_result or not latest_result.modified_prompt:
                raise NotFoundError("LLM prompt", "latest for user")

            return {
                "prompt_content": latest_result.modified_prompt,
                "file_exists": True,
                "file_size": len(latest_result.modified_prompt),
                "modified_time": latest_result.created_at.timestamp() if latest_result.created_at else None,
                "message": "Último prompt enviado para a LLM encontrado com sucesso.",
                "token_usage": latest_result.get_usage() or {},
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao ler o último prompt: {str(e)}"
            )