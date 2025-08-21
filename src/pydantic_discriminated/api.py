from enum import Enum
from typing import (
    Any,
    Dict,
    Type,
    Union,
    Callable,
    ClassVar,
    List,
    Optional,
    get_args,
    get_origin,
    TypeVar,
    Generic,
    overload,
    cast,
    ClassVar,
)
from pydantic import BaseModel, Field, model_serializer, field_serializer
import json
from functools import wraps

T = TypeVar("T", bound="DiscriminatedBaseModel")

# Store original methods in a dictionary
_original_methods = {}


# Global configuration with defaults
class DiscriminatedConfig:
    """Global configuration for discriminated models."""

    use_standard_fields: bool = True
    standard_category_field: str = "discriminator_category"
    standard_value_field: str = "discriminator_value"

    # Flag to control whether to patch BaseModel
    patch_base_model: bool = True

    # Flag to track if patching has already been applied
    _patched: bool = False

    @classmethod
    def enable_monkey_patching(cls):
        """Enable monkey patching of BaseModel for discriminator support in all models."""
        cls.patch_base_model = True
        # Apply the patch if not already applied
        if not cls._patched:
            _apply_monkey_patch()

    # @classmethod
    # def disable_monkey_patching(cls):
    #     """Disable monkey patching of BaseModel. Users must use DiscriminatorAwareBaseModel for containers."""
    #     cls.patch_base_model = False
    #     # No need to remove the patch, just set the flag to disable processing
    @classmethod
    def disable_monkey_patching(cls):
        """Disable monkey patching of BaseModel. Users must use DiscriminatorAwareBaseModel for containers."""
        print("DEBUG: Disabling monkey patching, previous value:", cls.patch_base_model)
        cls.patch_base_model = False
        print("DEBUG: After disabling, new value:", cls.patch_base_model)

    # @classmethod
    # def enable_monkey_patching(cls):
    #     """Enable monkey patching of BaseModel for discriminator support in all models."""
    #     cls.patch_base_model = True
    #     # Apply the patch if not already applied
    #     if not cls._patched:
    #         _apply_monkey_patch()

    # @classmethod
    # def disable_monkey_patching(cls):
    #     """Disable monkey patching of BaseModel. Users must use DiscriminatorAwareBaseModel for containers."""
    #     cls.patch_base_model = False
    #     # No need to remove the patch, just set the flag

    # @classmethod
    # def enable_monkey_patching(cls):
    #     """Enable monkey patching of BaseModel for discriminator support in all models."""
    #     cls.patch_base_model = True
    #     # Apply the patch if not already applied
    #     if not cls._patched:
    #         _apply_monkey_patch()

    # @classmethod
    # def disable_monkey_patching(cls):
    #     """Disable monkey patching of BaseModel. Users must use DiscriminatorAwareBaseModel for containers."""
    #     cls.patch_base_model = False
    #     # Remove the patch if it was applied
    #     if cls._patched:
    #         _remove_monkey_patch()


# def _apply_monkey_patch():
#     """Apply monkey patching to BaseModel."""
#     global _original_methods

#     # Only patch if not already patched
#     if not DiscriminatedConfig._patched:
#         # Store original methods
#         _original_methods["model_dump"] = BaseModel.model_dump
#         _original_methods["model_dump_json"] = BaseModel.model_dump_json

#         # Define new methods that use the originals
#         def patched_model_dump(self, **kwargs):
#             # Get the result from the original method
#             result = _original_methods["model_dump"](self, **kwargs)

#             # Only process if patching is enabled
#             if DiscriminatedConfig.patch_base_model:
#                 # Process it to add discriminators
#                 return _process_discriminators(self, result)
#             else:
#                 # Return the original result if patching is disabled
#                 return result

#         def patched_model_dump_json(self, **kwargs):
#             # Get data - will respect the patch_base_model flag
#             if DiscriminatedConfig.patch_base_model:
#                 # Use patched model_dump with discriminators
#                 data = patched_model_dump(self, **kwargs)
#             else:
#                 # Use original model_dump without discriminators
#                 data = _original_methods["model_dump"](self, **kwargs)

#             # Convert to JSON
#             encoder = kwargs.pop("encoder", None)
#             return json.dumps(data, default=encoder, **kwargs)

#         # Apply patches
#         BaseModel.model_dump = patched_model_dump
#         BaseModel.model_dump_json = patched_model_dump_json

#         # Mark as patched
#         DiscriminatedConfig._patched = True


# def _apply_monkey_patch():
#     """Apply monkey patching to BaseModel."""
#     global _original_methods

