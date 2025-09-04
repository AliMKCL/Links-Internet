"""
Minimal security utilities for input validation and sanitization.
"""
import re
import unicodedata


def sanitize_input(text: str, max_length: int = 512) -> str:
    """
    Sanitize user input with basic security measures.
    
    Args:
        text: Input string to sanitize
        max_length: Maximum allowed length (default: 512)
    
    Returns:
        Sanitized string safe for processing
    """
    if not text:
        return ""
    
    # Enforce max length
    if len(text) > max_length:
        text = text[:max_length]
    
    # Normalize Unicode to prevent encoding tricks
    text = unicodedata.normalize("NFKC", text)
    
    # Remove null bytes, control characters, and non-printable chars
    # Keep only printable ASCII chars, tabs, newlines, and basic spaces
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", "", text)
    
    # Collapse multiple whitespace into single spaces
    text = re.sub(r"\s+", " ", text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def validate_query_length(text: str, max_length: int = 512) -> bool:
    """
    Validate if query length is within acceptable limits.
    
    Args:
        text: Input text to validate
        max_length: Maximum allowed length
        
    Returns:
        True if valid, False otherwise
    """
    return text is not None and len(text) <= max_length


def log_suspicious_query(query: str, reason: str) -> None:
    """
    Log potentially suspicious queries for monitoring.
    
    Args:
        query: The suspicious query
        reason: Reason why it's flagged as suspicious
    """
    # Printing instead of logging for simplicity
    print(f"SECURITY WARNING: Suspicious query detected - {reason}")
    print(f"Query (first 100 chars): {query[:100]}")
