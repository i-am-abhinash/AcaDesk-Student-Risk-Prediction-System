import re

def sanitize_identifier(name: str) -> str:
    """
    Validates and sanitizes a SQL identifier (table or column name) to prevent SQL injection.
    Ensures the name matches the regex ^[a-zA-Z_][a-zA-Z0-9_]{0,63}$ and wraps it in backticks.
    """
    if not isinstance(name, str):
        raise ValueError(f"Identifier must be a string, got {type(name).__name__}")
        
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$", name):
        raise ValueError(f"Invalid SQL identifier: '{name}'. Identifiers must start with a letter or underscore and contain only letters, numbers, and underscores.")
        
    return f"`{name}`"