#     # Only patch if not already patched
#     if not DiscriminatedConfig._patched:
#         # Store original methods
#         _original_methods["model_dump"] = BaseModel.model_dump
#         _original_methods["model_dump_json"] = BaseModel.model_dump_json

#         # Define new methods that use the originals
#         def patched_model_dump(self, **kwargs):
#             # Get the result from the original method
#             result = _original_methods["model_dump"](self, **kwargs)

#             # Check if a specific flag is passed or use the global setting
#             use_discriminators = kwargs.pop(
#                 "use_discriminators", DiscriminatedConfig.patch_base_model
#             )

#             # Only process if discriminators should be used
#             if use_discriminators:
#                 # Process it to add discriminators
#                 return _process_discriminators(self, result)
#             else:
#                 # Return the original result
#                 return result

#         def patched_model_dump_json(self, **kwargs):
#             # Check if a specific flag is passed or use the global setting
#             use_discriminators = kwargs.pop(
#                 "use_discriminators", DiscriminatedConfig.patch_base_model
#             )

#             # Get data based on flag
#             if use_discriminators:
#                 # Use the patched model_dump with the flag
#                 data = patched_model_dump(self, use_discriminators=True, **kwargs)
#             else:
#                 # Use original model_dump
#                 data = _original_methods["model_dump"](self, **kwargs)

#             # Convert to JSON
#             encoder = kwargs.pop("encoder", None)
#             return json.dumps(data, default=encoder, **kwargs)

#         # Apply patches
#         BaseModel.model_dump = patched_model_dump
#         BaseModel.model_dump_json = patched_model_dump_json

#         # Mark as patched
#         DiscriminatedConfig._patched = True


# def _apply_monkey_patch():
#     """Apply monkey patching to BaseModel."""
#     global _original_methods

#     # Only patch if not already patched
#     if not DiscriminatedConfig._patched:
#         # Store original methods
#         _original_methods["model_dump"] = BaseModel.model_dump
#         _original_methods["model_dump_json"] = BaseModel.model_dump_json

#         # Define new methods that use the originals
#         def patched_model_dump(self, **kwargs):
#             # Extract our custom parameter
#             use_discriminators = kwargs.pop(
#                 "use_discriminators", DiscriminatedConfig.patch_base_model
#             )

#             # Get the result from the original method (without our custom parameter)
#             result = _original_methods["model_dump"](self, **kwargs)

#             # Only process if discriminators should be used
#             if use_discriminators:
#                 # Process it to add discriminators
#                 return _process_discriminators(self, result)
#             else:
#                 # Return the original result
#                 return result

#         def patched_model_dump_json(self, **kwargs):
#             # Extract our custom parameter
#             use_discriminators = kwargs.pop(
#                 "use_discriminators", DiscriminatedConfig.patch_base_model
#             )

#             # Get data based on flag
#             if use_discriminators:
#                 # Call our patched model_dump (which knows to handle use_discriminators)
#                 data = patched_model_dump(self, use_discriminators=True, **kwargs)
#             else:
#                 # Use original model_dump
#                 data = _original_methods["model_dump"](self, **kwargs)

#             # Convert to JSON
#             encoder = kwargs.pop("encoder", None)
#             return json.dumps(data, default=encoder, **kwargs)

#         # Apply patches
#         BaseModel.model_dump = patched_model_dump
#         BaseModel.model_dump_json = patched_model_dump_json


#         # Mark as patched
#         DiscriminatedConfig._patched = True
# def _apply_monkey_patch():
#     """Apply monkey patching to BaseModel."""
#     global _original_methods

#     # Only patch if not already patched
#     if not DiscriminatedConfig._patched:
#         # Store original methods
#         _original_methods["model_dump"] = BaseModel.model_dump
#         _original_methods["model_dump_json"] = BaseModel.model_dump_json

#         # Define new methods that use the originals
#         def patched_model_dump(self, **kwargs):
#             # Extract our custom parameter
#             use_discriminators = kwargs.pop(
#                 "use_discriminators", DiscriminatedConfig.patch_base_model
#             )

#             # Print debugging info
#             print(
#                 f"DEBUG patched_model_dump: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
#             )

#             # Get the result from the original method (without our custom parameter)
#             result = _original_methods["model_dump"](self, **kwargs)

#             # Only process if discriminators should be used
#             if use_discriminators:
#                 print("DEBUG: Adding discriminators to serialized data")
#                 # Process it to add discriminators
#                 return _process_discriminators(self, result)
#             else:
#                 print("DEBUG: NOT adding discriminators to serialized data")
#                 # Return the original result
#                 return result

