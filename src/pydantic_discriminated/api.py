"""
Pydantic Discriminated Union Support

This module provides functionality for working with discriminated unions in Pydantic models.
Discriminated unions allow handling polymorphic data structures in a type-safe way by using
a "discriminator" field to indicate the concrete type.

The module supports:
- Decorating models with discriminator information
- Automatic serialization with discriminator fields
- Registry for looking up model types by discriminator values
- Optional monkey patching of Pydantic's BaseModel for seamless integration
"""

from enum import Enum
import inspect
from typing import (
    Any,
    Dict,
    Type,
    Union,
    Callable,
    ClassVar,
    Optional,
    TypeVar,
    ClassVar,
)
from pydantic import BaseModel, model_serializer
import json

# TypeVar for use in generic type signatures, bound to DiscriminatedBaseModel
T = TypeVar("T", bound="DiscriminatedBaseModel")

# Store original methods in a dictionary when monkey patching
_original_methods = {}


class DiscriminatedConfig:
    """
    Global configuration for discriminated models.

    This class contains settings that control how discriminated models behave,
    including whether to use standard fields, field naming, and monkey patching behavior.

    Attributes:
        use_standard_fields (bool): Whether to include standard discriminator fields
            in addition to domain-specific ones. Default is True.
        standard_category_field (str): The field name for the standard category field.
            Default is "discriminator_category".
        standard_value_field (str): The field name for the standard value field.
            Default is "discriminator_value".
        patch_base_model (bool): Flag to control whether to patch BaseModel.
            Default is True.
        _patched (bool): Internal flag to track if patching has been applied.
            Default is False.
    """

    use_standard_fields: bool = True
    standard_category_field: str = "discriminator_category"
    standard_value_field: str = "discriminator_value"

    # Flag to control whether to patch BaseModel
    patch_base_model: bool = True

    # Flag to track if patching has already been applied
    _patched: bool = False

    @classmethod
    def enable_monkey_patching(cls):
        """
        Enable monkey patching of BaseModel for discriminator support in all models.

        This method enables the automatic inclusion of discriminator fields in
        serialized output from any Pydantic model. It applies the patch if not
        already applied.

        Examples:
            >>> from pydantic_discriminated import DiscriminatedConfig
            >>> DiscriminatedConfig.enable_monkey_patching()
        """
        cls.patch_base_model = True
        # Apply the patch if not already applied
        if not cls._patched:
            _apply_monkey_patch()

    @classmethod
    def disable_monkey_patching(cls):
        """
        Disable monkey patching of BaseModel.

        When disabled, users must use DiscriminatorAwareBaseModel for containers
        that need to preserve discriminator information in serialized output.
        The flag is changed but the patch remains applied to avoid runtime changes
        to method references.

        Examples:
            >>> from pydantic_discriminated import DiscriminatedConfig
            >>> DiscriminatedConfig.disable_monkey_patching()
        """
        print("DEBUG: Disabling monkey patching, previous value:", cls.patch_base_model)
        cls.patch_base_model = False
        print("DEBUG: After disabling, new value:", cls.patch_base_model)


