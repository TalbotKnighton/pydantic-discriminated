# pydantic-discriminated

A robust, type-safe implementation of discriminated unions for Pydantic models.

[![PyPI version](https://badge.fury.io/py/pydantic-discriminated.svg)](https://badge.fury.io/py/pydantic-discriminated)
[![Python versions](https://img.shields.io/pypi/pyversions/pydantic-discriminated.svg)](https://pypi.org/project/pydantic-discriminated/)

## What are Discriminated Unions?

Discriminated unions (also called tagged unions) let you work with polymorphic data in a type-safe way. A "discriminator" field tells you which concrete type you're dealing with.

## Installation

```bash
pip install pydantic-discriminated
```

## Quick Start

```python
from enum import Enum
from typing import List, Union
from pydantic import BaseModel

from pydantic_discriminated import discriminated_model, DiscriminatedBaseModel

# Define discriminated models with their tag values
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

# Container for shapes
class ShapeCollection(BaseModel):
    shapes: List[Union[Circle, Rectangle]]
    
    def total_area(self) -> float:
        return sum(shape.area() for shape in self.shapes)

# Parse polymorphic data correctly
data = {
    "shapes": [
        {"shape_type": "circle", "radius": 5},
        {"shape_type": "rectangle", "width": 10, "height": 20}
    ]
}

shapes = ShapeCollection.model_validate(data)
print(f"Total area: {shapes.total_area()}")  # 278.5795

# Each shape is properly typed
for shape in shapes.shapes:
    if isinstance(shape, Circle):
        print(f"Circle with radius {shape.radius}")
    elif isinstance(shape, Rectangle):
        print(f"Rectangle with dimensions {shape.width}x{shape.height}")
```

## Key Features

- **🔍 Type Safety**: Proper type hints for IDE autocomplete and static analysis
- **📦 Nested Models**: Works with models nested at any level
- **🔄 Seamless Integration**: Uses standard Pydantic methods (`model_validate`, `model_dump`)
- **🧩 Polymorphic Validation**: Automatically validates and dispatches to the correct model type
- **📚 OpenAPI Compatible**: Works great with FastAPI for generating correct schemas

## Why Use This?

If you've ever needed to handle polymorphic data structures (like different event types, various message formats, or heterogeneous API responses), you'll appreciate how this library makes it clean and type-safe.

### Common Use Cases

- **API Responses**: When an endpoint can return different object types
- **Event Processing**: Handle different event types in a type-safe way
- **State Machines**: Model different states with specific properties
- **Data Schemas**: Define polymorphic data models with validation

## How It Works

1. The `@discriminated_model` decorator registers models with their discriminator field and value
2. When parsing data, the discriminator value determines which model class to use
3. Type information is preserved, so IDEs and type checkers understand the specific model type
4. Serialization automatically includes the discriminator field

## Advanced Usage

### Enum Discriminators

```python
from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"

@discriminated_model(MessageType, MessageType.TEXT)
class TextMessage(DiscriminatedBaseModel):
    content: str

@discriminated_model(MessageType, MessageType.IMAGE)
class ImageMessage(DiscriminatedBaseModel):
    url: str
    width: int
    height: int
```

### Dynamic Model Selection

```python
# Validate data into the appropriate model based on discriminator
message_data = {"messagetype": "text", "content": "Hello world"}
message = TextMessage.validate_discriminated(message_data)

# Type checker doesn't know the exact type, so cast when needed
if isinstance(message, TextMessage):
    print(f"Text message: {message.content}")
```

### Configuration Options

```python
from pydantic_discriminated import DiscriminatedConfig

# Global configuration
DiscriminatedConfig.use_standard_fields = False

# Per-model configuration using model_config
@discriminated_model("animal_type", "cat")
class Cat(DiscriminatedBaseModel):
    model_config = {"use_standard_fields": False}
    name: str
    lives_left: int

# Direct parameter in decorator
@discriminated_model("animal_type", "dog", use_standard_fields=True)
class Dog(DiscriminatedBaseModel):
    name: str
    breed: str
```

## FastAPI Example

```python
from fastapi import FastAPI, HTTPException
from typing import Union, List

app = FastAPI()

@app.post("/shapes/")
def process_shape(shape: Union[Circle, Rectangle]):
    return {"area": shape.area()}

@app.post("/shape-collection/")
def process_shapes(shapes: ShapeCollection):
    return {"total_area": shapes.total_area()}
```

This will automatically generate the correct OpenAPI schema with discriminator support!

## Comparison with Alternatives

| Feature | pydantic-discriminated | python-union | pydantic-factories |
|---------|------------------------|--------------|-------------------|
| Type safety | ✅ Full | ⚠️ Partial | ⚠️ Limited |
| Nested models | ✅ Yes | ❌ No | ❌ No |
| IDE support | ✅ Full | ⚠️ Partial | ⚠️ Partial |
| OpenAPI integration | ✅ Yes | ⚠️ Partial | ❌ No |
| Configuration options | ✅ Yes | ❌ No | ❌ No |

## Learn More

- [Discriminated Unions in TypeScript](https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes-func.html#discriminated-unions)
- [Algebraic Data Types](https://en.wikipedia.org/wiki/Algebraic_data_type)
- [OpenAPI Discriminator Object](https://swagger.io/docs/specification/data-models/inheritance-and-polymorphism/)

## License

MIT

---

This library fills a significant gap in Pydantic's functionality. If you work with polymorphic data structures, it will make your life easier!