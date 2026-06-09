import logging
from sqlalchemy.orm import Session
from app.models.file_path import FilePath
from app.models.uploaded_file import UploadedFile
from app.providers.storage import get_storage_provider

logger = logging.getLogger(__name__)

def cleanup_invalid_paths(db: Session):
    """
    Identifies and removes database records that point to non-existent physical files.
    This is useful for environments with ephemeral storage (like Render).
    """
    try:
        logger.info("🧹 Starting Self-Healing Database Cleanup...")
        storage = get_storage_provider()
        
        # 1. Query all FilePath records
        file_paths = db.query(FilePath).all()
        invalid_count = 0
        total_count = len(file_paths)
        
        for fp in file_paths:
            file_exists = False
            
            # Find the corresponding uploaded file record to get the storage path
            uploaded_file = db.query(UploadedFile).filter(
                (UploadedFile.relative_path == fp.full_path) | 
                (UploadedFile.original_name == fp.file_name)
            ).first()
            
            # Possible locations to check
            possible_paths = []
            if fp.full_path:
                possible_paths.extend([
                    fp.full_path,
                    f"uploads/{fp.full_path}",
                    f"/app/uploads/{fp.full_path}"
                ])
                
            if uploaded_file and uploaded_file.storage_path:
                possible_paths.append(uploaded_file.storage_path)
            
            # Verify if any of the possible paths exist
            for path_str in possible_paths:
                if path_str and storage.path_exists(path_str):
                    file_exists = True
                    break
            
            if not file_exists:
                # File is missing on disk - perform cleanup
                logger.warning(f"🚨 Orphan record found: {fp.file_id} ({fp.full_path}). Deleting...")
                
                # Delete any associated UploadedFile record
                if uploaded_file:
                    db.delete(uploaded_file)
                
                # Delete the FilePath record
                db.delete(fp)
                invalid_count += 1
        
        if invalid_count > 0:
            db.commit()
            logger.info(f"✨ Cleanup complete: {invalid_count} orphan records removed out of {total_count}.")
        else:
            logger.info(f"✅ Database is clean. No orphan records found (Checked {total_count} files).")
            
    except Exception as e:
        logger.error(f"❌ Error during Self-Healing Cleanup: {str(e)}")
        db.rollback()
