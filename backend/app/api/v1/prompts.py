"""
Prompt management endpoints for VerificAI Backend
Updated with config and backup endpoints
Real persistence implemented for prompt configurations
"""

from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, CommonQueryParams, get_pagination_params
from app.models.user import User
from app.models.prompt import Prompt, PromptConfiguration, PromptCategory, PromptStatus
from app.schemas.prompt import (
    PromptCreate, PromptUpdate, PromptResponse, PromptListResponse,
    PromptSearchFilters, PromptTestRequest, PromptTestResponse,
    PromptCloneRequest, PromptValidationResult, PromptConfigsUpdate
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


# Force reload 3 - test file modification again
@router.get("/config", response_model=dict)
def get_prompt_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get prompt configuration for frontend"""
    # Default configuration
    default_config = {
        "general": {
            "id": "general",
            "name": "General Analysis",
            "type": "general",
            "description": "General purpose code analysis prompt",
            "content": "Analyze the following code for quality, bugs, and improvements:\n\n```{language}\n{code}\n```\n\nProvide a comprehensive analysis including:\n1. Code quality issues\n2. Potential bugs\n3. Performance improvements\n4. Security considerations\n5. Best practices violations",
            "isActive": True,
            "isDefault": True,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z"
        },
        "architectural": {
            "id": "architectural",
            "name": "Architectural Analysis",
            "type": "architectural",
            "description": "Architecture-focused code analysis prompt",
            "content": "Analyze the following code from an architectural perspective:\n\n```{language}\n{code}\n```\n\nFocus on:\n1. Design patterns usage\n2. Architectural principles compliance\n3. Scalability considerations\n4. Maintainability aspects\n5. System design recommendations",
            "isActive": True,
            "isDefault": True,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z"
        },
        "business": {
            "id": "business",
            "name": "Business Logic Analysis",
            "type": "business",
            "description": "Business logic focused code analysis prompt",
            "content": "Analyze the following code focusing on business logic:\n\n```{language}\n{code}\n```\n\nEvaluate:\n1. Business rule implementation\n2. Domain-specific patterns\n3. Business requirement compliance\n4. Process flow efficiency\n5. Business value optimization",
            "isActive": True,
            "isDefault": True,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z"
        }
    }

    # Try to load saved configuration from database - get most recent configs from any user (shared access)
    try:
        user_configs = db.query(PromptConfiguration).filter(
            PromptConfiguration.is_active == True
        ).order_by(PromptConfiguration.updated_at.desc()).all()

        # Get the most recent configuration for each type
        latest_configs = {}
        for config in user_configs:
            config_type = config.prompt_type.value
            if config_type not in latest_configs:
                latest_configs[config_type] = config

        # Override defaults with latest saved configurations
        if latest_configs:
            for config_type, config in latest_configs.items():
                if config_type in default_config:
                    config_data = {
                        "id": config_type,
                        "name": config.name,
                        "type": config_type,
                        "description": config.description,
                        "content": config.content,
                        "isActive": config.is_active,
                        "isDefault": config.is_default,
                        "settings": config.settings or {},
                        "createdAt": config.created_at.isoformat(),
                        "updatedAt": config.updated_at.isoformat()
                    }
                    default_config[config_type] = config_data

        return default_config
    except Exception as e:
        # If database error, return defaults
        return default_config


@router.post("/backup", response_model=dict)
def create_prompt_backup(
    prompt_config: PromptConfigsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Save prompt configuration to database (real persistence)"""
    print("DEBUG: New create_prompt_backup function called!")
    print(f"DEBUG: User ID: {current_user.id}")
    print(f"DEBUG: Prompt config keys: {list(prompt_config.keys())}")

    try:
        # Save each prompt configuration in the database
        saved_configs = []

        # Convert Pydantic model to dict
        config_dict = prompt_config.model_dump(exclude_unset=True)
        for config_key, config_data in config_dict.items():
            print(f"DEBUG: Processing config key: {config_key}")
            # Check if configuration already exists
            existing_config = db.query(PromptConfiguration).filter(
                PromptConfiguration.user_id == current_user.id,
                PromptConfiguration.prompt_type == config_key,
                PromptConfiguration.name == f"{config_key}_config"
            ).first()

            if existing_config:
                print(f"DEBUG: Updating existing config for {config_key}")
                # Update existing configuration
                existing_config.content = config_data.get('content', '')
                existing_config.settings = config_data.get('settings', {})
                existing_config.description = config_data.get('description', f'{config_key} configuration')
                existing_config.is_active = True
                existing_config.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(existing_config)
                saved_configs.append(existing_config)
            else:
                print(f"DEBUG: Creating new config for {config_key}")
                # Create new configuration
                new_config = PromptConfiguration(
                    user_id=current_user.id,
                    prompt_type=config_key,
                    name=f"{config_key}_config",
                    description=config_data.get('description', f'{config_key} configuration'),
                    content=config_data.get('content', ''),
                    settings=config_data.get('settings', {}),
                    is_active=True
                )
                db.add(new_config)
                db.commit()
                db.refresh(new_config)
                saved_configs.append(new_config)

        print(f"DEBUG: Saved {len(saved_configs)} configurations")
        result = {
            "success": True,
            "message": "Prompt configuration saved successfully (NEW VERSION)",
            "timestamp": datetime.utcnow().isoformat(),
            "saved_by": current_user.username,
            "saved_configs": len(saved_configs)
        }
        print(f"DEBUG: Returning result: {result}")
        return result
    except Exception as e:
        print(f"DEBUG: Error occurred: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return {
            "success": False,
            "message": f"Failed to save configuration: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "saved_by": current_user.username
        }


@router.post("/save", response_model=dict)
def save_prompt_configuration(
    prompt_config: PromptConfigsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Save prompt configuration"""
    try:
        # Save each prompt configuration in the database
        saved_configs = []

        # Convert Pydantic model to dict
        config_dict = prompt_config.model_dump(exclude_unset=True)
        for config_key, config_data in config_dict.items():
            # Check if configuration already exists
            existing_config = db.query(PromptConfiguration).filter(
                PromptConfiguration.user_id == current_user.id,
                PromptConfiguration.prompt_type == config_key,
                PromptConfiguration.name == f"{config_key}_config"
            ).first()

            if existing_config:
                # Update existing configuration
                existing_config.content = config_data.get('content', '')
                existing_config.settings = config_data.get('settings', {})
                existing_config.description = config_data.get('description', f'{config_key} configuration')
                existing_config.is_active = True
                existing_config.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(existing_config)
                saved_configs.append(existing_config)
            else:
                # Create new configuration
                new_config = PromptConfiguration(
                    user_id=current_user.id,
                    prompt_type=config_key,
                    name=f"{config_key}_config",
                    description=config_data.get('description', f'{config_key} configuration'),
                    content=config_data.get('content', ''),
                    settings=config_data.get('settings', {}),
                    is_active=True
                )
                db.add(new_config)
                db.commit()
                db.refresh(new_config)
                saved_configs.append(new_config)

        return {
            "success": True,
            "message": "Prompt configuration saved successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "saved_by": current_user.username,
            "saved_configs": len(saved_configs)
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"Failed to save configuration: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "saved_by": current_user.username
        }






@router.post("/", response_model=PromptResponse)
def create_prompt(
    prompt_data: PromptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create a new prompt"""
    prompt = Prompt(**prompt_data.model_dump(), author_id=current_user.id)
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    return prompt


@router.get("/", response_model=PaginatedResponse[PromptResponse])
def list_prompts(
    params: CommonQueryParams = Depends(),
    filters: PromptSearchFilters = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """List prompts with filtering and pagination"""
    query = db.query(Prompt)

    # Apply filters
    if filters.category:
        query = query.filter(Prompt.category == filters.category)
    if filters.status:
        query = query.filter(Prompt.status == filters.status)
    if filters.is_public is not None:
        query = query.filter(Prompt.is_public == filters.is_public)
    if filters.is_featured is not None:
        query = query.filter(Prompt.is_featured == filters.is_featured)
    if filters.author_id:
        query = query.filter(Prompt.author_id == filters.author_id)
    if filters.supported_language:
        # Simple contains check - in production, use JSON operations
        query = query.filter(Prompt.supported_languages.contains(filters.supported_language))
    if filters.supported_file_type:
        query = query.filter(Prompt.supported_file_types.contains(filters.supported_file_type))
    if filters.search:
        query = query.filter(
            Prompt.name.contains(filters.search) |
            Prompt.description.contains(filters.search)
        )

    # Filter by visibility: users can see their own prompts + public prompts
    # Admins can see all prompts
    if not current_user.is_admin:
        query = query.filter(
            (Prompt.author_id == current_user.id) |
            (Prompt.is_public == True)
        )

    # Get total count
    total = query.count()

    # Apply sorting
    if params.sort_by:
        sort_column = getattr(Prompt, params.sort_by, None)
        if sort_column:
            if params.sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(Prompt.created_at.desc())

    # Apply pagination
    prompts = query.offset(params.skip).limit(params.limit).all()

    return PaginatedResponse(
        items=prompts,
        total=total,
        skip=params.skip,
        limit=params.limit,
        pages=(total + params.limit - 1) // params.limit,
        current_page=(params.skip // params.limit) + 1,
        has_next=params.skip + params.limit < total,
        has_prev=params.skip > 0
    )




@router.get("/{prompt_id}", response_model=PromptResponse)
def get_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get prompt by ID"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Check permissions
    if not prompt.is_public and prompt.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return prompt


@router.put("/{prompt_id}", response_model=PromptResponse)
def update_prompt(
    prompt_id: int,
    prompt_data: PromptUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update prompt"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Check permissions
    if prompt.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update fields
    for field, value in prompt_data.model_dump(exclude_unset=True).items():
        setattr(prompt, field, value)

    db.commit()
    db.refresh(prompt)

    return prompt


@router.delete("/{prompt_id}", response_model=dict)
def delete_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete prompt"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Check permissions
    if prompt.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    db.delete(prompt)
    db.commit()

    return {"message": "Prompt deleted successfully"}


@router.post("/{prompt_id}/test", response_model=PromptTestResponse)
def test_prompt(
    prompt_id: int,
    test_data: PromptTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Test prompt with sample code"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Check permissions
    if not prompt.is_public and prompt.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # TODO: Implement actual testing logic
    # This is a placeholder response
    return PromptTestResponse(
        success=True,
        response="Test response - this is a placeholder",
        tokens_used=100,
        processing_time=2.5,
        cost_estimate=0.01
    )


@router.post("/{prompt_id}/clone", response_model=PromptResponse)
def clone_prompt(
    prompt_id: int,
    clone_data: PromptCloneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Clone prompt"""
    original_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not original_prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Check permissions
    if not original_prompt.is_public and original_prompt.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Create clone
    new_prompt = Prompt(
        name=clone_data.new_name,
        description=clone_data.new_description or original_prompt.description,
        category=original_prompt.category,
        system_prompt=original_prompt.system_prompt,
        user_prompt_template=original_prompt.user_prompt_template,
        output_format_instructions=original_prompt.output_format_instructions,
        temperature=original_prompt.temperature,
        max_tokens=original_prompt.max_tokens,
        model_name=original_prompt.model_name,
        tags=original_prompt.tags,
        supported_languages=original_prompt.supported_languages,
        supported_file_types=original_prompt.supported_file_types,
        author_id=current_user.id
    )

    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)

    return new_prompt


@router.post("/{prompt_id}/validate", response_model=PromptValidationResult)
def validate_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Validate prompt"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Check permissions
    if prompt.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # TODO: Implement actual validation logic
    # This is a placeholder response
    return PromptValidationResult(
        is_valid=True,
        errors=[],
        warnings=["This is a placeholder validation"],
        suggestions=["Consider adding more specific tags"]
    )


@router.post("/{prompt_id}/publish", response_model=PromptResponse)
def publish_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Publish prompt (make public)"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Check permissions
    if prompt.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    prompt.is_public = True
    prompt.status = PromptStatus.ACTIVE
    db.commit()
    db.refresh(prompt)

    return prompt


@router.post("/{prompt_id}/unpublish", response_model=PromptResponse)
def unpublish_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Unpublish prompt (make private)"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Check permissions
    if prompt.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    prompt.is_public = False
    db.commit()
    db.refresh(prompt)

    return prompt




@router.post("/import", response_model=PromptResponse)
def import_prompt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Import prompt from file"""
    # TODO: Implement actual import logic
    # This is a placeholder response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Import functionality not yet implemented"
    )


@router.get("/{prompt_id}/export")
def export_prompt(
    prompt_id: int,
    format: str = "json",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Export prompt"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Check permissions
    if not prompt.is_public and prompt.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # TODO: Implement actual export logic
    # This is a placeholder response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Export functionality not yet implemented"
    )