#         def patched_model_dump_json(self, **kwargs):
#             # Extract our custom parameter
#             use_discriminators = kwargs.pop(
#                 "use_discriminators", DiscriminatedConfig.patch_base_model
#             )

#             print(
#                 f"DEBUG patched_model_dump_json: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
#             )

#             # Get data based on flag
#             if use_discriminators:
#                 # Call our patched model_dump with the use_discriminators flag
#                 data = patched_model_dump(self, use_discriminators=True, **kwargs)
#             else:
#                 # Use original model_dump
#                 print("DEBUG: Using original model_dump (no discriminators)")
#                 data = _original_methods["model_dump"](self, **kwargs)

#             # Convert to JSON
#             encoder = kwargs.pop("encoder", None)
#             return json.dumps(data, default=encoder, **kwargs)

#         # Apply patches
#         BaseModel.model_dump = patched_model_dump
#         BaseModel.model_dump_json = patched_model_dump_json


#         # Mark as patched
#         DiscriminatedConfig._patched = True
# def _apply_monkey_patch():
#     """Apply monkey patching to BaseModel."""
#     global _original_methods

#     # Only patch if not already patched
#     if not DiscriminatedConfig._patched:
#         # Store original methods
#         _original_methods["model_dump"] = BaseModel.model_dump
#         _original_methods["model_dump_json"] = BaseModel.model_dump_json

#         # Define new methods that use the originals
#         def patched_model_dump(self, **kwargs):
#             # Extract our custom parameter
#             use_discriminators = kwargs.pop(
#                 "use_discriminators", DiscriminatedConfig.patch_base_model
#             )

#             print(
#                 f"DEBUG patched_model_dump: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
#             )

#             # Special handling for DiscriminatedBaseModel instances
#             if isinstance(self, DiscriminatedBaseModel):
#                 # Add the parameter back for the model's own handling
#                 kwargs["use_discriminators"] = use_discriminators

#             # Get the result from the original method (without our custom parameter)
#             result = _original_methods["model_dump"](self, **kwargs)

#             # Only process if discriminators should be used
#             if use_discriminators:
#                 print("DEBUG: Adding discriminators to serialized data")
#                 # Process it to add discriminators
#                 return _process_discriminators(self, result)
#             else:
#                 print("DEBUG: NOT adding discriminators to serialized data")
#                 # Return the original result
#                 return result

#         def patched_model_dump_json(self, **kwargs):
#             # Extract our custom parameter
#             use_discriminators = kwargs.pop(
#                 "use_discriminators", DiscriminatedConfig.patch_base_model
#             )

#             print(
#                 f"DEBUG patched_model_dump_json: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
#             )

#             # Get data based on flag
#             if use_discriminators:
#                 # Call our patched model_dump with the use_discriminators flag
#                 data = patched_model_dump(self, use_discriminators=True, **kwargs)
#             else:
#                 # Use our patched model_dump with use_discriminators=False to ensure consistency
#                 data = patched_model_dump(self, use_discriminators=False, **kwargs)

#             # Convert to JSON
#             encoder = kwargs.pop("encoder", None)
#             return json.dumps(data, default=encoder, **kwargs)

#         # Apply patches
#         BaseModel.model_dump = patched_model_dump
#         BaseModel.model_dump_json = patched_model_dump_json


#         # Mark as patched
#         DiscriminatedConfig._patched = True
# def _apply_monkey_patch():
#     """Apply monkey patching to BaseModel."""
#     global _original_methods

#     # Only patch if not already patched
#     if not DiscriminatedConfig._patched:
#         # Store original methods
#         _original_methods["model_dump"] = BaseModel.model_dump
#         _original_methods["model_dump_json"] = BaseModel.model_dump_json

#         # Define new methods that use the originals
#         def patched_model_dump(self, **kwargs):
#             # Extract our custom parameter
#             use_discriminators = None
#             if "use_discriminators" in kwargs:
#                 use_discriminators = kwargs.pop("use_discriminators")
#             else:
#                 use_discriminators = DiscriminatedConfig.patch_base_model

#             print(
#                 f"DEBUG patched_model_dump: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
#             )

#             # Special handling for DiscriminatedBaseModel instances
#             # Let them handle it themselves using their overridden method
#             if isinstance(self, DiscriminatedBaseModel):
#                 # Add the parameter back for the model's own handling
#                 kwargs["use_discriminators"] = use_discriminators
#                 return super(type(self), self).model_dump(**kwargs)

#             # Get the result from the original method (without our custom parameter)
#             result = _original_methods["model_dump"](self, **kwargs)

