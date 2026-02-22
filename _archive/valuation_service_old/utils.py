import math
from typing import Any, Dict, List, Union

def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively traverse the object and replace NaN and Infinity float values with None.
    This ensures compliance with standard JSON specifications.
    
    Args:
        obj: The object to sanitize (dict, list, float, etc.)
        
    Returns:
        The sanitized object.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_for_json(item) for item in obj)
    return obj