def _apply_monkey_patch():
    """
    Apply monkey patching to BaseModel.

    This function patches Pydantic's BaseModel class to support discriminated unions
    by overriding the model_dump and model_dump_json methods. The patching is applied
    only once (controlled by DiscriminatedConfig._patched).

    Note:
        This is an internal function not meant to be called directly by users.
        Use DiscriminatedConfig.enable_monkey_patching() instead.
    """
    global _original_methods

    # Only patch if not already patched
    if not DiscriminatedConfig._patched:
        # Store original methods
        _original_methods["model_dump"] = BaseModel.model_dump
        _original_methods["model_dump_json"] = BaseModel.model_dump_json

        # Define new methods that use the originals
        def patched_model_dump(self, **kwargs: Any) -> Dict[str, Any]:
            """
            Patched version of model_dump that handles discriminator fields.

            Args:
                **kwargs: Keyword arguments to pass to the original model_dump method.
                    A special 'use_discriminators' parameter can be passed to override
                    the global setting.

            Returns:
                (dict): The serialized model with discriminator fields included or excluded
                    based on configuration.
            """
            # Extract our custom parameter
            use_discriminators = None
            if "use_discriminators" in kwargs:
                use_discriminators = kwargs.pop("use_discriminators")
            else:
                use_discriminators = DiscriminatedConfig.patch_base_model

            print(
                f"DEBUG patched_model_dump: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
            )

            # Get the result from the original method (without our custom parameter)
            result = _original_methods["model_dump"](self, **kwargs)

            # Special handling for nested discriminated models
            # This is the key change - we need to process the result differently
            # based on whether we want discriminator fields or not
            if use_discriminators:
                print("DEBUG: Adding discriminators to serialized data")
                # Process it to add discriminators
                return _process_discriminators(self, result, use_discriminators=True)
            else:
                print("DEBUG: Removing discriminators from serialized data")
                # Process it to REMOVE discriminators from nested models
                return _process_discriminators(self, result, use_discriminators=False)

        # def patched_model_dump_json(self, **kwargs: Any) -> str:
        #     """
        #     Patched version of model_dump_json that handles discriminator fields.

        #     Args:
        #         **kwargs: Keyword arguments to pass to the original model_dump_json method.
        #             A special 'use_discriminators' parameter can be passed to override
        #             the global setting.

        #     Returns:
        #         (str): The JSON string representation of the model with discriminator fields
        #             included or excluded based on configuration.
        #     """
        #     # Extract our custom parameter
        #     use_discriminators = None
        #     if "use_discriminators" in kwargs:
        #         use_discriminators = kwargs.pop("use_discriminators")
        #     else:
        #         use_discriminators = DiscriminatedConfig.patch_base_model

        #     print(
        #         f"DEBUG patched_model_dump_json: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
        #     )

        #     # Separate model_dump kwargs from json.dumps kwargs
        #     # Common JSON arguments that should not be passed to model_dump
        #     json_specific_args = {
        #         "indent",
        #         "ensure_ascii",
        #         "separators",
        #         "default",
        #         "encoder",
        #         "sort_keys",
        #     }

        #     model_dump_kwargs = {k: v for k, v in kwargs.items() if k not in json_specific_args}
        #     json_kwargs = {k: v for k, v in kwargs.items() if k in json_specific_args}

        #     # Add our discriminator flag to model_dump kwargs
        #     model_dump_kwargs["use_discriminators"] = use_discriminators

        #     # Get the model data using patched_model_dump
        #     data = patched_model_dump(self, **model_dump_kwargs)

        #     # Convert to JSON
        #     encoder = json_kwargs.pop("encoder", None) if "encoder" in json_kwargs else None
        #     return json.dumps(data, default=encoder, **json_kwargs)

        # def patched_model_dump_json(self, **kwargs: Any) -> str:
        #     """
        #     Patched version of model_dump_json that handles discriminator fields.

        #     Args:
        #         **kwargs: Keyword arguments to pass to the original model_dump_json method.
        #             A special 'use_discriminators' parameter can be passed to override
        #             the global setting.

        #     Returns:
        #         (str): The JSON string representation of the model with discriminator fields
        #             included or excluded based on configuration.
        #     """
        #     # Extract our custom parameter
        #     use_discriminators = None
        #     if "use_discriminators" in kwargs:
        #         use_discriminators = kwargs.pop("use_discriminators")
        #     else:
        #         use_discriminators = DiscriminatedConfig.patch_base_model

        #     print(
        #         f"DEBUG patched_model_dump_json: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
        #     )

        #     # Get the data with appropriate discriminator handling
        #     data = self.model_dump(use_discriminators=use_discriminators)

        #     # Now call the original model_dump_json but with our processed data
        #     # Since we can't directly pass the data to the original method,
        #     # we need to handle the JSON conversion ourselves

        #     # Get parameters accepted by json.dumps
        #     json_params = set(inspect.signature(json.dumps).parameters.keys())
        #     json_params.add("encoder")  # Special case in Pydantic

        #     # Filter out our custom parameter and extract JSON-specific kwargs
        #     kwargs.pop("use_discriminators", None)  # Remove if present again
        #     json_kwargs = {k: v for k, v in kwargs.items() if k in json_params}

        #     # Handle encoder separately as it maps to 'default' in json.dumps
        #     encoder = json_kwargs.pop("encoder", None) if "encoder" in json_kwargs else None

        #     # Convert to JSON
        #     return json.dumps(data, default=encoder, **json_kwargs)

        # def patched_model_dump_json(self, **kwargs: Any) -> str:
        #     """
        #     Patched version of model_dump_json that handles discriminator fields.

        #     Args:
        #         **kwargs: Keyword arguments to pass to the original model_dump_json method.
        #             A special 'use_discriminators' parameter can be passed to override
        #             the global setting.

        #     Returns:
        #         (str): The JSON string representation of the model with discriminator fields
        #             included or excluded based on configuration.
        #     """
        #     # Extract our custom parameter
        #     use_discriminators = None
        #     if "use_discriminators" in kwargs:
        #         use_discriminators = kwargs.pop("use_discriminators")
        #     else:
        #         use_discriminators = DiscriminatedConfig.patch_base_model

        #     print(
        #         f"DEBUG patched_model_dump_json: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
        #     )

        #     # Process the model to add or remove discriminators as needed
        #     # Note: this creates a new dict that we can pass to json.dumps
        #     data = patched_model_dump(self, use_discriminators=use_discriminators)

        #     # Get the original json.dumps parameters from the kwargs
        #     # Note: we don't need to filter because we already removed our custom parameter
        #     # And we're directly calling json.dumps rather than the original method

        #     # Handle 'encoder' parameter which maps to 'default' in json.dumps
        #     encoder = kwargs.pop("encoder", None) if "encoder" in kwargs else None

        #     # Use json.dumps directly with all remaining kwargs
        #     return json.dumps(data, default=encoder, **kwargs)

        # def patched_model_dump_json(self, **kwargs: Any) -> str:
        #     # Extract our custom parameter
        #     use_discriminators = None
        #     if "use_discriminators" in kwargs:
        #         use_discriminators = kwargs.pop("use_discriminators")
        #     else:
        #         use_discriminators = DiscriminatedConfig.patch_base_model

        #     # Get JSON parameters dynamically using inspect
        #     json_params = set(inspect.signature(json.dumps).parameters.keys())
        #     if "obj" in json_params:
        #         json_params.remove("obj")
        #     json_params.add("encoder")

        #     # Split kwargs into model_dump and json kwargs
        #     model_dump_kwargs = {}
        #     json_kwargs = {}

        #     for k, v in kwargs.items():
        #         if k in json_params:
        #             json_kwargs[k] = v
        #         else:
        #             model_dump_kwargs[k] = v

        #     # Get model data and process discriminators
        #     data = _original_methods["model_dump"](self, **model_dump_kwargs)
        #     data = _process_discriminators(self, data, use_discriminators=use_discriminators)

        #     # Handle encoder parameter
        #     encoder = json_kwargs.pop("encoder", None) if "encoder" in json_kwargs else None

        #     # Convert to JSON
        #     return json.dumps(data, default=encoder, **json_kwargs)
        def patched_model_dump_json(self, **kwargs: Any) -> str:
            """
            Patched version of model_dump_json that handles discriminator fields.

            Args:
                **kwargs: Keyword arguments to pass to the original model_dump_json method.
                    A special 'use_discriminators' parameter can be passed to override
                    the global setting.

            Returns:
                (str): The JSON string representation of the model with discriminator fields
                    included or excluded based on configuration.
            """
            # Extract our custom parameter
            use_discriminators = None
            if "use_discriminators" in kwargs:
                use_discriminators = kwargs.pop("use_discriminators")
            else:
                use_discriminators = DiscriminatedConfig.patch_base_model

            print(
                f"DEBUG patched_model_dump_json: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
            )

            # Get JSON parameters dynamically using inspect
            json_params = set(inspect.signature(json.dumps).parameters.keys())
            # Remove 'obj' which is the first positional parameter of json.dumps
            if "obj" in json_params:
                json_params.remove("obj")
            # Add 'encoder' which is Pydantic-specific and maps to 'default' in json.dumps
            json_params.add("encoder")

            # Split kwargs into model_dump and json kwargs
            model_dump_kwargs = {}
            json_kwargs = {}

            for k, v in kwargs.items():
                if k in json_params:
                    json_kwargs[k] = v
                else:
                    # If not a JSON parameter, assume it's for model_dump
                    model_dump_kwargs[k] = v

            # Get model data with discriminators handled appropriately
            # Instead of calling model_dump directly, use the original method and process the result
            data = _original_methods["model_dump"](self, **model_dump_kwargs)
            data = _process_discriminators(self, data, use_discriminators=use_discriminators)

            # Handle encoder parameter specifically
            encoder = json_kwargs.pop("encoder", None) if "encoder" in json_kwargs else None

            # Convert to JSON
            return json.dumps(data, default=encoder, **json_kwargs)

        # Apply patches
        BaseModel.model_dump = patched_model_dump
        BaseModel.model_dump_json = patched_model_dump_json

        # Mark as patched
        DiscriminatedConfig._patched = True


