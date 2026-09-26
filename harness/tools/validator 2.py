"""Schema and argument validation engine for workspace tools."""

from typing import Any, Dict, List, Optional, Tuple


def validate_tool_arguments(
    schema: Dict[str, Any], arguments: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """Validates tool arguments against a JSON Schema dictionary.

    Returns:
        (True, None) if valid.
        (False, error_message) if invalid.
    """
    if not isinstance(arguments, dict):
        return False, f"Expected arguments dictionary, received {type(arguments).__name__}."

    # Check for malformed JSON raw arguments passed from LLM parser
    if "_raw_arguments_malformed" in arguments:
        return (
            False,
            f"Malformed JSON in tool arguments: {arguments.get('_error', 'Failed to parse JSON string')}.",
        )

    # 1. Validate required fields
    required_fields: List[str] = schema.get("required", [])
    for req in required_fields:
        if req not in arguments or arguments[req] is None:
            return False, f"Missing required parameter: '{req}'."

    # 2. Validate property types & enum constraints
    properties: Dict[str, Any] = schema.get("properties", {})
    type_map = {
        "string": (str,),
        "integer": (int,),
        "number": (int, float),
        "boolean": (bool,),
        "array": (list, tuple),
        "object": (dict,),
    }

    for param_name, param_val in arguments.items():
        if param_name.startswith("_"):
            continue
        if param_name not in properties:
            # We allow extra properties if additionalProperties is not False, but ignore or validate if present
            continue

        param_schema = properties[param_name]
        expected_type_str = param_schema.get("type")

        if expected_type_str and expected_type_str in type_map:
            expected_types = type_map[expected_type_str]
            # Special case: in Python, bool is a subclass of int. Ensure int is not a bool
            if expected_type_str in ("integer", "number") and isinstance(param_val, bool):
                return (
                    False,
                    f"Invalid type for parameter '{param_name}': expected {expected_type_str}, received boolean.",
                )
            if not isinstance(param_val, expected_types):
                return (
                    False,
                    f"Invalid type for parameter '{param_name}': expected {expected_type_str}, received {type(param_val).__name__}.",
                )

        # Enum check
        enum_values = param_schema.get("enum")
        if enum_values is not None and param_val not in enum_values:
            return (
                False,
                f"Invalid value for parameter '{param_name}': '{param_val}'. Must be one of {enum_values}.",
            )

    return True, None