#             # Only process if discriminators should be used
#             if use_discriminators:
#                 print("DEBUG: Adding discriminators to serialized data")
#                 # Process it to add discriminators
#                 return _process_discriminators(self, result)
#             else:
#                 print("DEBUG: NOT adding discriminators to serialized data")
#                 # Return the original result
#                 return result

#         def patched_model_dump_json(self, **kwargs):
#             # Extract our custom parameter
#             use_discriminators = None
#             if "use_discriminators" in kwargs:
#                 use_discriminators = kwargs.pop("use_discriminators")
#             else:
#                 use_discriminators = DiscriminatedConfig.patch_base_model

#             print(
#                 f"DEBUG patched_model_dump_json: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
#             )

#             # Get data based on flag
#             if use_discriminators:
#                 # Use model_dump but make sure to create a copy of kwargs to avoid modifying the original
#                 kwargs_copy = kwargs.copy()
#                 kwargs_copy["use_discriminators"] = True
#                 data = self.model_dump(**kwargs_copy)
#             else:
#                 # Use model_dump with use_discriminators=False
#                 kwargs_copy = kwargs.copy()
#                 kwargs_copy["use_discriminators"] = False
#                 data = self.model_dump(**kwargs_copy)

#             # Convert to JSON
#             encoder = kwargs.pop("encoder", None)
#             return json.dumps(data, default=encoder, **kwargs)

#         # Apply patches
#         BaseModel.model_dump = patched_model_dump
#         BaseModel.model_dump_json = patched_model_dump_json


#         # Mark as patched
#         DiscriminatedConfig._patched = True
def _apply_monkey_patch():
    """Apply monkey patching to BaseModel."""
    global _original_methods

    # Only patch if not already patched
    if not DiscriminatedConfig._patched:
        # Store original methods
        _original_methods["model_dump"] = BaseModel.model_dump
        _original_methods["model_dump_json"] = BaseModel.model_dump_json

        # Define new methods that use the originals
        def patched_model_dump(self, **kwargs):
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

        def patched_model_dump_json(self, **kwargs):
            # Extract our custom parameter
            use_discriminators = None
            if "use_discriminators" in kwargs:
                use_discriminators = kwargs.pop("use_discriminators")
            else:
                use_discriminators = DiscriminatedConfig.patch_base_model

            print(
                f"DEBUG patched_model_dump_json: use_discriminators={use_discriminators}, global setting={DiscriminatedConfig.patch_base_model}"
            )

            # Use model_dump but make sure to create a copy of kwargs to avoid modifying the original
            kwargs_copy = kwargs.copy()
            kwargs_copy["use_discriminators"] = use_discriminators
            data = self.model_dump(**kwargs_copy)

            # Convert to JSON
            encoder = kwargs.pop("encoder", None)
            return json.dumps(data, default=encoder, **kwargs)

        # Apply patches
        BaseModel.model_dump = patched_model_dump
        BaseModel.model_dump_json = patched_model_dump_json

        # Mark as patched
        DiscriminatedConfig._patched = True


# def _remove_monkey_patch():
#     """Remove monkey patching from BaseModel."""
#     global _original_methods

#     # Only remove if currently patched
#     if DiscriminatedConfig._patched:
#         # Restore original methods
#         if "model_dump" in _original_methods:
#             BaseModel.model_dump = _original_methods["model_dump"]
#         if "model_dump_json" in _original_methods:
#             BaseModel.model_dump_json = _original_methods["model_dump_json"]

#         # Mark as unpatched
#         DiscriminatedConfig._patched = False


# def _process_discriminators(model, data):
#     """
#     Process data to add discriminators for nested models.

#     Args:
#         model: The model instance that produced the data
#         data: The data to process

#     Returns:
#         Processed data with discriminators added
#     """
#     # Add debugging to see when this is called
#     print(
#         f"DEBUG _process_discriminators: processing model type {type(model).__name__}"
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
#                 for item, item_data in zip(field_value, value):
#                     if hasattr(item, "_discriminator_field") and hasattr(
#                         item, "_discriminator_value"
#                     ):
#                         # It's a discriminated model - add the discriminator
#                         item_data = dict(item_data)  # Make a copy
#                         item_data[item._discriminator_field] = item._discriminator_value
#                         print(
#                             f"DEBUG: Added discriminator {item._discriminator_field}={item._discriminator_value} to item"
#                         )