# def _process_discriminators(model, data, use_discriminators=True):
#     """
#     Process data to add or remove discriminators for nested models.

#     This function recursively processes a data structure to add or remove discriminator
#     fields from discriminated models at all nesting levels.

#     Args:
#         model: The model instance that produced the data.
#         data: The data to process.
#         use_discriminators: Whether to include discriminator fields. Defaults to True.

#     Returns:
#         The processed data with discriminators added or removed according to the
#         use_discriminators parameter.

#     Note:
#         This is an internal function not meant to be called directly by users.
#     """
#     # Add debugging to see when this is called
#     print(
#         f"DEBUG _process_discriminators: processing model type {type(model).__name__}, use_discriminators={use_discriminators}"
#     )

#     # Handle dictionaries
#     if isinstance(data, dict):
#         result = {}
#         for key, value in data.items():
#             # Get the original field value from the model if possible
#             field_value = getattr(model, key, None)


#             # Process based on field type
#             if isinstance(field_value, list) and isinstance(value, list):
#                 # Handle lists of models
#                 result[key] = []
#                 for idx, (item, item_data) in enumerate(zip(field_value, value)):
#                     if isinstance(item, DiscriminatedBaseModel):
#                         # For discriminated models, use their own model_dump with our flag
#                         try:
#                             processed_data = item.model_dump(use_discriminators=use_discriminators)
#                             result[key].append(processed_data)
#                         except Exception as e:
#                             print(f"DEBUG: Error processing item {idx} in list: {e}")
#                             # Fall back to original data if there's an error
#                             if use_discriminators:
#                                 # Add discriminator fields
#                                 item_data = dict(item_data)  # Make a copy
#                                 item_data[item._discriminator_field] = item._discriminator_value
#                                 if getattr(
#                                     item,
#                                     "_use_standard_fields",
#                                     DiscriminatedConfig.use_standard_fields,
#                                 ):
#                                     item_data[DiscriminatedConfig.standard_category_field] = (
#                                         item._discriminator_field
#                                     )
#                                     item_data[DiscriminatedConfig.standard_value_field] = (
#                                         item._discriminator_value
#                                     )
#                             else:
#                                 # Remove discriminator fields
#                                 item_data = dict(item_data)  # Make a copy
#                                 if item._discriminator_field in item_data:
#                                     del item_data[item._discriminator_field]
#                                 if DiscriminatedConfig.standard_category_field in item_data:
#                                     del item_data[DiscriminatedConfig.standard_category_field]
#                                 if DiscriminatedConfig.standard_value_field in item_data:
#                                     del item_data[DiscriminatedConfig.standard_value_field]
#                             result[key].append(item_data)
#                     elif isinstance(item, BaseModel):
#                         # For other models, process recursively
#                         processed_data = _process_discriminators(
#                             item, item_data, use_discriminators
#                         )
#                         result[key].append(processed_data)
#                     else:
#                         # For other types, keep as is
#                         result[key].append(item_data)
#             elif isinstance(field_value, DiscriminatedBaseModel) and isinstance(value, dict):
#                 # It's a discriminated model - use its model_dump with our flag
#                 try:
#                     result[key] = field_value.model_dump(use_discriminators=use_discriminators)
#                 except Exception as e:
#                     print(f"DEBUG: Error processing field {key}: {e}")
#                     # Fall back to manual processing
#                     if use_discriminators:
#                         # Add discriminator fields
#                         value_copy = dict(value)  # Make a copy
#                         value_copy[field_value._discriminator_field] = (
#                             field_value._discriminator_value
#                         )
#                         if getattr(
#                             field_value,
#                             "_use_standard_fields",
#                             DiscriminatedConfig.use_standard_fields,
#                         ):
#                             value_copy[DiscriminatedConfig.standard_category_field] = (
#                                 field_value._discriminator_field
#                             )
#                             value_copy[DiscriminatedConfig.standard_value_field] = (
#                                 field_value._discriminator_value
#                             )
#                         result[key] = value_copy
#                     else:
#                         # Remove discriminator fields
#                         value_copy = dict(value)  # Make a copy
#                         if field_value._discriminator_field in value_copy:
#                             del value_copy[field_value._discriminator_field]
#                         if DiscriminatedConfig.standard_category_field in value_copy:
#                             del value_copy[DiscriminatedConfig.standard_category_field]
#                         if DiscriminatedConfig.standard_value_field in value_copy:
#                             del value_copy[DiscriminatedConfig.standard_value_field]
#                         result[key] = value_copy
#             elif isinstance(field_value, BaseModel) and isinstance(value, dict):
#                 # It's a regular BaseModel - process it recursively
#                 result[key] = _process_discriminators(field_value, value, use_discriminators)
#             else:
#                 # Other types - keep as is
#                 result[key] = value
#         return result
#     # Handle other types
#     return data
# def _process_discriminators(model, data, use_discriminators=True):
#     """
#     Process data to add or remove discriminators for nested models.

#     This function recursively processes a data structure to add or remove discriminator
#     fields from discriminated models at all nesting levels.

#     Args:
#         model: The model instance that produced the data.
#         data: The data to process.
#         use_discriminators: Whether to include discriminator fields. Defaults to True.

#     Returns:
#         The processed data with discriminators added or removed according to the
#         use_discriminators parameter.
#     """
#     # Add debugging to see when this is called
#     print(
#         f"DEBUG _process_discriminators: processing model type {type(model).__name__}, use_discriminators={use_discriminators}"
#     )

#     # Handle dictionaries
#     if isinstance(data, dict):
#         result = {}
#         for key, value in data.items():
#             # Get the original field value from the model if possible
#             field_value = getattr(model, key, None)

#             # Process based on field type
#             if isinstance(field_value, list) and isinstance(value, list):
#                 # Handle lists of models
#                 result[key] = []
#                 for idx, item_data in enumerate(value):
#                     # Try to get the original item, but it might not be accessible
#                     item = None
#                     if idx < len(field_value):
#                         item = field_value[idx]


