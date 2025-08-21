import unittest
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Union, Optional
from enum import Enum
from pydantic import BaseModel, Field

from pydantic_discriminated import (
    discriminated_model,
    DiscriminatedBaseModel,
    DiscriminatedConfig,
    # _process_discriminators,
)
from pydantic_discriminated.api import _process_discriminators


# Define test models
class AnimalType(str, Enum):
    DOG = "dog"
    CAT = "cat"
    BIRD = "bird"


@discriminated_model(AnimalType, AnimalType.DOG)
class Dog(DiscriminatedBaseModel):
    name: str
    breed: str
    age: int


@discriminated_model(AnimalType, AnimalType.CAT)
class Cat(DiscriminatedBaseModel):
    name: str
    lives_left: int
    color: str


@discriminated_model(AnimalType, AnimalType.BIRD)
class Bird(DiscriminatedBaseModel):
    name: str
    can_fly: bool
    species: str


class PetOwner(BaseModel):
    name: str
    pets: List[Union[Dog, Cat, Bird]]
    favorite_pet: Optional[Union[Dog, Cat, Bird]] = None


class NestedStructure(BaseModel):
    metadata: Dict[str, Any]
    owners: List[PetOwner]


class ComplexStructureTests(unittest.TestCase):
    def setUp(self):
        # Reset to default state before each test
        DiscriminatedConfig.enable_monkey_patching()

        # Create some test models
        self.dog = Dog(name="Rex", breed="German Shepherd", age=5)
        self.cat = Cat(name="Whiskers", lives_left=9, color="white")
        self.bird = Bird(name="Tweety", can_fly=True, species="Canary")

        # Store the field name used for discriminator
        # This is AnimalType.__name__.lower() from the decorator
        self.disc_field = "animaltype"

        # Create a pet owner with pets
        self.owner = PetOwner(
            name="Alice", pets=[self.dog, self.cat, self.bird], favorite_pet=self.dog
        )

        # Create a complex nested structure
        self.nested = NestedStructure(
            metadata={
                "created_at": "2023-01-01",
                "animals_by_type": {
                    "dogs": [self.dog],
                    "cats": [self.cat],
                    "mixed": [self.dog, self.cat, self.bird],
                },
            },
            owners=[self.owner],
        )

    def test_pandas_series_processing(self):
        """Test processing pandas Series with discriminated models."""
        # Create a pandas Series with a discriminated model
        series = pd.Series(
            {
                "owner_name": "Bob",
                "pet": self.dog,
                "pets_list": [self.cat, self.bird],
                "pet_dict": {"primary": self.dog, "secondary": self.cat},
            }
        )

        # Create a dict representation like what would be produced during serialization
        series_dict = {
            "owner_name": "Bob",
            "pet": self.dog.model_dump(),
            "pets_list": [self.cat.model_dump(), self.bird.model_dump()],
            "pet_dict": {"primary": self.dog.model_dump(), "secondary": self.cat.model_dump()},
        }

        # Process with discriminators enabled
        processed_with_disc = _process_discriminators(series, series_dict, use_discriminators=True)

        # Check that discriminators are present - use self.disc_field instead of AnimalType.value
        self.assertIn(self.disc_field, processed_with_disc["pet"])
        self.assertEqual(processed_with_disc["pet"][self.disc_field], AnimalType.DOG.value)
        self.assertIn(self.disc_field, processed_with_disc["pets_list"][0])
        self.assertEqual(processed_with_disc["pets_list"][0][self.disc_field], AnimalType.CAT.value)
        self.assertIn(self.disc_field, processed_with_disc["pet_dict"]["primary"])
        self.assertEqual(
            processed_with_disc["pet_dict"]["primary"][self.disc_field], AnimalType.DOG.value
        )

        # Process with discriminators disabled
        processed_without_disc = _process_discriminators(
            series, series_dict, use_discriminators=False
        )

        # Check that discriminators are not present
        self.assertNotIn(self.disc_field, processed_without_disc["pet"])
        self.assertNotIn(self.disc_field, processed_without_disc["pets_list"][0])
        self.assertNotIn(self.disc_field, processed_without_disc["pet_dict"]["primary"])

    def test_numpy_array_processing(self):
        """Test processing structures with numpy arrays."""
        # Create a structure with numpy arrays
        numpy_data = {
            "array": np.array([1, 2, 3]),
            "matrix": np.array([[1, 2], [3, 4]]),
            "pet_in_array": {"data": np.array([self.dog.model_dump()])},
        }

        # Process with discriminators
        processed = _process_discriminators(None, numpy_data, use_discriminators=True)

        # Verify the structure is preserved
        self.assertTrue(isinstance(processed["array"], np.ndarray))
        self.assertEqual(processed["array"].tolist(), [1, 2, 3])
        self.assertTrue(isinstance(processed["matrix"], np.ndarray))
        self.assertEqual(processed["matrix"].tolist(), [[1, 2], [3, 4]])

        # Check the nested dict with model in array
        self.assertTrue(isinstance(processed["pet_in_array"]["data"], np.ndarray))
        # Cannot check discriminator here as numpy arrays don't get processed internally

    def test_custom_object_processing(self):
        """Test processing with custom objects."""

        # Define a custom object that has dict-like and attribute access
        class CustomContainer:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
                self._data = kwargs

            def __getitem__(self, key):
                return self._data[key]

            def get(self, key, default=None):
                return self._data.get(key, default)

            def keys(self):
                return self._data.keys()

        # Create a custom container with models
        container = CustomContainer(
            name="Custom Container", pet=self.dog, nested={"pets": [self.cat, self.bird]}
        )

        # Create a dict representation
        container_dict = {
            "name": "Custom Container",
            "pet": self.dog.model_dump(),
            "nested": {"pets": [self.cat.model_dump(), self.bird.model_dump()]},
        }

        # Process with discriminators
        processed = _process_discriminators(container, container_dict, use_discriminators=True)

        # Check that discriminators are present - use self.disc_field instead of AnimalType.value
        self.assertIn(self.disc_field, processed["pet"])
        self.assertEqual(processed["pet"][self.disc_field], AnimalType.DOG.value)
        self.assertIn(self.disc_field, processed["nested"]["pets"][0])
        self.assertEqual(processed["nested"]["pets"][0][self.disc_field], AnimalType.CAT.value)

        # Process without discriminators
        processed_no_disc = _process_discriminators(
            container, container_dict, use_discriminators=False
        )

        # Check that discriminators are not present
        self.assertNotIn(self.disc_field, processed_no_disc["pet"])
        self.assertNotIn(self.disc_field, processed_no_disc["nested"]["pets"][0])

    def test_mixed_object_types(self):
        """Test processing a mix of different object types."""
        # Create a mixed structure with different types
        mixed_data = {
            "series": pd.Series(
                {"name": "Series Data", "value": 42}
            ).to_dict(),  # Convert to dict first
            "model": self.owner.model_dump(),
            "numpy": np.array([1, 2, 3]),
            "list_of_mixed": [
                self.dog.model_dump(),
                pd.Series({"type": "series"}).to_dict(),  # Convert to dict
                {"type": "plain_dict", "pet": self.cat.model_dump()},
            ],
        }

        # Process with discriminators
        processed = _process_discriminators(None, mixed_data, use_discriminators=True)

        # Verify the structure
        self.assertIsInstance(processed["series"], dict)
        self.assertEqual(processed["series"]["name"], "Series Data")
        self.assertEqual(processed["series"]["value"], 42)

        # Check that discriminators exist in nested models
        self.assertIn("pets", processed["model"])
        self.assertIn(self.disc_field, processed["model"]["pets"][0])
        self.assertEqual(processed["model"]["pets"][0][self.disc_field], AnimalType.DOG.value)

        # Check numpy array
        self.assertTrue(isinstance(processed["numpy"], np.ndarray))

        # Check mixed list
        self.assertIn(self.disc_field, processed["list_of_mixed"][0])
        self.assertEqual(processed["list_of_mixed"][0][self.disc_field], AnimalType.DOG.value)
        self.assertEqual(processed["list_of_mixed"][1]["type"], "series")
        self.assertIn(self.disc_field, processed["list_of_mixed"][2]["pet"])
        self.assertEqual(
            processed["list_of_mixed"][2]["pet"][self.disc_field], AnimalType.CAT.value
        )

        # Process without discriminators
        processed_no_disc = _process_discriminators(None, mixed_data, use_discriminators=False)

        # Verify discriminators are removed
        self.assertNotIn(self.disc_field, processed_no_disc["model"]["pets"][0])
        self.assertNotIn(self.disc_field, processed_no_disc["list_of_mixed"][0])
        self.assertNotIn(self.disc_field, processed_no_disc["list_of_mixed"][2]["pet"])

    def test_error_handling(self):
        """Test that errors are handled gracefully."""

        # Create an object that raises errors on attribute/item access
        class ProblematicObject:
            def __getattr__(self, name):
                raise AttributeError(f"Attribute error for {name}")

            def __getitem__(self, key):
                raise KeyError(f"Key error for {key}")

            def get(self, key, default=None):
                raise ValueError(f"Value error for {key}")

        # Create data with problematic objects
        problem_data = {
            "normal": "value",
            "problem": ProblematicObject(),
            "nested": {"deeper": [{"problem": ProblematicObject()}, self.dog.model_dump()]},
        }

        # This should not raise exceptions, even with problematic objects
        try:
            processed = _process_discriminators(
                ProblematicObject(), problem_data, use_discriminators=True
            )

            # Check that normal values are processed
            self.assertEqual(processed["normal"], "value")
            self.assertIn("problem", processed)  # Problematic object should still be included
            self.assertIn(
                self.disc_field, processed["nested"]["deeper"][1]
            )  # Dog should have discriminator

            # Process without discriminators
            processed_no_disc = _process_discriminators(
                ProblematicObject(), problem_data, use_discriminators=False
            )

            # Check discriminators are removed
            self.assertNotIn(self.disc_field, processed_no_disc["nested"]["deeper"][1])

        except Exception as e:
            self.fail(f"_process_discriminators raised exception with problematic objects: {e}")


if __name__ == "__main__":
    unittest.main()
