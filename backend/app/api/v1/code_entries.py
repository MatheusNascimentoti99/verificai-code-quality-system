"""
API endpoints for code entries
"""

import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_user
# Force reload
from app.models.user import User
from app.models.code_entry import CodeEntry
from app.schemas import (
    CodeEntryCreate, CodeEntryUpdate, CodeEntryResponse, CodeEntryList,
    CodeEntryDeleteResponse, CodeLanguageDetection
)

router = APIRouter()


def detect_programming_language(code: str) -> str:
    """
    Detect programming language based on code patterns
    """
    # Remove empty lines and trim for better pattern matching
    code_lines = [line.strip() for line in code.split('\n') if line.strip()]
    sample_code = '\n'.join(code_lines[:10])  # Check first 10 non-empty lines

    # Language detection patterns
    patterns = {
        'python': [
            r'\bdef\s+\w+\s*\(',  # def function(
            r'\bclass\s+\w+\s*:',  # class ClassName:
            r'\bimport\s+\w+',  # import module
            r'\bfrom\s+\w+\s+import',
            r'\bif\s+__name__\s*==\s*["\']__main__["\']',
            r'\bprint\s*\(',  # print(
            r'\belif\s+',  # elif
            r'\btry\s*:',  # try:
            r'\bexcept\s+',  # except
            r'"""[\s\S]*?"""',  # docstring
            r"'''[\s\S]*?'''"  # docstring
        ],
        'javascript': [
            r'\bfunction\s+\w+\s*\(',  # function name(
            r'\bconst\s+\w+\s*=',  # const name =
            r'\blet\s+\w+\s*=',  # let name =
            r'\bvar\s+\w+\s*=',  # var name =
            r'=>',  # arrow function
            r'console\.\w+\s*\(',  # console.log(
            r'\bimport\s+.*\bfrom\b',
            r'\bexport\s+',
            r'\brequire\s*\(',
            r'module\.exports',
            r'process\.',
            r'node:'
        ],
        'typescript': [
            r':\s*string\s*[=;)]',  # : string
            r':\s*number\s*[=;)]',  # : number
            r':\s*boolean\s*[=;)]',  # : boolean
            r'\binterface\s+\w+',  # interface Name
            r'\btype\s+\w+\s*=',  # type Name =
            r'\benum\s+\w+',  # enum Name
            r'\bas\s+\w+\s*:',  # as type:
            r'<\w+>',  # generics
            r'\bdeclare\s+',
            r'\bimplements\s+',
            r'\bprivate\s+\w+\s*:',
            r'\bpublic\s+\w+\s*:'
        ],
        'java': [
            r'\bpublic\s+class\s+\w+',  # public class
            r'\bprivate\s+\w+\s+\w+\s*[=;]',  # private type name
            r'\bprotected\s+\w+\s+\w+\s*[=;]',  # protected type name
            r'\bimport\s+java\.',
            r'System\.out\.print',
            r'public\s+static\s+void\s+main',
            r'@Override',
            r'@\w+',
            r'new\s+\w+\s*\(',
            r'throws\s+\w+',
            r'\bcatch\s*\(\w+\s+\w+\s*\)'
        ],
        'csharp': [
            r'\busing\s+\w+\s*;',  # using Namespace;
            r'\bnamespace\s+\w+',  # namespace Name
            r'\bpublic\s+class\s+\w+',  # public class
            r'Console\.\w+\s*\(',  # Console.WriteLine(
            r'@\w+',  # attributes
            r'public\s+\w+\s+\w+\s*{',  # property
            r'private\s+\w+\s+\w+\s*[;=]',
            r'protected\s+\w+\s+\w+\s*[;=]',
            r'List<\w+>',
            r'Dictionary<',
            r'\.Value',
            r'\.Key'
        ],
        'php': [
            r'<\?php',  # opening tag
            r'\$\w+\s*=',  # $variable =
            r'->\w+\s*\(',  # ->method(
            r'::\w+\s*\(',  # ::method(
            r'\becho\s+',  # echo
            r'\bfunction\s+\w+\s*\(',  # function name(
            r'\bclass\s+\w+',  # class name
            r'\bpublic\s+function',
            r'\bprivate\s+function',
            r'\bprotected\s+function',
            r'array\s*\(',
            r'\$_POST',
            r'\$_GET',
            r'\$_SESSION'
        ],
        'ruby': [
            r'\bdef\s+\w+',  # def method
            r'\bclass\s+\w+',  # class name
            r'\brequire\s+',  # require
            r'\binclude\s+',  # include
            r'\bputs\s+',  # puts
            r'\bprint\s+',  # print
            r'@\w+',  # instance variable
            r'@@\w+',  # class variable
            r'\$\w+',  # global variable
            r'do\s*\|.*\|',  # block
            r'\.each\s+do',
            r'\.map\s+do',
            r'end\s*$'
        ],
        'go': [
            r'\bfunc\s+\w+\s*\(',  # func name(
            r'\bpackage\s+\w+',  # package name
            r'\bimport\s+\(',  # import (
            r'fmt\.\w+\s*\(',  # fmt.Println(
            r'go\s+\w+\s*\(',  # go routine
            r'\bchan\s+\w+',  # channel
            r'struct\s+\{',  # struct
            r'interface\s+\{',
            r':=',  # short variable declaration
            r'\bdefer\s+',
            r'select\s*{',
            r'\bcase\s+'
        ],
        'rust': [
            r'\bfn\s+\w+\s*\(',  # fn name(
            r'\blet\s+mut\s+\w+',  # let mut name
            r'\blet\s+\w+',  # let name
            r'\buse\s+::',  # use std::
            r'\bmod\s+\w+',  # mod name
            r'\bpub\s+fn',  # public function
            r'\bstruct\s+\w+',  # struct name
            r'\benum\s+\w+',  # enum name
            r'impl\s+\w+',  # implementation
            r'\bmatch\s+',  # match
            r'->\s*\w+',  # return type
            r'\.unwrap\(\)',
            r'\.expect\(',
            r'Result<',
            r'Option<'
        ],
        'cpp': [
            r'#include\s*<',  # #include <header>
            r'#include\s*"',  # #include "header"
            r'\bstd::',  # std::
            r'->\w+',  # arrow operator
            r'\bclass\s+\w+',  # class name
            r'\bstruct\s+\w+',  # struct name
            r'\btemplate\s*<',
            r'namespace\s+\w+',  # namespace
            r'::\w+',  # scope resolution
            r'\bvirtual\s+',
            r'\boverride\b',
            r'\bconst\b',
            r'std::cout\s*<<',
            r'std::cin\s*>>',
            r'\bnew\s+\w+',
            r'\bdelete\s+'
        ],
        'c': [
            r'#include\s*<',  # #include <header>
            r'#include\s*"',  # #include "header"
            r'\bint\s+main\s*\(',  # int main(
            r'printf\s*\(',  # printf(
            r'scanf\s*\(',  # scanf(
            r'\*\w+',  # pointer
            r'\&\w+',  # address
            r'malloc\s*\(',
            r'free\s*\(',
            r'struct\s+\w+',  # struct name
            r'typedef\s+',
            r'#define\s+',
            r'#ifdef\s+',
            r'#endif'
        ],
        'html': [
            r'<!DOCTYPE\s+html>',
            r'<html[^>]*>',
            r'<head[^>]*>',
            r'<body[^>]*>',
            r'<div[^>]*>',
            r'<script[^>]*>',
            r'<style[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'href\s*=',
            r'src\s*=',
            r'class\s*=',
            r'id\s*=',
            r'</\w+>'
        ],
        'css': [
            r'\.\w+\s*{',  # .class {
            r'#\w+\s*{',  # #id {
            r'@\w+',  # @media, @import
            r'color\s*:',
            r'background\s*:',
            r'font-size\s*:',
            r'margin\s*:',
            r'padding\s*:',
            r'display\s*:',
            r'position\s*:',
            r'width\s*:',
            r'height\s*:'
        ],
        'sql': [
            r'\bSELECT\b.*\bFROM\b',
            r'\bINSERT\s+INTO\b',
            r'\bUPDATE\b.*\bSET\b',
            r'\bDELETE\s+FROM\b',
            r'\bCREATE\s+TABLE\b',
            r'\bALTER\s+TABLE\b',
            r'\bDROP\s+TABLE\b',
            r'\bJOIN\b',
            r'\bLEFT\s+JOIN\b',
            r'\bRIGHT\s+JOIN\b',
            r'\bINNER\s+JOIN\b',
            r'\bWHERE\b',
            r'\bORDER\s+BY\b',
            r'\bGROUP\s+BY\b'
        ],
        'json': [
            r'^\s*\{',  # starts with {
            r'^\s*\[',  # starts with [
            r'"\w+"\s*:',  # "key":
            r',\s*"',  # ,"
            r'\[\s*\{',  # [{
            r'\}\s*\]',  # }]
            r'true|false|null'
        ],
        'xml': [
            r'<\?xml',  # XML declaration
            r'<[^>]+>',  # tags
            r'</[^>]+>',  # closing tags
            r'<[^/>]+/>',  # self-closing tags
            r'=\s*"[^"]*"',  # attributes
            r'=\s*\'[^\']*\''
        ],
        'yaml': [
            r'^\w+\s*:',  # key: value
            r'^\s*-\s+',  # list item
            r'^\s*#',  # comment
            r'^---',  # document separator
            r'^\.\.\.',  # end of document
            r'null\s*$',
            r'true|false',
            r'\|\s*$',  # multiline string
            r'>\s*$'  # folded string
        ],
        'markdown': [
            r'^#{1,6}\s+',  # headers
            r'\*\*.*?\*\*',  # bold
            r'\*.*?\*',  # italic
            r'\[.*?\]\(.*?\)',  # links
            r'!\[.*?\]\(.*?\)',  # images
            r'^\s*[-*+]\s+',  # unordered list
            r'^\s*\d+\.\s+',  # ordered list
            r'^```',  # code blocks
            r'^>`',  # blockquotes
            r'\|.*\|',  # tables
            r'---',  # horizontal rule
            r'\+\+\+.*?\+\+\+',  # highlights
            '==.*?=='  # marks
        ]
    }

    # Calculate confidence scores for each language
    language_scores = {}

    for language, lang_patterns in patterns.items():
        score = 0
        matches = 0

        for pattern in lang_patterns:
            try:
                pattern_matches = len(re.findall(pattern, sample_code, re.IGNORECASE | re.MULTILINE))
                if pattern_matches > 0:
                    matches += 1
                    # Some patterns are more specific than others
                    if any(keyword in pattern.lower() for keyword in
                          ['public class', 'def ', 'function', 'import java', '<?php', 'namespace', 'package']):
                        score += pattern_matches * 2  # Higher weight for specific patterns
                    else:
                        score += pattern_matches
            except re.error:
                # Skip invalid patterns
                continue

        if matches > 0:
            # Normalize score based on number of matching patterns
            language_scores[language] = score / len(lang_patterns)

    # Return the language with the highest score, or 'text' if no matches
    if language_scores:
        best_language = max(language_scores, key=language_scores.get)
        # Only return the language if it has a reasonable confidence score
        if language_scores[best_language] > 0.1:
            return best_language

    return 'text'