#                     if isinstance(item, DiscriminatedBaseModel) and isinstance(item_data, dict):
#                         # Process discriminated models in lists
#                         if use_discriminators:
#                             # Add discriminator fields
#                             item_data_copy = dict(item_data)  # Make a copy
#                             item_data_copy[item._discriminator_field] = item._discriminator_value
#                             if getattr(
#                                 item,
#                                 "_use_standard_fields",
#                                 DiscriminatedConfig.use_standard_fields,
#                             ):
#                                 item_data_copy[DiscriminatedConfig.standard_category_field] = (
#                                     item._discriminator_field
#                                 )
#                                 item_data_copy[DiscriminatedConfig.standard_value_field] = (
#                                     item._discriminator_value
#                                 )
#                             result[key].append(item_data_copy)
#                         else:
#                             # Remove discriminator fields
#                             item_data_copy = dict(item_data)  # Make a copy
#                             if item._discriminator_field in item_data_copy:
#                                 del item_data_copy[item._discriminator_field]
#                             if DiscriminatedConfig.standard_category_field in item_data_copy:
#                                 del item_data_copy[DiscriminatedConfig.standard_category_field]
#                             if DiscriminatedConfig.standard_value_field in item_data_copy:
#                                 del item_data_copy[DiscriminatedConfig.standard_value_field]
#                             result[key].append(item_data_copy)
#                     elif isinstance(item, BaseModel) and isinstance(item_data, dict):
#                         # Recursively process other models in lists
#                         processed_data = _process_discriminators(
#                             item, item_data, use_discriminators
#                         )
#                         result[key].append(processed_data)
#                     elif isinstance(item_data, dict):
#                         # Special case: could be a discriminated model without the original object
#                         # Check for discriminator fields in the data
#                         if not use_discriminators and "animal_type" in item_data:
#                             # This looks like a discriminated model, remove discriminator fields
#                             item_data_copy = dict(item_data)
#                             for disc_field in [
#                                 "animal_type",
#                                 DiscriminatedConfig.standard_category_field,
#                                 DiscriminatedConfig.standard_value_field,
#                             ]:
#                                 if disc_field in item_data_copy:
#                                     del item_data_copy[disc_field]
#                             result[key].append(item_data_copy)
#                         else:
#                             # Just process it recursively as a normal dictionary
#                             processed_data = _process_discriminators(
#                                 type("DummyModel", (BaseModel,), {})(),
#                                 item_data,
#                                 use_discriminators,
#                             )
#                             result[key].append(processed_data)
#                     elif isinstance(item_data, list):
#                         # Handle lists in lists recursively
#                         processed_items = []
#                         for sub_item in item_data:
#                             if isinstance(sub_item, dict):
#                                 processed_sub_item = _process_discriminators(
#                                     type("DummyModel", (BaseModel,), {})(),
#                                     sub_item,
#                                     use_discriminators,
#                                 )
#                                 processed_items.append(processed_sub_item)
#                             else:
#                                 processed_items.append(sub_item)
#                         result[key].append(processed_items)
#                     else:
#                         # Other types in lists - keep as is
#                         result[key].append(item_data)
#             elif isinstance(field_value, DiscriminatedBaseModel) and isinstance(value, dict):
#                 # Process discriminated models
#                 if use_discriminators:
#                     # Add discriminator fields
#                     value_copy = dict(value)  # Make a copy
#                     value_copy[field_value._discriminator_field] = field_value._discriminator_value
#                     if getattr(
#                         field_value, "_use_standard_fields", DiscriminatedConfig.use_standard_fields
#                     ):
#                         value_copy[DiscriminatedConfig.standard_category_field] = (
#                             field_value._discriminator_field
#                         )
#                         value_copy[DiscriminatedConfig.standard_value_field] = (
#                             field_value._discriminator_value
#                         )
#                     result[key] = value_copy
#                 else:
#                     # Remove discriminator fields
#                     value_copy = dict(value)  # Make a copy
#                     if field_value._discriminator_field in value_copy:
#                         del value_copy[field_value._discriminator_field]
#                     if DiscriminatedConfig.standard_category_field in value_copy:
#                         del value_copy[DiscriminatedConfig.standard_category_field]
#                     if DiscriminatedConfig.standard_value_field in value_copy:
#                         del value_copy[DiscriminatedConfig.standard_value_field]
#                     result[key] = value_copy
#             elif isinstance(field_value, BaseModel) and isinstance(value, dict):
#                 # Recursively process other models
#                 result[key] = _process_discriminators(field_value, value, use_discriminators)
#             elif isinstance(value, dict):
#                 # Special case for nested dictionaries
#                 processed_dict = {}
#                 for sub_key, sub_value in value.items():
#                     if isinstance(sub_value, list):
#                         # Handle lists in dictionaries
#                         processed_list = []
#                         for sub_item in sub_value:
#                             if isinstance(sub_item, dict):
#                                 # Check if it looks like a discriminated model
#                                 if not use_discriminators and "animal_type" in sub_item:
#                                     # Remove discriminator fields
#                                     sub_item_copy = dict(sub_item)
#                                     for disc_field in [
#                                         "animal_type",
#                                         DiscriminatedConfig.standard_category_field,
#                                         DiscriminatedConfig.standard_value_field,
#                                     ]:
#                                         if disc_field in sub_item_copy:
#                                             del sub_item_copy[disc_field]
#                                     processed_list.append(sub_item_copy)
#                                 else:
#                                     # Process it recursively
#                                     processed_sub_item = _process_discriminators(
#                                         type("DummyModel", (BaseModel,), {})(),
#                                         sub_item,
#                                         use_discriminators,
#                                     )
#                                     processed_list.append(processed_sub_item)
#                             else:
#                                 processed_list.append(sub_item)
#                         processed_dict[sub_key] = processed_list
#                     elif isinstance(sub_value, dict):
#                         # Recursively process nested dictionaries
#                         processed_dict[sub_key] = _process_discriminators(
#                             type("DummyModel", (BaseModel,), {})(), sub_value, use_discriminators
#                         )
#                     else:
#                         processed_dict[sub_key] = sub_value
#                 result[key] = processed_dict
#             elif isinstance(value, list):
#                 # Handle lists that might contain nested models
#                 result[key] = []
#                 for item_data in value:
#                     if isinstance(item_data, dict):
#                         # Check if it looks like a discriminated model
#                         if not use_discriminators and "animal_type" in item_data:
#                             # Remove discriminator fields
#                             item_data_copy = dict(item_data)
#                             for disc_field in [
#                                 "animal_type",
#                                 DiscriminatedConfig.standard_category_field,
#                                 DiscriminatedConfig.standard_value_field,
#                             ]:
#                                 if disc_field in item_data_copy:
#                                     del item_data_copy[disc_field]
#                             result[key].append(item_data_copy)
#                         else:
#                             # Process it recursively
#                             processed_data = _process_discriminators(
#                                 type("DummyModel", (BaseModel,), {})(),
#                                 item_data,
#                                 use_discriminators,
#                             )
#                             result[key].append(processed_data)
#                     elif isinstance(item_data, list):
#                         # Handle nested lists
#                         processed_items = []
#                         for sub_item in item_data:
#                             if isinstance(sub_item, dict):
#                                 processed_sub_item = _process_discriminators(
#                                     type("DummyModel", (BaseModel,), {})(),
#                                     sub_item,
#                                     use_discriminators,
#                                 )
#                                 processed_items.append(processed_sub_item)
#                             else:
#                                 processed_items.append(sub_item)
#                         result[key].append(processed_items)
#                     else:
#                         result[key].append(item_data)
#             else:
#                 # Other types - keep as is
#                 result[key] = value
#         return result
#     elif isinstance(data, list):
#         # Handle top-level lists
#         result = []
#         for item in data:
#             if isinstance(item, dict):
#                 # Check if it looks like a discriminated model
#                 if not use_discriminators and "animal_type" in item:
#                     # Remove discriminator fields
#                     item_copy = dict(item)
#                     for disc_field in [
#                         "animal_type",
#                         DiscriminatedConfig.standard_category_field,
#                         DiscriminatedConfig.standard_value_field,
#                     ]:
#                         if disc_field in item_copy:
#                             del item_copy[disc_field]
#                     result.append(item_copy)
#                 else:
#                     # Process it recursively
#                     processed_item = _process_discriminators(
#                         type("DummyModel", (BaseModel,), {})(), item, use_discriminators
#                     )
#                     result.append(processed_item)
#             elif isinstance(item, list):
#                 # Handle nested lists
#                 processed_items = []
#                 for sub_item in item:
#                     if isinstance(sub_item, dict):
#                         processed_sub_item = _process_discriminators(
#                             type("DummyModel", (BaseModel,), {})(), sub_item, use_discriminators
#                         )
#                         processed_items.append(processed_sub_item)
#                     else:
#                         processed_items.append(sub_item)
#                 result.append(processed_items)
#             else:
#                 result.append(item)
#         return result
#     # Handle other types
#     return data
def _process_discriminators(model, data, use_discriminators=True):
    """
    Process data to add or remove discriminators for nested models.

    This function recursively processes a data structure to add or remove discriminator
    fields from discriminated models at all nesting levels. It handles any type of
    Python collection including dictionaries, lists, tuples, sets, and custom iterables.

    Args:
        model: The model instance that produced the data.
        data: The data to process (any type).
        use_discriminators: Whether to include discriminator fields. Defaults to True.

    Returns:
        The processed data with discriminators added or removed according to the
        use_discriminators parameter.
    """
    print(
        f"DEBUG _process_discriminators: processing model type {type(model).__name__}, use_discriminators={use_discriminators}"
    )

    # Get all known discriminator field names from the registry
    known_discriminator_fields = set(DiscriminatedModelRegistry._registry.keys())
    # Add standard fields to the set
    standard_fields = {
        DiscriminatedConfig.standard_category_field,
        DiscriminatedConfig.standard_value_field,
    }

    def process_value(value, parent_model=None, field_name=None):
        """
        Process any value recursively, handling collection types appropriately.

        Args:
            value: The value to process.
            parent_model: The model that contains this value, if available.
            field_name: The field name in the parent model, if available.

        Returns:
            Processed value with discriminators handled appropriately.
        """
        # Handle different types of values
        if isinstance(value, dict):
            return process_dict(value, parent_model)
        elif isinstance(value, (list, tuple, set)):
            return process_collection(value, parent_model, field_name)
        else:
            # For non-collection types, return as is
            return value

    def process_dict(d, parent_model=None):
        """
        Process a dictionary, handling discriminator fields appropriately.

        Args:
            d: The dictionary to process.
            parent_model: The model that contains this dictionary, if available.

        Returns:
            Processed dictionary with discriminators handled appropriately.
        """
        if not isinstance(d, dict):
            return d

        result = {}
        for key, value in d.items():
            # Check if this key is a discriminator field
            is_discriminator = key in known_discriminator_fields or key in standard_fields

            # Handle based on whether we want discriminators and what type the value is
            if is_discriminator and not use_discriminators:
                # Skip discriminator fields when not wanted
                continue
            else:
                # Get the field model if available
                field_model = getattr(parent_model, key, None) if parent_model else None
                # Process the value recursively
                result[key] = process_value(value, field_model, key)

        return result

    def process_collection(collection, parent_model=None, field_name=None):
        """
        Process any collection type (list, tuple, set, etc.), handling items appropriately.

        Args:
            collection: The collection to process.
            parent_model: The model that contains this collection, if available.
            field_name: The field name in the parent model, if available.

        Returns:
            Processed collection with discriminators handled appropriately.
        """
        # Try to get the collection field from the parent model
        original_items = []
        if parent_model and field_name:
            original_field = getattr(parent_model, field_name, None)
            if isinstance(original_field, (list, tuple, set)):
                original_items = list(original_field)

        # Create results of the same type as the input
        result_items = []

        # Process each item
        for i, item in enumerate(collection):
            # Try to get original model for this item
            original_model = original_items[i] if i < len(original_items) else None

            # Process the item recursively
            processed_item = process_value(item, original_model, None)
            result_items.append(processed_item)

        # Convert result back to the original collection type
        if isinstance(collection, list):
            return result_items
        elif isinstance(collection, tuple):
            return tuple(result_items)
        elif isinstance(collection, set):
            return set(result_items)
        else:
            # For any other collection type, try to instantiate with the processed items
            # Fall back to returning a list if that fails
            try:
                return type(collection)(result_items)
            except Exception:
                return result_items

    # Start processing from the top level
    return process_value(data, model)


