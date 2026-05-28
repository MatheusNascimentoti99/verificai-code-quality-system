"""
File processor service for VerificAI Backend
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import mimetypes
from app.core.config import settings

logger = logging.getLogger(__name__)


class ProcessedFile:
    """Processed file data structure"""

    def __init__(self, path: str, content: str, language: str = "", size: int = 0, line_count: int = 0):
        self.path = path
        self.content = content
        self.language = language
        self.size = size
        self.line_count = line_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'path': self.path,
            'content': self.content,
            'language': self.language,
            'size': self.size,
            'line_count': self.line_count
        }


class LanguageDetector:
    """Detect programming language from file extension"""

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
        """Detect programming language from file path"""
        path = Path(file_path)
        extension = path.suffix.lower()

        # Check exact extension match
        if extension in self.LANGUAGE_MAP:
            return self.LANGUAGE_MAP[extension]

        # Check if filename matches common patterns
        filename = path.name.lower()
        if filename == 'dockerfile':
            return 'docker'
        if filename == 'makefile':
            return 'make'
        if filename == '.gitignore':
            return 'git'
        if filename.startswith('.env'):
            return 'env'

        # Default to text
        return 'text'


class FileProcessor:
    """Service for processing files for analysis"""

    def __init__(self):
        self.language_detector = LanguageDetector()
        self.allowed_extensions = set(settings.ALLOWED_EXTENSIONS) if hasattr(settings, 'ALLOWED_EXTENSIONS') else {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.r'
        }

    async def process_files(self, file_paths: List[str]) -> List[ProcessedFile]:
        """Process multiple files for analysis"""
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
        """Process a single file for analysis"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            # Skip common irrelevant directories even if individual file is requested
            path = Path(file_path)
            if any(part in str(path).split(os.sep) for part in ['.git', 'node_modules', '__pycache__', 'venv', 'env', 'dist', 'build']):
                logger.debug(f"Skipping file in excluded directory: {file_path}")
                return None

            # Check file extension
            if path.suffix.lower() not in self.allowed_extensions:
                logger.warning(f"File extension not allowed: {path.suffix}")
                return None

            # Check file size before reading (ignore files > 1MB)
            size = os.path.getsize(file_path)
            if size > 1024 * 1024:
                logger.warning(f"File too large: {file_path} ({size} bytes). Skipping.")
                return None

            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Detect language
            language = self.language_detector.detect_language(file_path)

            # Count lines
            line_count = len(content.split('\n'))

            # Extract relevant code
            relevant_code = self.extract_relevant_code(content, language)

            return ProcessedFile(
                path=file_path,
                content=relevant_code,
                language=language,
                size=size,
                line_count=line_count
            )

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return None

    async def process_directory(self, directory_path: str) -> List[ProcessedFile]:
        """Process all files in a directory"""
        processed_files = []

        try:
            path = Path(directory_path)
            if not path.exists():
                logger.error(f"Directory not found: {directory_path}")
                return processed_files

            # Gather all files first
            all_files = [str(f) for f in path.rglob('*') if f.is_file()]
            
            # Filter relevant files
            relevant_files = self.filter_relevant_files(all_files)
            
            logger.info(f"Processing {len(relevant_files)} files in {directory_path}")

            # Walk through relevant files
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
        """Extract relevant code sections for analysis"""
        # Remove empty lines and trim whitespace
        lines = [line.strip() for line in file_content.split('\n') if line.strip()]

        # Join lines with newlines
        content = '\n'.join(lines)

        # Language-specific optimizations
        if language == 'python':
            content = self._optimize_python_code(content)
        elif language in ['javascript', 'typescript']:
            content = self._optimize_js_code(content)
        elif language == 'java':
            content = self._optimize_java_code(content)

        return content

    def _optimize_python_code(self, code: str) -> str:
        """Optimize Python code for analysis"""
        lines = code.split('\n')
        optimized_lines = []

        for line in lines:
            # Skip import statements (they're usually not relevant for code quality analysis)
            if line.strip().startswith(('import ', 'from ')):
                continue

            # Skip docstrings that are too long
            if line.strip().startswith(('"""', "'''")) and len(line) > 100:
                continue

            optimized_lines.append(line)

        return '\n'.join(optimized_lines)

    def _optimize_js_code(self, code: str) -> str:
        """Optimize JavaScript/TypeScript code for analysis"""
        lines = code.split('\n')
        optimized_lines = []

        for line in lines:
            # Skip import statements
            if line.strip().startswith(('import ', 'require(')):
                continue

            # Skip console.log statements
            if 'console.log' in line:
                continue

            optimized_lines.append(line)

        return '\n'.join(optimized_lines)

    def _optimize_java_code(self, code: str) -> str:
        """Optimize Java code for analysis"""
        lines = code.split('\n')
        optimized_lines = []

        for line in lines:
            # Skip import statements
            if line.strip().startswith('import '):
                continue

            # Skip package declarations
            if line.strip().startswith('package '):
                continue

            optimized_lines.append(line)

        return '\n'.join(optimized_lines)

    def get_file_stats(self, file_paths: List[str]) -> Dict[str, Any]:
        """Get statistics about the files"""
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

                    # Count lines
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        stats['total_lines'] += lines

                    # Count languages
                    language = self.language_detector.detect_language(file_path)
                    stats['languages'][language] = stats['languages'].get(language, 0) + 1

                    # Count file types
                    ext = path.suffix.lower()
                    stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1

            except Exception as e:
                logger.error(f"Error getting stats for {file_path}: {str(e)}")
                continue

        return stats

    def filter_relevant_files(self, file_paths: List[str]) -> List[str]:
        """Filter out irrelevant files"""
        relevant_files = []

        for file_path in file_paths:
            path = Path(file_path)

            # Skip common irrelevant files and directories
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