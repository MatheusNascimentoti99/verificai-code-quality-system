"""
Analysis service for VerificAI Backend
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.analysis import Analysis, AnalysisStatus, AnalysisResult
from app.models.prompt import Prompt
from app.models.user import User
from app.core.exceptions import (
    NotFoundError, ValidationError, BusinessRuleError,
    DuplicateResourceError
)


class AnalysisService:
    """Service for analysis operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_analysis(self, user_id: int, analysis_data: Dict[str, Any], is_admin: bool = False) -> Analysis:
        """Create a new analysis"""
        analysis_data = dict(analysis_data)

        # Validate prompt exists and user has access
        prompt_id = analysis_data.get('prompt_id')
        prompt = self.db.query(Prompt).filter(Prompt.id == prompt_id).first()
        if not prompt:
            raise NotFoundError("Prompt", str(prompt_id))

        # Check prompt permissions
        if not prompt.is_public and prompt.author_id != user_id and not is_admin:
            raise BusinessRuleError("Access denied to prompt")

        # Validate analysis data
        self._validate_analysis_data(analysis_data)

        file_paths = analysis_data.pop('file_paths', []) or []

        # Create analysis
        analysis = Analysis(
            **analysis_data,
            user_id=user_id,
            status=AnalysisStatus.PENDING
        )
        analysis.set_file_paths(file_paths)

        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        return analysis

    def get_analysis_by_id(self, analysis_id: int) -> Optional[Analysis]:
        """Get analysis by ID"""
        return self.db.query(Analysis).filter(Analysis.id == analysis_id).first()

    def get_analyses(
        self,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "desc"
    ) -> List[Analysis]:
        """Get analyses with filtering, sorting, and pagination"""
        query = self.db.query(Analysis)

        # Apply user filter
        if user_id:
            query = query.filter(Analysis.user_id == user_id)

        # Apply filters
        if filters:
            if filters.get('status'):
                query = query.filter(Analysis.status == filters['status'])
            if filters.get('prompt_id'):
                query = query.filter(Analysis.prompt_id == filters['prompt_id'])
            if filters.get('language'):
                query = query.filter(Analysis.language == filters['language'])
            if filters.get('min_score') is not None:
                query = query.filter(Analysis.overall_score >= filters['min_score'])
            if filters.get('max_score') is not None:
                query = query.filter(Analysis.overall_score <= filters['max_score'])

        # Apply search
        if search:
            query = query.filter(
                or_(
                    Analysis.name.contains(search),
                    Analysis.description.contains(search)
                )
            )

        # Apply sorting
        if sort_by:
            sort_column = getattr(Analysis, sort_by, None)
            if sort_column:
                if sort_order == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(sort_column)
        else:
            query = query.order_by(desc(Analysis.created_at))

        return query.offset(skip).limit(limit).all()

    def get_analysis_result(self, analysis_id: int, user_id: int, is_admin: bool = False) -> Optional[AnalysisResult]:
        """Get analysis result"""
        analysis = self.get_analysis_by_id(analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", str(analysis_id))

        # Check permissions
        if not is_admin and analysis.user_id != user_id:
            raise BusinessRuleError("Access denied")

        return analysis.result

    def update_analysis(self, analysis_id: int, user_id: int, analysis_data: Dict[str, Any], is_admin: bool = False) -> Analysis:
        """Update analysis"""
        analysis = self.get_analysis_by_id(analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", str(analysis_id))

        # Check permissions
        if not is_admin and analysis.user_id != user_id:
            raise BusinessRuleError("Access denied")

        # Can only update pending analyses
        if analysis.status != AnalysisStatus.PENDING:
            raise BusinessRuleError("Can only update pending analyses")

        # Validate analysis data
        self._validate_analysis_data(analysis_data, is_update=True)

        # Update fields
        for field, value in analysis_data.items():
            if hasattr(analysis, field):
                setattr(analysis, field, value)

        self.db.commit()
        self.db.refresh(analysis)

        return analysis

    def delete_analysis(self, analysis_id: int, user_id: int, is_admin: bool = False) -> bool:
        """Delete analysis"""
        analysis = self.get_analysis_by_id(analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", str(analysis_id))

        # Check permissions
        if not is_admin and analysis.user_id != user_id:
            raise BusinessRuleError("Access denied")

        # Can only delete pending or completed analyses
        if analysis.status == AnalysisStatus.PROCESSING:
            raise BusinessRuleError("Cannot delete analysis while processing")

        self.db.delete(analysis)
        self.db.commit()

        return True

    def start_analysis(self, analysis_id: int) -> Analysis:
        """Start analysis processing"""
        analysis = self.get_analysis_by_id(analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", str(analysis_id))

        if analysis.status != AnalysisStatus.PENDING:
            raise BusinessRuleError("Analysis must be in pending status to start")

        analysis.start_processing()
        self.db.commit()
        self.db.refresh(analysis)

        return analysis

    def complete_analysis(self, analysis_id: int, result_data: Dict[str, Any]) -> Analysis:
        """Complete analysis with results"""
        analysis = self.get_analysis_by_id(analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", str(analysis_id))

        if analysis.status != AnalysisStatus.PROCESSING:
            raise BusinessRuleError("Analysis must be in processing status to complete")

        # Create result
        result = AnalysisResult(
            analysis_id=analysis_id,
            **result_data
        )

        self.db.add(result)
        analysis.complete_processing()
        analysis.calculate_scores()
        self.db.commit()
        self.db.refresh(analysis)

        return analysis

    def fail_analysis(self, analysis_id: int, error_message: str) -> Analysis:
        """Mark analysis as failed"""
        analysis = self.get_analysis_by_id(analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", str(analysis_id))

        analysis.fail_processing(error_message)
        self.db.commit()
        self.db.refresh(analysis)

        return analysis

    def cancel_analysis(self, analysis_id: int, user_id: int, is_admin: bool = False) -> Analysis:
        """Cancel analysis"""
        analysis = self.get_analysis_by_id(analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", str(analysis_id))

        # Check permissions
        if not is_admin and analysis.user_id != user_id:
            raise BusinessRuleError("Access denied")

        # Can only cancel processing analyses
        if analysis.status != AnalysisStatus.PROCESSING:
            raise BusinessRuleError("Can only cancel processing analyses")

        analysis.cancel_processing()
        self.db.commit()
        self.db.refresh(analysis)

        return analysis

    def restart_analysis(self, analysis_id: int, user_id: int, is_admin: bool = False) -> Analysis:
        """Restart analysis"""
        analysis = self.get_analysis_by_id(analysis_id)
        if not analysis:
            raise NotFoundError("Analysis", str(analysis_id))

        # Check permissions
        if not is_admin and analysis.user_id != user_id:
            raise BusinessRuleError("Access denied")

        # Can only restart failed or cancelled analyses
        if analysis.status not in [AnalysisStatus.FAILED, AnalysisStatus.CANCELLED]:
            raise BusinessRuleError("Can only restart failed or cancelled analyses")

        # Reset analysis status
        analysis.status = AnalysisStatus.PENDING
        analysis.progress_percentage = 0
        analysis.error_message = None
        analysis.started_at = None
        analysis.completed_at = None

        # Delete existing result if any
        if analysis.result:
            self.db.delete(analysis.result)

        self.db.commit()
        self.db.refresh(analysis)

        return analysis

    def get_analysis_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get analysis statistics"""
        query = self.db.query(Analysis)

        if user_id:
            query = query.filter(Analysis.user_id == user_id)

        analyses = query.all()
        total_analyses = len(analyses)
        completed_analyses = sum(1 for analysis in analyses if analysis.status == AnalysisStatus.COMPLETED)
        failed_analyses = sum(1 for analysis in analyses if analysis.status == AnalysisStatus.FAILED)

        completed_scores = [analysis.overall_score or 0 for analysis in analyses if analysis.status == AnalysisStatus.COMPLETED]
        average_score = sum(completed_scores) / len(completed_scores) if completed_scores else 0

        analyses_by_language: Dict[str, int] = {}
        analyses_by_status: Dict[str, int] = {status.value: 0 for status in AnalysisStatus}
        total_tokens_used = 0

        for analysis in analyses:
            if analysis.language:
                analyses_by_language[analysis.language] = analyses_by_language.get(analysis.language, 0) + 1
            analyses_by_status[analysis.status.value] = analyses_by_status.get(analysis.status.value, 0) + 1
            total_tokens_used += analysis.tokens_used or 0

        return {
            "total_analyses": total_analyses,
            "completed_analyses": completed_analyses,
            "failed_analyses": failed_analyses,
            "average_score": average_score,
            "average_processing_time": 0.0,
            "total_tokens_used": total_tokens_used,
            "total_cost": 0.0,
            "analyses_by_language": analyses_by_language,
            "analyses_by_status": analyses_by_status,
        }

    def get_user_analyses(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Analysis]:
        """Get analyses for a specific user"""
        return self.db.query(Analysis)\
            .filter(Analysis.user_id == user_id)\
            .order_by(desc(Analysis.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()

    def update_analysis_progress(self, analysis_id: int, progress_percentage: int) -> None:
        """Update analysis progress"""
        analysis = self.get_analysis_by_id(analysis_id)
        if analysis:
            analysis.update_progress(progress_percentage)
            self.db.commit()

    def get_recent_analyses(self, user_id: Optional[int] = None, limit: int = 10) -> List[Analysis]:
        """Get recent analyses"""
        query = self.db.query(Analysis)

        if user_id:
            query = query.filter(Analysis.user_id == user_id)

        return query.order_by(desc(Analysis.created_at)).limit(limit).all()

    def _validate_analysis_data(self, data: Dict[str, Any], is_update: bool = False) -> None:
        """Validate analysis data"""
        required_fields = ['name', 'prompt_id']

        if not is_update:
            for field in required_fields:
                if field not in data or not data[field]:
                    raise ValidationError(f"Field '{field}' is required")

        # Validate that at least one of repository_url, file_paths, or code_content is provided
        if not is_update:
            has_source = (
                data.get('repository_url') or
                data.get('file_paths') or
                data.get('code_content')
            )
            if not has_source:
                raise ValidationError("At least one of repository_url, file_paths, or code_content must be provided")

        # Validate score ranges if provided
        score_fields = ['overall_score', 'security_score', 'performance_score', 'maintainability_score']
        for field in score_fields:
            if field in data and data[field] is not None:
                score = data[field]
                if not (0 <= score <= 100):
                    raise ValidationError(f"{field} must be between 0 and 100")