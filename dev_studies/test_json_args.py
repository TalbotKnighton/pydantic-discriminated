import inspect
import json
from typing import Dict, Any, Set
from pydantic import BaseModel


def get_json_dumps_params() -> Set[str]:
    """
    Get the parameter names for json.dumps using inspect.

    Returns:
        Set of parameter names for json.dumps
    """
    # Get the signature of json.dumps
    sig = inspect.signature(json.dumps)

    # Extract parameter names (excluding 'obj' which is the first positional parameter)
    params = set(sig.parameters.keys())
    if "obj" in params:
        params.remove("obj")

    print(f"JSON dumps parameters: {sorted(params)}")
    return params


def get_model_dump_params() -> Set[str]:
    """
    Get the parameter names for BaseModel.model_dump using inspect.

    Returns:
        Set of parameter names for BaseModel.model_dump
    """
    # Get the signature of BaseModel.model_dump
    sig = inspect.signature(BaseModel.model_dump)

    # Extract parameter names (excluding 'self' which is the first parameter)
    params = set(sig.parameters.keys())
    if "self" in params:
        params.remove("self")

    print(f"BaseModel.model_dump parameters: {sorted(params)}")
    return params


def get_model_dump_json_params() -> Set[str]:
    """
    Get the parameter names for BaseModel.model_dump_json using inspect.

    Returns:
        Set of parameter names for BaseModel.model_dump_json
    """
    # Get the signature of BaseModel.model_dump_json
    sig = inspect.signature(BaseModel.model_dump_json)

    # Extract parameter names (excluding 'self' which is the first parameter)
    params = set(sig.parameters.keys())
    if "self" in params:
        params.remove("self")

    print(f"BaseModel.model_dump_json parameters: {sorted(params)}")
    return params


def identify_json_specific_params() -> Set[str]:
    """
    Identify JSON-specific parameters by comparing model_dump_json and model_dump parameters,
    and validating against json.dumps parameters.

    Returns:
        Set of JSON-specific parameter names
    """
    # Get parameters for each function
    json_dumps_params = get_json_dumps_params()
    model_dump_params = get_model_dump_params()
    model_dump_json_params = get_model_dump_json_params()

    # Find parameters that are in model_dump_json but not in model_dump
    json_specific_params = model_dump_json_params - model_dump_params

    # Make sure these parameters are actually in json.dumps
    valid_json_params = {param for param in json_specific_params if param in json_dumps_params}

    # Add 'encoder' which is a special case (gets mapped to 'default' in json.dumps)
    if "encoder" in model_dump_json_params and "encoder" not in model_dump_params:
        valid_json_params.add("encoder")

    print(f"Parameters unique to model_dump_json: {sorted(json_specific_params)}")
    print(f"Valid JSON-specific parameters: {sorted(valid_json_params)}")

    return valid_json_params


def test_parameter_separation():
    """Test separating model_dump parameters from json.dumps parameters."""
    # Get the valid JSON-specific parameters
    json_specific_params = identify_json_specific_params()

    # Example kwargs
    test_kwargs = {
        "exclude_unset": True,  # model_dump param
        "indent": 2,  # json.dumps param
        "exclude_none": True,  # model_dump param
        "sort_keys": True,  # json.dumps param
        "ensure_ascii": False,  # json.dumps param
        "use_discriminators": True,  # our custom param
    }

    # Separate the kwargs
    model_dump_kwargs = {
        k: v
        for k, v in test_kwargs.items()
        if k not in json_specific_params and k != "use_discriminators"
    }
    json_kwargs = {k: v for k, v in test_kwargs.items() if k in json_specific_params}

    # Get our custom parameter separately
    use_discriminators = test_kwargs.get("use_discriminators", True)

    print(f"\nOriginal kwargs: {test_kwargs}")
    print(f"model_dump kwargs: {model_dump_kwargs}")
    print(f"json.dumps kwargs: {json_kwargs}")
    print(f"use_discriminators: {use_discriminators}")

    # Verify each param is in the right place
    for param, value in test_kwargs.items():
        if param == "use_discriminators":
            assert use_discriminators == value, f"use_discriminators incorrectly handled"
        elif param in json_specific_params:
            assert param in json_kwargs, f"{param} should be in json_kwargs"
            assert json_kwargs[param] == value, f"{param} has wrong value in json_kwargs"
        else:
            assert param in model_dump_kwargs, f"{param} should be in model_dump_kwargs"
            assert (
                model_dump_kwargs[param] == value
            ), f"{param} has wrong value in model_dump_kwargs"

    print("Parameter separation test passed!")

    return json_specific_params


if __name__ == "__main__":
    print("Testing JSON parameter identification and separation")
    print("-" * 70)

    json_specific_params = test_parameter_separation()

    print("\nFinal JSON-specific parameters to use in patched_model_dump_json:")
    print(sorted(json_specific_params))
