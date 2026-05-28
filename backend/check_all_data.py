#!/usr/bin/env python3
"""
Script para verificar todos os dados no banco de dados
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.prompt import Prompt, PromptConfiguration, GeneralCriteria, GeneralAnalysisResult
from app.models.analysis import Analysis
from app.models.uploaded_file import UploadedFile
from app.models.file_path import FilePath
from app.models.code_entry import CodeEntry

def check_all_data():
    """Verifica todos os dados no banco de dados"""
    db = SessionLocal()

    try:
        print("=== VERIFICACAO COMPLETA DE DADOS ===")
        print()

        # Verificar usuários
        users = db.query(User).all()
        print(f"USUARIOS: {len(users)}")
        for user in users:
            print(f"  - {user.username} ({user.email}) - {user.role}")
        print()

        # Verificar prompts
        prompts = db.query(Prompt).all()
        print(f"PROMPTS: {len(prompts)}")
        for prompt in prompts:
            author = db.query(User).filter(User.id == prompt.user_id).first()
            author_name = author.username if author else "Unknown"
            print(f"  - ID {prompt.id}: {prompt.name} (por {author_name}) - {prompt.type}")
        print()

        # Verificar configurações de prompts
        prompt_configs = db.query(PromptConfiguration).all()
        print(f"CONFIGURACOES DE PROMPTS: {len(prompt_configs)}")
        for config in prompt_configs:
            author = db.query(User).filter(User.id == config.user_id).first()
            author_name = author.username if author else "Unknown"
            print(f"  - ID {config.id}: {config.name} (por {author_name}) - {config.prompt_type}")
        print()

        # Verificar critérios gerais
        criteria = db.query(GeneralCriteria).all()
        print(f"CRITERIOS GERAIS: {len(criteria)}")
        for criterion in criteria:
            author = db.query(User).filter(User.id == criterion.user_id).first()
            author_name = author.username if author else "Unknown"
            print(f"  - ID {criterion.id}: {criterion.text[:50]}... (por {author_name})")
        print()

        # Verificar análises
        analyses = db.query(Analysis).all()
        print(f"ANALISES: {len(analyses)}")
        for analysis in analyses:
            author = db.query(User).filter(User.id == analysis.user_id).first()
            author_name = author.username if author else "Unknown"
            print(f"  - ID {analysis.id}: {analysis.name} (por {author_name}) - {analysis.status}")
        print()

        # Verificar uploads
        uploads = db.query(UploadedFile).all()
        print(f"UPLOADS: {len(uploads)}")
        for upload in uploads:
            author = db.query(User).filter(User.id == upload.user_id).first()
            author_name = author.username if author else "Unknown"
            # FIX: UploadedFile model uses original_name, not filename
            print(f"  - ID {upload.id}: {upload.original_name} (por {author_name}) - {upload.status}")
        print()

        # Verificar Code Entries
        code_entries = db.query(CodeEntry).all()
        print(f"CODE ENTRIES (PASTED CODE): {len(code_entries)}")
        for entry in code_entries:
            author = db.query(User).filter(User.id == entry.user_id).first()
            author_name = author.username if author else "Unknown"
            print(f"  - ID {entry.id}: {entry.title} (por {author_name}) - {entry.lines_count} linhas")
        print()

        # Verificar Resultados de Análise Geral
        gen_results = db.query(GeneralAnalysisResult).all()
        print(f"RESULTADOS DE ANÁLISE GERAL: {len(gen_results)}")
        for res in gen_results:
            author = db.query(User).filter(User.id == res.user_id).first()
            author_name = author.username if author else "Unknown"
            print(f"  - ID {res.id}: {res.analysis_name} (por {author_name}) - {res.created_at}")
        print()

        # Verificar file paths
        file_paths = db.query(FilePath).all()
        print(f"FILE PATHS: {len(file_paths)}")
        for file_path in file_paths:
            author = db.query(User).filter(User.id == file_path.user_id).first()
            author_name = author.username if author else "Unknown"
            print(f"  - ID {file_path.id}: {file_path.full_path} (por {author_name})")
        print()

        print("=== RESUMO ===")
        print(f"Usuarios: {len(users)}")
        print(f"Prompts: {len(prompts)}")
        print(f"Configuracoes de Prompts: {len(prompt_configs)}")
        print(f"Criterios Gerais: {len(criteria)}")
        print(f"Analises: {len(analyses)}")
        print(f"Uploads: {len(uploads)}")
        print(f"File Paths: {len(file_paths)}")
        print(f"Code Entries: {len(code_entries)}")
        print(f"Resultados Gerais: {len(gen_results)}")

    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_all_data()