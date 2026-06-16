"""
Endpoints for Architectural Analysis — VerificAI
Follows the same patterns as api/v1/general_analysis.py.
Prefix: /api/v1/architectural-analysis
"""

import json
from typing import Any, List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Form, Request,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.architectural import (
    ArchitecturalDoc,
    ArchitecturalCriteria,
    ArchitecturalAnalysisResult,
)
from app.schemas.architectural_analysis import (
    ArchitecturalDocCreate,
    ArchitecturalDocUpdate,
    ArchitecturalDocResponse,
    ArchitecturalCriteriaCreate,
    ArchitecturalCriteriaResponse,
    ArchitecturalAnalyzeRequest,
    ArchitecturalAnalysisResultResponse,
)
from app.services.architectural_analysis import (
    ArchitecturalAnalysisService,
    ALLOWED_FILE_EXTENSIONS,
    MAX_CONTENT_CHARS,
)
from app.core.dependencies import get_architectural_analysis_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_criteria_response(criterion: ArchitecturalCriteria) -> ArchitecturalCriteriaResponse:
    return ArchitecturalCriteriaResponse(
        id=f"arch_criteria_{criterion.id}",
        text=criterion.text,
        active=criterion.is_active,
        order=criterion.order,
    )


def _format_doc_response(doc: ArchitecturalDoc) -> ArchitecturalDocResponse:
    return ArchitecturalDocResponse(
        id=doc.id,
        user_id=doc.user_id,
        title=doc.title,
        sharepoint_url=doc.sharepoint_url,
        content=doc.content,
        file_name=doc.file_name,
        content_type=doc.content_type,
    )


def _format_result_response(result: ArchitecturalAnalysisResult) -> dict:
    return {
        "id": result.id,
        "analysis_name": result.analysis_name,
        "overall_status": result.overall_status,
        "criteria_count": result.criteria_count,
        "criteria_results": result.get_criteria_results(),
        "raw_response": result.raw_response,
        "model_used": result.model_used,
        "usage": result.get_usage(),
        "file_paths": result.get_file_paths(),
        "processing_time": result.processing_time,
        "doc_id": result.doc_id,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


# ---------------------------------------------------------------------------
# Docs endpoints
# ---------------------------------------------------------------------------

@router.post("/docs", response_model=ArchitecturalDocResponse)
async def create_architectural_doc(
    data: ArchitecturalDocCreate,
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Create an architectural documentation entry (textarea content)."""
    doc = service.create_doc(data, current_user.id)
    return _format_doc_response(doc)


@router.post("/docs/upload", response_model=ArchitecturalDocResponse)
async def upload_architectural_doc(
    title: str = Form(...),
    sharepoint_url: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Upload a .txt / .md / .html file as architectural documentation."""
    # Validate extension
    file_name = file.filename or "upload.txt"
    ext = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não permitido: '{ext}'. Aceito: {ALLOWED_FILE_EXTENSIONS}",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_CONTENT_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. Máximo: {MAX_CONTENT_CHARS} caracteres.",
        )

    doc = service.create_doc_from_upload(
        user_id=current_user.id,
        title=title,
        file_name=file_name,
        raw_bytes=raw_bytes,
        content_type=ext.lstrip("."),
        sharepoint_url=sharepoint_url,
    )
    return _format_doc_response(doc)


@router.get("/docs", response_model=List[ArchitecturalDocResponse])
async def list_architectural_docs(
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """List all architectural docs for the current user."""
    docs = service.list_docs(current_user.id)
    return [_format_doc_response(d) for d in docs]


@router.get("/docs/{doc_id}", response_model=ArchitecturalDocResponse)
async def get_architectural_doc(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Get a specific architectural doc by ID."""
    doc = service.get_doc(doc_id, current_user.id)
    return _format_doc_response(doc)


@router.put("/docs/{doc_id}", response_model=ArchitecturalDocResponse)
async def update_architectural_doc(
    doc_id: int,
    data: ArchitecturalDocUpdate,
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Update an existing architectural doc."""
    doc = service.update_doc(doc_id, data, current_user.id)
    return _format_doc_response(doc)


@router.delete("/docs/{doc_id}")
async def delete_architectural_doc(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Delete an architectural doc."""
    service.delete_doc(doc_id, current_user.id)
    return {"message": "Documentação arquitetural removida com sucesso.", "deleted_id": doc_id}


# ---------------------------------------------------------------------------
# Criteria endpoints
# ---------------------------------------------------------------------------

@router.get("/criteria", response_model=List[ArchitecturalCriteriaResponse])
async def list_architectural_criteria(
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """List active architectural criteria for the current user."""
    criteria = service.list_criteria(current_user.id)
    return [_format_criteria_response(c) for c in criteria]


@router.post("/criteria", response_model=ArchitecturalCriteriaResponse)
async def create_architectural_criterion(
    data: ArchitecturalCriteriaCreate,
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Create a new architectural criterion."""
    criterion = service.create_criterion(current_user.id, data.text)
    return _format_criteria_response(criterion)


@router.put("/criteria/{criteria_id}", response_model=ArchitecturalCriteriaResponse)
async def update_architectural_criterion(
    criteria_id: str,
    data: ArchitecturalCriteriaCreate,
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Update an existing architectural criterion."""
    criterion = service.update_criterion(criteria_id, data.text, current_user.id)
    return _format_criteria_response(criterion)


@router.delete("/criteria/{criteria_id}")
async def delete_architectural_criterion(
    criteria_id: str,
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Delete an architectural criterion."""
    service.delete_criterion(criteria_id, current_user.id)
    return {"message": "Critério removido com sucesso.", "deleted_id": criteria_id}


# ---------------------------------------------------------------------------
# Analysis execution
# ---------------------------------------------------------------------------

@router.options("/analyze")
async def options_analyze(request: Request) -> Any:
    """Handle CORS preflight for /analyze."""
    return {}


@router.post("/analyze")
async def run_architectural_analysis(
    request: ArchitecturalAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Execute an architectural analysis using the LLM."""
    try:
        result = await service.run_analysis(request, current_user)
        return _format_result_response(result)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar análise arquitetural: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Results endpoints
# ---------------------------------------------------------------------------

@router.get("/results")
async def list_architectural_results(
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """List all architectural analysis results for the current user."""
    results = service.list_results(current_user.id)
    return [_format_result_response(r) for r in results]


@router.get("/results/{result_id}")
async def get_architectural_result(
    result_id: int,
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Get a specific architectural analysis result."""
    result = service.get_result(result_id, current_user.id)
    return _format_result_response(result)


@router.delete("/results/{result_id}")
async def delete_architectural_result(
    result_id: int,
    current_user: User = Depends(get_current_user),
    service: ArchitecturalAnalysisService = Depends(get_architectural_analysis_service),
) -> Any:
    """Delete a specific architectural analysis result."""
    service.delete_result(result_id, current_user.id)
    return {"message": "Resultado removido com sucesso.", "deleted_id": result_id}