class DiscriminatedModelRegistry:
    """
    Registry to store and retrieve discriminated models.

    This class maintains a registry of discriminated models indexed by their
    category and discriminator value, allowing lookup of the appropriate model class
    at validation time.

    Attributes:
        _registry (Dict[str, Dict[Any, Type["DiscriminatedBaseModel"]]]): Internal registry
            storing models by category and discriminator value.
    """

    _registry: Dict[str, Dict[Any, Type["DiscriminatedBaseModel"]]] = {}

    @classmethod
    def register(cls, category: str, value: Any, model_cls: Type["DiscriminatedBaseModel"]) -> None:
        """
        Register a model class for a specific category and discriminator value.

        Args:
            category (str): The discriminator category (field name).
            value (Any): The discriminator value.
            model_cls : The model class to register.

        Examples:
            >>> DiscriminatedModelRegistry.register("shape_type", "circle", Circle)
        """
        if category not in cls._registry:
            cls._registry[category] = {}
        cls._registry[category][value] = model_cls

    @classmethod
    def get_model(cls, category: str, value: Any) -> Type["DiscriminatedBaseModel"]:
        """
        Get a model class by category and discriminator value.

        Args:
            category: The discriminator category (field name).
            value: The discriminator value.

        Returns:
            Type["DiscriminatedBaseModel"]: The model class registered for this category and value.

        Raises:
            ValueError: If no model is registered for the given category and value.

        Examples:
            >>> model_cls = DiscriminatedModelRegistry.get_model("shape_type", "circle")
            >>> instance = model_cls(radius=5)
        """
        if category not in cls._registry:
            raise ValueError(f"No models registered for category '{category}'")
        if value not in cls._registry[category]:
            raise ValueError(f"No model found for value '{value}' in category '{category}'")
        return cls._registry[category][value]

    @classmethod
    def get_models_for_category(cls, category: str) -> Dict[Any, Type["DiscriminatedBaseModel"]]:
        """
        Get all models registered for a specific category.

        Args:
            category: The discriminator category (field name).

        Returns:
            Dict[Any, Type["DiscriminatedBaseModel"]]: Dictionary mapping discriminator values
                to model classes for the specified category.

        Raises:
            ValueError: If no models are registered for the given category.

        Examples:
            >>> models = DiscriminatedModelRegistry.get_models_for_category("shape_type")
            >>> for value, model_cls in models.items():
            ...     print(f"{value}: {model_cls.__name__}")
        """
        if category not in cls._registry:
            raise ValueError(f"No models registered for category '{category}'")
        return cls._registry[category]


