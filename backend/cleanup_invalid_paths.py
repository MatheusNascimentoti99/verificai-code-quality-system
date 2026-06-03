#!/usr/bin/env python3
"""
Script para limpar file paths inválidos do banco de dados
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.database import get_db
from app.models.file_path import FilePath
from app.models.uploaded_file import UploadedFile
from app.providers.storage import get_storage_provider

def cleanup_invalid_paths():
    """Remove file paths que não correspondem a arquivos reais"""

    # Database connection
    DATABASE_URL = "postgresql://verificai:verificai123@postgres:5432/verificai"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print("🔍 Iniciando limpeza de file paths inválidos...")
        storage = get_storage_provider()

        # Buscar todos os file paths
        all_paths = db.query(FilePath).all()
        print(f"📊 Encontrados {len(all_paths)} file paths no banco de dados")

        invalid_count = 0
        valid_count = 0

        for fp in all_paths:
            file_exists = False

            possible_paths = [fp.full_path]

            uploaded_file = db.query(UploadedFile).filter(
                (UploadedFile.relative_path == fp.full_path) |
                (UploadedFile.original_name == fp.file_name)
            ).first()

            if uploaded_file and uploaded_file.storage_path:
                possible_paths.append(uploaded_file.storage_path)

            for path in possible_paths:
                if path and storage.path_exists(path):
                    file_exists = True
                    break

            if not file_exists:
                print(f"❌ Path inválido: {fp.full_path} (ID: {fp.file_id})")
                db.delete(fp)
                invalid_count += 1
            else:
                print(f"✅ Path válido: {fp.full_path}")
                valid_count += 1

        # Commit das alterações
        if invalid_count > 0:
            db.commit()
            print(f"🧹 Limpeza concluída! Removidos {invalid_count} paths inválidos")
            print(f"✅ Mantidos {valid_count} paths válidos")
        else:
            print("✅ Todos os paths são válidos!")

    except Exception as e:
        print(f"❌ Erro durante limpeza: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_invalid_paths()