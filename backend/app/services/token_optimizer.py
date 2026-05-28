"""
Token optimization utilities for VerificAI Backend
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class TokenOptimizer:
    """Token optimization utilities"""

    def __init__(self):
        self.max_tokens = 32000  # Default context window limit

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Simple estimation: ~4 characters per token
        return len(text) // 4

    def optimize_code(self, code: str, language: str = "") -> str:
        """Optimize code for token usage"""
        # Remove comments first
        optimized = self._remove_comments(code, language)

        # Remove empty lines
        optimized = self._remove_empty_lines(optimized)
        
        # NOTE: We avoid collapsing all whitespace to a single line 
        # to preserve code structure (especially for Python/Indentation).
        
        return optimized

    def optimize_prompt(self, prompt: str) -> str:
        """Optimize prompt for token usage"""
        # Strip redundant whitespace from ends
        return prompt.strip()

    def create_chunks(self, content: str, max_chunk_size: int = 15000) -> List[str]:
        """Split content into optimal chunks"""
        chunks = []
        current_chunk = []
        current_size = 0
        lines = content.split('\n')

        for line in lines:
            line_size = len(line) + 1
            if current_size + line_size > max_chunk_size:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
            
            current_chunk.append(line)
            current_size += line_size

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def optimize_content(self, processed_files: List[Dict[str, Any]], max_tokens: int = 100000) -> str:
        """Optimize content from processed files"""
        optimized_content = []

        total_estimated_tokens = 0
        
        for file_info in processed_files:
            file_path = file_info.get('path', '')
            file_content = file_info.get('content', '')
            language = file_info.get('language', '')

            # Optimize each file
            optimized_code = self.optimize_code(file_content, language)
            
            # Simple header
            header = f"\n\n// File: {file_path} ({language})\n"
            
            # Check if we are exceeding limits (rough estimate)
            # If we already have too much, we might need to skip or truncate
            if total_estimated_tokens + self.estimate_tokens(optimized_code) > max_tokens:
                logger.warning(f"Maximum token limit reached while processing {file_path}. Truncating.")
                optimized_content.append(f"{header}// [CONTENT TRUNCATED DUE TO TOKEN LIMIT]\n")
                break

            optimized_content.append(header)
            optimized_content.append(optimized_code)
            
            total_estimated_tokens += self.estimate_tokens(optimized_code)

        return "".join(optimized_content).strip()

    def _remove_comments(self, code: str, language: str = "") -> str:
        """Remove comments from code based on language basics"""
        lines = code.split('\n')
        optimized_lines = []
        
        lang_lower = language.lower() if language else ""

        for line in lines:
            original_line = line
            # Javascript, Typescript, Java, C, C++, Go
            if any(ext in lang_lower for ext in ['javascript', 'typescript', 'js', 'ts', 'java', 'c', 'cpp', 'go']):
                if '//' in line:
                    # Very simple check, doesn't handle strings with //
                    line = line.split('//')[0]
            
            # Python, Ruby, Shell, YAML, TOML
            elif any(ext in lang_lower for ext in ['python', 'py', 'ruby', 'sh', 'yaml', 'yml', 'toml', 'dockerfile']):
                if '#' in line:
                    line = line.split('#')[0]
            
            # HTML, XML
            elif any(ext in lang_lower for ext in ['html', 'xml']):
                # Regex would be better, but this is a simple optimizer
                pass

            # Only add if line is not empty after stripping
            if line.strip() or original_line.strip() == "": # Keep empty lines for now, will remove later
                optimized_lines.append(line.rstrip())

        return '\n'.join(optimized_lines)

    def _remove_empty_lines(self, text: str) -> str:
        """Remove successive empty lines from text"""
        lines = text.split('\n')
        result = []
        for line in lines:
            if line.strip():
                result.append(line)
        return '\n'.join(result)
