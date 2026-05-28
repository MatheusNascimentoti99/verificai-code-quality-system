"""
Service for general analysis workflows.
"""

import json
from typing import List, Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.analysis import Analysis, AnalysisStatus
from app.models.code_entry import CodeEntry
from app.models.prompt import Prompt, PromptType, GeneralCriteria, GeneralAnalysisResult as GeneralAnalysisResultModel
from app.models.uploaded_file import UploadedFile, FileStatus
from app.models.user import User
from app.schemas.analysis import AnalysisCreate
from app.services.analysis import AnalysisService
from app.services.storage_provider import get_storage_provider


class GeneralAnalysisService:
    """Encapsulates general analysis use cases."""

    def __init__(self, db: Session):
        self.db = db
        self.analysis_service = AnalysisService(db)

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

    def resolve_uploaded_file_path(self, file_path: str, user_id: int) -> str:
        """Resolve an uploaded file path to the actual storage locator."""
        try:
            storage = get_storage_provider()

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