#                         # Add standard fields if configured
#                         if getattr(
#                             item,
#                             "_use_standard_fields",
#                             DiscriminatedConfig.use_standard_fields,
#                         ):
#                             item_data[DiscriminatedConfig.standard_category_field] = (
#                                 item._discriminator_field
#                             )
#                             item_data[DiscriminatedConfig.standard_value_field] = (
#                                 item._discriminator_value
#                             )

#                     result[key].append(item_data)
#             elif hasattr(field_value, "_discriminator_field") and hasattr(
#                 field_value, "_discriminator_value"
#             ):
#                 # It's a discriminated model - add the discriminator
#                 result[key] = dict(value)  # Make a copy
#                 result[key][
#                     field_value._discriminator_field
#                 ] = field_value._discriminator_value

#                 # Add standard fields if configured
#                 if getattr(
#                     field_value,
#                     "_use_standard_fields",
#                     DiscriminatedConfig.use_standard_fields,
#                 ):
#                     result[key][
#                         DiscriminatedConfig.standard_category_field
#                     ] = field_value._discriminator_field
#                     result[key][
#                         DiscriminatedConfig.standard_value_field
#                     ] = field_value._discriminator_value
#             elif isinstance(field_value, BaseModel) and isinstance(value, dict):
#                 # It's a regular BaseModel - process it recursively
#                 result[key] = _process_discriminators(field_value, value)
#             else:
#                 # Other types - keep as is
#                 result[key] = value
#         return result


# #     # Handle other types
# #     return data
# def _process_discriminators(model, data):
#     """
#     Process data to add discriminators for nested models.

#     Args:
#         model: The model instance that produced the data
#         data: The data to process

#     Returns:
#         Processed data with discriminators added
#     """
#     # Add debugging to see when this is called
#     print(
#         f"DEBUG _process_discriminators: processing model type {type(model).__name__}"
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
#                 for item, item_data in zip(field_value, value):
#                     if hasattr(item, "_discriminator_field") and hasattr(
#                         item, "_discriminator_value"
#                     ):
#                         # It's a discriminated model - add the discriminator
#                         item_data = dict(item_data)  # Make a copy
#                         item_data[item._discriminator_field] = item._discriminator_value
#                         print(
#                             f"DEBUG: Added discriminator {item._discriminator_field}={item._discriminator_value} to item"
#                         )

#                         # Add standard fields if configured
#                         if getattr(
#                             item,
#                             "_use_standard_fields",
#                             DiscriminatedConfig.use_standard_fields,
#                         ):
#                             item_data[DiscriminatedConfig.standard_category_field] = (
#                                 item._discriminator_field
#                             )
#                             item_data[DiscriminatedConfig.standard_value_field] = (
#                                 item._discriminator_value
#                             )

#                     result[key].append(item_data)
#             elif hasattr(field_value, "_discriminator_field") and hasattr(
#                 field_value, "_discriminator_value"
#             ):
#                 # It's a discriminated model - add the discriminator
#                 result[key] = dict(value)  # Make a copy
#                 result[key][
#                     field_value._discriminator_field
#                 ] = field_value._discriminator_value

#                 # Add standard fields if configured
#                 if getattr(
#                     field_value,
#                     "_use_standard_fields",
#                     DiscriminatedConfig.use_standard_fields,
#                 ):
#                     result[key][
#                         DiscriminatedConfig.standard_category_field
#                     ] = field_value._discriminator_field
#                     result[key][
#                         DiscriminatedConfig.standard_value_field
#                     ] = field_value._discriminator_value
#             elif isinstance(field_value, BaseModel) and isinstance(value, dict):
#                 # It's a regular BaseModel - process it recursively
#                 result[key] = _process_discriminators(field_value, value)
#             else:
#                 # Other types - keep as is
#                 result[key] = value
#         return result

#     # Handle other types
#     return data


# def _process_discriminators(model, data):
#     """
#     Process data to add discriminators for nested models.

#     Args:
#         model: The model instance that produced the data
#         data: The data to process

#     Returns:
#         Processed data with discriminators added
#     """
#     # Add debugging to see when this is called
#     print(
#         f"DEBUG _process_discriminators: processing model type {type(model).__name__}"
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
#                         # For discriminated models, use their own model_dump with use_discriminators=True
#                         # to ensure discriminator fields are included
#                         try:
#                             processed_data = item.model_dump(use_discriminators=True)
#                             result[key].append(processed_data)
#                         except Exception as e:
#                             print(f"DEBUG: Error processing item {idx} in list: {e}")
#                             # Fall back to original data if there's an error
#                             result[key].append(item_data)
#                     else:
#                         # For other types, keep as is
#                         result[key].append(item_data)
#             elif isinstance(field_value, DiscriminatedBaseModel) and isinstance(
#                 value, dict
#             ):
#                 # It's a discriminated model - use its model_dump with use_discriminators=True
#                 try:
#                     result[key] = field_value.model_dump(use_discriminators=True)
#                 except Exception as e:
#                     print(f"DEBUG: Error processing field {key}: {e}")
#                     # Fall back to original data
#                     result[key] = value
#             elif isinstance(field_value, BaseModel) and isinstance(value, dict):
#                 # It's a regular BaseModel - process it recursively
#                 result[key] = _process_discriminators(field_value, value)
#             else:
#                 # Other types - keep as is
#                 result[key] = value
#         return result


