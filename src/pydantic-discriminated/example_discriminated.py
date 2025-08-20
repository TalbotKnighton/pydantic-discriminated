from enum import Enum
from typing import List, Union, Optional, Dict, Any, cast
from pydantic import BaseModel, ConfigDict

from pydantic_discriminated import (
    discriminated_model,
    DiscriminatedModelRegistry,
    DiscriminatedBaseModel,
    DiscriminatorAwareBaseModel,
    DiscriminatedConfig,
)

# Set global configuration
# DiscriminatedConfig.use_standard_fields = False  # Uncomment to change global default


# Example 1: Using string literals with default config
@discriminated_model("animal_type", "dog")
class Dog(DiscriminatedBaseModel):
    name: str
    breed: str


# Example 2: Using string literals with custom config via model_config
@discriminated_model("animal_type", "cat")
class Cat(DiscriminatedBaseModel):
    model_config = ConfigDict(use_standard_fields=False)
    name: str
    lives_left: int


# Example 3: Using string literals with custom config via decorator parameter
@discriminated_model("animal_type", "bird", use_standard_fields=False)
class Bird(DiscriminatedBaseModel):
    name: str
    wingspan: float


# Example 4: Using enums
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


@discriminated_model(MessageType, MessageType.VIDEO)
class VideoMessage(DiscriminatedBaseModel):
    url: str
    duration: float


# Container models - inherit from DiscriminatorAwareBaseModel to handle nested discriminators
class AnimalShelter(DiscriminatorAwareBaseModel):
    animals: List[Union[Dog, Cat, Bird]]


class Conversation(DiscriminatorAwareBaseModel):
    messages: List[Union[TextMessage, ImageMessage, VideoMessage]]


def test_configuration_options():
    """Test the different configuration options"""
    print("\n--- Testing Configuration Options ---")

    # Create instances of each model
    dog = Dog(name="Rex", breed="German Shepherd")
    cat = Cat(name="Whiskers", lives_left=9)
    bird = Bird(name="Polly", wingspan=0.5)

    # Check their serialized forms
    dog_dict = dog.model_dump()
    cat_dict = cat.model_dump()
    bird_dict = bird.model_dump()

    print(f"Dog (default config): {dog_dict}")
    print(f"Cat (model_config): {cat_dict}")
    print(f"Bird (decorator param): {bird_dict}")

    # Check if standard fields are included based on configuration
    assert "animal_type" in dog_dict, "animal_type missing from dog"
    assert (
        "discriminator_category" in dog_dict
    ), "discriminator_category missing from dog (should be included by default)"
    assert (
        "discriminator_value" in dog_dict
    ), "discriminator_value missing from dog (should be included by default)"

    assert "animal_type" in cat_dict, "animal_type missing from cat"
    assert (
        "discriminator_category" not in cat_dict
    ), "discriminator_category should not be in cat (disabled via model_config)"
    assert (
        "discriminator_value" not in cat_dict
    ), "discriminator_value should not be in cat (disabled via model_config)"

    assert "animal_type" in bird_dict, "animal_type missing from bird"
    assert (
        "discriminator_category" not in bird_dict
    ), "discriminator_category should not be in bird (disabled via decorator param)"
    assert (
        "discriminator_value" not in bird_dict
    ), "discriminator_value should not be in bird (disabled via decorator param)"

    # Create a shelter with mixed animals
    shelter = AnimalShelter(animals=[dog, cat, bird])

    # Check nested serialization respects individual model configs
    shelter_dict = shelter.model_dump()
    print(f"Shelter serialized: {shelter_dict}")

    # Check access to discriminator fields
    print(f"dog.animal_type: {dog.animal_type}")
    print(f"dog.discriminator_category: {dog.discriminator_category}")
    print(f"dog.discriminator_value: {dog.discriminator_value}")

    print(f"cat.animal_type: {cat.animal_type}")
    try:
        print(f"cat.discriminator_category: {cat.discriminator_category}")
    except AttributeError:
        print(
            "cat.discriminator_category: AttributeError (as expected with use_standard_fields=False)"
        )

    print("Configuration test passed!")


def main():
    # Print the registry to see what's registered
    print("Registry contents:")
    for category, models in DiscriminatedModelRegistry._registry.items():
        print(f"  Category: {category}")
        for disc_value, model_cls in models.items():
            print(f"    {disc_value} -> {model_cls.__name__}")

    # Run configuration test
    test_configuration_options()

    # Show all models for a category
    print("\nAll models for animal_type:")
    models = DiscriminatedModelRegistry.get_models_for_category("animal_type")
    for value, model in models.items():
        print(f"  {value} -> {model.__name__}")


if __name__ == "__main__":
    main()
