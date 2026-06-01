"""
General analysis endpoints for VerificAI Backend - STO-007
Updated for token display fix - FINAL VERSION
"""

print("MODULE LOADED: general_analysis.py - 2025-12-09 22:08 - LATEST-CODE-ENTRY TEST")

import os
from typing import List, Optional, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Body, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_general_analysis_service
from app.models.user import User
from app.models.analysis import Analysis, AnalysisStatus
from app.models.prompt import Prompt, PromptCategory, PromptType
from app.models.prompt import GeneralCriteria, GeneralAnalysisResult as GeneralAnalysisResultModel
from app.models.uploaded_file import UploadedFile, FileStatus
from app.models.code_entry import CodeEntry
from app.schemas.analysis import AnalysisResponse
from app.schemas.general_analysis import (
    GeneralAnalysisRequest,
    AnalyzeSelectedRequest,
    GeneralCriteriaResponse,
    CriterionCreate,
    GeneralAnalysisResultResponse,
)
from app.api.v1.analysis import process_analysis
from app.services.general_analysis_service import GeneralAnalysisService
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.post("/create", response_model=AnalysisResponse)
async def create_general_analysis(
    request: GeneralAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Create a general analysis with custom criteria"""
    analysis = service.create_general_analysis(request, current_user)

    # Start background processing
    background_tasks.add_task(process_analysis, analysis.id, db)

    return analysis


@router.get("/criteria")
async def get_user_criteria(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Get shared criteria from all users"""
    try:
        all_criteria = service.get_user_criteria()

        seen_texts = set()
        result = []
        for criterion in all_criteria:
            if criterion.text not in seen_texts:
                seen_texts.add(criterion.text)
                result.append(GeneralCriteriaResponse(
                    id=f"criteria_{criterion.id}",
                    text=criterion.text,
                    active=criterion.is_active
                ))

        return result
    except Exception as e:
        print(f"ERROR in get_user_criteria: {e}")
        import traceback
        traceback.print_exc()
        raise e


@router.post("/criteria", response_model=GeneralCriteriaResponse)
async def create_criteria(
    request: CriterionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Create a new criterion"""
    new_criterion = service.create_criterion(current_user.id, request.text)

    return GeneralCriteriaResponse(
        id=f"criteria_{new_criterion.id}",
        text=new_criterion.text,
        active=new_criterion.is_active
    )


@router.put("/criteria/{criteria_id}", response_model=GeneralCriteriaResponse)
async def update_criteria(
    criteria_id: str,
    request: CriterionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Update an existing criterion"""
    criterion = service.update_criterion(criteria_id, request.text)

    return GeneralCriteriaResponse(
        id=f"criteria_{criterion.id}",
        text=criterion.text,
        active=criterion.is_active
    )


@router.delete("/criteria/{criteria_id}")
async def delete_criteria(
    criteria_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Delete a criterion"""
    service.delete_criterion(criteria_id)

    return {"message": "Criterion deleted successfully"}


@router.post("/criteria/{criteria_id}/delete")
async def delete_criteria_post(
    criteria_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete criterion using POST method"""
    try:
        actual_id = int(criteria_id.replace("criteria_", ""))
    except ValueError:
        return {"error": "Invalid criteria ID format"}

    criterion = db.query(GeneralCriteria).filter(
        GeneralCriteria.id == actual_id
    ).first()

    if not criterion:
        return {"error": f"Criterion not found with ID {actual_id}"}

    db.delete(criterion)
    db.commit()

    return {"message": "Criterion deleted successfully", "deleted_id": actual_id}

@router.get("/results/{analysis_id}", response_model=GeneralAnalysisResultResponse)
async def get_general_analysis_result(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Get general analysis result"""
    payload = service.get_general_analysis_result(analysis_id, current_user)
    return GeneralAnalysisResultResponse(**payload)

@router.options("/analyze-selected")
async def options_analyze_selected(request: Request):
    """Handle OPTIONS requests for CORS preflight"""
    return {}

@router.post("/analyze-selected")
async def analyze_selected_criteria(
    request: AnalyzeSelectedRequest,
    current_user: User = Depends(get_current_user),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Analyze selected criteria using the service layer."""
    return await service.analyze_selected_criteria(request, current_user)


@router.get("/results")
async def get_analysis_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Get all analysis results for the current user"""
    try:
        return service.get_analysis_results_payload(current_user)

    except Exception as e:
        print(f"ERROR in get_analysis_results: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving analysis results: {str(e)}"
        )

@router.get("/latest-raw-response")
async def get_latest_raw_response(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get the latest raw LLM response without any processing"""
    try:
        from pathlib import Path

        # Path to the raw response file
        prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
        raw_response_path = prompts_dir / "raw_response.txt"

        # Check if the file exists
        if not raw_response_path.exists():
            return {
                "success": False,
                "message": "Nenhuma resposta bruta da LLM encontrada. Execute uma anlise primeiro.",
                "response_content": None,
                "file_exists": False
            }

        # Read the raw response content
        with open(raw_response_path, "r", encoding="utf-8") as f:
            response_content = f.read()

        # Get file metadata
        import os
        file_stats = os.stat(raw_response_path)
        file_size = file_stats.st_size
        modified_time = file_stats.st_mtime

        return {
            "success": True,
            "message": "Resposta bruta da LLM carregada com sucesso",
            "response_content": response_content,
            "file_size": file_size,
            "modified_time": modified_time,
            "file_path": str(raw_response_path),
            "is_raw": True
        }

    except Exception as e:
        print(f"DEBUG: Error reading raw response: {e}")
        return {
            "success": False,
            "message": f"Erro ao ler resposta bruta da LLM: {str(e)}",
            "response_content": None,
            "file_exists": False
        }


@router.get("/criteria-working")
async def get_criteria_working(
    db: Session = Depends(get_db)
) -> Any:
    """Get all criteria (working public endpoint)"""
    try:
        # Get all active criteria from database
        all_criteria = db.query(GeneralCriteria).filter(
            GeneralCriteria.is_active == True
        ).order_by(GeneralCriteria.order, GeneralCriteria.created_at).all()

        # Convert to response format
        result = []
        for criterion in all_criteria:
            result.append({
                "id": f"criteria_{criterion.id}",
                "text": criterion.text,
                "active": criterion.is_active
            })

        return result

    except Exception as e:
        print(f"ERROR in get_criteria_working: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving criteria: {str(e)}"
        )

@router.get("/results/{result_id}")
async def get_analysis_result(
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Get a specific analysis result by ID"""
    try:
        return service.get_analysis_result_payload(result_id, current_user)

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in get_analysis_result: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving analysis result: {str(e)}"
        )

@router.delete("/results/{result_id}")
async def delete_analysis_result(
    result_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """Delete a specific analysis result"""
    try:
        # Find the analysis result
        result = db.query(GeneralAnalysisResultModel).filter(
            GeneralAnalysisResultModel.id == result_id
        ).first()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found"
            )

        # Delete the result
        db.delete(result)
        db.commit()

        return {
            "success": True,
            "message": f"Analysis result {result_id} deleted successfully",
            "deleted_id": result_id
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in delete_analysis_result: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting analysis result: {str(e)}"
        )


@router.delete("/results")
async def delete_multiple_analysis_results(
    request: dict,
    db: Session = Depends(get_db)
) -> Any:
    """Delete multiple analysis results"""
    try:
        result_ids = request.get("result_ids", [])
        
        if not result_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No result IDs provided"
            )

        # Find and delete the results
        deleted_count = 0
        for result_id in result_ids:
            result = db.query(GeneralAnalysisResultModel).filter(
                GeneralAnalysisResultModel.id == result_id
            ).first()
            
            if result:
                db.delete(result)
                deleted_count += 1

        db.commit()

        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} analysis results",
            "deleted_count": deleted_count,
            "requested_ids": result_ids
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in delete_multiple_analysis_results: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting analysis results: {str(e)}"
        )


@router.delete("/results/all")
async def delete_all_analysis_results(
    request: Request = None,  # Adding request to handle any potential body
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all analysis results for current user"""
    try:
        print(f"Starting delete all analysis results for user {current_user.id}")

        # Get all analysis results for this user first
        analysis_results = db.query(GeneralAnalysisResultModel).filter(
            GeneralAnalysisResultModel.user_id == current_user.id
        ).all()

        print(f"Found {len(analysis_results)} analysis results to delete for user {current_user.id}")

        if len(analysis_results) == 0:
            return {
                "success": True,
                "message": "No analysis results found to delete",
                "deleted_count": 0
            }

        # Delete all results
        deleted_count = 0
        for result in analysis_results:
            db.delete(result)
            deleted_count += 1

        db.commit()

        print(f"Successfully deleted {deleted_count} analysis results for user {current_user.id}")

        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} analysis results",
            "deleted_count": deleted_count
        }

    except Exception as e:
        print(f"ERROR in delete_all_analysis_results: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting all analysis results: {str(e)}"
        )




@router.get("/latest-prompt")
async def get_latest_prompt(
    current_user: User = Depends(get_current_user),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Get the latest prompt sent to LLM"""
    print("DEBUG: LATEST PROMPT ENDPOINT CALLED")
    try:
        # Try to get token usage information from the latest general analysis result
        res = service.get_latest_prompt(current_user)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhuma resposta encontrada. Execute uma análise primeiro."
            )
        return res
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma resposta encontrada. Execute uma análise primeiro."
        )
    except Exception as e:
        print(f"DEBUG: Error reading latest prompt: {e}")
        return {
            "success": False,
            "message": f"Erro ao ler prompt: {str(e)}",
            "prompt_content": None,
            "file_exists": False,
            "token_usage": {}
        }


@router.get("/latest-response")
async def get_latest_response(
    current_user: User = Depends(get_current_user),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    
    
    """Get the latest LLM response"""
    try:
        # Try to get token usage information from the latest general analysis result
        # FIXED VERSION - Token retrieval implemented correctly - 2025-10-05
        print("DEBUG: TOKEN FIX FINAL - Starting token usage retrieval")  # Final debug marker
        res = service.get_latest_response(current_user)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhuma resposta encontrada. Execute uma análise primeiro."
            )
            
        return res
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma resposta encontrada. Execute uma análise primeiro."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao ler resposta da LLM: {str(e)}"
        )

