# pydantic-discriminated

Type-safe discriminated unions for Pydantic models.

[![PyPI Version](https://img.shields.io/pypi/v/pydantic-discriminated.svg)](https://pypi.org/project/pydantic-discriminated/)
[![Python Versions](https://img.shields.io/pypi/pyversions/pydantic-discriminated.svg)](https://pypi.org/project/pydantic-discriminated/)
[![License](https://img.shields.io/github/license/TalbotKnighton/pydantic-discriminated.svg)](https://github.com/TalbotKnighton/pydantic-discriminated/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://talbotknighton.github.io/pydantic-discriminated/)

## Comparison with Alternatives

### Why pydantic-discriminated?

While several libraries offer partial solutions to handling polymorphic data structures, pydantic-discriminated stands out by providing:

1. **True type safety** that works with IDEs and static type checkers
2. **Seamless integration** with Pydantic's ecosystem including FastAPI
3. **Flexible configuration** with per-call control over serialization behavior
4. **Comprehensive support** for nested models at any level
5. **Simple API** with an intuitive decorator-based approach

Most alternatives either lack proper type information, don't support nested structures, or require complex manual configuration. pydantic-discriminated solves these limitations with a clean, type-safe API that feels like a natural extension of Pydantic itself.

### Feature Comparison

| Feature | pydantic-discriminated | pydantic TaggedUnion | python-union | pydantic-factories | cattrs + attrs | marshmallow + marshmallow-oneofschema |
|---------|------------------------|----------------------|--------------|-------------------|---------------|--------------------------------------|
| **Type Safety** | ✅ Full type-checking support | ⚠️ Limited | ⚠️ Partial | ⚠️ Limited | ⚠️ Partial | ❌ No |
| **Nested Models** | ✅ Arbitrary nesting levels | ✅ Supported | ❌ Limited | ❌ No | ⚠️ Limited | ⚠️ Limited |
| **IDE Support** | ✅ Full autocomplete | ⚠️ Partial | ⚠️ Partial | ⚠️ Partial | ⚠️ Partial | ❌ No |
| **Runtime Control** | ✅ Flexible configuration | ❌ No | ❌ No | ❌ No | ⚠️ Limited | ⚠️ Limited |
| **OpenAPI Support** | ✅ Complete | ✅ Basic | ⚠️ Manual setup | ❌ No | ❌ No | ⚠️ Partial |
| **Serialization Control** | ✅ Per-call options | ❌ No | ❌ No | ❌ No | ⚠️ Limited | ⚠️ Limited |
| **Standard Fields** | ✅ Configurable | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **Validation** | ✅ Full Pydantic validation | ✅ Full Pydantic validation | ⚠️ Basic | ⚠️ Limited | ✅ Supported | ✅ Supported |
| **Enum Support** | ✅ Native Enum integration | ❌ No | ❌ No | ❌ No | ⚠️ Manual | ⚠️ Manual |
| **Monkey Patching** | ✅ Optional & configurable | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **FastAPI Integration** | ✅ Seamless | ⚠️ Basic | ⚠️ Manual setup | ❌ No | ❌ No | ⚠️ Limited |
| **Learning Curve** | ✅ Simple decorator pattern | ⚠️ Moderate | ⚠️ Moderate | ⚠️ Steep | ⚠️ Steep | ⚠️ Steep |
| **Pydantic v2 Support** | ✅ Full support | ✅ Supported | ❌ Limited | ⚠️ Partial | ❓ Unknown | ❓ Unknown |


## What are Discriminated Unions?

Discriminated unions (also called tagged unions) let you work with polymorphic data in a type-safe way. A "discriminator" field tells you which concrete type you're dealing with.

```python
from pydantic_discriminated import discriminated_model, DiscriminatedBaseModel

@discriminated_model("shape_type", "circle")
class Circle(DiscriminatedBaseModel):
    radius: float
    
    def area(self) -> float:
        return 3.14159 * self.radius ** 2

@discriminated_model("shape_type", "rectangle")
class Rectangle(DiscriminatedBaseModel):
    width: float
    height: float
    
    def area(self) -> float:
        return self.width * self.height

# Parse data with the correct type
data = {"shape_type": "circle", "radius": 5}
circle = Circle.model_validate(data)  # Fully typed as Circle
print(f"Area: {circle.area()}")  # 78.53975
```

## Features

- **🔍 Type Safety**: Proper type hints for IDE autocomplete and static analysis
- **📦 Nested Models**: Works with models nested at any level
- **🔄 Seamless Integration**: Uses standard Pydantic methods (`model_validate`, `model_dump`)
- **🧩 Polymorphic Validation**: Automatically validates and dispatches to the correct model type
- **📚 OpenAPI Compatible**: Works great with FastAPI for generating correct schemas
- **🔧 Flexible Serialization**: Control how and when discriminator fields appear in output

## Installation

```bash
pip install pydantic-discriminated
```

## How It Works

pydantic-discriminated uses a combination of techniques to provide powerful discriminated union functionality:

1. **Decorator-based Registration**: Models are registered with their discriminator field and value
2. **Enhanced Serialization**: Controls when discriminator fields appear in serialized output
3. **Type Preservation**: Maintains proper typing for IDE support and static analysis
4. **Flexible Configuration**: Offers both global and per-model configuration options

## Two Serialization Approaches

### 1. Automatic (Simple)

With monkey patching enabled (the default), discriminator fields are automatically included:

```python
from pydantic import BaseModel
from pydantic_discriminated import discriminated_model, DiscriminatedBaseModel

@discriminated_model("shape_type", "circle")
class Circle(DiscriminatedBaseModel):
    radius: float

# Regular BaseModel works automatically
class Container(BaseModel):
    my_shape: Circle

container = Container(my_shape=Circle(radius=5))
data = container.model_dump()
# Includes shape_type automatically:
# {"my_shape": {"radius": 5, "shape_type": "circle", ...}}
```

### 2. Explicit (Advanced)

For more control, you can disable monkey patching and use `DiscriminatorAwareBaseModel`:

```python
from pydantic_discriminated import (
    discriminated_model, DiscriminatedBaseModel,
    DiscriminatorAwareBaseModel, DiscriminatedConfig
)

# Disable automatic patching
DiscriminatedConfig.disable_monkey_patching()

@discriminated_model("shape_type", "circle")
class Circle(DiscriminatedBaseModel):
    radius: float

# Use the aware base model for containers
class Container(DiscriminatorAwareBaseModel):
    my_shape: Circle

container = Container(my_shape=Circle(radius=5))
data = container.model_dump()
# Still includes shape_type:
# {"my_shape": {"radius": 5, "shape_type": "circle", ...}}
```

## Quick Example

Define discriminated models for different event types:

```python
from enum import Enum
from typing import List, Union
from pydantic import BaseModel
from pydantic_discriminated import discriminated_model, DiscriminatedBaseModel

class EventType(str, Enum):
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    LOGIN_ATTEMPT = "login_attempt"

@discriminated_model(EventType, EventType.USER_CREATED)
class UserCreatedEvent(DiscriminatedBaseModel):
    user_id: str
    username: str

@discriminated_model(EventType, EventType.USER_UPDATED)
class UserUpdatedEvent(DiscriminatedBaseModel):
    user_id: str
    fields_changed: List[str]

@discriminated_model(EventType, EventType.LOGIN_ATTEMPT)
class LoginAttemptEvent(DiscriminatedBaseModel):
    user_id: str
    success: bool
    ip_address: str

# Container that handles any event type
class EventProcessor(BaseModel):
    events: List[Union[UserCreatedEvent, UserUpdatedEvent, LoginAttemptEvent]]
    
    def process(self):
        for event in self.events:
            if isinstance(event, UserCreatedEvent):
                print(f"New user created: {event.username}")
            elif isinstance(event, UserUpdatedEvent):
                print(f"User {event.user_id} updated fields: {event.fields_changed}")
            elif isinstance(event, LoginAttemptEvent):
                result = "succeeded" if event.success else "failed"
                print(f"Login {result} for user {event.user_id} from {event.ip_address}")
```

## Fine-Grained Control

You can control discriminator field inclusion on a per-call basis:

```python
# Always include discriminator fields (with monkey patching enabled)
data = shape.model_dump()

# Explicitly control discriminator inclusion
with_disc = shape.model_dump(use_discriminators=True)
without_disc = shape.model_dump(use_discriminators=False)
```

## Documentation

- [Full Documentation](https://talbotknighton.github.io/pydantic-discriminated/)
- [API Reference](https://talbotknighton.github.io/pydantic-discriminated/api-reference/)
- [Examples](https://talbotknighton.github.io/pydantic-discriminated/examples/basic-usage/)

## When To Use

This library is perfect for:

- **API Responses**: When endpoints return different object types
- **Event Systems**: Handling different event types in a type-safe way
- **State Machines**: Representing different states with specific properties
- **Polymorphic Data**: Working with heterogeneous data structures

## Resources

- [GitHub Repository](https://github.com/TalbotKnighton/pydantic-discriminated)
- [PyPI Package](https://pypi.org/project/pydantic-discriminated/)
- [Issue Tracker](https://github.com/TalbotKnighton/pydantic-discriminated/issues)

## License

MIT

---

Built by [Talbot Knighton](https://github.com/TalbotKnighton)