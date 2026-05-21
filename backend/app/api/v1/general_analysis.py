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
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.analysis import Analysis, AnalysisStatus
from app.models.prompt import Prompt, PromptCategory, PromptType
from app.models.prompt import GeneralCriteria, GeneralAnalysisResult as GeneralAnalysisResultModel
from app.models.uploaded_file import UploadedFile, FileStatus
from app.models.code_entry import CodeEntry
from app.schemas.analysis import AnalysisCreate, AnalysisResponse
from app.api.v1.analysis import process_analysis
from app.services.prompt_service import get_prompt_service
from app.services.llm_service import llm_service
from app.services.storage_provider import get_storage_provider

router = APIRouter()

def get_uploaded_file_path(file_path: str, db: Session, user_id: int) -> str:
    """
    Find an uploaded file by its relative path and return its storage path.
    This handles the transition from path-based to upload-based file access.
    """
    try:
        print(f"DEBUG: get_uploaded_file_path called with: file_path='{file_path}', user_id={user_id}")

        # Helper function to find the most recent uploaded file.
        # Local files are validated on disk; blob URLs are accepted as-is.
        def find_most_recent_existing(files_query):
            # Order by created_at descending to get most recent first
            files = files_query.order_by(UploadedFile.created_at.desc()).all()

            for uploaded_file in files:
                import os
                # Use storage_path for both local and blob storage.
                file_locator = uploaded_file.storage_path
                if str(file_locator).startswith("http://") or str(file_locator).startswith("https://"):
                    print(f"DEBUG: Found blob file: {uploaded_file.original_name} at {file_locator} from {uploaded_file.created_at}")
                    return uploaded_file, file_locator

                if os.path.exists(file_locator):
                    print(f"DEBUG: Found existing local file: {uploaded_file.original_name} at {file_locator} from {uploaded_file.created_at}")
                    return uploaded_file, file_locator
                else:
                    print(f"DEBUG: File not found on disk: {file_locator}")

            return None, None

        # First, try to find by relative_path (for folder uploads)
        print(f"DEBUG: Trying to find by relative_path: '{file_path}'")
        files_query = db.query(UploadedFile).filter(
            UploadedFile.relative_path == file_path,
            UploadedFile.user_id == user_id,
            UploadedFile.status == FileStatus.COMPLETED
        )
        uploaded_file, full_disk_path = find_most_recent_existing(files_query)

        if not uploaded_file:
            # If not found, try by original_name (for single file uploads)
            print(f"DEBUG: Trying to find by original_name: '{file_path}'")
            files_query = db.query(UploadedFile).filter(
                UploadedFile.original_name == file_path,
                UploadedFile.user_id == user_id,
                UploadedFile.status == FileStatus.COMPLETED
            )
            uploaded_file, full_disk_path = find_most_recent_existing(files_query)

        if not uploaded_file:
            # If still not found, try partial matching (filename only)
            filename = file_path.split('/')[-1].split('\\')[-1]
            print(f"DEBUG: Trying to find by filename only: '{filename}'")
            files_query = db.query(UploadedFile).filter(
                UploadedFile.original_name == filename,
                UploadedFile.user_id == user_id,
                UploadedFile.status == FileStatus.COMPLETED
            )
            uploaded_file, full_disk_path = find_most_recent_existing(files_query)

        if not uploaded_file:
            # If still not found, try by storage_path containing the filename
            print(f"DEBUG: Trying to find by storage_path containing: '{file_path}'")
            files_query = db.query(UploadedFile).filter(
                UploadedFile.storage_path.like(f'%{file_path}%'),
                UploadedFile.user_id == user_id,
                UploadedFile.status == FileStatus.COMPLETED
            )
            uploaded_file, full_disk_path = find_most_recent_existing(files_query)

        # Let's also check what files are available for this user if still not found
        if not uploaded_file:
            print(f"DEBUG: Checking all available files for user {user_id}:")
            all_files = db.query(UploadedFile).filter(
                UploadedFile.user_id == user_id,
                UploadedFile.status == FileStatus.COMPLETED
            ).order_by(UploadedFile.created_at.desc()).all()
            print(f"DEBUG: Found {len(all_files)} total files for user")
            for f in all_files[:5]:  # Show first 5 files
                print(f"DEBUG:  - original_name: '{f.original_name}', file_path: '{f.file_path}', date: {f.created_at}")

        if uploaded_file and full_disk_path:
            print(f"DEBUG: Returning valid file path: {full_disk_path}")
            return full_disk_path

        # If no uploaded file found, fall back to original path (for backward compatibility)
        print(f"DEBUG: No uploaded file found for path: {file_path}, using original path")
        return file_path

    except Exception as e:
        print(f"DEBUG: Error finding uploaded file: {e}")
        import traceback
        traceback.print_exc()
        return file_path