#     # Handle other types
#     return data
def _process_discriminators(model, data, use_discriminators=True):
    """
    Process data to add or remove discriminators for nested models.

    Args:
        model: The model instance that produced the data
        data: The data to process
        use_discriminators: Whether to include discriminator fields

    Returns:
        Processed data with discriminators added or removed
    """
    # Add debugging to see when this is called
    print(
        f"DEBUG _process_discriminators: processing model type {type(model).__name__}, use_discriminators={use_discriminators}"
    )

    # Handle dictionaries
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Get the original field value from the model if possible
            field_value = getattr(model, key, None)

            # Process based on field type
            if isinstance(field_value, list) and isinstance(value, list):
                # Handle lists of models
                result[key] = []
                for idx, (item, item_data) in enumerate(zip(field_value, value)):
                    if isinstance(item, DiscriminatedBaseModel):
                        # For discriminated models, use their own model_dump with our flag
                        try:
                            processed_data = item.model_dump(use_discriminators=use_discriminators)
                            result[key].append(processed_data)
                        except Exception as e:
                            print(f"DEBUG: Error processing item {idx} in list: {e}")
                            # Fall back to original data if there's an error
                            if use_discriminators:
                                # Add discriminator fields
                                item_data = dict(item_data)  # Make a copy
                                item_data[item._discriminator_field] = item._discriminator_value
                                if getattr(
                                    item,
                                    "_use_standard_fields",
                                    DiscriminatedConfig.use_standard_fields,
                                ):
                                    item_data[DiscriminatedConfig.standard_category_field] = (
                                        item._discriminator_field
                                    )
                                    item_data[DiscriminatedConfig.standard_value_field] = (
                                        item._discriminator_value
                                    )
                            else:
                                # Remove discriminator fields
                                item_data = dict(item_data)  # Make a copy
                                if item._discriminator_field in item_data:
                                    del item_data[item._discriminator_field]
                                if DiscriminatedConfig.standard_category_field in item_data:
                                    del item_data[DiscriminatedConfig.standard_category_field]
                                if DiscriminatedConfig.standard_value_field in item_data:
                                    del item_data[DiscriminatedConfig.standard_value_field]
                            result[key].append(item_data)
                    elif isinstance(item, BaseModel):
                        # For other models, process recursively
                        processed_data = _process_discriminators(
                            item, item_data, use_discriminators
                        )
                        result[key].append(processed_data)
                    else:
                        # For other types, keep as is
                        result[key].append(item_data)
            elif isinstance(field_value, DiscriminatedBaseModel) and isinstance(value, dict):
                # It's a discriminated model - use its model_dump with our flag
                try:
                    result[key] = field_value.model_dump(use_discriminators=use_discriminators)
                except Exception as e:
                    print(f"DEBUG: Error processing field {key}: {e}")
                    # Fall back to manual processing
                    if use_discriminators:
                        # Add discriminator fields
                        value_copy = dict(value)  # Make a copy
                        value_copy[field_value._discriminator_field] = (
                            field_value._discriminator_value
                        )
                        if getattr(
                            field_value,
                            "_use_standard_fields",
                            DiscriminatedConfig.use_standard_fields,
                        ):
                            value_copy[DiscriminatedConfig.standard_category_field] = (
                                field_value._discriminator_field
                            )
                            value_copy[DiscriminatedConfig.standard_value_field] = (
                                field_value._discriminator_value
                            )
                        result[key] = value_copy
                    else:
                        # Remove discriminator fields
                        value_copy = dict(value)  # Make a copy
                        if field_value._discriminator_field in value_copy:
                            del value_copy[field_value._discriminator_field]
                        if DiscriminatedConfig.standard_category_field in value_copy:
                            del value_copy[DiscriminatedConfig.standard_category_field]
                        if DiscriminatedConfig.standard_value_field in value_copy:
                            del value_copy[DiscriminatedConfig.standard_value_field]
                        result[key] = value_copy
            elif isinstance(field_value, BaseModel) and isinstance(value, dict):
                # It's a regular BaseModel - process it recursively
                result[key] = _process_discriminators(field_value, value, use_discriminators)
            else:
                # Other types - keep as is
                result[key] = value
        return result
    # Handle other types
    return data


