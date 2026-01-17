from typing import Any, Dict, List
import json

def to_toon(data: Any, indent: int = 0) -> str:

    if data is None:
        return "null"

    if isinstance(data, bool):
        return "true" if data else "false"

    if isinstance(data, (int, float)):
        return str(data)

    if isinstance(data, str):

        if needs_quoting(data):
            return json.dumps(data)
        return data

    if isinstance(data, list):
        return format_array(data, indent)

    if isinstance(data, dict):
        return format_object(data, indent)

    return json.dumps(data)

def needs_quoting(s: str) -> bool:

    if not s:
        return True

    special_chars = [',', '\n', ':', '[', ']', '{', '}']
    return any(char in s for char in special_chars)

def format_array(arr: List[Any], indent: int) -> str:

    if not arr:
        return "[]"

    if all(isinstance(item, dict) for item in arr):

        if len(arr) > 0:
            first_keys = set(arr[0].keys())
            if all(set(item.keys()) == first_keys for item in arr):
                return format_tabular_array(arr, indent)

    lines = [f"[{len(arr)}]"]
    ind = "  " * (indent + 1)

    for item in arr:
        item_str = to_toon(item, indent + 1)

        item_lines = item_str.split('\n')
        lines.extend([ind + line for line in item_lines])

    return '\n'.join(lines)

def format_tabular_array(arr: List[Dict[str, Any]], indent: int) -> str:

    if not arr:
        return "[]"

    keys = list(arr[0].keys())
    lines = []

    header = f"[{len(arr)}] " + "{" + ", ".join(keys) + "}"
    lines.append(header)

    ind = "  " * (indent + 1) if indent > 0 else ""

    for item in arr:
        values = []
        for key in keys:
            value = item[key]

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

            item_str = json.dumps(item)
        else:
            item_str = str(item)
        items.append(item_str)

    return "[" + ", ".join(items) + "]"

def format_object(obj: Dict[str, Any], indent: int) -> str:

    if not obj:
        return "{}"

    lines = []
    ind = "  " * indent

    for key, value in obj.items():
        value_str = to_toon(value, indent + 1)

        if '\n' in value_str:
            lines.append(f"{ind}{key}:")

            for value_line in value_str.split('\n'):
                lines.append(f"{ind}  {value_line}")
        else:
            lines.append(f"{ind}{key}: {value_str}")

    return '\n'.join(lines)

def format_response_as_toon(data: Any) -> str:

    return to_toon(data)