# Technical Implementation

This page explains the technical details of how pydantic-discriminated works under the hood.

## Architecture Overview

pydantic-discriminated consists of several key components:

1. **DiscriminatedBaseModel**: Base class for all discriminated models
2. **DiscriminatorAwareBaseModel**: Base class for containers that need to handle discriminated models
3. **DiscriminatedModelRegistry**: Central registry of discriminated models and their values
4. **DiscriminatedConfig**: Global configuration settings
5. **Monkey Patching System**: Optional enhancement to Pydantic's BaseModel for automatic discriminator handling

## Discriminator Registration

The `@discriminated_model` decorator performs several important tasks:

1. Registers the model class in the `DiscriminatedModelRegistry` with its category and value
2. Sets class-level attributes (`_discriminator_field`, `_discriminator_value`) to store discriminator information
3. Adds the discriminator field to the model's annotations
4. Overrides `__init__` to ensure discriminator values are set on the instance

```python
@discriminated_model("animal_type", "dog")
class Dog(DiscriminatedBaseModel):
    name: str
    breed: str
```

This registration enables:
- Type-safe validation (ensuring the discriminator field has the correct value)
- Runtime access to discriminator information
- Proper serialization of discriminator fields

## Serialization Strategies

### 1. Monkey Patching Approach

When enabled, this approach patches Pydantic's `BaseModel.model_dump` and `BaseModel.model_dump_json` methods to automatically process discriminator fields in nested models.

The patching process:
1. Stores the original methods in `_original_methods`
2. Defines patched versions that check the `use_discriminators` parameter or global setting
3. Processes nested models to add discriminator fields when appropriate

This approach allows regular `BaseModel` containers to automatically handle discriminated models.

### 2. Explicit Base Class Approach

For more control or when monkey patching is disabled, `DiscriminatorAwareBaseModel` provides explicit handling of discriminated fields:

- Overrides `model_dump` and `model_dump_json` to always process discriminators
- Recursively processes nested models to ensure consistent behavior
- Not affected by the global monkey patching setting

## Discriminator Processing

The `_process_discriminators` function is responsible for:

1. Recursively traversing the serialized data structure
2. Identifying discriminated models at any nesting level
3. Adding or removing discriminator fields based on configuration
4. Handling lists of models, individual models, and regular fields appropriately

## Standard Fields

For interoperability with different systems, pydantic-discriminated supports standard discriminator fields:

- **Domain-specific field**: The field name used in your domain model (e.g., `"shape_type"`)
- **Standard category field**: Always `"discriminator_category"`, stores the field name
- **Standard value field**: Always `"discriminator_value"`, stores the discriminator value

This allows other systems to identify and process discriminated models without prior knowledge of your domain-specific fields.

## Configuration Options

The `DiscriminatedConfig` class provides global settings:

- **use_standard_fields**: Whether to include standard discriminator fields
- **standard_category_field**: Name of the standard category field
- **standard_value_field**: Name of the standard value field
- **patch_base_model**: Whether to apply monkey patching to BaseModel

These can be overridden:
1. Globally via `DiscriminatedConfig`
2. Per-model via `model_config`
3. Per-decorator via parameters
4. Per-call via `use_discriminators` parameter

## Performance Considerations

The library is designed for efficiency:

- Registry lookups are O(1)
- Serialization processing adds minimal overhead
- Type information is preserved without runtime cost
- Monkey patching is applied only once regardless of imports

## Implementation Challenges

Some interesting challenges addressed in the implementation:

1. **Preserving Type Safety**: Ensuring IDEs and type checkers understand discriminated unions
2. **Recursive Processing**: Handling models nested at arbitrary depths
3. **Configuration Flexibility**: Balancing global settings with per-model and per-call options
4. **Monkey Patching Control**: Providing both automatic and explicit approaches
5. **Discriminator Validation**: Ensuring discriminator values match at validation time

## Extending the Library

To extend the library, you can:

1. Create custom base classes that inherit from `DiscriminatedBaseModel`
2. Add middleware to process discriminator fields in specific ways
3. Implement custom serializers for special discriminator handling
4. Extend `DiscriminatedConfig` with additional settings

## Integration with Other Libraries

pydantic-discriminated is designed to work seamlessly with:

- **FastAPI**: For generating correct OpenAPI schemas with discriminators
- **SQLModel**: For ORM models that need discriminator functionality
- **Type checkers**: mypy, pyright, etc.
- **API clients**: For properly serializing discriminated models in requests