class GeneralAnalysisRequest(BaseModel):
    """Request model for general analysis"""
    name: str
    description: Optional[str] = None
    file_paths: List[str]
    criteria: List[str]
    llm_provider: str = "openai"
    temperature: float = 0.7
    max_tokens: int = 500000


class AnalyzeSelectedRequest(BaseModel):
    """Request model for analyzing selected criteria"""
    criteria_ids: List[str]
    file_paths: List[str] = []  # Mantido para compatibilidade, mas não será usado
    use_code_entry: bool = False  # Changed to False by default to prefer uploaded files
    code_entry_id: Optional[str] = None  # ID específico do code_entry (opcional)
    analysis_name: Optional[str] = "Análise de Critérios Gerais"
    temperature: float = 0.7
    max_tokens: int = 500000


class GeneralCriteriaResponse(BaseModel):
    """Criteria model for general analysis"""
    id: str
    text: str
    active: bool = True


class CriterionCreate(BaseModel):
    """Request model for creating a criterion"""
    text: str


class GeneralAnalysisResult(BaseModel):
    """Result model for general analysis"""
    id: str
    analysis_type: str = "general"
    timestamp: Any
    overall_assessment: str
    criteria_results: List[dict]
    token_usage: dict
    processing_time: float
    status: str


@router.post("/create", response_model=AnalysisResponse)
async def create_general_analysis(
    request: GeneralAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create a general analysis with custom criteria"""
    # Create or get general prompt
    general_prompt = db.query(Prompt).filter(
        Prompt.prompt_type == PromptType.GENERAL,
        Prompt.user_id == current_user.id
    ).first()

    criteria_text = "\n".join([f"- {criterion}" for criterion in request.criteria])
    prompt_content = f"""
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
"""

    if not general_prompt:
        # Create general prompt with user criteria
        general_prompt = Prompt(
            prompt_type=PromptType.GENERAL,
            name="General Analysis Prompt",
            content=prompt_content,
            user_id=current_user.id,
            version=1
        )
        db.add(general_prompt)
        db.commit()
        db.refresh(general_prompt)
    else:
        # Update prompt content with new criteria
        general_prompt.content = prompt_content
        general_prompt.version += 1
        db.commit()

    # Create analysis
    analysis_data = AnalysisCreate(
        name=request.name,
        description=request.description,
        prompt_id=general_prompt.id,
        file_paths=request.file_paths,
        configuration={
            "llm_provider": request.llm_provider,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "criteria": request.criteria,
            "analysis_type": "general"
        }
    )

    analysis_dict = analysis_data.model_dump()
    file_paths = analysis_dict.pop("file_paths", [])
    
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


@router.get("/criteria")
async def get_user_criteria(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get shared criteria from all users"""
    try:
        # Get all criteria from database (shared access)
        all_criteria = db.query(GeneralCriteria).filter(
            GeneralCriteria.is_active == True
        ).order_by(GeneralCriteria.order, GeneralCriteria.created_at).all()

        # Deduplicate by text and convert to response format
        seen_texts = set()
        result = []
        for criterion in all_criteria:
            if criterion.text not in seen_texts:
                seen_texts.add(criterion.text)
                result.append({
                    "id": f"criteria_{criterion.id}",
                    "text": criterion.text,
                    "active": criterion.is_active
                })

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
    db: Session = Depends(get_db)
) -> Any:
    """Create a new criterion"""
    # Get the highest order number for this user
    max_order = db.query(GeneralCriteria).filter(
        GeneralCriteria.user_id == current_user.id
    ).order_by(GeneralCriteria.order.desc()).first()

    next_order = (max_order.order + 1) if max_order else 0

    # Create new criterion
    new_criterion = GeneralCriteria(
        user_id=current_user.id,
        text=request.text,
        is_active=True,
        order=next_order
    )

    db.add(new_criterion)
    db.commit()
    db.refresh(new_criterion)

    # Return created criterion
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
    db: Session = Depends(get_db)
) -> Any:
    """Update an existing criterion"""
    # Extract the actual ID from the criteria_id string
    try:
        actual_id = int(criteria_id.replace("criteria_", ""))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid criteria ID format"
        )

    # Find the criterion (allow update of any criteria since they are shared)
    criterion = db.query(GeneralCriteria).filter(
        GeneralCriteria.id == actual_id
    ).first()

    if not criterion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Criterion not found"
        )

    # Update the criterion
    criterion.text = request.text
    db.commit()
    db.refresh(criterion)

    return GeneralCriteriaResponse(
        id=f"criteria_{criterion.id}",
        text=criterion.text,
        active=criterion.is_active
    )


