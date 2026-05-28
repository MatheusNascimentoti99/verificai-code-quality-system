"""
Analysis endpoints for VerificAI Backend
"""

from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, CommonQueryParams, get_pagination_params
from app.models.user import User
from app.models.analysis import Analysis, AnalysisStatus
from app.schemas.analysis import (
    AnalysisCreate, AnalysisUpdate, AnalysisResponse, AnalysisListResponse,
    AnalysisResultResponse, AnalysisSearchFilters, AnalysisStats,
    BatchAnalysisRequest, BatchAnalysisResponse
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.post("/", response_model=AnalysisResponse)
def create_analysis(
    analysis_data: AnalysisCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create a new analysis"""
    # Validate prompt exists and user has access
    from app.models.prompt import Prompt
    prompt = db.query(Prompt).filter(Prompt.id == analysis_data.prompt_id).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    if not prompt.is_public and prompt.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to prompt"
        )

    analysis_dict = analysis_data.model_dump()
    file_paths = analysis_dict.pop("file_paths", [])

    # Create analysis
    analysis = Analysis(
        **analysis_dict,
        user_id=current_user.id,
        status=AnalysisStatus.PENDING
    )
    analysis.set_file_paths(file_paths)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Start background processing
    background_tasks.add_task(process_analysis, analysis.id, db)

    return analysis


@router.get("/", response_model=PaginatedResponse[AnalysisResponse])
def list_analyses(
    params: CommonQueryParams = Depends(),
    filters: AnalysisSearchFilters = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """List analyses with filtering and pagination"""
    query = db.query(Analysis)

    # Apply filters
    if filters.status:
        query = query.filter(Analysis.status == filters.status)
    if filters.user_id:
        # Users can only see their own analyses unless admin
        if filters.user_id != current_user.id and not current_user.is_admin:
            query = query.filter(Analysis.user_id == current_user.id)
        else:
            query = query.filter(Analysis.user_id == filters.user_id)
    else:
        # Users can only see their own analyses unless admin
        if not current_user.is_admin:
            query = query.filter(Analysis.user_id == current_user.id)

    if filters.prompt_id:
        query = query.filter(Analysis.prompt_id == filters.prompt_id)
    if filters.language:
        query = query.filter(Analysis.language == filters.language)
    if filters.min_score is not None:
        query = query.filter(Analysis.overall_score >= filters.min_score)
    if filters.max_score is not None:
        query = query.filter(Analysis.overall_score <= filters.max_score)
    if filters.search:
        query = query.filter(
            Analysis.name.contains(filters.search) |
            Analysis.description.contains(filters.search)
        )

    # Get total count
    total = query.count()

    # Apply sorting
    if params.sort_by:
        sort_column = getattr(Analysis, params.sort_by, None)
        if sort_column:
            if params.sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(Analysis.created_at.desc())

    # Apply pagination
    analyses = query.offset(params.skip).limit(params.limit).all()

    return PaginatedResponse(
        items=analyses,
        total=total,
        skip=params.skip,
        limit=params.limit,
        pages=(total + params.limit - 1) // params.limit,
        current_page=(params.skip // params.limit) + 1,
        has_next=params.skip + params.limit < total,
        has_prev=params.skip > 0
    )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get analysis by ID"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Check permissions
    if analysis.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return analysis


@router.get("/{analysis_id}/result", response_model=AnalysisResultResponse)
def get_analysis_result(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get analysis result"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Check permissions
    if analysis.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if not analysis.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis result not available"
        )

    return analysis.result


@router.put("/{analysis_id}", response_model=AnalysisResponse)
def update_analysis(
    analysis_id: int,
    analysis_data: AnalysisUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update analysis"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Check permissions
    if analysis.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Can only update pending analyses
    if analysis.status != AnalysisStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update pending analyses"
        )

    # Update fields
    for field, value in analysis_data.model_dump(exclude_unset=True).items():
        setattr(analysis, field, value)

    db.commit()
    db.refresh(analysis)

    return analysis


@router.delete("/{analysis_id}", response_model=dict)
def delete_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete analysis"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Check permissions
    if analysis.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Can only delete pending or completed analyses
    if analysis.status == AnalysisStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete analysis while processing"
        )

    db.delete(analysis)
    db.commit()

    return {"message": "Analysis deleted successfully"}


@router.post("/{analysis_id}/cancel", response_model=dict)
def cancel_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Cancel analysis"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Check permissions
    if analysis.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Can only cancel processing analyses
    if analysis.status != AnalysisStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel processing analyses"
        )

    analysis.cancel_processing()
    db.commit()

    return {"message": "Analysis cancelled successfully"}


@router.post("/{analysis_id}/restart", response_model=AnalysisResponse)
def restart_analysis(
    analysis_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Restart analysis"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Check permissions
    if analysis.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Can only restart failed or cancelled analyses
    if analysis.status not in [AnalysisStatus.FAILED, AnalysisStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only restart failed or cancelled analyses"
        )

    # Reset analysis status
    analysis.status = AnalysisStatus.PENDING
    analysis.progress_percentage = 0
    analysis.error_message = None
    analysis.started_at = None
    analysis.completed_at = None

    db.commit()

    # Start background processing
    background_tasks.add_task(process_analysis, analysis.id, db)

    return analysis


@router.post("/batch", response_model=BatchAnalysisResponse)
def create_batch_analysis(
    batch_data: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create batch analysis"""
    # TODO: Implement actual batch analysis logic
    # This is a placeholder response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Batch analysis functionality not yet implemented"
    )


@router.get("/stats", response_model=AnalysisStats)
def get_analysis_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get analysis statistics"""
    # Users can only see their own stats unless admin
    if current_user.is_admin:
        query = db.query(Analysis)
    else:
        query = db.query(Analysis).filter(Analysis.user_id == current_user.id)

    total_analyses = query.count()
    completed_analyses = query.filter(Analysis.status == AnalysisStatus.COMPLETED).count()
    failed_analyses = query.filter(Analysis.status == AnalysisStatus.FAILED).count()

    # Calculate average score for completed analyses
    completed_query = query.filter(Analysis.status == AnalysisStatus.COMPLETED)
    avg_score = completed_query.with_entities(Analysis.overall_score).all()
    avg_score = sum([score[0] or 0 for score in avg_score]) / len(avg_score) if avg_score else 0

    return AnalysisStats(
        total_analyses=total_analyses,
        completed_analyses=completed_analyses,
        failed_analyses=failed_analyses,
        average_score=avg_score,
        average_processing_time=0.0,  # TODO: Calculate actual processing time
        total_tokens_used=0,  # TODO: Sum actual tokens used
        total_cost=0.0,  # TODO: Calculate actual cost
        analyses_by_language={},  # TODO: Group by language
        analyses_by_status={}  # TODO: Group by status
    )


@router.post("/upload", response_model=AnalysisResponse)
def upload_analysis_file(
    file: UploadFile = File(...),
    prompt_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
) -> Any:
    """Upload file for analysis"""
    # TODO: Implement actual file upload and analysis
    # This is a placeholder response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="File upload functionality not yet implemented"
    )


# Background task for processing analysis
async def process_analysis(analysis_id: int, db: Session) -> None:
    """Process analysis in background using the orchestrator"""
    from app.models.analysis import AnalysisResult
    from app.services.analysis_orchestrator import AnalysisOrchestrator

    try:
        # Get analysis
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return

        # Initialize orchestrator
        orchestrator = AnalysisOrchestrator()

        # Start analysis using orchestrator
        job_id = await orchestrator.start_analysis(analysis)

        logger.info(f"Analysis {analysis_id} started with job ID: {job_id}")

    except Exception as e:
        # Mark analysis as failed
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            analysis.fail_processing(str(e))
            db.commit()

        logger.error(f"Error starting analysis {analysis_id}: {str(e)}")


@router.post("/{analysis_id}/start", response_model=dict)
async def start_analysis(
    analysis_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Start analysis processing"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Check permissions
    if analysis.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Can only start pending analyses
    if analysis.status != AnalysisStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only start pending analyses"
        )

    # Start background processing
    background_tasks.add_task(process_analysis, analysis.id, db)

    return {"message": "Analysis started successfully", "job_id": str(analysis.id)}


@router.get("/queue/status", response_model=dict)
async def get_queue_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get analysis queue status"""
    from app.services.analysis_orchestrator import AnalysisOrchestrator

    orchestrator = AnalysisOrchestrator()
    queue_status = await orchestrator.queue.get_queue_status()

    # Filter active job by user permission
    if queue_status.get('active_job') and not current_user.is_admin:
        active_job = queue_status['active_job']
        if active_job['user_id'] != current_user.id:
            queue_status['active_job'] = None

    return queue_status


@router.get("/queue/active", response_model=dict)
async def get_active_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get currently active analysis"""
    from app.services.analysis_orchestrator import AnalysisOrchestrator

    orchestrator = AnalysisOrchestrator()
    active_analysis = await orchestrator.get_active_analysis()

    # Check permissions
    if active_analysis and not current_user.is_admin:
        if active_analysis['user_id'] != current_user.id:
            return None

    return active_analysis


@router.post("/{analysis_id}/cancel", response_model=dict)
async def cancel_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Cancel analysis"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Check permissions
    if analysis.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Can only cancel processing analyses
    if analysis.status != AnalysisStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel processing analyses"
        )

    # Cancel using orchestrator
    from app.services.analysis_orchestrator import AnalysisOrchestrator
    orchestrator = AnalysisOrchestrator()
    cancelled = await orchestrator.cancel_analysis(str(analysis_id))

    if cancelled:
        analysis.cancel_processing()
        db.commit()
        return {"message": "Analysis cancelled successfully"}
    else:
        return {"message": "Analysis was not found in active jobs"}


@router.get("/{analysis_id}/status", response_model=dict)
async def get_analysis_status(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get detailed analysis status"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Check permissions
    if analysis.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get detailed status from orchestrator
    from app.services.analysis_orchestrator import AnalysisOrchestrator
    orchestrator = AnalysisOrchestrator()
    detailed_status = await orchestrator.get_analysis_status(str(analysis_id))

    return {
        "analysis_id": analysis_id,
        "name": analysis.name,
        "status": analysis.status,
        "progress": analysis.progress_percentage,
        "created_at": analysis.created_at.isoformat(),
        "started_at": analysis.started_at.isoformat() if analysis.started_at else None,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "error_message": analysis.error_message,
        "queue_status": detailed_status
    }