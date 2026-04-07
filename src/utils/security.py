"""Security utilities and validation functions."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Union


class SecurityError(Exception):
    """Base exception for security-related errors."""
    pass


class CommandInjectionError(SecurityError):
    """Raised when command injection is detected."""
    pass


class PathTraversalError(SecurityError):
    """Raised when path traversal is detected."""
    pass


def validate_editor_command(editor: str) -> str:
    """Validate and sanitize editor command for security.
    
    Args:
        editor: Editor command string
        
    Returns:
        Sanitized editor command
        
    Raises:
        CommandInjectionError: If command appears to contain injection attempts
    """
    if not editor:
        raise CommandInjectionError("Empty editor command")
    
    # Check for command injection patterns
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "&&", "||"]
    for char in dangerous_chars:
        if char in editor:
            raise CommandInjectionError(f"Potentially dangerous character '{char}' in editor command: {editor}")
    
    # Ensure the command exists and is executable
    editor_parts = shlex.split(editor)
    if not editor_parts:
        raise CommandInjectionError("Invalid editor command format")
    
    editor_cmd = editor_parts[0]
    if not shutil.which(editor_cmd):
        raise CommandInjectionError(f"Editor command not found or not executable: {editor_cmd}")
    
    return editor


def safe_subprocess_run(
    command: Union[str, List[str]], 
    *,
    shell: bool = False,
    timeout: Optional[int] = 30,
    **kwargs
) -> subprocess.CompletedProcess:
    """Safely run subprocess with security validation.
    
    Args:
        command: Command to run (list preferred over string)
        shell: Whether to use shell (discouraged for security)
        timeout: Command timeout in seconds
        **kwargs: Additional subprocess arguments
        
    Returns:
        Completed process result
        
    Raises:
        CommandInjectionError: If command appears unsafe
        SecurityError: If shell=True with string command
    """
    if shell and isinstance(command, str):
        raise SecurityError(
            "Using shell=True with string commands is dangerous. "
            "Use a list of arguments instead."
        )
    
    if isinstance(command, str):
        command = shlex.split(command)
    
    if not command:
        raise CommandInjectionError("Empty command")
    
    # Validate the main command exists
    if not shutil.which(command[0]):
        raise CommandInjectionError(f"Command not found: {command[0]}")
    
    return subprocess.run(
        command,
        shell=shell,
        timeout=timeout,
        **kwargs
    )


def validate_file_path(
    file_path: Union[str, Path], 
    allowed_roots: Optional[List[Union[str, Path]]] = None,
    must_exist: bool = True
) -> Path:
    """Validate file path for security (prevent path traversal).
    
    Args:
        file_path: Path to validate
        allowed_roots: List of allowed root directories (optional)
        must_exist: Whether the path must exist
        
    Returns:
        Resolved, validated Path object
        
    Raises:
        PathTraversalError: If path traversal is detected
        FileNotFoundError: If must_exist=True and path doesn't exist
    """
    path = Path(file_path).resolve()
    
    # Check for path traversal attempts
    if ".." in str(file_path):
        # Double check with resolved path
        input_path = Path(file_path)
        if any(part == ".." for part in input_path.parts):
            raise PathTraversalError(f"Path traversal detected in: {file_path}")
    
    # Validate against allowed roots
    if allowed_roots:
        allowed = False
        for root in allowed_roots:
            root_path = Path(root).resolve()
            try:
                path.relative_to(root_path)
                allowed = True
                break
            except ValueError:
                continue
        
        if not allowed:
            raise PathTraversalError(
                f"Path outside allowed directories: {path}. "
                f"Allowed roots: {[str(r) for r in allowed_roots]}"
            )
    
    # Check existence if required
    if must_exist and not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    
    return path


def get_safe_editor() -> str:
    """Get a safe editor command with fallbacks.
    
    Returns:
        Safe editor command
        
    Raises:
        CommandInjectionError: If no safe editor is available
    """
    # Priority order of editors to try
    editor_candidates = [
        os.environ.get("EDITOR", ""),
        "notepad" if os.name == "nt" else "",
        "nano",
        "vim", 
        "emacs",
        "gedit",
        "xdg-open",
    ]
    
    for editor in editor_candidates:
        if not editor:
            continue
            
        try:
            validated_editor = validate_editor_command(editor)
            return validated_editor
        except CommandInjectionError:
            continue
    
    raise CommandInjectionError("No safe editor available")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and illegal characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove directory separators and other dangerous characters
    dangerous_chars = ["\\", "/", "..", ":", "*", "?", "\"", "<", ">", "|"]
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "_")
    
    # Ensure it's not empty and doesn't start with a dot (hidden file)
    sanitized = sanitized.strip()
    if not sanitized or sanitized.startswith("."):
        sanitized = "file_" + sanitized
    
    return sanitized