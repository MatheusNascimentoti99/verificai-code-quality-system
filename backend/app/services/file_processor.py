"""
File processing helpers: resolve paths and build source bundles.
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.code_entry import CodeEntry
from app.models.uploaded_file import UploadedFile, FileStatus
from app.providers.base import StorageProvider


logger = logging.getLogger(__name__)


class ProcessedFile:
    """Processed file data structure."""

    def __init__(self, path: str, content: str, language: str = "", size: int = 0, line_count: int = 0):
        self.path = path
        self.content = content
        self.language = language
        self.size = size
        self.line_count = line_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'path': self.path,
            'content': self.content,
            'language': self.language,
            'size': self.size,
            'line_count': self.line_count,
        }


class LanguageDetector:
    """Detect programming language from file extension."""

    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.r': 'r',
        '.m': 'objective-c',
        '.mm': 'objective-c',
        '.sql': 'sql',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.cfg': 'ini',
        '.conf': 'ini',
        '.md': 'markdown',
        '.txt': 'text',
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell',
        '.fish': 'shell',
        '.ps1': 'powershell',
        '.bat': 'batch',
        '.dockerfile': 'docker',
        '.dockerignore': 'docker',
        '.gitignore': 'git',
        '.env': 'env',
    }

    def detect_language(self, file_path: str) -> str:
        """Detect programming language from file path."""
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension in self.LANGUAGE_MAP:
            return self.LANGUAGE_MAP[extension]

        filename = path.name.lower()
        if filename == 'dockerfile':
            return 'docker'
        if filename == 'makefile':
            return 'make'
        if filename == '.gitignore':
            return 'git'
        if filename.startswith('.env'):
            return 'env'

        return 'text'


class FileProcessorService:
    def __init__(self, db: Optional[Session] = None, storage_provider: Optional[StorageProvider] = None):
        self.db = db
        self.storage_provider = storage_provider
        self.language_detector = LanguageDetector()
        self.allowed_extensions = set(settings.ALLOWED_EXTENSIONS) if hasattr(settings, 'ALLOWED_EXTENSIONS') else {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.r'
        }

    def resolve_uploaded_file_path(self, file_path: str, user_id: int) -> str:
        """Resolve an uploaded file path to the actual storage locator."""
        try:
            storage = self.storage_provider
            if storage is None or self.db is None:
                return file_path

            def find_most_recent_existing(files_query):
                files = files_query.order_by(UploadedFile.created_at.desc()).all()
                for uploaded_file in files:
                    file_locator = uploaded_file.storage_path
                    if str(file_locator).startswith(("http://", "https://", "minio://")):
                        return uploaded_file, file_locator
                    if storage.path_exists(file_locator):
                        return uploaded_file, file_locator
                return None, None

            files_query = self.db.query(UploadedFile).filter(
                UploadedFile.relative_path == file_path,
                UploadedFile.user_id == user_id,
                UploadedFile.status == FileStatus.COMPLETED,
            )
            uploaded_file, full_disk_path = find_most_recent_existing(files_query)

            if not uploaded_file:
                files_query = self.db.query(UploadedFile).filter(
                    UploadedFile.original_name == file_path,
                    UploadedFile.user_id == user_id,
                    UploadedFile.status == FileStatus.COMPLETED,
                )
                uploaded_file, full_disk_path = find_most_recent_existing(files_query)

            if not uploaded_file:
                filename = file_path.split('/')[-1].split('\\')[-1]
                files_query = self.db.query(UploadedFile).filter(
                    UploadedFile.original_name == filename,
                    UploadedFile.user_id == user_id,
                    UploadedFile.status == FileStatus.COMPLETED,
                )
                uploaded_file, full_disk_path = find_most_recent_existing(files_query)

            if not uploaded_file:
                files_query = self.db.query(UploadedFile).filter(
                    UploadedFile.storage_path.like(f'%{file_path}%'),
                    UploadedFile.user_id == user_id,
                    UploadedFile.status == FileStatus.COMPLETED,
                )
                uploaded_file, full_disk_path = find_most_recent_existing(files_query)

            return full_disk_path if uploaded_file and full_disk_path else file_path
        except Exception:
            return file_path

    def _get_code_entry(self, code_entry_id: Optional[str], user_id: int) -> Optional[CodeEntry]:
        """Get the code entry requested by the user or the latest active one."""
        if self.db is None:
            return None

        if code_entry_id:
            return self.db.query(CodeEntry).filter(
                CodeEntry.id == code_entry_id,
                CodeEntry.user_id == user_id,
                CodeEntry.is_active == True,  # noqa: E712
            ).first()

        return self.db.query(CodeEntry).filter(
            CodeEntry.user_id == user_id,
            CodeEntry.is_active == True,  # noqa: E712
        ).order_by(CodeEntry.created_at.desc()).first()

    async def build_source_bundle(self, request_data, current_user) -> Tuple[str, str, int]:
        """Collect source code from code entries or uploaded files."""
        all_source_code = ""
        source_info = ""
        total_files_processed = 0

        is_using_files = len(request_data.file_paths) > 0

        if not is_using_files and request_data.use_code_entry:
            code_entry = self._get_code_entry(request_data.code_entry_id, current_user.id)
            if not code_entry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nenhum código encontrado na tabela de colagem. Por favor, cole um código na página de colagem primeiro.",
                )

            all_source_code = code_entry.code_content or ""
            file_size = len(all_source_code)
            source_info = (
                f"\n\n{'='*60}\n"
                f"CÓDIGO COLADO: {code_entry.title}\n"
                f"DESCRIÇÃO: {code_entry.description or 'Sem descrição'}\n"
                f"LINGUAGEM: {code_entry.language or 'Não detectada'}\n"
                f"TAMANHO: {file_size} caracteres\n"
                f"LINHAS: {code_entry.lines_count}\n"
                f"CRIADO EM: {code_entry.created_at}\n"
                f"{'='*60}\n\n"
            )
            total_files_processed = 1
            return all_source_code, source_info, total_files_processed

        if not request_data.file_paths:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file paths provided")

        for source_file_path in request_data.file_paths:
            actual_file_path = source_file_path
            try:
                actual_file_path = self.resolve_uploaded_file_path(source_file_path, current_user.id)
                file_content = await self.storage_provider.read_text(actual_file_path)
                file_size = len(file_content)
                file_extension = source_file_path.split('.')[-1] if '.' in source_file_path else 'txt'

                source_info += f"\n\n{'='*60}\n"
                source_info += f"ARQUIVO: {source_file_path}\n"
                source_info += f"TAMANHO: {file_size} caracteres\n"
                source_info += f"TIPO: {file_extension.upper()}\n"
                source_info += f"{'='*60}\n\n"
                all_source_code += file_content
                total_files_processed += 1
            except Exception as file_error:
                print(f"❌ DEBUG: Error processing file {source_file_path} (actual: {actual_file_path}): {file_error}")
                continue

        if total_files_processed == 0:
            is_cloud = "render" in os.environ.get("HOSTNAME", "").lower() or "vercel" in os.environ.get("HOSTNAME", "").lower()
            detail_msg = "Nenhum código pôde ser lido para análise. O arquivo não existe no disco."
            if is_cloud:
                detail_msg += " Devido ao ambiente cloud (Render/Vercel), arquivos locais são perdidos após o restart. Por favor, remova caminhos antigos ou use a 'Colagem de Código'."
            else:
                file_previews = request_data.file_paths[:3] if request_data.file_paths else []
                detail_msg += f" Verifique se os diretórios {file_previews}... existem."

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail_msg)

        return all_source_code, source_info, total_files_processed

    async def process_files(self, file_paths: List[str]) -> List[ProcessedFile]:
        """Process multiple files for analysis."""
        processed_files = []

        for file_path in file_paths:
            try:
                processed_file = await self.process_file(file_path)
                if processed_file:
                    processed_files.append(processed_file)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                continue

        return processed_files

    async def process_file(self, file_path: str) -> Optional[ProcessedFile]:
        """Process a single file for analysis."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            path = Path(file_path)
            if any(part in str(path).split(os.sep) for part in ['.git', 'node_modules', '__pycache__', 'venv', 'env', 'dist', 'build']):
                logger.debug(f"Skipping file in excluded directory: {file_path}")
                return None

            if path.suffix.lower() not in self.allowed_extensions:
                logger.warning(f"File extension not allowed: {path.suffix}")
                return None

            size = os.path.getsize(file_path)
            if size > 1024 * 1024:
                logger.warning(f"File too large: {file_path} ({size} bytes). Skipping.")
                return None

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            language = self.language_detector.detect_language(file_path)
            line_count = len(content.split('\n'))
            relevant_code = self.extract_relevant_code(content, language)

            return ProcessedFile(
                path=file_path,
                content=relevant_code,
                language=language,
                size=size,
                line_count=line_count,
            )

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return None

    async def process_directory(self, directory_path: str) -> List[ProcessedFile]:
        """Process all files in a directory."""
        processed_files = []

        try:
            path = Path(directory_path)
            if not path.exists():
                logger.error(f"Directory not found: {directory_path}")
                return processed_files

            all_files = [str(f) for f in path.rglob('*') if f.is_file()]
            relevant_files = self.filter_relevant_files(all_files)

            logger.info(f"Processing {len(relevant_files)} files in {directory_path}")

            for file_path in relevant_files:
                try:
                    processed_file = await self.process_file(file_path)
                    if processed_file:
                        processed_files.append(processed_file)
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error processing directory {directory_path}: {str(e)}")

        return processed_files

    def extract_relevant_code(self, file_content: str, language: str) -> str:
        """Extract relevant code sections for analysis."""
        lines = [line.strip() for line in file_content.split('\n') if line.strip()]
        content = '\n'.join(lines)

        if language == 'python':
            content = self._optimize_python_code(content)
        elif language in ['javascript', 'typescript']:
            content = self._optimize_js_code(content)
        elif language == 'java':
            content = self._optimize_java_code(content)

        return content

    def _optimize_python_code(self, code: str) -> str:
        """Optimize Python code for analysis."""
        lines = code.split('\n')
        optimized_lines = []

        for line in lines:
            if line.strip().startswith(('import ', 'from ')):
                continue

            if line.strip().startswith(('"""', "'''")) and len(line) > 100:
                continue

            optimized_lines.append(line)

        return '\n'.join(optimized_lines)

    def _optimize_js_code(self, code: str) -> str:
        """Optimize JavaScript/TypeScript code for analysis."""
        lines = code.split('\n')
        optimized_lines = []

        for line in lines:
            if line.strip().startswith(('import ', 'require(')):
                continue

            if 'console.log' in line:
                continue

            optimized_lines.append(line)

        return '\n'.join(optimized_lines)

    def _optimize_java_code(self, code: str) -> str:
        """Optimize Java code for analysis."""
        lines = code.split('\n')
        optimized_lines = []

        for line in lines:
            if line.strip().startswith('import '):
                continue

            if line.strip().startswith('package '):
                continue

            optimized_lines.append(line)

        return '\n'.join(optimized_lines)

    def get_file_stats(self, file_paths: List[str]) -> Dict[str, Any]:
        """Get statistics about the files."""
        stats = {
            'total_files': len(file_paths),
            'total_size': 0,
            'total_lines': 0,
            'languages': {},
            'file_types': {}
        }

        for file_path in file_paths:
            try:
                path = Path(file_path)
                if path.exists():
                    size = path.stat().st_size
                    stats['total_size'] += size

                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        stats['total_lines'] += lines

                    language = self.language_detector.detect_language(file_path)
                    stats['languages'][language] = stats['languages'].get(language, 0) + 1

                    ext = path.suffix.lower()
                    stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1

            except Exception as e:
                logger.error(f"Error getting stats for {file_path}: {str(e)}")
                continue

        return stats

    def filter_relevant_files(self, file_paths: List[str]) -> List[str]:
        """Filter out irrelevant files."""
        relevant_files = []

        for file_path in file_paths:
            path = Path(file_path)

            skip_patterns = [
                '__pycache__',
                '.git',
                '.vscode',
                '.idea',
                'node_modules',
                'venv',
                'env',
                '.env',
                '*.log',
                '*.tmp',
                '*.bak',
                'dist',
                'build',
                'coverage'
            ]

            skip = False
            for pattern in skip_patterns:
                if pattern in str(path) or path.name == pattern:
                    skip = True
                    break

            if not skip:
                relevant_files.append(file_path)

        return relevant_files