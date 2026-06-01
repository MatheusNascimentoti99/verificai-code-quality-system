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


@router.delete("/criteria-temp/{criteria_id}")
async def delete_criteria_temp(
    criteria_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Temporary delete criterion endpoint"""
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


@router.post("/criteria-simple/{criteria_id}/delete")
async def delete_criteria_simple(
    criteria_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Simple delete criterion endpoint"""
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


@router.get("/debug-direct")
async def debug_direct(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Direct database test"""
    try:
        # Test direct database access
        criterion = db.query(GeneralCriteria).filter(GeneralCriteria.id == 57).first()
        return {
            "criterion_57_found": criterion is not None,
            "criterion_57_text": criterion.text if criterion else None,
            "criterion_57_user_id": criterion.user_id if criterion else None,
            "total_criteria": db.query(GeneralCriteria).count()
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/debug-delete-test")
async def debug_delete_test(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Test DELETE logic directly"""
    try:
        # Test the exact logic from DELETE endpoint
        criteria_id = 'criteria_23'
        actual_id = int(criteria_id.replace('criteria_', ''))

        criterion = db.query(GeneralCriteria).filter(
            GeneralCriteria.id == actual_id
        ).first()

        if criterion:
            result = {
                "found": True,
                "id": criterion.id,
                "user_id": criterion.user_id,
                "text": criterion.text,
                "is_active": criterion.is_active
            }
        else:
            all_criteria = db.query(GeneralCriteria).all()
            all_ids = [c.id for c in all_criteria]
            result = {
                "found": False,
                "searched_id": actual_id,
                "available_ids": all_ids
            }

        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/debug-test")
async def debug_test(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Debug endpoint to verify if changes are applied"""
    # Test finding a criterion without user_id filter
    criterion = db.query(GeneralCriteria).filter(
        GeneralCriteria.id == 55
    ).first()

    return {
        "message": "Debug test successful",
        "criterion_found": criterion is not None,
        "criterion_text": criterion.text if criterion else None,
        "criterion_user_id": criterion.user_id if criterion else None,
        "current_user_id": current_user.id
    }


@router.get("/latest-code-entry")
async def get_latest_code_entry(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Get the latest code entry from the current user"""
    try:
        print(f"DEBUG: Getting latest code entry for user {current_user.id}")
        latest_entry = service.get_latest_code_entry(current_user.id)

        if not latest_entry:
            return {
                "success": False,
                "message": "Nenhum código encontrado. Por favor, cole um código na página de colagem primeiro.",
                "code_content": None,
                "title": None,
                "language": None,
                "lines_count": 0,
                "characters_count": 0
            }

        print(f"DEBUG: Found latest code entry: {latest_entry.title} ({latest_entry.lines_count} lines)")

        return {
            "success": True,
            "message": "Código recuperado com sucesso",
            "code_content": latest_entry.code_content,
            "title": latest_entry.title,
            "description": latest_entry.description,
            "language": latest_entry.language,
            "lines_count": latest_entry.lines_count,
            "characters_count": latest_entry.characters_count,
            "created_at": latest_entry.created_at,
            "entry_id": str(latest_entry.id)
        }

    except Exception as e:
        print(f"ERROR in get_latest_code_entry: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving latest code entry: {str(e)}"
        )


@router.get("/results/{analysis_id}", response_model=GeneralAnalysisResultResponse)
async def get_general_analysis_result(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Get general analysis result"""
    payload = service.get_general_analysis_result(analysis_id, current_user)
    return GeneralAnalysisResultResponse(**payload)


@router.post("/get-latest-code-entry")
async def get_latest_code_entry_post(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Get the latest code entry from the current user using POST method"""
    try:
        print(f"DEBUG: Getting latest code entry for user {current_user.id}")
        latest_entry = service.get_latest_code_entry(current_user.id)

        if not latest_entry:
            return {
                "success": False,
                "message": "Nenhum código encontrado. Por favor, cole um código na página de colagem primeiro.",
                "code_content": None,
                "title": None,
                "language": None,
                "lines_count": 0,
                "characters_count": 0
            }

        print(f"DEBUG: Found latest code entry: {latest_entry.title} ({latest_entry.lines_count} lines)")

        return {
            "success": True,
            "message": "Código recuperado com sucesso",
            "code_content": latest_entry.code_content,
            "title": latest_entry.title,
            "description": latest_entry.description,
            "language": latest_entry.language,
            "lines_count": latest_entry.lines_count,
            "characters_count": latest_entry.characters_count,
            "created_at": latest_entry.created_at,
            "entry_id": str(latest_entry.id)
        }

    except Exception as e:
        print(f"ERROR in get_latest_code_entry_post: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving latest code entry: {str(e)}"
        )


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


@router.get("/debug-test-public")
async def test_endpoint() -> Any:
    """Simple test endpoint"""
    return {"message": "Test endpoint works", "status": "ok"}


@router.get("/debug-file-path")
async def debug_file_path(file_path: str, db: Session = Depends(get_db)) -> Any:
    """Debug endpoint to test file path resolution"""
    try:
        # Test with user_id = 1 (test user)
        actual_path = get_uploaded_file_path(file_path, db, 1)

        import os
        file_exists = os.path.exists(actual_path)

        return {
            "original_path": file_path,
            "resolved_path": actual_path,
            "file_exists": file_exists or actual_path.startswith("http://") or actual_path.startswith("https://"),
            "can_read": os.access(actual_path, os.R_OK) if file_exists else False
        }
    except Exception as e:
        return {"error": str(e), "original_path": file_path}


@router.post("/debug-cors-test")
async def debug_cors_test() -> Any:
    """Test CORS without authentication"""
    return {"message": "CORS test successful", "status": "ok", "cors": "working"}


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


@router.get("/criteria_public_test")
async def get_criteria_public_test(
    db: Session = Depends(get_db)
) -> Any:
    """Alternative test endpoint without hyphen"""
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
        print(f"ERROR in get_criteria_public_test: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving criteria: {str(e)}"
        )


@router.get("/results-public")
async def get_analysis_results_public(
    db: Session = Depends(get_db)
) -> Any:
    """Get all analysis results (public endpoint for testing)"""
    try:
        # Get all analysis results for user_id = 1 (testing)
        results = db.query(GeneralAnalysisResultModel).filter(
            GeneralAnalysisResultModel.user_id == 1
        ).order_by(GeneralAnalysisResultModel.created_at.desc()).all()

        # Convert to response format
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
                "usage": result.get_usage()
            })

        return {
            "success": True,
            "results": formatted_results,
            "total": len(formatted_results)
        }

    except Exception as e:
        print(f"ERROR in get_analysis_results_public: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving analysis results: {str(e)}"
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


@router.put("/results/{analysis_id}/manual", response_model=GeneralAnalysisResultResponse)
async def update_manual_result(
    analysis_id: int,
    result_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: GeneralAnalysisService = Depends(get_general_analysis_service)
) -> Any:
    """Update analysis result manually"""
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
        # Create manual result
        from app.models.analysis import AnalysisResult
        manual_result = AnalysisResult(
            analysis_id=analysis.id,
            summary=result_data.get("overall_assessment", ""),
            detailed_findings="Manual analysis result",
            recommendations=result_data.get("recommendations", ""),
            confidence=result_data.get("confidence", 1.0),
            model_used="manual",
            tokens_used=0,
            processing_time="0.0",
            quality_score=result_data.get("score", 0),
            issues=result_data.get("criteria_results", [])
        )
        db.add(manual_result)
    else:
        # Update existing result
        analysis.result.summary = result_data.get("overall_assessment", analysis.result.summary)
        analysis.result.confidence = result_data.get("confidence", analysis.result.confidence)
        analysis.result.quality_score = result_data.get("score", analysis.result.quality_score)
        analysis.result.issues = result_data.get("criteria_results", analysis.result.issues)
        analysis.result.model_used = "manual"

    db.commit()
    db.refresh(analysis)

    # Return updated result using the service
    payload = service.get_general_analysis_result(analysis_id, current_user)
    return GeneralAnalysisResultResponse(**payload)



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
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get the latest prompt sent to LLM"""
    print("DEBUG: LATEST PROMPT ENDPOINT CALLED")
    try:
        from pathlib import Path

        # Path to the latest prompt file
        prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
        latest_prompt_path = prompts_dir / "latest_prompt.txt"

        # Check if the file exists
        if not latest_prompt_path.exists():
            return {
                "success": False,
                "message": "Nenhum prompt encontrado. Execute uma anlise primeiro.",
                "prompt_content": None,
                "file_exists": False
            }

        # Read the prompt content
        with open(latest_prompt_path, "r", encoding="utf-8") as f:
            prompt_content = f.read()

        # Get file metadata
        import os
        file_stats = os.stat(latest_prompt_path)
        file_size = file_stats.st_size
        modified_time = file_stats.st_mtime

        # Try to get token usage information from the latest general analysis result
        # FIXED VERSION - Token retrieval implemented correctly - 2025-10-05
        print("DEBUG: TOKEN FIX FINAL - Starting token usage retrieval")  # Final debug marker
        token_usage = {}
        try:
            from app.core.database import SessionLocal
            from app.models.prompt import GeneralAnalysisResult

            db = SessionLocal()
            # Get the most recent general analysis result for the current user
            latest_result = db.query(GeneralAnalysisResult)\
                .filter(GeneralAnalysisResult.user_id == current_user.id)\
                .order_by(GeneralAnalysisResult.created_at.desc())\
                .first()

            if latest_result and latest_result.usage:
                # Use the complete token usage data from Gemini
                usage_data = latest_result.usage
                print("DEBUG: TOKEN FIX FINAL - Found usage data")  # Final debug marker

                token_usage = {
                    "total_tokens": usage_data.get("totalTokenCount", 0),
                    "prompt_tokens": usage_data.get("promptTokenCount", 0),
                    "completion_tokens": usage_data.get("candidatesTokenCount", 0),
                    # Include additional token data for completeness
                    "thoughts_tokens": usage_data.get("thoughtsTokenCount", 0)
                }
                print(f"DEBUG: TOKEN FIX FINAL - Mapped token_usage: {token_usage}")  # Final debug marker
            else:
                print("DEBUG: TOKEN FIX FINAL - No usage data found")  # Final debug marker

            db.close()
        except Exception as token_error:
            print(f"DEBUG: TOKEN FIX FINAL - Error getting token usage: {token_error}")
            # Continue without token info
            token_usage = {}

        return {
            "success": True,
            "message": "Prompt recuperado com sucesso",
            "prompt_content": prompt_content,
            "file_exists": True,
            "file_size": file_size,
            "modified_time": modified_time,
            "file_path": str(latest_prompt_path),
            "token_usage": token_usage
        }

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
    current_user: User = Depends(get_current_user)
) -> Any:
    import sys
    """Get the latest LLM response"""
    try:
        # Try to get token usage information from the latest general analysis result
        # FIXED VERSION - Token retrieval implemented correctly - 2025-10-05
        print("DEBUG: TOKEN FIX FINAL - Starting token usage retrieval")  # Final debug marker
        token_usage = {}
        response_content = {
            "success": False,
            "message": "Nenhuma resposta da LLM encontrada. Execute uma análise primeiro.",
            "response_content": None,
            "file_exists": False,
            "file_size": 0,
            "modified_time": None,
            "token_usage": {}
        }
        try:
            from app.core.database import SessionLocal
            from app.models.prompt import GeneralAnalysisResult

            db = SessionLocal()
            # Get the most recent general analysis result for the current user
            latest_result = db.query(GeneralAnalysisResult)\
                .filter(GeneralAnalysisResult.user_id == current_user.id)\
                .order_by(GeneralAnalysisResult.created_at.desc())\
                .first()

            if latest_result and latest_result.usage:
                # Use the complete token usage data from Gemini
                usage_data = latest_result.usage
                print("DEBUG: TOKEN FIX FINAL - Found usage data")  # Final debug marker

                token_usage = {
                    "total_tokens": usage_data.get("totalTokenCount", 0),
                    "prompt_tokens": usage_data.get("promptTokenCount", 0),
                    "completion_tokens": usage_data.get("candidatesTokenCount", 0),
                    # Include additional token data for completeness
                    "thoughts_tokens": usage_data.get("thoughtsTokenCount", 0)
                }
                response_content = {
                    "success": True,
                    "message": "Resposta da LLM recuperada com sucesso",
                    "response_content": latest_result.raw_response,
                    "file_exists": True,
                    "file_size": sys.getsizeof(latest_result.raw_response) if latest_result.raw_response else 0,
                    "modified_time": latest_result.created_at.timestamp() if latest_result.created_at else None,
                    "token_usage": token_usage
                }
                print(f"DEBUG: TOKEN FIX FINAL - Mapped token_usage: {token_usage}")  # Final debug marker
            else:
                print("DEBUG: TOKEN FIX FINAL - No usage data found")  # Final debug marker

            db.close()
        except Exception as token_error:
            print(f"DEBUG: TOKEN FIX FINAL - Error getting token usage: {token_error}")
            # Continue without token info
            token_usage = {}
        return response_content

    except Exception as e:
        print(f"DEBUG: Error reading latest response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao ler resposta da LLM: {str(e)}"
        )

