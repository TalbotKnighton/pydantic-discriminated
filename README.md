# pydantic-discriminated

A robust, type-safe implementation of discriminated unions for Pydantic models.

[![PyPI version](https://img.shields.io/pypi/v/pydantic-discriminated.svg)](https://pypi.org/project/pydantic-discriminated/)
[![Python versions](https://img.shields.io/pypi/pyversions/pydantic-discriminated.svg)](https://pypi.org/project/pydantic-discriminated/)
[![License](https://img.shields.io/github/license/TalbotKnighton/pydantic-discriminated.svg)](https://github.com/TalbotKnighton/pydantic-discriminated/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://talbotknighton.github.io/pydantic-discriminated/latest/)

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
print(f"Total area: {shapes.total_area()}") # 278.5795

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
- **🔧 Flexible Configuration**: Control when and how discriminator fields are included in serialization

## How It Works

Under the hood, pydantic-discriminated uses several advanced techniques to provide its functionality:

1. **Model Registration**: The `@discriminated_model` decorator registers models in a central registry with their discriminator field and value
2. **Custom Model Serialization**: Enhances Pydantic's serialization to properly handle discriminator fields
3. **Monkey Patching (Optional)**: Can patch Pydantic's BaseModel to handle discriminators in nested models automatically
4. **Type Annotations**: Preserves type information for static analyzers and IDEs

## Flexible Serialization

You can control when discriminator fields are included in serialized output:

```python
from pydantic_discriminated import DiscriminatedConfig

# Global configuration - include discriminators when serializing
DiscriminatedConfig.enable_monkey_patching()

# Serialize with discriminators
shape = Circle(radius=5)
data = shape.model_dump()  # Will include 'shape_type': 'circle'

# Disable discriminators globally
DiscriminatedConfig.disable_monkey_patching()

# Now serialization won't include discriminators by default
data = shape.model_dump()  # Won't include 'shape_type'

# Override per-call behavior
data = shape.model_dump(use_discriminators=True)  # Will include 'shape_type': 'circle'
```

## Two Usage Approaches

### 1. Automatic Monkey Patching (Simple)

This approach patches Pydantic's BaseModel to automatically include discriminator fields:

```python
from pydantic_discriminated import discriminated_model, DiscriminatedBaseModel, DiscriminatedConfig

# Enable monkey patching (default)
DiscriminatedConfig.enable_monkey_patching()

@discriminated_model("shape_type", "circle")
class Circle(DiscriminatedBaseModel):
    radius: float

# Regular BaseModel containers work automatically
class ShapeContainer(BaseModel):
    shape: Circle

container = ShapeContainer(shape=Circle(radius=5))
data = container.model_dump()  # Will include shape_type automatically
```

### 2. Explicit Base Class (Advanced)

For more control, you can use the DiscriminatorAwareBaseModel for your containers:

```python
from pydantic_discriminated import (
    discriminated_model, DiscriminatedBaseModel, 
    DiscriminatorAwareBaseModel, DiscriminatedConfig
)

# Disable monkey patching
DiscriminatedConfig.disable_monkey_patching()

@discriminated_model("shape_type", "circle")
class Circle(DiscriminatedBaseModel):
    radius: float

# Use DiscriminatorAwareBaseModel for containers
class ShapeContainer(DiscriminatorAwareBaseModel):
    shape: Circle

container = ShapeContainer(shape=Circle(radius=5))
data = container.model_dump()  # Will include shape_type
```

## Advanced Usage

### Enum Discriminators

```python
from enum import Enum
from pydantic_discriminated import discriminated_model, DiscriminatedBaseModel

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

### Standard Fields

By default, discriminator fields are included both as domain-specific fields (e.g., `shape_type`) and as standard fields for interoperability:

```python
circle = Circle(radius=5)
data = circle.model_dump()
# Results in:
# {
#   "radius": 5,
#   "shape_type": "circle",              # Domain-specific discriminator
#   "discriminator_category": "shape_type", # Standard category field
#   "discriminator_value": "circle"      # Standard value field
# }
```

You can control this behavior globally or per-model:

```python
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
from fastapi import FastAPI
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

## License

MIT

---

This library fills a significant gap in Pydantic's functionality. If you work with polymorphic data structures, it will make your life easier!