@router.delete("/criteria/{criteria_id}")
async def delete_criteria(
    criteria_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete a criterion"""
    # Extract the actual ID from the criteria_id string
    try:
        actual_id = int(criteria_id.replace("criteria_", ""))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid criteria ID format"
        )

    # Debug: Log the ID being searched
    print(f"DEBUG: Searching for criterion with ID: {actual_id}")
    print(f"DEBUG: Original criteria_id: {criteria_id}")

    # Find the criterion (allow deletion of any criteria since they are shared)
    criterion = db.query(GeneralCriteria).filter(
        GeneralCriteria.id == actual_id
    ).first()

    if not criterion:
        # Debug: Check if criterion exists with different query
        all_criteria = db.query(GeneralCriteria).all()
        print(f"DEBUG: All criteria IDs: {[c.id for c in all_criteria]}")
        print(f"DEBUG: Criterion with ID {actual_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Criterion not found"
        )

    # Delete the criterion
    db.delete(criterion)
    db.commit()

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
    db: Session = Depends(get_db)
) -> Any:
    """Get the latest code entry from the current user"""
    try:
        print(f"DEBUG: Getting latest code entry for user {current_user.id}")

        # Get the most recent code entry for the current user
        latest_entry = db.query(CodeEntry).filter(
            CodeEntry.user_id == current_user.id,
            CodeEntry.is_active == True
        ).order_by(CodeEntry.created_at.desc()).first()

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


@router.get("/results/{analysis_id}", response_model=GeneralAnalysisResult)
async def get_general_analysis_result(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get general analysis result"""
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

    # Parse result into general analysis format
    criteria_results = []
    if analysis.result.issues:
        for issue in analysis.result.get_issues():
            criteria_results.append({
                "criterion": issue.get("criterion", "Unknown"),
                "assessment": issue.get("assessment", ""),
                "status": issue.get("status", "unknown"),
                "confidence": issue.get("confidence", 0.0),
                "evidence": issue.get("evidence", []),
                "recommendations": issue.get("recommendations", [])
            })

    return GeneralAnalysisResult(
        id=str(analysis.id),
        analysis_type="general",
        timestamp=analysis.created_at,
        overall_assessment=analysis.result.summary,
        criteria_results=criteria_results,
        token_usage={
            "total_tokens": analysis.result.tokens_used or 0,
            "prompt_tokens": analysis.result.tokens_used or 0,  # Placeholder
            "completion_tokens": 0  # Placeholder
        },
        processing_time=float(analysis.result.processing_time or 0),
        status=analysis.status
    )


@router.post("/get-latest-code-entry")
async def get_latest_code_entry_post(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get the latest code entry from the current user using POST method"""
    try:
        print(f"DEBUG: Getting latest code entry for user {current_user.id}")

        # Get the most recent code entry for the current user
        latest_entry = db.query(CodeEntry).filter(
            CodeEntry.user_id == current_user.id,
            CodeEntry.is_active == True
        ).order_by(CodeEntry.created_at.desc()).first()

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
    db: Session = Depends(get_db)
) -> Any:
    """Analyze selected criteria using LLM with dynamic prompt insertion"""
    # DEBUG: Updated with better logging for debugging
    try:
        print(f"DEBUG: === STARTING ANALYZE-SELECTED FUNCTION ===")
        print(f"DEBUG: Starting analysis for criteria: {request.criteria_ids}")
        print(f"DEBUG: File paths: {request.file_paths}")
        print(f"DEBUG: User: {current_user.username} (ID: {current_user.id})")
        print(f"DEBUG: use_code_entry: {request.use_code_entry}")
        print(f"DEBUG: code_entry_id: {request.code_entry_id}")

        # Get prompt service
        print("DEBUG: Getting prompt service...")
        prompt_service = get_prompt_service(db)
        storage = get_storage_provider()

        # Step 1: Read the general prompt from database (CORRECTED TO USE PROMPT ID 4)
        print("DEBUG: Getting general prompt from database...")
        try:
            # CORRECTED: Use prompt ID 4 which has the correct structure and placeholder
            general_prompt = prompt_service.get_general_prompt(4)  # Use Template com Código Fonte no Início
            print(f"DEBUG: Using prompt ID 4 (Template com Código Fonte no Início) - contains [INSERIR CÓDIGO AQUI]")
            if "[INSERIR CÓDIGO AQUI]" not in general_prompt:
                print(f"DEBUG: WARNING - Prompt ID 4 doesn't contain placeholder, using default")
                general_prompt = prompt_service._get_default_general_prompt()
        except Exception as e:
            print(f"DEBUG: Error getting prompt 4, using default: {e}")
            general_prompt = prompt_service._get_default_general_prompt()
        print(f"DEBUG: Retrieved general prompt length: {len(general_prompt)}")

        # Step 2: Get selected criteria from database
        print("DEBUG: Getting selected criteria from database...")
        selected_criteria = prompt_service.get_selected_criteria(request.criteria_ids)
        print(f"DEBUG: Found {len(selected_criteria)} criteria")

        if not selected_criteria:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid criteria found"
            )

        # Step 3: Insert criteria into prompt (in memory only)
        modified_prompt = prompt_service.insert_criteria_into_prompt(general_prompt, selected_criteria)
        print(f"DEBUG: Modified prompt length: {len(modified_prompt)}")

        # Step 4: Get source code from code_entries table or files
        try:
            all_source_code = ""
            source_info = ""
            total_files_processed = 0

            # Determine source: Prioritize file_paths if provided and not empty
            is_using_files = len(request.file_paths) > 0
            
            if not is_using_files and request.use_code_entry:
                # Buscar código da tabela code_entries
                print(f"DEBUG: No files provided, but use_code_entry=True. Getting code from code_entries table")

                code_entry = None

                # Se um ID específico foi fornecido, usar esse
                if request.code_entry_id:
                    code_entry = db.query(CodeEntry).filter(
                        CodeEntry.id == request.code_entry_id,
                        CodeEntry.user_id == current_user.id,
                        CodeEntry.is_active == True
                    ).first()
                    print(f"DEBUG: Looking for specific code_entry_id: {request.code_entry_id}")
                else:
                    # Caso contrário, buscar o mais recente
                    code_entry = db.query(CodeEntry).filter(
                        CodeEntry.user_id == current_user.id,
                        CodeEntry.is_active == True
                    ).order_by(CodeEntry.created_at.desc()).first()
                    print(f"DEBUG: Looking for latest code entry")

                if not code_entry:
                    raise HTTPException(
                        status_code=400,
                        detail="Nenhum código encontrado na tabela de colagem. Por favor, cole um código na página de colagem primeiro."
                    )

                all_source_code = code_entry.code_content
                file_size = len(all_source_code)

                # Adicionar informações sobre o código
                source_info = f"\n\n{'='*60}\n"
                source_info += f"CÓDIGO COLADO: {code_entry.title}\n"
                source_info += f"DESCRIÇÃO: {code_entry.description or 'Sem descrição'}\n"
                source_info += f"LINGUAGEM: {code_entry.language or 'Não detectada'}\n"
                source_info += f"TAMANHO: {file_size} caracteres\n"
                source_info += f"LINHAS: {code_entry.lines_count}\n"
                source_info += f"CRIADO EM: {code_entry.created_at}\n"
                source_info += f"{'='*60}\n\n"

                print(f"DEBUG: Found code entry: {code_entry.title} ({file_size} characters)")
                total_files_processed = 1

            else:
                # Mantido para compatibilidade: ler dos arquivos (caminho original)
                if not request.file_paths or len(request.file_paths) == 0:
                    raise HTTPException(status_code=400, detail="No file paths provided")

                print(f"DEBUG: Processing {len(request.file_paths)} files for analysis")

                # Process each file and combine them
                for i, source_file_path in enumerate(request.file_paths):
                    try:
                        print(f"DEBUG: Processing file {i+1}/{len(request.file_paths)}: {source_file_path}")

                        # Try to find the uploaded file and get its real storage path
                        actual_file_path = get_uploaded_file_path(source_file_path, db, current_user.id)
                        print(f"DEBUG: Actual file locator to read: {actual_file_path}")

                        file_content = await storage.read_text(actual_file_path)
                        file_size = len(file_content)
                        print(f"DEBUG: File read successfully: {file_size} characters")

                        # Add file header and content to the combined source code
                        file_extension = source_file_path.split('.')[-1] if '.' in source_file_path else 'txt'
                        source_info += f"\n\n{'='*60}\n"
                        source_info += f"ARQUIVO: {source_file_path}\n"
                        source_info += f"TAMANHO: {file_size} caracteres\n"
                        source_info += f"TIPO: {file_extension.upper()}\n"
                        source_info += f"{'='*60}\n\n"
                        all_source_code += file_content

                        total_files_processed += 1

                    except Exception as file_error:
                        error_msg = str(file_error)
                        print(f"❌ DEBUG: Error processing file {source_file_path} (actual: {actual_file_path}): {error_msg}")
                        # Continue with other files even if one fails
                        continue

                print(f"DEBUG: Successfully processed {total_files_processed}/{len(request.file_paths)} files")

            print(f"DEBUG: Total source code size: {len(all_source_code)} characters")

            if total_files_processed == 0:
                is_cloud = "render" in os.environ.get("HOSTNAME", "").lower() or "vercel" in os.environ.get("HOSTNAME", "").lower()
                detail_msg = "Nenhum código pôde ser lido para análise. O arquivo não existe no disco."
                if is_cloud:
                    detail_msg += " Devido ao ambiente cloud (Render/Vercel), arquivos locais são perdidos após o restart. Por favor, remova caminhos antigos ou use a 'Colagem de Código'."
                else:
                    file_previews = request.file_paths[:3] if request.file_paths else []
                    detail_msg += f" Verifique se os diretórios {file_previews}... existem."
                
                # Changing from 500 to 400 so it's treated as a bad request (client side error) instead of server crash
                raise HTTPException(status_code=400, detail=detail_msg)

        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ DEBUG: Error reading source code: {e}")
            raise HTTPException(status_code=500, detail=f"Erro crítico ao ler código fonte: {str(e)}")

        # Replace placeholder with source code (from code_entries or files)
        full_source_code = source_info + all_source_code
        final_prompt = modified_prompt.replace("[INSERIR CÓDIGO AQUI]", full_source_code)
        print(f"DEBUG: Replaced placeholder with source code")
        print(f"DEBUG: Final prompt length: {len(final_prompt)}")

        # DEBUG: Check if we're reaching the prompt saving section
        print(f"DEBUG: About to save prompt - total_files_processed: {total_files_processed}")
        print(f"DEBUG: Prompt directory will be: {Path(__file__).parent.parent.parent.parent / 'prompts'}")

        # Save the final prompt to files for analysis
        try:
            from datetime import datetime

            # Create prompts directory if it doesn't exist
            prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
            print(f"DEBUG: Creating prompts directory at: {prompts_dir}")
            prompts_dir.mkdir(exist_ok=True)
            print(f"DEBUG: Prompts directory exists: {prompts_dir.exists()}")

            # Create latest prompt file (always overwritten with the most recent)
            latest_prompt_path = prompts_dir / "latest_prompt.txt"

            # Write the complete prompt to latest file (always the most recent)
            with open(latest_prompt_path, "w", encoding="utf-8") as f:
                f.write("="*80 + "\n")
                f.write(f"LTIMO PROMPT ENVIADO PARA LLM - {datetime.now().isoformat()}\n")
                f.write("="*80 + "\n\n")
                f.write(f"TAMANHO TOTAL: {len(final_prompt)} caracteres\n")
                f.write(f"ARQUIVOS PROCESSADOS: {total_files_processed}\n")
                f.write(f"CRITRIOS: {len(request.criteria_ids)}\n")
                f.write(f"USURIO: {current_user.username} (ID: {current_user.id})\n\n")
                f.write("="*80 + "\n")
                f.write("CONTEDO COMPLETO DO PROMPT:\n")
                f.write("="*80 + "\n\n")
                f.write(final_prompt)
                f.write("\n\n" + "="*80 + "\n")
                f.write("FIM DO PROMPT\n")
                f.write("="*80 + "\n")

            print(f"DEBUG: ltimo prompt salvo em: {latest_prompt_path}")

        except Exception as save_error:
            print(f"DEBUG: Erro ao salvar prompt em arquivo: {save_error}")

        # Log do prompt completo para debug
        print("\n" + "="*80)
        print("PROMPT FINAL ENVIADO PARA A LLM:")
        print("="*80)
        print(final_prompt[:1000] + "..." if len(final_prompt) > 1000 else final_prompt)
        print("="*80)
        print("FIM DO PROMPT")
        print("="*80 + "\n")

        # Force override max_tokens to prevent truncation
        forced_max_tokens = 32000  # Force 32000 tokens to ensure complete response

        # Increase timeout for LLM response to ensure complete analysis
        import time
        processing_start = time.time()
        try:
            llm_response = await llm_service.send_prompt(
                final_prompt,
                temperature=request.temperature,
                max_tokens=forced_max_tokens  # Force 32000 tokens to prevent truncation
            )
        except Exception as llm_error:
            print(f"ERROR: LLM service failed: {llm_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro na comunicao com o servio de LLM: {str(llm_error)}"
            )

        print("XXXXXXXXXX DEBUG: LLM response received XXXXXXXXXX")
        print(f"DEBUG: LLM response type: {type(llm_response)}")
        print(f"DEBUG: LLM response keys: {llm_response.keys() if isinstance(llm_response, dict) else 'Not a dict'}")
        print(f"DEBUG: Full LLM response: {llm_response}")

        llm_response_content = llm_response.get('response', llm_response.get('text', ''))
        print("YYYYYYYYYY DEBUG: Checking response content YYYYYYYYYY")
        print(f"DEBUG: LLM response content type: {type(llm_response_content)}")
        print(f"DEBUG: LLM response content length: {len(llm_response_content)}")
        print(f"DEBUG: LLM response['response'] preview: {llm_response_content[:200]}")
        print(f"DEBUG: Is response empty? {not llm_response_content}")
        print("ZZZZZZZZZ END LLM SERVICE DEBUG ZZZZZZZZZ")

        # Step 6.5: Save the raw response to a file for the "Last Response" tab
        try:
            from datetime import datetime
            prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
            latest_response_path = prompts_dir / "latest_response.txt"
            
            with open(latest_response_path, "w", encoding="utf-8") as f:
                f.write(llm_response_content)
            print(f"DEBUG: Última resposta salva em: {latest_response_path}")
        except Exception as save_error:
            print(f"DEBUG: Erro ao salvar resposta em arquivo: {save_error}")

        # Check if response is empty
        if not llm_response_content:
            print("ERROR: LLM response is empty!")
            extracted_content = {"criteria_results": {}, "raw_response": ""}
        else:
            # Step 7: Extract content from LLM response
            print(f"=== RAW LLM RESPONSE FOR DEBUG ===")
            print(f"Content length: {len(llm_response_content)}")
            print(f"=== END RAW LLM RESPONSE ===")

            try:
                # Improved extraction logic using the #FIM_ANALISE_CRITERIO# tag
                criteria_results = {}
                
                # Method 1: Try to split by the explicit tag we requested in the prompt
                if "#FIM_ANALISE_CRITERIO#" in llm_response_content:
                    print("DEBUG: Using #FIM_ANALISE_CRITERIO# for robust extraction")
                    import re
                    # Find criteria blocks
                    # Example format: ## Critério 1: Name\nContent...#FIM_ANALISE_CRITERIO#
                    blocks = re.split(r'#FIM_ANALISE_CRITERIO#', llm_response_content)
                    
                    for block in blocks:
                        # Extract criteria header and content from block
                        # Match "## Critério X: Name"
                        match = re.search(r'##\s*Crit[ée]rio\s*(\d+(?:\.\d+)*)\s*[:\-]?\s*(.+?)\n(.*?)$', block, re.DOTALL)
                        if match:
                            crit_id = match.group(1)
                            crit_name = match.group(2).strip()
                            crit_content = match.group(3).strip()
                            
                            criteria_results[f"criteria_{crit_id}"] = {
                                "name": crit_name,
                                "content": crit_content
                            }
                
                # Method 2: Fallback to regex if tags are missing or only some are present
                if not criteria_results or len(criteria_results) < len(request.criteria_ids):
                    print("DEBUG: Falling back to regex extraction (missing tags or incomplete)")
                    import re
                    # More flexible pattern that doesn't strictly require newline before ##
                    criteria_pattern = r'##\s*Crit[ée]rio\s*(\d+(?:\.\d+)*)\s*[:\-]?\s*(.+?)\n(.*?)(?=\s*##\s*Crit[ée]rio\s*\d+|\s*##\s*(?:Resultado|Recomendações)\s*(?:Geral|)|#FIM_ANALISE_CRITERIO#|#FIM#|$)'
                    matches = re.findall(criteria_pattern, llm_response_content, re.DOTALL)
                    
                    for match in matches:
                        crit_id = match[0]
                        if f"criteria_{crit_id}" not in criteria_results:
                            criteria_results[f"criteria_{crit_id}"] = {
                                "name": match[1].strip(),
                                "content": match[2].strip()
                            }

                extracted_content = {
                    "criteria_results": criteria_results,
                    "raw_response": llm_response_content.strip()
                }
            except Exception as extract_error:
                print(f"ERROR: Extraction failed: {extract_error}")
                extracted_content = {
                    "criteria_results": {},
                    "raw_response": llm_response_content
                }
            
            print(f"DEBUG: Extracted {len(extracted_content.get('criteria_results', {}))} criteria results")
            print(f"DEBUG: extracted_content keys: {extracted_content.keys() if isinstance(extracted_content, dict) else 'Not a dict'}")
            print(f"DEBUG: criteria_results in extracted_content: {extracted_content.get('criteria_results', {}) if isinstance(extracted_content, dict) else 'N/A'}")

            # DEBUG: Show criteria_results details
            if isinstance(extracted_content, dict) and 'criteria_results' in extracted_content:
                criteria_results = extracted_content['criteria_results']
                print(f"DEBUG: criteria_results type: {type(criteria_results)}")
                print(f"DEBUG: criteria_results content: {criteria_results}")
                print(f"DEBUG: criteria_results empty: {not criteria_results}")
                if isinstance(criteria_results, dict):
                    print(f"DEBUG: criteria_results keys: {list(criteria_results.keys())}")
                    for key, value in criteria_results.items():
                        print(f"DEBUG: {key}: {type(value)} - {str(value)[:100] if value else 'None'}")

            # Step 7.5: Map extracted criteria results to actual criteria IDs
            print(f"DEBUG: Starting criteria ID mapping...")
            print(f"DEBUG: Selected criteria: {selected_criteria}")
            print(f"DEBUG: Request criteria IDs: {request.criteria_ids}")

            # Create mapping from criteria name to criteria ID
            criteria_name_to_id = {}
            for criteria in selected_criteria:
                # criteria is a GeneralCriteria object with id and text attributes
                criteria_name_to_id[criteria.text.strip().lower()] = criteria.id
                print(f"DEBUG: Mapping '{criteria.text.strip().lower()}' to ID {criteria.id}")

            # Also create a mapping from the position in the request to the criteria ID
            position_to_id = {}
            for i, criteria_id_str in enumerate(request.criteria_ids):
                actual_id = int(criteria_id_str.replace("criteria_", ""))
                position_to_id[i] = actual_id
                print(f"DEBUG: Position {i} maps to criteria_{actual_id}")

            # Remap criteria_results to use actual criteria IDs instead of position-based keys
            remapped_criteria_results = {}

            # First pass: Try to map by name matching and position
            for extracted_key, result_data in extracted_content.get("criteria_results", {}).items():
                print(f"DEBUG: Processing extracted key: {extracted_key}, result: {result_data}")

                # Extract the position number from the key (criteria_1, criteria_2, etc.)
                key_position = None
                if extracted_key.startswith("criteria_"):
                    try:
                        key_position = int(extracted_key.replace("criteria_", "")) - 1  # Convert to 0-based index
                    except ValueError:
                        pass

                # Method 1: Try to map by position first (most reliable)
                if key_position is not None and key_position in position_to_id:
                    criteria_id = position_to_id[key_position]
                    # IMPORTANT: Always use the original criteria text from database
                    original_criteria = next((c for c in selected_criteria if c.id == criteria_id), None)
                    if original_criteria:
                        result_data["name"] = original_criteria.text  # Override LLM name with original
                        remapped_criteria_results[f"criteria_{criteria_id}"] = result_data
                        print(f"DEBUG: Mapped by position {key_position} to criteria_{criteria_id}, using original name: '{original_criteria.text}'")
                        continue

                # Method 2: Try to find matching criteria by name (fallback)
                result_name = result_data.get("name", "").strip().lower()
                print(f"DEBUG: Looking for criteria with name: '{result_name}'")

                # Try exact match first
                if result_name in criteria_name_to_id:
                    criteria_id = criteria_name_to_id[result_name]
                    # IMPORTANT: Always use the original criteria text from database
                    original_criteria = next((c for c in selected_criteria if c.id == criteria_id), None)
                    if original_criteria:
                        result_data["name"] = original_criteria.text  # Override LLM name with original
                        remapped_criteria_results[f"criteria_{criteria_id}"] = result_data
                        print(f"DEBUG: Found exact match - mapped to criteria_{criteria_id}, using original name: '{original_criteria.text}'")
                else:
                    # Try fuzzy matching
                    found_match = False
                    for criteria_text, candidate_id in criteria_name_to_id.items():
                        # Check if the result name contains the criteria text or vice versa
                        if (result_name in criteria_text or
                            criteria_text in result_name or
                            result_name.split(':')[0].strip() in criteria_text or
                            criteria_text.split(':')[0].strip() in result_name):
                            # IMPORTANT: Always use the original criteria text from database
                            original_criteria = next((c for c in selected_criteria if c.id == candidate_id), None)
                            if original_criteria:
                                result_data["name"] = original_criteria.text  # Override LLM name with original
                                remapped_criteria_results[f"criteria_{candidate_id}"] = result_data
                                print(f"DEBUG: Found fuzzy match - mapped '{result_name}' to criteria_{candidate_id}, using original name: '{original_criteria.text}'")
                                found_match = True
                                break

                    if not found_match:
                        # CRITICAL FIX: Never keep problematic names like "criteria_2"
                        # Always override with a clean name or use position-based mapping as final fallback
                        if key_position is not None and key_position < len(selected_criteria):
                            # Final fallback: use the criteria at this position
                            fallback_criteria = selected_criteria[key_position]
                            result_data["name"] = fallback_criteria.text
                            remapped_criteria_results[f"criteria_{fallback_criteria.id}"] = result_data
                            print(f"DEBUG: FINAL FALLBACK - Using position {key_position} to get criteria '{fallback_criteria.text}'")
                        else:
                            # Clean up problematic names
                            if result_name:
                                # Remove common problematic patterns
                                cleaned_name = result_name
                                for prefix in ['criteria_', 'critrio ', 'criterion ', '##']:
                                    if cleaned_name.lower().startswith(prefix):
                                        cleaned_name = cleaned_name[len(prefix):].strip()

                                # If still looks like a technical ID, use generic name
                                if cleaned_name.startswith('criteria_') or len(cleaned_name) < 3:
                                    result_data["name"] = "Critrio analisado"
                                else:
                                    result_data["name"] = cleaned_name.capitalize()
                            else:
                                result_data["name"] = "Critrio analisado"

                            remapped_criteria_results[extracted_key] = result_data
                            print(f"DEBUG: No match found for '{result_name}' (type: {type(result_name)}), using cleaned name: '{result_data.get('name')}'")

            # Remove fallback logic to prevent duplicate results
            # Only use results that were actually returned by the LLM analysis

            print(f"DEBUG: Final remapped criteria_results: {remapped_criteria_results}")
            extracted_content["criteria_results"] = remapped_criteria_results

        # Step 8: Save analysis results to database
        import json
        from datetime import datetime

        # Calculate processing time
        processing_duration = time.time() - processing_start
        processing_time_str = f"{processing_duration:.2f}s"

        print(f"DEBUG: Starting database save process for analysis: {request.analysis_name[:50]}...")
        print(f"DEBUG: Criteria results count: {len(extracted_content.get('criteria_results', {}))}")
        print(f"DEBUG: Processing time: {processing_time_str}")

        db_analysis_result = None
        try:
            # Create GeneralAnalysisResult record
            # Truncate analysis_name to 200 chars to match database schema String(200)
            safe_analysis_name = request.analysis_name[:197] + "..." if len(request.analysis_name) > 200 else request.analysis_name
            
            print(f"DEBUG: Creating GeneralAnalysisResult record with name: {safe_analysis_name}")
            
            db_analysis_result = GeneralAnalysisResultModel(
                analysis_name=safe_analysis_name,
                criteria_count=len(selected_criteria),
                user_id=current_user.id,
                criteria_results=extracted_content.get("criteria_results", {}),
                raw_response=extracted_content.get("raw_response", ""),
                model_used=llm_response.get("model", "claude-3-sonnet-20240229"),
                usage=llm_response.get("usage", {}),
                file_paths=json.dumps(request.file_paths),
                modified_prompt=modified_prompt,
                processing_time=processing_time_str
            )

            print("DEBUG: Adding record to session and flushing...")
            db.add(db_analysis_result)
            db.flush() # Flush to catch potential constraint errors before commit

            print("DEBUG: Committing transaction...")
            db.commit()

            db.commit()
            print("DEBUG: Commit successful.")
            db.refresh(db_analysis_result)

            print(f"DEBUG: Successfully saved analysis result to database with ID: {db_analysis_result.id}")

        except Exception as db_error:
            print(f"CRITICAL ERROR: Database save failed: {str(db_error)}")
            import traceback
            traceback.print_exc()
            db.rollback() # Always rollback on error
            db_analysis_result = None
            print("DEBUG: Rollback performed after database error.")

        # Step 9: Create analysis result structure
        result_data = {
            "success": True,
            "analysis_name": request.analysis_name,
            "criteria_count": len(selected_criteria),
            "timestamp": llm_response.get("timestamp", datetime.utcnow().isoformat()),
            "model_used": llm_response.get("model", "unknown-model"),
            "usage": llm_response.get("usage", {}),
            "criteria_results": extracted_content.get("criteria_results", {}),
            "raw_response": extracted_content.get("raw_response", ""),
            "debug_raw_llm_response": llm_response_content,  # For debugging
            "modified_prompt": modified_prompt,
            "file_paths": request.file_paths,
            "saved_to_db": True,
            "db_result_id": db_analysis_result.id
        }

        return result_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in analyze_selected_criteria: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing selected criteria: {str(e)}"
        )


@router.get("/results")
async def get_analysis_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get all analysis results for the current user"""
    try:
        # Get all analysis results for the user
        results = db.query(GeneralAnalysisResultModel).filter(
            GeneralAnalysisResultModel.user_id == current_user.id
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
    db: Session = Depends(get_db)
) -> Any:
    """Get a specific analysis result by ID"""
    try:
        # Get the analysis result
        result = db.query(GeneralAnalysisResultModel).filter(
            GeneralAnalysisResultModel.id == result_id,
            GeneralAnalysisResultModel.user_id == current_user.id
        ).first()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found"
            )

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
                "modified_prompt": result.modified_prompt
            }
        }

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


