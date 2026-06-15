"""
API endpoints for file path management
"""

import logging
from typing import List, Any
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file_path import FilePath
from app.providers.storage import get_storage_provider
from app.schemas.file_path import (
    FilePathCreate,
    FilePathResponse,
    FilePathBulkCreate,
    FilePathBulkResponse,
    FilePathListResponse,
    FilePathUpdate,
    FilePathDeleteRequest
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/public")
async def get_public_file_paths(db: Session = Depends(get_db)):
    """Get file paths for public access - no authentication required"""
    try:
        # Get ALL file paths without user filtering - NO LIMIT
        file_paths = db.query(FilePath).order_by(desc(FilePath.created_at)).all()

        # Extract objects with both path and ID for proper frontend synchronization
        paths_data = [
            {"full_path": fp.full_path, "file_id": fp.file_id} 
            for fp in file_paths if fp.full_path
        ]

        logger.info(f"🔥🔥🔥 Public endpoint returning {len(paths_data)} file paths - ALL FILES - NO LIMIT 🔥🔥🔥")

        return {
            "file_paths": paths_data,
            "total_count": len(paths_data),
            "message": f"Found {len(paths_data)} file paths - ALL FILES"
        }

    except Exception as e:
        logger.error(f"Error in public endpoint: {str(e)}")
        return {"file_paths": [], "total_count": 0, "message": "Error occurred"}


@router.post("/sync-uploaded")
async def sync_uploaded_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Sync uploaded files to file_paths table for display"""
    try:
        from app.models.uploaded_file import UploadedFile, FileStatus

        # Get all uploaded files for this user that don't have corresponding file_paths
        uploaded_files = db.query(UploadedFile).filter(
            UploadedFile.user_id == current_user.id,
            UploadedFile.status == FileStatus.COMPLETED
        ).all()

        synced_count = 0

        for uploaded_file in uploaded_files:
            # Check if file_path already exists for this uploaded file
            existing_path = db.query(FilePath).filter(
                FilePath.user_id == current_user.id,
                or_(
                    FilePath.full_path == uploaded_file.relative_path,
                    FilePath.full_path == uploaded_file.original_name
                )
            ).first()

            if not existing_path:
                # Create file_path record for uploaded file
                file_path = FilePath(
                    file_id=f"path_{uuid4().hex}",
                    full_path=uploaded_file.relative_path or uploaded_file.original_name,
                    file_name=uploaded_file.original_name,
                    file_extension=uploaded_file.file_extension or "",
                    folder_path=uploaded_file.relative_path.split('/')[0] if uploaded_file.relative_path else "",
                    file_size=uploaded_file.file_size,
                    is_processed=False,
                    user_id=current_user.id,
                    is_public=False,
                    access_level="private"
                )
                db.add(file_path)
                synced_count += 1

        db.commit()

        return {
            "success": True,
            "synced_count": synced_count,
            "message": f"Successfully synced {synced_count} files"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing uploaded files: {str(e)}"
        )


@router.get("/dev-paths")
async def get_dev_file_paths(db: Session = Depends(get_db)):
    """Get file paths for development - simple endpoint without authentication"""
    try:
        # Get all file paths - NO LIMIT
        file_paths = db.query(FilePath).order_by(desc(FilePath.created_at)).all()
        logger.info(f"DEBUG: Total file_paths queried: {len(file_paths)}")

        # Extract just the full paths for simplicity
        paths = [fp.full_path for fp in file_paths if fp.full_path]
        logger.info(f"DEBUG: Paths with non-null full_path: {len(paths)}")

        # Returns ALL FILES with NO LIMIT
        logger.info(f"[INFO] dev-paths endpoint returning {len(paths)} file paths - ALL FILES - NO LIMIT")

        return {
            "file_paths": paths,
            "total_count": len(paths),
            "message": f"Found {len(paths)} file paths - VERSION 2.0"
        }

    except Exception as e:
        logger.error(f"Error in dev-paths endpoint: {str(e)}")
        return {"file_paths": [], "total_count": 0, "message": "Error occurred"}


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is working"""
    return {"message": "File paths router is working!"}

@router.post("/cleanup-invalid")
async def cleanup_invalid_paths_endpoint(
    db: Session = Depends(get_db)
):
    """Remove file paths lacking physical files (useful for Render ephemeral disk resets)"""
    try:
        from app.models.uploaded_file import UploadedFile
        import os
        from pathlib import Path
        
        all_paths = db.query(FilePath).all()
        invalid_count = 0
        valid_count = 0
        errors = []
        
        for fp in all_paths:
            file_exists = False
            
            # Check uploaded files table first for physical path mapping
            uploaded = db.query(UploadedFile).filter(
                (UploadedFile.relative_path == fp.full_path) | 
                (UploadedFile.original_name == fp.file_name)
            ).order_by(UploadedFile.created_at.desc()).first()
            
            possible_paths = [
                fp.full_path,
                f"uploads/{fp.full_path}",
                f"/app/uploads/{fp.full_path}",
                f"/app/{fp.full_path}",
            ]
            
            if uploaded and uploaded.storage_path:
                possible_paths.append(uploaded.storage_path)
                
            for path in possible_paths:
                if path and Path(path).exists():
                    file_exists = True
                    break
                    
            if not file_exists:
                try:
                    # Clear uploaded file associations first if any
                    if uploaded:
                        db.delete(uploaded)
                    db.delete(fp)
                    invalid_count += 1
                except Exception as del_err:
                    db.rollback()
                    errors.append(f"Could not delete {fp.file_id}: {str(del_err)}")
            else:
                valid_count += 1
                
        if invalid_count > 0:
            db.commit()
            
        return {
            "success": True, 
            "removed_count": invalid_count, 
            "kept_count": valid_count,
            "errors": errors
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=FilePathBulkResponse)
async def create_file_paths_bulk(
    file_paths_data: FilePathBulkCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create multiple file paths at once"""
    try:
        created_paths = []
        errors = []

        for file_path_data in file_paths_data.file_paths:
            try:
                # Check if file path already exists
                existing_path = db.query(FilePath).filter(
                    FilePath.full_path == file_path_data.full_path,
                    FilePath.user_id == current_user.id
                ).first()

                if existing_path:
                    errors.append(f"File path already exists: {file_path_data.full_path}")
                    continue

                # Create new file path
                db_file_path = FilePath(
                    **file_path_data.model_dump(),
                    user_id=current_user.id
                )
                db.add(db_file_path)
                db.commit()
                db.refresh(db_file_path)
                created_paths.append(db_file_path)

                logger.info(f"File path created: {file_path_data.full_path} by user {current_user.id}")

            except Exception as e:
                logger.error(f"Error creating file path {file_path_data.full_path}: {str(e)}")
                errors.append(f"Failed to create path: {file_path_data.full_path} - {str(e)}")
                db.rollback()

        return FilePathBulkResponse(
            created_count=len(created_paths),
            file_paths=created_paths,
            errors=errors
        )

    except Exception as e:
        logger.error(f"Error in bulk file path creation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=FilePathResponse)
async def create_file_path(
    file_path_data: FilePathCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a single file path"""
    try:
        # Check if file path already exists
        existing_path = db.query(FilePath).filter(
            FilePath.full_path == file_path_data.full_path,
            FilePath.user_id == current_user.id
        ).first()

        if existing_path:
            raise HTTPException(status_code=400, detail="File path already exists")

        # Create new file path
        db_file_path = FilePath(
            **file_path_data.model_dump(),
            user_id=current_user.id
        )
        db.add(db_file_path)
        db.commit()
        db.refresh(db_file_path)

        logger.info(f"File path created: {file_path_data.full_path} by user {current_user.id}")

        return db_file_path

    except Exception as e:
        logger.error(f"Error creating file path: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=FilePathListResponse)
async def get_file_paths(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str = Query(None, description="Search in file names"),
    extension: str = Query(None, description="Filter by file extension"),
    folder: str = Query(None, description="Filter by folder path"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file paths with pagination and filtering"""
    try:
        # Build query - get file paths only for current user
        query = db.query(FilePath).filter(FilePath.user_id == current_user.id)

        # Apply filters
        if search:
            query = query.filter(FilePath.file_name.contains(search))
        if extension:
            query = query.filter(FilePath.file_extension == extension)
        if folder:
            query = query.filter(FilePath.folder_path.contains(folder))

        # Get total count
        total_count = query.count()

        # Calculate total pages
        total_pages = (total_count + per_page - 1) // per_page

        # Get paginated results
        file_paths = query.order_by(desc(FilePath.created_at))\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()

        return FilePathListResponse(
            file_paths=file_paths,
            total_count=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error getting file paths: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{file_id}", response_model=FilePathResponse)
async def get_file_path(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific file path by ID"""
    try:
        file_path = db.query(FilePath).filter(
            FilePath.file_id == file_id,
            FilePath.user_id == current_user.id
        ).first()

        if not file_path:
            raise HTTPException(status_code=404, detail="File path not found")

        return file_path

    except Exception as e:
        logger.error(f"Error getting file path {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{file_id}", response_model=FilePathResponse)
async def update_file_path(
    file_id: str,
    file_path_data: FilePathUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a file path"""
    try:
        file_path = db.query(FilePath).filter(
            FilePath.file_id == file_id,
            FilePath.user_id == current_user.id
        ).first()

        if not file_path:
            raise HTTPException(status_code=404, detail="File path not found")

        # Update fields
        update_data = file_path_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(file_path, field, value)

        file_path.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(file_path)

        logger.info(f"File path updated: {file_id} by user {current_user.id}")

        return file_path

    except Exception as e:
        logger.error(f"Error updating file path {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/all")
async def delete_all_file_paths(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all file paths for current user"""
    try:
        logger.info(f"Starting delete all file paths for user {current_user.id}")

        # Get all file paths for this user first
        file_paths = db.query(FilePath).filter(
            FilePath.user_id == current_user.id
        ).all()

        logger.info(f"Found {len(file_paths)} file paths to delete for user {current_user.id}")

        if len(file_paths) == 0:
            return {
                "message": "No file paths found to delete",
                "deleted_count": 0
            }

        # Delete one by one to identify any problematic records
        deleted_count = 0
        for file_path in file_paths:
            try:
                db.delete(file_path)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting file path {file_path.file_id}: {str(e)}")
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Error deleting file path {file_path.file_id}")

        db.commit()

        logger.info(f"Successfully deleted {deleted_count} file paths for user {current_user.id}")

        return {
            "message": f"Successfully deleted {deleted_count} file paths",
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(f"Error in delete all file paths: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{file_id}")
async def delete_file_path(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a file path and its physical file"""
    try:
        from app.models.uploaded_file import UploadedFile
        storage = get_storage_provider()

        file_path = db.query(FilePath).filter(
            FilePath.file_id == file_id,
            FilePath.user_id == current_user.id
        ).first()

        if not file_path:
            raise HTTPException(status_code=404, detail="File path not found")

        deleted_physical_files = 0
        errors = []

        # Look for corresponding uploaded files with matching paths
        uploaded_files = db.query(UploadedFile).filter(
            UploadedFile.user_id == current_user.id,
            or_(
                UploadedFile.relative_path == file_path.full_path,
                UploadedFile.original_name == file_path.file_name
            )
        ).all()

        # Delete physical files
        for uploaded_file in uploaded_files:
            if uploaded_file.storage_path:
                try:
                    await storage.delete(uploaded_file.storage_path)
                    deleted_physical_files += 1
                    logger.info(f"Deleted physical file: {uploaded_file.storage_path}")
                except Exception as e:
                    error_msg = f"Failed to delete physical file {uploaded_file.storage_path}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Delete the uploaded file record from database
            db.delete(uploaded_file)

        # Delete the file path record from database
        db.delete(file_path)
        db.commit()

        logger.info(f"File path deleted: {file_id} by user {current_user.id}")

        return {
            "message": f"File path deleted successfully. Deleted {deleted_physical_files} physical file(s).",
            "deleted_physical_files": deleted_physical_files,
            "errors": errors
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file path {file_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/")
async def delete_file_paths_bulk(
    file_ids: List[str] = Body(default=[]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete multiple file paths and their physical files"""
    try:
        if len(file_ids) == 0:
            raise HTTPException(status_code=400, detail="No file IDs provided. Use /all to delete all.")

        from app.models.uploaded_file import UploadedFile
        storage = get_storage_provider()

        # Handle file_id format mismatch: frontend might send 'file_x' instead of 'path_file_x'
        normalized_ids = []
        for fid in file_ids:
            if fid.startswith("path_"):
                normalized_ids.append(fid)
                normalized_ids.append(fid.replace("path_", "", 1))
            else:
                normalized_ids.append(fid)
                normalized_ids.append(f"path_{fid}")

        # Get file paths before deletion to know which physical files to delete
        file_paths_to_delete = db.query(FilePath).filter(
            FilePath.file_id.in_(normalized_ids),
            FilePath.user_id == current_user.id
        ).all()

        deleted_physical_files = 0
        deleted_db_records = 0
        errors = []

        # For each file path, find and delete the corresponding physical file
        for file_path in file_paths_to_delete:
            try:
                # Look for corresponding uploaded files with matching paths
                uploaded_files = db.query(UploadedFile).filter(
                    UploadedFile.user_id == current_user.id,
                    or_(
                        UploadedFile.relative_path == file_path.full_path,
                        UploadedFile.original_name == file_path.file_name
                    )
                ).all()

                # Delete physical files
                for uploaded_file in uploaded_files:
                    if uploaded_file.storage_path:
                        try:
                            await storage.delete(uploaded_file.storage_path)
                            deleted_physical_files += 1
                            logger.info(f"Deleted physical file: {uploaded_file.storage_path}")
                        except Exception as e:
                            error_msg = f"Failed to delete physical file {uploaded_file.storage_path}: {str(e)}"
                            logger.error(error_msg)
                            errors.append(error_msg)

                    # Delete the uploaded file record from database
                    db.delete(uploaded_file)

            except Exception as e:
                error_msg = f"Error processing file path {file_path.file_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Delete the file path records from database
        deleted_db_records = db.query(FilePath).filter(
            FilePath.file_id.in_(normalized_ids),
            FilePath.user_id == current_user.id
        ).delete(synchronize_session=False)

        db.commit()

        return {
            "message": f"Successfully deleted {deleted_db_records} file paths and {deleted_physical_files} physical files",
            "deleted_db_records": deleted_db_records,
            "deleted_physical_files": deleted_physical_files,
            "errors": errors
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk file path deletion: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/summary")
async def get_file_paths_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get summary statistics for file paths"""
    try:
        # Get total count
        total_count = db.query(FilePath).filter(
            FilePath.user_id == current_user.id
        ).count()

        # Get unique extensions
        extensions = db.query(
            FilePath.file_extension,
            func.count(FilePath.file_extension).label('count')
        ).filter(
            FilePath.user_id == current_user.id,
            FilePath.file_extension.isnot(None)
        ).group_by(FilePath.file_extension).all()

        # Get unique folders
        folders = db.query(
            FilePath.folder_path,
            func.count(FilePath.folder_path).label('count')
        ).filter(
            FilePath.user_id == current_user.id
        ).group_by(FilePath.folder_path).all()

        # Get total size
        total_size = db.query(
            func.sum(FilePath.file_size)
        ).filter(
            FilePath.user_id == current_user.id,
            FilePath.file_size.isnot(None)
        ).scalar() or 0

        return {
            "total_count": total_count,
            "total_size": total_size,
            "unique_extensions": [
                {"extension": ext.file_extension, "count": ext.count}
                for ext in extensions
            ],
            "unique_folders": [
                {"folder": folder.folder_path, "count": folder.count}
                for folder in folders
            ]
        }

    except Exception as e:
        logger.error(f"Error getting file paths summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