@router.get("/code-entries/test")
async def test_endpoint():
    """Test endpoint to check if module is loading"""
    print("DEBUG: test_endpoint called")
    return {"message": "Module is working correctly", "authenticated": "no"}


@router.post("/code-entries/detect-language", response_model=CodeLanguageDetection)
async def detect_language(code_content: str = Body(...)):
    """
    Detect programming language from code content
    """
    language = detect_programming_language(code_content)
    return CodeLanguageDetection(language=language)


@router.post("/code-entries", response_model=CodeEntryResponse)
async def create_code_entry(
    code_entry: CodeEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new code entry
    """
    # Auto-detect language if not provided
    if not code_entry.language:
        detected_language = detect_programming_language(code_entry.code_content)
        code_entry.language = detected_language

    # Create the code entry
    db_code_entry = CodeEntry(
        code_content=code_entry.code_content,
        title=code_entry.title,
        description=code_entry.description,
        language=code_entry.language,
        lines_count=code_entry.lines_count,
        characters_count=code_entry.characters_count,
        user_id=current_user.id
    )

    db.add(db_code_entry)
    db.commit()
    db.refresh(db_code_entry)

    return db_code_entry


@router.get("/code-entries", response_model=List[CodeEntryList])
async def list_code_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    language: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List code entries for the current user
    """
    print(f"DEBUG: list_code_entries called for user {current_user.id}")

    # Query code entries for the current user
    query = db.query(CodeEntry).filter(
        CodeEntry.user_id == current_user.id,
        CodeEntry.is_active == True
    )

    # Filter by language if specified
    if language:
        query = query.filter(CodeEntry.language == language)

    # Order by most recent and apply pagination
    code_entries = query.order_by(CodeEntry.created_at.desc()).offset(skip).limit(limit).all()

    # Convert to response format
    result = []
    for entry in code_entries:
        print(f"DEBUG: Processing entry {entry.id}, code_content length: {len(entry.code_content) if entry.code_content else 0}")
        result.append(CodeEntryList(
            id=entry.id,
            title=entry.title,
            description=entry.description,
            language=entry.language,
            lines_count=entry.lines_count,
            characters_count=entry.characters_count,
            created_at=entry.created_at,
            is_active=entry.is_active,
            code_content=entry.code_content  # Added code_content field
        ))

    print(f"DEBUG: Returning {len(result)} code entries for user {current_user.id}")
    return result


@router.get("/code-entries/{entry_id}", response_model=CodeEntryResponse)
async def get_code_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific code entry by ID
    """
    code_entry = db.query(CodeEntry).filter(
        CodeEntry.id == entry_id,
        CodeEntry.user_id == current_user.id,
        CodeEntry.is_active == True
    ).first()

    if not code_entry:
        raise HTTPException(status_code=404, detail="Code entry not found")

    return code_entry


@router.put("/code-entries/{entry_id}", response_model=CodeEntryResponse)
async def update_code_entry(
    entry_id: str,
    code_entry_update: CodeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a code entry
    """
    code_entry = db.query(CodeEntry).filter(
        CodeEntry.id == entry_id,
        CodeEntry.user_id == current_user.id,
        CodeEntry.is_active == True
    ).first()

    if not code_entry:
        raise HTTPException(status_code=404, detail="Code entry not found")

    # Update fields if provided
    update_data = code_entry_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(code_entry, field, value)

    db.commit()
    db.refresh(code_entry)

    return code_entry


@router.delete("/code-entries/{entry_id}", response_model=CodeEntryDeleteResponse)
async def delete_code_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a code entry (soft delete)
    """
    code_entry = db.query(CodeEntry).filter(
        CodeEntry.id == entry_id,
        CodeEntry.user_id == current_user.id,
        CodeEntry.is_active == True
    ).first()

    if not code_entry:
        raise HTTPException(status_code=404, detail="Code entry not found")

    # Soft delete
    code_entry.is_active = False
    db.commit()

    return CodeEntryDeleteResponse(
        message="Code entry deleted successfully",
        success=True
    )


@router.get("/code-entries/stats/languages")
async def get_language_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about programming languages used
    """
    stats = db.query(
        CodeEntry.language,
        func.count(CodeEntry.id).label('count')
    ).filter(
        CodeEntry.user_id == current_user.id,
        CodeEntry.is_active == True,
        CodeEntry.language.isnot(None)
    ).group_by(CodeEntry.language).all()

    return {lang: count for lang, count in stats}# Force reload
