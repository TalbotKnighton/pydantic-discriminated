# src/pydantic_discriminated/__init__.py

"""
pydantic-discriminated: Type-safe discriminated unions for Pydantic models.
"""

__version__ = "0.1.13"

# Import and expose the main components of the API
from pydantic_discriminated.api import (  # Assuming this is your main module file
    # Core functionality
    discriminated_model,
    DiscriminatedBaseModel,
    DiscriminatorAwareBaseModel,
    # Configuration
    DiscriminatedConfig,
    # Registry and utilities
    DiscriminatedModelRegistry,
)

# Define what's available through the public API
__all__ = [
    "discriminated_model",
    "DiscriminatedBaseModel",
    "DiscriminatorAwareBaseModel",
    "DiscriminatedConfig",
    "DiscriminatedModelRegistry",
]