class DiscriminatedModelRegistry:
    """Registry to store and retrieve discriminated models."""

    _registry: Dict[str, Dict[Any, Type["DiscriminatedBaseModel"]]] = {}

    @classmethod
    def register(cls, category: str, value: Any, model_cls: Type["DiscriminatedBaseModel"]) -> None:
        """Register a model class for a specific category and discriminator value."""
        if category not in cls._registry:
            cls._registry[category] = {}
        cls._registry[category][value] = model_cls

    @classmethod
    def get_model(cls, category: str, value: Any) -> Type["DiscriminatedBaseModel"]:
        """Get a model class by category and discriminator value."""
        if category not in cls._registry:
            raise ValueError(f"No models registered for category '{category}'")
        if value not in cls._registry[category]:
            raise ValueError(f"No model found for value '{value}' in category '{category}'")
        return cls._registry[category][value]

    @classmethod
    def get_models_for_category(cls, category: str) -> Dict[Any, Type["DiscriminatedBaseModel"]]:
        """Get all models registered for a specific category."""
        if category not in cls._registry:
            raise ValueError(f"No models registered for category '{category}'")
        return cls._registry[category]


# class DiscriminatorAwareBaseModel(BaseModel):
#     """
#     Base model that handles discriminators in serialization, including nested models.
#     Use this as a base class for container models when monkey patching is disabled.
#     """

#     def model_dump(self, **kwargs):
#         """
#         Override model_dump to include discriminators at all nesting levels.
#         """
#         # Get standard serialization
#         result = super().model_dump(**kwargs)

#         # Process the result to handle discriminated models
#         def process_value(value):
#             if isinstance(value, dict):
#                 return {k: process_value(v) for k, v in value.items()}
#             elif isinstance(value, list):
#                 return [process_value(item) for item in value]
#             elif hasattr(value, "_discriminator_field") and hasattr(
#                 value, "_discriminator_value"
#             ):
#                 # It's a discriminated model - add discriminator fields
#                 data = value.model_dump()
#                 data[value._discriminator_field] = value._discriminator_value

#                 # Add standard fields if configured
#                 if getattr(
#                     value,
#                     "_use_standard_fields",
#                     DiscriminatedConfig.use_standard_fields,
#                 ):
#                     data[DiscriminatedConfig.standard_category_field] = (
#                         value._discriminator_field
#                     )
#                     data[DiscriminatedConfig.standard_value_field] = (
#                         value._discriminator_value
#                     )

#                 return data
#             else:
#                 return value

#         # Process all values in the result
#         for key, value in result.items():
#             result[key] = process_value(value)

#         return result

#     def model_dump_json(self, **kwargs):
#         """
#         Override model_dump_json to include discriminators at all nesting levels.
#         """
#         # Get data with discriminators
#         data = self.model_dump(**kwargs)

#         # Convert to JSON
#         encoder = kwargs.pop("encoder", None)
#         return json.dumps(data, default=encoder, **kwargs)


class DiscriminatorAwareBaseModel(BaseModel):
    """
    Base model that handles discriminators in serialization, including nested models.
    Use this as a base class for container models when monkey patching is disabled.
    """

    def model_dump(self, **kwargs):
        """
        Override model_dump to include discriminators at all nesting levels.
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

    def model_dump_json(self, **kwargs):
        """
        Override model_dump_json to include discriminators at all nesting levels.
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
    """

    # Legacy fields for compatibility
    _discriminator_field: ClassVar[str] = ""
    _discriminator_value: ClassVar[Any] = None
    _use_standard_fields: ClassVar[bool] = DiscriminatedConfig.use_standard_fields

    def __getattr__(self, name):
        """
        Custom attribute access to handle discriminator field.
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

    def model_dump(self, **kwargs):
        """Override model_dump to control when discriminators are included."""
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
    def serialize_model(self):
        """Custom serializer that includes discriminator fields only when requested."""
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
    def model_validate(cls: Type[T], obj: Any, **kwargs) -> T:
        """
        Validate the given object and return an instance of this model.
        Enhanced to handle discriminator validation.

        Args:
            obj: The object to validate
            **kwargs: Additional arguments to pass to the original model_validate

        Returns:
            An instance of this model
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
    def model_validate_json(cls: Type[T], json_data: Union[str, bytes], **kwargs) -> T:
        """
        Validate the given JSON data and return an instance of this model.
        Enhanced to handle discriminator validation.

        Args:
            json_data: The JSON data to validate
            **kwargs: Additional arguments to pass to the original model_validate_json

        Returns:
            An instance of this model
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

        Args:
            data: The data to validate

        Returns:
            An instance of the appropriate discriminated model
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


