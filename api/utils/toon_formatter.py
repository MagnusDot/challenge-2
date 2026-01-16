"""
TOON formatter utility for API responses.

Converts JSON/Python data structures to TOON format for token-efficient LLM communication.
"""

from typing import Any, Dict, List
import json


def to_toon(data: Any, indent: int = 0) -> str:
    """
    Convert Python data structure to TOON format.
    
    TOON (Token-Oriented Object Notation) is a compact, human-readable
    encoding that uses ~40% fewer tokens than JSON.
    
    Args:
        data: Python data structure to convert
        indent: Current indentation level
        
    Returns:
        TOON-formatted string
        
    Examples:
        >>> to_toon({"name": "John", "age": 30})
        'name: John\\nage: 30'
        
        >>> to_toon([{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}])
        '[2] {id, name}\\n1, Alice\\n2, Bob'
    """
    if data is None:
        return "null"
    
    if isinstance(data, bool):
        return "true" if data else "false"
    
    if isinstance(data, (int, float)):
        return str(data)
    
    if isinstance(data, str):
        # Quote strings that contain special characters or are empty
        if needs_quoting(data):
            return json.dumps(data)
        return data
    
    if isinstance(data, list):
        return format_array(data, indent)
    
    if isinstance(data, dict):
        return format_object(data, indent)
    
    # Fallback to JSON for unsupported types
    return json.dumps(data)


def needs_quoting(s: str) -> bool:
    """Check if a string needs to be quoted in TOON."""
    if not s:  # Empty string
        return True
    
    # Check for special characters that require quoting
    special_chars = [',', '\n', ':', '[', ']', '{', '}']
    return any(char in s for char in special_chars)


def format_array(arr: List[Any], indent: int) -> str:
    """
    Format array in TOON.
    
    If array contains uniform objects, use tabular format.
    Otherwise, use standard array format.
    """
    if not arr:
        return "[]"
    
    # Check if array contains uniform objects (tabular format)
    if all(isinstance(item, dict) for item in arr):
        # Check if all objects have the same keys
        if len(arr) > 0:
            first_keys = set(arr[0].keys())
            if all(set(item.keys()) == first_keys for item in arr):
                return format_tabular_array(arr, indent)
    
    # Standard array format
    lines = [f"[{len(arr)}]"]
    ind = "  " * (indent + 1)
    
    for item in arr:
        item_str = to_toon(item, indent + 1)
        # Add indentation to each line of the item
        item_lines = item_str.split('\n')
        lines.extend([ind + line for line in item_lines])
    
    return '\n'.join(lines)


def format_tabular_array(arr: List[Dict[str, Any]], indent: int) -> str:
    """
    Format uniform array of objects as TOON table.
    
    Example:
        [3] {id, name, age}
        1, Alice, 30
        2, Bob, 25
        3, Charlie, 35
    """
    if not arr:
        return "[]"
    
    keys = list(arr[0].keys())
    lines = []
    
    # Header: [N] {field1, field2, ...}
    header = f"[{len(arr)}] " + "{" + ", ".join(keys) + "}"
    lines.append(header)
    
    # Rows: value1, value2, ...
    ind = "  " * (indent + 1) if indent > 0 else ""
    
    for item in arr:
        values = []
        for key in keys:
            value = item[key]
            # Format nested objects/arrays on same line when possible
            if isinstance(value, dict):
                value_str = format_inline_object(value)
            elif isinstance(value, list):
                value_str = format_inline_array(value)
            elif isinstance(value, str):
                value_str = json.dumps(value) if needs_quoting(value) else value
            elif value is None:
                value_str = "null"
            elif isinstance(value, bool):
                value_str = "true" if value else "false"
            else:
                value_str = str(value)
            values.append(value_str)
        
        lines.append(ind + ", ".join(values))
    
    return '\n'.join(lines)


def format_inline_object(obj: Dict[str, Any]) -> str:
    """Format object inline for table cells."""
    if not obj:
        return "{}"
    
    pairs = []
    for key, value in obj.items():
        if isinstance(value, str):
            val_str = json.dumps(value) if needs_quoting(value) else value
        elif value is None:
            val_str = "null"
        elif isinstance(value, bool):
            val_str = "true" if value else "false"
        else:
            val_str = str(value)
        pairs.append(f"{key}: {val_str}")
    
    return "{" + ", ".join(pairs) + "}"


def format_inline_array(arr: List[Any]) -> str:
    """Format array inline for table cells."""
    if not arr:
        return "[]"
    
    items = []
    for item in arr:
        if isinstance(item, str):
            item_str = json.dumps(item) if needs_quoting(item) else item
        elif item is None:
            item_str = "null"
        elif isinstance(item, bool):
            item_str = "true" if item else "false"
        elif isinstance(item, (dict, list)):
            # Nested structures - use JSON for simplicity
            item_str = json.dumps(item)
        else:
            item_str = str(item)
        items.append(item_str)
    
    return "[" + ", ".join(items) + "]"


def format_object(obj: Dict[str, Any], indent: int) -> str:
    """
    Format object in TOON.
    
    Example:
        name: John
        age: 30
        address:
          city: Paris
          country: France
    """
    if not obj:
        return "{}"
    
    lines = []
    ind = "  " * indent
    
    for key, value in obj.items():
        value_str = to_toon(value, indent + 1)
        
        # Check if value is multi-line
        if '\n' in value_str:
            lines.append(f"{ind}{key}:")
            # Add indented value lines
            for value_line in value_str.split('\n'):
                lines.append(f"{ind}  {value_line}")
        else:
            lines.append(f"{ind}{key}: {value_str}")
    
    return '\n'.join(lines)


def format_response_as_toon(data: Any) -> str:
    """
    Format API response as TOON.
    
    This is the main entry point for converting API responses.
    
    Args:
        data: Response data (list, dict, or primitive)
        
    Returns:
        TOON-formatted string
    """
    return to_toon(data)