@router.put("/results/{analysis_id}/manual", response_model=GeneralAnalysisResult)
async def update_manual_result(
    analysis_id: int,
    result_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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

    # Return updated result
    return await get_general_analysis_result(analysis_id, current_user, db)



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
    """Get the latest LLM response"""
    try:
        from pathlib import Path

        # Path to the latest response file
        prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
        latest_response_path = prompts_dir / "latest_response.txt"

        # Check if the file exists
        if not latest_response_path.exists():
            return {
                "success": False,
                "message": "Nenhuma resposta da LLM encontrada. Execute uma anlise primeiro.",
                "response_content": None,
                "file_exists": False
            }

        # Read the response content
        with open(latest_response_path, "r", encoding="utf-8") as f:
            response_content = f.read()

        # Get file metadata
        import os
        file_stats = os.stat(latest_response_path)
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
            "message": "Resposta da LLM recuperada com sucesso",
            "response_content": response_content,
            "file_exists": True,
            "file_size": file_size,
            "modified_time": modified_time,
            "file_path": str(latest_response_path),
            "token_usage": token_usage
        }

    except Exception as e:
        print(f"DEBUG: Error reading latest response: {e}")
        return {
            "success": False,
            "message": f"Erro ao ler resposta da LLM: {str(e)}",
            "response_content": None,
            "file_exists": False,
            "token_usage": {}
        }

