import unittest
import logging
import json
import sys
from enum import Enum
from typing import List, Union, Optional, Dict, Any, cast
from pydantic import BaseModel

from pydantic_discriminated import (
    discriminated_model,
    DiscriminatedModelRegistry,
    DiscriminatedBaseModel,
    DiscriminatorAwareBaseModel,
    DiscriminatedConfig,
)

# Configure logging to output to both file and console
logger = logging.getLogger("discriminator_tests")
logger.setLevel(logging.DEBUG)

# Console handler with INFO level
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)

# File handler with DEBUG level for detailed logs
file_handler = logging.FileHandler("discriminator_tests.log", mode="w")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)


# JSON file handler for structured output
class JsonFileHandler(logging.FileHandler):
    def __init__(self, filename, mode="w"):
        super().__init__(filename, mode=mode)
        self.records = []

    def emit(self, record):
        log_entry = {
            "timestamp": self.formatter.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "test": getattr(record, "test", None),
            "result": getattr(record, "result", None),
        }
        self.records.append(log_entry)
        with open(self.baseFilename, "w") as f:
            json.dump(self.records, f, indent=2)


json_handler = JsonFileHandler("discriminator_tests.json")
json_handler.setLevel(logging.INFO)
json_formatter = logging.Formatter("%(asctime)s")
json_handler.setFormatter(json_formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(json_handler)

# Show starting state
logger.info(f"Monkey patching enabled at startup: {DiscriminatedConfig.patch_base_model}")


# Example 1: Using string literals with default config
@discriminated_model("animal_type", "dog")
class Dog(DiscriminatedBaseModel):
    name: str
    breed: str


# Example 2: Using string literals with custom config via model_config
@discriminated_model("animal_type", "cat")
class Cat(DiscriminatedBaseModel):
    model_config = {"use_standard_fields": False}
    name: str
    lives_left: int


# Example 3: Using enums
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


class DiscriminatorTests(unittest.TestCase):

    def setUp(self):
        # Reset to default state before each test
        DiscriminatedConfig.enable_monkey_patching()
        logger.debug("Test setup complete - monkey patching enabled")

    def tearDown(self):
        # Clean up after each test
        DiscriminatedConfig.enable_monkey_patching()
        logger.debug("Test teardown complete - monkey patching reset to enabled")

    def test_serialization_performance(self):
        """Test that the patching doesn't significantly impact performance"""
        import time

        # Create a complex model
        dogs = [Dog(name=f"Dog{i}", breed="Breed") for i in range(100)]
        cats = [Cat(name=f"Cat{i}", lives_left=9) for i in range(100)]

        class BigShelter(BaseModel):
            dogs: List[Dog]
            cats: List[Cat]

        shelter = BigShelter(dogs=dogs, cats=cats)

        # Measure time with discriminators
        start = time.time()
        _ = shelter.model_dump()
        end = time.time()
        with_disc_time = end - start

        # Measure time without discriminators
        start = time.time()
        _ = shelter.model_dump(use_discriminators=False)
        end = time.time()
        without_disc_time = end - start

        # Log the times
        logger.info(f"Serialization time with discriminators: {with_disc_time:.6f}s")
        logger.info(f"Serialization time without discriminators: {without_disc_time:.6f}s")

        # We don't assert on exact times, but log for awareness

    def test_custom_json_encoder(self):
        """Test using a custom JSON encoder with model_dump_json"""
        from datetime import datetime

        class ModelWithDateTime(BaseModel):
            name: str
            timestamp: datetime

        model = ModelWithDateTime(name="Test", timestamp=datetime(2023, 1, 1))

        # Custom encoder function
        def custom_encoder(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        # Test with custom encoder
        json_str = model.model_dump_json(encoder=custom_encoder)
        data = json.loads(json_str)

        # Verify the datetime was properly encoded
        self.assertEqual(data["timestamp"], "2023-01-01T00:00:00")

    def test_json_serialization_edge_cases(self):
        """Test JSON serialization with complex nested structures and edge cases"""
        # Create models with nested structures
        dog = Dog(name="Rex", breed="German Shepherd")
        cat = Cat(name="Whiskers", lives_left=9)

        class ComplexContainer(BaseModel):
            animals: List[Union[Dog, Cat]]
            empty_list: List[str] = []
            none_value: Optional[str] = None
            nested_dict: Dict[str, Any] = {"key": {"nested": None}}  # Initialize with None

        # Create the container and set nested structure after initialization
        container = ComplexContainer(animals=[dog, cat])
        # We need to manually set this after creation to avoid validation issues
        container.nested_dict = {"key": {"nested": [dog, None, cat]}}

        logger.debug("Testing JSON serialization with complex nested structures")

        # First verify discriminators are present by default
        json_str = container.model_dump_json(indent=2)
        logger.debug(f"Default JSON serialization:\n{json_str}")
        data = json.loads(json_str)

        # Check first level discriminators
        self.assertIn(
            "animal_type",
            data["animals"][0],
            "Discriminator should be present in first level by default",
        )

        # Check nested discriminators
        self.assertIn(
            "animal_type",
            data["nested_dict"]["key"]["nested"][0],
            "Discriminator should be present in nested structures by default",
        )
        self.assertIn(
            "animal_type",
            data["nested_dict"]["key"]["nested"][2],
            "Discriminator should be present in nested structures by default",
        )

        # Now test with use_discriminators=False
        json_str_no_disc = container.model_dump_json(use_discriminators=False)
        logger.debug(f"JSON serialization with use_discriminators=False:\n{json_str_no_disc}")
        data_no_disc = json.loads(json_str_no_disc)

        # Check first level discriminators are removed
        self.assertNotIn(
            "animal_type",
            data_no_disc["animals"][0],
            "Discriminator should NOT be present in first level with use_discriminators=False",
        )

        # Check nested discriminators are removed
        self.assertNotIn(
            "animal_type",
            data_no_disc["nested_dict"]["key"]["nested"][0],
            "Discriminator should NOT be present in nested structures with use_discriminators=False",
        )
        self.assertNotIn(
            "animal_type",
            data_no_disc["nested_dict"]["key"]["nested"][2],
            "Discriminator should NOT be present in nested structures with use_discriminators=False",
        )

    def test_json_serialization_with_options(self):
        """Test JSON serialization with various JSON options to ensure they're handled correctly"""
        logger.info("Running test_json_serialization_with_options")

        # Create some instances
        dog = Dog(name="Rex", breed="German Shepherd")
        cat = Cat(name="Whiskers", lives_left=9)

        class ShelterWithComplexFields(BaseModel):
            name: str
            animals: List[Union[Dog, Cat]]
            metadata: Dict[str, Any]

        # Create a shelter with some complex metadata
        shelter = ShelterWithComplexFields(
            name="Happy Pets",
            animals=[dog, cat],
            metadata={
                "founded": "2020-01-01",
                "location": {"city": "San Francisco", "state": "CA"},
                "capacity": 100,
            },
        )

        # Test with monkey patching enabled
        DiscriminatedConfig.enable_monkey_patching()
        logger.debug("With monkey patching enabled:")

        # 1. Test with default options
        json_default = shelter.model_dump_json()
        logger.debug(f"Default JSON: {json_default}")

        # Parse and verify discriminators are present
        data_default = json.loads(json_default)
        self.assertIn(
            "animal_type",
            data_default["animals"][0],
            "Discriminator field should be present by default",
        )

        # 2. Test with indent option
        json_indented = shelter.model_dump_json(indent=2)
        logger.debug(f"Indented JSON: {json_indented}")

        # Verify the JSON is properly indented (will have newlines)
        self.assertIn("\n", json_indented, "JSON should be indented with newlines")

        # Parse and verify discriminators are still present
        data_indented = json.loads(json_indented)
        self.assertIn(
            "animal_type",
            data_indented["animals"][0],
            "Discriminator field should be present with indent option",
        )

        # 3. Test with both indent and sort_keys options
        json_sorted = shelter.model_dump_json(indent=2, sort_keys=True)
        logger.debug(f"Sorted and indented JSON: {json_sorted}")

        # Parse and verify discriminators are still present
        data_sorted = json.loads(json_sorted)
        self.assertIn(
            "animal_type",
            data_sorted["animals"][0],
            "Discriminator field should be present with indent and sort_keys options",
        )

        # 4. Test with exclude_unset and indent options (model_dump and json options)
        json_exclude = shelter.model_dump_json(exclude_unset=True, indent=2)
        logger.debug(f"JSON with exclude_unset and indent: {json_exclude}")

        # Verify it's properly indented
        self.assertIn("\n", json_exclude, "JSON should be indented with newlines")

        # Parse and verify discriminators are still present
        data_exclude = json.loads(json_exclude)
        self.assertIn(
            "animal_type",
            data_exclude["animals"][0],
            "Discriminator field should be present with exclude_unset option",
        )

        # 5. Test with use_discriminators=False to verify it works with JSON options
        json_no_disc = shelter.model_dump_json(indent=2, use_discriminators=False)
        logger.debug(f"JSON with use_discriminators=False: {json_no_disc}")

        # Parse and verify discriminators are NOT present
        data_no_disc = json.loads(json_no_disc)
        self.assertNotIn(
            "animal_type",
            data_no_disc["animals"][0],
            "Discriminator field should NOT be present with use_discriminators=False",
        )
        self.assertNotIn(
            "discriminator_category",
            data_no_disc["animals"][0],
            "Standard discriminator field should NOT be present with use_discriminators=False",
        )

        logger.info("test_json_serialization_with_options PASSED")

    def test_monkey_patching_approach(self):
        """Test the monkey patching approach (BaseModel is patched)"""
        logger.info("Running test_monkey_patching_approach")

        # Make sure monkey patching is enabled
        DiscriminatedConfig.enable_monkey_patching()
        logger.debug(f"Monkey patching now enabled: {DiscriminatedConfig.patch_base_model}")

        # Create instances
        dog = Dog(name="Rex", breed="German Shepherd")
        cat = Cat(name="Whiskers", lives_left=9)

        # Use regular BaseModel for containers
        class AnimalShelter(BaseModel):
            animals: List[Union[Dog, Cat]]

        # Create a shelter
        shelter = AnimalShelter(animals=[dog, cat])

        # Serialize - discriminators should be included automatically
        shelter_dict = shelter.model_dump()
        logger.debug(f"Shelter serialized with BaseModel: {shelter_dict}")

        # Check if discriminators are preserved
        for i, animal in enumerate(shelter_dict["animals"]):
            self.assertIn("animal_type", animal, f"animal_type missing from animal {i}: {animal}")
            logger.debug(
                f"Animal {i} has discriminator field: animal_type={animal.get('animal_type')}"
            )

        # Test with multi-level nesting
        class AnimalNetwork(BaseModel):
            name: str
            main_shelter: AnimalShelter

        network = AnimalNetwork(name="City Network", main_shelter=shelter)
        network_dict = network.model_dump()

        logger.debug(f"Network serialized with BaseModel: {network_dict}")

        # Check that discriminators are preserved at all levels
        for i, animal in enumerate(network_dict["main_shelter"]["animals"]):
            self.assertIn("animal_type", animal, f"animal_type missing from nested animal {i}")
            logger.debug(
                f"Nested animal {i} has discriminator field: animal_type={animal.get('animal_type')}"
            )

        logger.info("test_monkey_patching_approach PASSED")

    def test_explicit_base_class_approach(self):
        """Test the explicit base class approach (without monkey patching)"""
        logger.info("Running test_explicit_base_class_approach")

        # Disable monkey patching
        DiscriminatedConfig.disable_monkey_patching()
        logger.debug(f"Monkey patching now disabled: {DiscriminatedConfig.patch_base_model}")
        logger.debug(f"Is BaseModel patched? {DiscriminatedConfig._patched}")

        # Create instances
        dog = Dog(name="Rex", breed="German Shepherd")
        cat = Cat(name="Whiskers", lives_left=9)

        # First try with regular BaseModel - should NOT include discriminators
        class RegularShelter(BaseModel):
            animals: List[Union[Dog, Cat]]

        regular_shelter = RegularShelter(animals=[dog, cat])
        regular_dict = regular_shelter.model_dump()
        logger.debug(f"Regular shelter (BaseModel): {regular_dict}")

        # Check first animal - should NOT have discriminator fields when patching is disabled
        first_animal = regular_dict["animals"][0]
        has_animal_type = "animal_type" in first_animal
        has_category = "discriminator_category" in first_animal

        logger.debug(f"First animal has 'animal_type'? {has_animal_type}")
        logger.debug(f"First animal has 'discriminator_category'? {has_category}")

        # This should be False when patching is disabled
        self.assertFalse(
            has_animal_type,
            "Regular model should NOT include discriminator fields when patching is disabled",
        )
        self.assertFalse(
            has_category,
            "Regular model should NOT include standard discriminator fields when patching is disabled",
        )

        # Now try with DiscriminatorAwareBaseModel - should include discriminators
        class AwareShelter(DiscriminatorAwareBaseModel):
            animals: List[Union[Dog, Cat]]

        aware_shelter = AwareShelter(animals=[dog, cat])
        aware_dict = aware_shelter.model_dump()
        logger.debug(f"Aware shelter (DiscriminatorAwareBaseModel): {aware_dict}")

        # Check first animal in aware model - should ALWAYS have discriminator fields
        first_aware_animal = aware_dict["animals"][0]
        aware_has_animal_type = "animal_type" in first_aware_animal
        aware_has_category = "discriminator_category" in first_aware_animal

        logger.debug(f"First aware animal has 'animal_type'? {aware_has_animal_type}")
        logger.debug(f"First aware animal has 'discriminator_category'? {aware_has_category}")

        # This should be True regardless of patching
        self.assertTrue(
            aware_has_animal_type,
            "DiscriminatorAwareBaseModel should include discriminator fields",
        )
        self.assertTrue(
            aware_has_category,
            "DiscriminatorAwareBaseModel should include standard discriminator fields",
        )

        logger.info("test_explicit_base_class_approach PASSED")

    def test_direct_model_dump(self):
        """Test direct model dump of discriminated models"""
        logger.info("Running test_direct_model_dump")

        # Create a dog instance
        dog = Dog(name="Rex", breed="German Shepherd")

        # With monkey patching enabled
        DiscriminatedConfig.enable_monkey_patching()
        logger.debug("With monkey patching ENABLED:")

        # Standard serialization - should include discriminators
        dog_dict = dog.model_dump()
        logger.debug(f"Standard serialization: {dog_dict}")
        self.assertIn(
            "animal_type",
            dog_dict,
            "Discriminator field should be included when patching is enabled",
        )
        self.assertIn(
            "discriminator_category",
            dog_dict,
            "Standard discriminator field should be included when patching is enabled",
        )

        # With explicit use_discriminators=True - should include discriminators
        dog_dict_explicit_true = dog.model_dump(use_discriminators=True)
        logger.debug(f"With use_discriminators=True: {dog_dict_explicit_true}")
        self.assertIn(
            "animal_type",
            dog_dict_explicit_true,
            "Discriminator field should be included with use_discriminators=True",
        )
        self.assertIn(
            "discriminator_category",
            dog_dict_explicit_true,
            "Standard discriminator field should be included with use_discriminators=True",
        )

        # With explicit use_discriminators=False - should NOT include discriminators
        dog_dict_explicit_false = dog.model_dump(use_discriminators=False)
        logger.debug(f"With use_discriminators=False: {dog_dict_explicit_false}")
        self.assertNotIn(
            "animal_type",
            dog_dict_explicit_false,
            "Discriminator field should NOT be included with use_discriminators=False",
        )
        self.assertNotIn(
            "discriminator_category",
            dog_dict_explicit_false,
            "Standard discriminator field should NOT be included with use_discriminators=False",
        )

        # With monkey patching disabled
        DiscriminatedConfig.disable_monkey_patching()
        logger.debug("With monkey patching DISABLED:")

        # Standard serialization - should NOT include discriminators
        dog_dict_no_patch = dog.model_dump()
        logger.debug(f"Standard serialization: {dog_dict_no_patch}")
        self.assertNotIn(
            "animal_type",
            dog_dict_no_patch,
            "Discriminator field should NOT be included when patching is disabled",
        )
        self.assertNotIn(
            "discriminator_category",
            dog_dict_no_patch,
            "Standard discriminator field should NOT be included when patching is disabled",
        )

        # With explicit use_discriminators=True - should include discriminators
        dog_dict_no_patch_true = dog.model_dump(use_discriminators=True)
        logger.debug(f"With use_discriminators=True: {dog_dict_no_patch_true}")
        self.assertIn(
            "animal_type",
            dog_dict_no_patch_true,
            "Discriminator field should be included with use_discriminators=True",
        )
        self.assertIn(
            "discriminator_category",
            dog_dict_no_patch_true,
            "Standard discriminator field should be included with use_discriminators=True",
        )

        # With explicit use_discriminators=False - should NOT include discriminators
        dog_dict_no_patch_false = dog.model_dump(use_discriminators=False)
        logger.debug(f"With use_discriminators=False: {dog_dict_no_patch_false}")
        self.assertNotIn(
            "animal_type",
            dog_dict_no_patch_false,
            "Discriminator field should NOT be included with use_discriminators=False",
        )
        self.assertNotIn(
            "discriminator_category",
            dog_dict_no_patch_false,
            "Standard discriminator field should NOT be included with use_discriminators=False",
        )

        logger.info("test_direct_model_dump PASSED")

    def test_switching_approaches(self):
        """Test switching between approaches"""
        logger.info("Running test_switching_approaches")

        # Create instances
        dog = Dog(name="Rex", breed="German Shepherd")
        cat = Cat(name="Whiskers", lives_left=9)

        # Define both types of containers
        class RegularShelter(BaseModel):
            animals: List[Union[Dog, Cat]]

        class AwareShelter(DiscriminatorAwareBaseModel):
            animals: List[Union[Dog, Cat]]

        # First with monkey patching
        DiscriminatedConfig.enable_monkey_patching()
        logger.debug("With monkey patching enabled:")

        regular_shelter = RegularShelter(animals=[dog, cat])
        regular_dict = regular_shelter.model_dump()
        logger.debug(f"Regular shelter serialization: {regular_dict}")

        # Check first animal's discriminator fields - should be present
        first_animal = regular_dict["animals"][0]
        has_animal_type = "animal_type" in first_animal
        has_category = "discriminator_category" in first_animal

        logger.debug(
            f"First animal discriminator fields: animal_type={has_animal_type}, discriminator_category={has_category}"
        )
        self.assertTrue(
            has_animal_type,
            "Discriminator field should be present when patching is enabled",
        )
        self.assertTrue(
            has_category,
            "Standard discriminator field should be present when patching is enabled",
        )

        # Then without monkey patching
        DiscriminatedConfig.disable_monkey_patching()
        logger.debug("With monkey patching disabled:")

        regular_shelter_no_patch = RegularShelter(animals=[dog, cat])
        regular_dict_no_patch = regular_shelter_no_patch.model_dump()
        logger.debug(f"Regular shelter serialization: {regular_dict_no_patch}")

        # Check first animal's discriminator fields - should NOT be present
        first_animal_no_patch = regular_dict_no_patch["animals"][0]
        has_animal_type_no_patch = "animal_type" in first_animal_no_patch
        has_category_no_patch = "discriminator_category" in first_animal_no_patch

        logger.debug(
            f"First animal discriminator fields: animal_type={has_animal_type_no_patch}, discriminator_category={has_category_no_patch}"
        )
        self.assertFalse(
            has_animal_type_no_patch,
            "Discriminator field should NOT be present when patching is disabled",
        )
        self.assertFalse(
            has_category_no_patch,
            "Standard discriminator field should NOT be present when patching is disabled",
        )

        # Test with DiscriminatorAwareBaseModel - should always include discriminators
        aware_shelter_no_patch = AwareShelter(animals=[dog, cat])
        aware_dict_no_patch = aware_shelter_no_patch.model_dump()
        logger.debug(f"Aware shelter serialization: {aware_dict_no_patch}")

        # Check first animal's discriminator fields - should be present
        first_animal_aware = aware_dict_no_patch["animals"][0]
        has_animal_type_aware = "animal_type" in first_animal_aware
        has_category_aware = "discriminator_category" in first_animal_aware

        logger.debug(
            f"First aware animal discriminator fields: animal_type={has_animal_type_aware}, discriminator_category={has_category_aware}"
        )
        self.assertTrue(
            has_animal_type_aware,
            "Discriminator field should be present in DiscriminatorAwareBaseModel",
        )
        self.assertTrue(
            has_category_aware,
            "Standard discriminator field should be present in DiscriminatorAwareBaseModel",
        )

        logger.info("test_switching_approaches PASSED")

    def test_json_serialization(self):
        """Test JSON serialization with both approaches"""
        logger.info("Running test_json_serialization")

        # Create some instances
        dog = Dog(name="Rex", breed="German Shepherd")
        cat = Cat(name="Whiskers", lives_left=9)

        # With monkey patching
        DiscriminatedConfig.enable_monkey_patching()
        logger.debug("With monkey patching enabled:")

        class RegularShelter(BaseModel):
            animals: List[Union[Dog, Cat]]

        regular_shelter = RegularShelter(animals=[dog, cat])
        regular_json = regular_shelter.model_dump_json()
        logger.debug(f"Regular shelter JSON: {regular_json}")

        # Parse the JSON to check for discriminator fields
        regular_data = json.loads(regular_json)
        first_animal_json = regular_data["animals"][0]
        self.assertIn(
            "animal_type",
            first_animal_json,
            "Discriminator field should be present in JSON when patching is enabled",
        )
        self.assertIn(
            "discriminator_category",
            first_animal_json,
            "Standard discriminator field should be present in JSON when patching is enabled",
        )

        # Without monkey patching
        DiscriminatedConfig.disable_monkey_patching()
        logger.debug("With monkey patching disabled:")

        class AwareShelter(DiscriminatorAwareBaseModel):
            animals: List[Union[Dog, Cat]]

        aware_shelter = AwareShelter(animals=[dog, cat])
        aware_json = aware_shelter.model_dump_json()
        logger.debug(f"Aware shelter JSON: {aware_json}")

        # Parse the JSON to check for discriminator fields
        aware_data = json.loads(aware_json)
        first_animal_aware_json = aware_data["animals"][0]
        self.assertIn(
            "animal_type",
            first_animal_aware_json,
            "Discriminator field should be present in JSON with DiscriminatorAwareBaseModel",
        )
        self.assertIn(
            "discriminator_category",
            first_animal_aware_json,
            "Standard discriminator field should be present in JSON with DiscriminatorAwareBaseModel",
        )

        logger.info("test_json_serialization PASSED")

    def test_explicit_model_dump_with_discriminators(self):
        """Test explicitly controlling discriminators with use_discriminators parameter"""
        logger.info("Running test_explicit_model_dump_with_discriminators")

        # Create dog instance
        dog = Dog(name="Rex", breed="German Shepherd")
        cat = Cat(name="Whiskers", lives_left=9)

        # Create container
        class RegularShelter(BaseModel):
            animals: List[Union[Dog, Cat]]

        # Create shelter
        shelter = RegularShelter(animals=[dog, cat])

        # Try all combinations
        logger.debug("With monkey patching ENABLED:")
        DiscriminatedConfig.enable_monkey_patching()

        # 1. Default - should include discriminators
        shelter_dict = shelter.model_dump()
        logger.debug("Default serialization:")
        has_animal_type = "animal_type" in shelter_dict["animals"][0]
        logger.debug(f"  First animal has 'animal_type'? {has_animal_type}")
        self.assertTrue(
            has_animal_type,
            "Discriminator field should be present by default when patching is enabled",
        )

        # 2. Explicit True - should include discriminators
        shelter_dict_true = shelter.model_dump(use_discriminators=True)
        logger.debug("With use_discriminators=True:")
        has_animal_type_true = "animal_type" in shelter_dict_true["animals"][0]
        logger.debug(f"  First animal has 'animal_type'? {has_animal_type_true}")
        self.assertTrue(
            has_animal_type_true,
            "Discriminator field should be present with use_discriminators=True",
        )

        # 3. Explicit False - should NOT include discriminators
        shelter_dict_false = shelter.model_dump(use_discriminators=False)
        logger.debug("With use_discriminators=False:")
        has_animal_type_false = "animal_type" in shelter_dict_false["animals"][0]
        logger.debug(f"  First animal has 'animal_type'? {has_animal_type_false}")
        self.assertFalse(
            has_animal_type_false,
            "Discriminator field should NOT be present with use_discriminators=False",
        )

        logger.debug("With monkey patching DISABLED:")
        DiscriminatedConfig.disable_monkey_patching()

        # 4. Default - should NOT include discriminators
        shelter_dict_disabled = shelter.model_dump()
        logger.debug("Default serialization:")
        has_animal_type_disabled = "animal_type" in shelter_dict_disabled["animals"][0]
        logger.debug(f"  First animal has 'animal_type'? {has_animal_type_disabled}")
        self.assertFalse(
            has_animal_type_disabled,
            "Discriminator field should NOT be present by default when patching is disabled",
        )

        # 5. Explicit True - should include discriminators
        shelter_dict_disabled_true = shelter.model_dump(use_discriminators=True)
        logger.debug("With use_discriminators=True:")
        has_animal_type_disabled_true = "animal_type" in shelter_dict_disabled_true["animals"][0]
        logger.debug(f"  First animal has 'animal_type'? {has_animal_type_disabled_true}")
        self.assertTrue(
            has_animal_type_disabled_true,
            "Discriminator field should be present with use_discriminators=True even when patching is disabled",
        )

        # 6. Explicit False - should NOT include discriminators
        shelter_dict_disabled_false = shelter.model_dump(use_discriminators=False)
        logger.debug("With use_discriminators=False:")
        has_animal_type_disabled_false = "animal_type" in shelter_dict_disabled_false["animals"][0]
        logger.debug(f"  First animal has 'animal_type'? {has_animal_type_disabled_false}")
        self.assertFalse(
            has_animal_type_disabled_false,
            "Discriminator field should NOT be present with use_discriminators=False",
        )

        logger.info("test_explicit_model_dump_with_discriminators PASSED")


def main():
    # Print registry contents
    logger.info("Registry contents:")
    for category, models in DiscriminatedModelRegistry._registry.items():
        logger.info(f"  Category: {category}")
        for disc_value, model_cls in models.items():
            logger.info(f"    {disc_value} -> {model_cls.__name__}")

    # Run tests with unittest
    test_suite = unittest.TestLoader().loadTestsFromTestCase(DiscriminatorTests)
    test_result = unittest.TextTestRunner(verbosity=2).run(test_suite)

    # Log overall test results
    passed = test_result.wasSuccessful()
    logger.info(f"All tests {'PASSED' if passed else 'FAILED'}")
    logger.info(
        f"Tests run: {test_result.testsRun}, Errors: {len(test_result.errors)}, Failures: {len(test_result.failures)}"
    )

    # Reset to default state
    DiscriminatedConfig.enable_monkey_patching()


if __name__ == "__main__":
    main()