class DiscriminatorAwareBaseModel(BaseModel):
    """
    Base model that handles discriminators in serialization, including nested models.

    Use this as a base class for container models when monkey patching is disabled.
    This class ensures that discriminator fields are properly included in serialized
    output even when the global monkey patching is disabled.

    Examples:
        >>> class Container(DiscriminatorAwareBaseModel):
        ...     shape: Circle
        >>> container = Container(shape=Circle(radius=5))
        >>> data = container.model_dump()  # Will include discriminator fields
    """

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Override model_dump to include discriminators at all nesting levels.

        This method ensures that discriminator fields are included in the serialized
        output regardless of the global monkey patching setting.

        Args:
            **kwargs: Keyword arguments to pass to the parent model_dump method.

        Returns:
            (dict): The serialized model with discriminator fields included.
        """
        # Always use discriminators for this class by setting the flag
        kwargs["use_discriminators"] = True

        # Get standard serialization with discriminators
        if DiscriminatedConfig._patched:
            # If BaseModel is patched, use the patched method with our flag
            return super().model_dump(**kwargs)
        else:
            # If not patched, use the original method and process it ourselves
            result = super().model_dump(**kwargs)
            return _process_discriminators(self, result)

    def model_dump_json(self, **kwargs: Any) -> str:
        """
        Override model_dump_json to include discriminators at all nesting levels.

        This method ensures that discriminator fields are included in the JSON
        serialized output regardless of the global monkey patching setting.

        Args:
            **kwargs: Keyword arguments to pass to the parent model_dump_json method.

        Returns:
            (str): The JSON string representation of the model with discriminator fields included.
        """
        # Always use discriminators for this class
        kwargs["use_discriminators"] = True

        # Get data with discriminators (will use our overridden model_dump)
        if DiscriminatedConfig._patched:
            # If patched, use the patched method with our flag
            return super().model_dump_json(**kwargs)
        else:
            # If not patched, get data and convert to JSON ourselves
            data = self.model_dump(**kwargs)
            encoder = kwargs.pop("encoder", None)
            return json.dumps(data, default=encoder, **kwargs)


class DiscriminatedBaseModel(BaseModel):
    """
    Base class for discriminated models that ensures discriminator fields are included
    in serialization only when requested.

    This class must be used as the base class for all models that will be part of
    a discriminated union. It provides methods for validating and serializing
    discriminated models.

    Attributes:
        _discriminator_field (ClassVar[str]): The discriminator field name.
        _discriminator_value (ClassVar[Any]): The discriminator value for this model.
        _use_standard_fields (ClassVar[bool]): Whether to use standard discriminator fields.
            Defaults to the global setting in DiscriminatedConfig.

    Examples:
        >>> @discriminated_model("shape_type", "circle")
        ... class Circle(DiscriminatedBaseModel):
        ...     radius: float
        >>> circle = Circle(radius=5)
        >>> data = circle.model_dump()  # Includes discriminator fields
    """

    # Legacy fields for compatibility
    _discriminator_field: ClassVar[str] = ""
    _discriminator_value: ClassVar[Any] = None
    _use_standard_fields: ClassVar[bool] = DiscriminatedConfig.use_standard_fields

    def __getattr__(self, name: str) -> Any:
        """
        Custom attribute access to handle discriminator field.

        This method allows accessing the discriminator value through the discriminator
        field name, as well as through the standard discriminator fields.

        Args:
            name (str): The attribute name being accessed.

        Returns:
            (Any): The discriminator value if name is the discriminator field or a standard
            discriminator field, otherwise raises AttributeError.

        Raises:
            (AttributeError): If the attribute doesn't exist and isn't a discriminator field.
        """
        # Handle access to the legacy discriminator field
        if name == self._discriminator_field:
            return self._discriminator_value

        # Handle access to standard discriminator fields
        if name == DiscriminatedConfig.standard_category_field:
            return self._discriminator_field
        if name == DiscriminatedConfig.standard_value_field:
            return self._discriminator_value

        # Default behavior for other attributes
        return super().__getattr__(name)

    def model_dump(self, **kwargs: Any):
        """
        Override model_dump to control when discriminators are included.

        This method allows controlling whether discriminator fields are included
        in the serialized output using the use_discriminators parameter or the
        global setting.

        Args:
            **kwargs: Keyword arguments to pass to the parent model_dump method.
                A special 'use_discriminators' parameter can be passed to override
                the global setting.

        Returns:
            (dict): The serialized model with discriminator fields included or excluded
                based on configuration.
        """
        # Extract our custom parameter or use the global setting
        use_discriminators = kwargs.pop("use_discriminators", DiscriminatedConfig.patch_base_model)
        print(f"DEBUG DiscriminatedBaseModel.model_dump: use_discriminators={use_discriminators}")

        # Get the result from the original method (without our custom parameter)
        if DiscriminatedConfig._patched:
            # If patched, use the original method via the global store
            # Make a copy of kwargs to avoid modifying the original
            kwargs_copy = kwargs.copy()
            if "use_discriminators" in kwargs_copy:
                del kwargs_copy["use_discriminators"]
            data = _original_methods["model_dump"](self, **kwargs_copy)
        else:
            # If not patched, use the superclass method
            data = super().model_dump(**kwargs)

        # Remove discriminator fields if they shouldn't be included
        if not use_discriminators:
            # Remove domain-specific discriminator field
            if self._discriminator_field in data:
                data.pop(self._discriminator_field)

            # Remove standard fields if present
            if self._use_standard_fields:
                if DiscriminatedConfig.standard_category_field in data:
                    data.pop(DiscriminatedConfig.standard_category_field)
                if DiscriminatedConfig.standard_value_field in data:
                    data.pop(DiscriminatedConfig.standard_value_field)

        return data

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """
        Custom serializer that includes discriminator fields only when requested.

        This method is used by Pydantic's serialization system to convert the model
        to a dictionary. It includes the discriminator fields, which can later be
        filtered out by model_dump if needed.

        Returns:
            (dict): Dictionary representation of the model, including discriminator fields.
        """
        # Get all field values without special handling
        data = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

        # Add discriminator fields if configured to do so in global settings
        # These will be filtered in model_dump if needed
        if self._discriminator_field and self._discriminator_value is not None:
            data[self._discriminator_field] = self._discriminator_value

        # Add standard fields if configured
        if self._use_standard_fields:
            data[DiscriminatedConfig.standard_category_field] = self._discriminator_field
            data[DiscriminatedConfig.standard_value_field] = self._discriminator_value

        return data

    @classmethod
    def model_validate(cls: Type[T], obj: Any, **kwargs: Any) -> T:
        """
        Validate the given object and return an instance of this model.

        Enhanced to handle discriminator validation. This method checks if the
        discriminator value in the input data matches the expected value for this
        model class.

        Args:
            obj: The object to validate.
            **kwargs: Additional arguments to pass to the original model_validate.

        Returns:
            An instance of this model.

        Raises:
            ValueError: If the discriminator value in the input data doesn't match
                the expected value for this model class.

        Examples:
            >>> data = {"shape_type": "circle", "radius": 5}
            >>> circle = Circle.model_validate(data)
        """
        use_standard_fields = getattr(
            cls, "_use_standard_fields", DiscriminatedConfig.use_standard_fields
        )

        if isinstance(obj, dict):
            new_obj = obj.copy()  # Create a copy to avoid modifying the original

            # Check if we have standard discriminator fields
            if (
                use_standard_fields
                and DiscriminatedConfig.standard_category_field in new_obj
                and DiscriminatedConfig.standard_value_field in new_obj
            ):

                # Use standard fields for validation
                if new_obj[DiscriminatedConfig.standard_category_field] != cls._discriminator_field:
                    raise ValueError(
                        f"Invalid discriminator category: expected {cls._discriminator_field}, "
                        f"got {new_obj[DiscriminatedConfig.standard_category_field]}"
                    )
                if new_obj[DiscriminatedConfig.standard_value_field] != cls._discriminator_value:
                    raise ValueError(
                        f"Invalid discriminator value: expected {cls._discriminator_value}, "
                        f"got {new_obj[DiscriminatedConfig.standard_value_field]}"
                    )

            # Check legacy field if present
            elif cls._discriminator_field and cls._discriminator_field in new_obj:
                if new_obj[cls._discriminator_field] != cls._discriminator_value:
                    raise ValueError(
                        f"Invalid discriminator value: expected {cls._discriminator_value}, "
                        f"got {new_obj[cls._discriminator_field]}"
                    )

            # Add domain-specific discriminator field if missing
            if cls._discriminator_field and cls._discriminator_field not in new_obj:
                new_obj[cls._discriminator_field] = cls._discriminator_value

            # Add standard discriminator fields if configured and missing
            if use_standard_fields:
                if DiscriminatedConfig.standard_category_field not in new_obj:
                    new_obj[DiscriminatedConfig.standard_category_field] = cls._discriminator_field
                if DiscriminatedConfig.standard_value_field not in new_obj:
                    new_obj[DiscriminatedConfig.standard_value_field] = cls._discriminator_value

            obj = new_obj

        # Call the original model_validate
        instance = super().model_validate(obj, **kwargs)

        # Set the discriminator values on the instance
        object.__setattr__(instance, "_discriminator_field", cls._discriminator_field)
        object.__setattr__(instance, "_discriminator_value", cls._discriminator_value)
        object.__setattr__(instance, "_use_standard_fields", use_standard_fields)

        # For backward compatibility, also set the domain-specific field
        if cls._discriminator_field:
            object.__setattr__(instance, cls._discriminator_field, cls._discriminator_value)

        # Set standard fields if configured
        if use_standard_fields:
            object.__setattr__(
                instance,
                DiscriminatedConfig.standard_category_field,
                cls._discriminator_field,
            )
            object.__setattr__(
                instance,
                DiscriminatedConfig.standard_value_field,
                cls._discriminator_value,
            )

        return instance

    @classmethod
    def model_validate_json(cls: Type[T], json_data: Union[str, bytes], **kwargs: Any) -> T:
        """
        Validate the given JSON data and return an instance of this model.

        Enhanced to handle discriminator validation. This method parses the JSON data
        and then uses model_validate to validate it.

        Args:
            json_data: The JSON data to validate.
            **kwargs: Additional arguments to pass to model_validate.

        Returns:
            An instance of this model.

        Examples:
            >>> json_str = '{"shape_type": "circle", "radius": 5}'
            >>> circle = Circle.model_validate_json(json_str)
        """
        # Parse JSON first
        if isinstance(json_data, bytes):
            json_data = json_data.decode()
        data = json.loads(json_data)

        # Now validate with our enhanced model_validate
        return cls.model_validate(data, **kwargs)

    @classmethod
    def validate_discriminated(cls, data: Dict[str, Any]) -> "DiscriminatedBaseModel":
        """
        Validate and return the appropriate discriminated model based on the discriminator value.

        This method looks at the discriminator fields in the data and dispatches
        to the appropriate model class based on the discriminator value.

        Args:
            data: The data to validate.

        Returns:
            An instance of the appropriate discriminated model.

        Raises:
            ValueError: If no discriminator fields are found in the data.

        Examples:
            >>> data = {"shape_type": "circle", "radius": 5}
            >>> shape = DiscriminatedBaseModel.validate_discriminated(data)
            >>> isinstance(shape, Circle)
            True
        """
        use_standard_fields = getattr(
            cls, "_use_standard_fields", DiscriminatedConfig.use_standard_fields
        )

        # First check standard discriminator fields if configured
        if (
            use_standard_fields
            and DiscriminatedConfig.standard_category_field in data
            and DiscriminatedConfig.standard_value_field in data
        ):

            category = data[DiscriminatedConfig.standard_category_field]
            value = data[DiscriminatedConfig.standard_value_field]

        # Fall back to domain-specific field
        elif cls._discriminator_field and cls._discriminator_field in data:
            category = cls._discriminator_field
            value = data[cls._discriminator_field]
        else:
            raise ValueError(f"No discriminator fields found in data")

        # Get the appropriate model class
        model_cls = DiscriminatedModelRegistry.get_model(category, value)

        # Validate with the model class
        return model_cls.model_validate(data)


def discriminated_model(
    category: Union[str, Type[Enum]],
    discriminator: Any,
    use_standard_fields: Optional[bool] = None,
) -> Callable[[Type[T]], Type[T]]:
    """
    Decorator to create a discriminated model.

    This decorator registers a model class with the DiscriminatedModelRegistry
    and sets up the discriminator field and value.

    Args:
        category: The category field name or Enum class. If an Enum class is provided,
            its lowercase name is used as the field name.
        discriminator: The discriminator value for this model.
        use_standard_fields: Whether to use standard discriminator fields.
            Defaults to the global setting in DiscriminatedConfig.

    Returns:
        A decorator function that registers the model class.

    Examples:
        >>> @discriminated_model("shape_type", "circle")
        ... class Circle(DiscriminatedBaseModel):
        ...     radius: float

        >>> from enum import Enum
        >>> class ShapeType(str, Enum):
        ...     CIRCLE = "circle"
        ...     RECTANGLE = "rectangle"
        >>> @discriminated_model(ShapeType, ShapeType.CIRCLE)
        ... class Circle(DiscriminatedBaseModel):
        ...     radius: float
    """
    category_field = category
    if isinstance(category, type) and issubclass(category, Enum):
        category_field = category.__name__.lower()

    field_name = str(category_field)

    def decorator(cls: Type[T]) -> Type[T]:
        """
        The actual decorator function that transforms the model class.

        This inner function registers the model class with the DiscriminatedModelRegistry,
        sets up discriminator attributes, and overrides __init__ to ensure discriminator
        values are set correctly.

        Args:
            cls: The model class to decorate.

        Returns:
            The decorated model class.

        Raises:
            TypeError: If the class doesn't inherit from DiscriminatedBaseModel.
        """
        # Make sure the class inherits from DiscriminatedBaseModel
        if not issubclass(cls, DiscriminatedBaseModel):
            raise TypeError(f"{cls.__name__} must inherit from DiscriminatedBaseModel")

        # Register the model
        DiscriminatedModelRegistry.register(field_name, discriminator, cls)

        # Store the discriminator information as class variables
        cls._discriminator_field = field_name
        cls._discriminator_value = discriminator

        # Set standard fields configuration
        if use_standard_fields is not None:
            cls._use_standard_fields = use_standard_fields
        elif hasattr(cls, "model_config") and "use_standard_fields" in cls.model_config:
            cls._use_standard_fields = cls.model_config["use_standard_fields"]
        else:
            cls._use_standard_fields = DiscriminatedConfig.use_standard_fields

        # Add the discriminator fields to the model's annotations
        if not hasattr(cls, "__annotations__"):
            cls.__annotations__ = {}

        # Determine the type of the discriminator field
        if isinstance(discriminator, Enum):
            field_type = type(discriminator)
        else:
            field_type = type(discriminator)

        # Add domain-specific field to annotations
        cls.__annotations__[field_name] = field_type

        # Add standard fields to annotations if configured
        if cls._use_standard_fields:
            cls.__annotations__[DiscriminatedConfig.standard_category_field] = str
            cls.__annotations__[DiscriminatedConfig.standard_value_field] = field_type

        # Update model_config to exclude discriminator fields by default
        if not hasattr(cls, "model_config"):
            cls.model_config = {}

        # Get existing excluded fields or create an empty set
        excluded = cls.model_config.get("excluded", set())
        if isinstance(excluded, list):
            excluded = set(excluded)

        # Add discriminator fields to excluded
        excluded.add(field_name)
        if cls._use_standard_fields:
            excluded.add(DiscriminatedConfig.standard_category_field)
            excluded.add(DiscriminatedConfig.standard_value_field)

        cls.model_config["excluded"] = excluded

        # Override __init__ to set the discriminator values
        original_init = cls.__init__

        def init_with_discriminator(self, **data):
            """
            Overridden __init__ that ensures discriminator values are set correctly.

            This function adds the discriminator field and value to the initialization
            data if missing, then calls the original __init__, and finally ensures
            that discriminator attributes are set on the instance.

            Args:
                **data (dict[Any, Any]): Keyword arguments for initialization.
            """
            # Add domain-specific discriminator field if missing
            if field_name not in data:
                data[field_name] = discriminator

            # Add standard fields if configured
            use_std_fields = cls._use_standard_fields
            if use_std_fields:
                if DiscriminatedConfig.standard_category_field not in data:
                    data[DiscriminatedConfig.standard_category_field] = field_name
                if DiscriminatedConfig.standard_value_field not in data:
                    data[DiscriminatedConfig.standard_value_field] = discriminator

            original_init(self, **data)

            # Ensure discriminator values are set as instance attributes
            object.__setattr__(self, field_name, discriminator)
            object.__setattr__(self, "_discriminator_field", field_name)
            object.__setattr__(self, "_discriminator_value", discriminator)
            object.__setattr__(self, "_use_standard_fields", use_std_fields)

            # Set standard fields if configured
            if use_std_fields:
                object.__setattr__(self, DiscriminatedConfig.standard_category_field, field_name)
                object.__setattr__(self, DiscriminatedConfig.standard_value_field, discriminator)

        cls.__init__ = init_with_discriminator

        return cls

    return decorator


# Apply patching based on configuration
if DiscriminatedConfig.patch_base_model:
    _apply_monkey_patch()