# def discriminated_model(
#     category: Union[str, Type[Enum]],
#     discriminator: Any,
#     use_standard_fields: Optional[bool] = None,
# ) -> Callable[[Type[T]], Type[T]]:
#     """
#     Decorator to create a discriminated model.

#     Args:
#         category: The category field name or Enum class
#         discriminator: The discriminator value for this model
#         use_standard_fields: Whether to use standard discriminator fields (default: global setting)

#     Returns:
#         A decorator function that registers the model class
#     """
#     category_field = category
#     if isinstance(category, type) and issubclass(category, Enum):
#         category_field = category.__name__.lower()

#     field_name = str(category_field)

#     def decorator(cls: Type[T]) -> Type[T]:
#         # Make sure the class inherits from DiscriminatedBaseModel
#         if not issubclass(cls, DiscriminatedBaseModel):
#             raise TypeError(f"{cls.__name__} must inherit from DiscriminatedBaseModel")

#         # Register the model
#         DiscriminatedModelRegistry.register(field_name, discriminator, cls)

#         # Store the discriminator information as class variables
#         cls._discriminator_field = field_name
#         cls._discriminator_value = discriminator

#         # Set standard fields configuration
#         if use_standard_fields is not None:
#             cls._use_standard_fields = use_standard_fields
#         elif hasattr(cls, "model_config") and "use_standard_fields" in cls.model_config:
#             cls._use_standard_fields = cls.model_config["use_standard_fields"]
#         else:
#             cls._use_standard_fields = DiscriminatedConfig.use_standard_fields

#         # Add the discriminator fields to the model's annotations
#         if not hasattr(cls, "__annotations__"):
#             cls.__annotations__ = {}

#         # Determine the type of the discriminator field
#         if isinstance(discriminator, Enum):
#             field_type = type(discriminator)
#         else:
#             field_type = type(discriminator)

#         # Add domain-specific field to annotations
#         cls.__annotations__[field_name] = field_type

#         # Add standard fields to annotations if configured
#         if cls._use_standard_fields:
#             cls.__annotations__[DiscriminatedConfig.standard_category_field] = str
#             cls.__annotations__[DiscriminatedConfig.standard_value_field] = field_type

#         # Override __init__ to set the discriminator values
#         original_init = cls.__init__

#         def init_with_discriminator(self, **data):
#             # Add domain-specific discriminator field if missing
#             if field_name not in data:
#                 data[field_name] = discriminator

#             # Add standard fields if configured
#             use_std_fields = cls._use_standard_fields
#             if use_std_fields:
#                 if DiscriminatedConfig.standard_category_field not in data:
#                     data[DiscriminatedConfig.standard_category_field] = field_name
#                 if DiscriminatedConfig.standard_value_field not in data:
#                     data[DiscriminatedConfig.standard_value_field] = discriminator

#             original_init(self, **data)

#             # Ensure discriminator values are set as instance attributes
#             object.__setattr__(self, field_name, discriminator)
#             object.__setattr__(self, "_discriminator_field", field_name)
#             object.__setattr__(self, "_discriminator_value", discriminator)
#             object.__setattr__(self, "_use_standard_fields", use_std_fields)

#             # Set standard fields if configured
#             if use_std_fields:
#                 object.__setattr__(
#                     self, DiscriminatedConfig.standard_category_field, field_name
#                 )
#                 object.__setattr__(
#                     self, DiscriminatedConfig.standard_value_field, discriminator
#                 )

#         cls.__init__ = init_with_discriminator

#         return cls

#     return decorator


def discriminated_model(
    category: Union[str, Type[Enum]],
    discriminator: Any,
    use_standard_fields: Optional[bool] = None,
) -> Callable[[Type[T]], Type[T]]:
    """
    Decorator to create a discriminated model.

    Args:
        category: The category field name or Enum class
        discriminator: The discriminator value for this model
        use_standard_fields: Whether to use standard discriminator fields (default: global setting)

    Returns:
        A decorator function that registers the model class
    """
    category_field = category
    if isinstance(category, type) and issubclass(category, Enum):
        category_field = category.__name__.lower()

    field_name = str(category_field)

    def decorator(cls: Type[T]) -> Type[T]:
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
