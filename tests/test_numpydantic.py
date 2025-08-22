import unittest
import logging
import numpy as np
import json
import sys
from typing import List, Dict, Any, Union, Optional
from pydantic import BaseModel
from enum import Enum

try:
    import numpydantic
    from numpydantic import NDArray, Shape

    NUMPYDANTIC_AVAILABLE = True
except ImportError:
    NUMPYDANTIC_AVAILABLE = False

    # Create mocks for the test to skip if numpydantic isn't installed
    class NDArray:
        pass

    class Shape:
        pass


from pydantic_discriminated.api import (
    discriminated_model,
    DiscriminatedBaseModel,
    DiscriminatedConfig,
)

# Configure logging
logger = logging.getLogger("numpydantic_tests")
logger.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# Define test models
class DataType(str, Enum):
    TIMESERIES = "timeseries"
    IMAGE = "image"
    SCALAR = "scalar"


@discriminated_model(DataType, DataType.TIMESERIES)
class TimeseriesData(DiscriminatedBaseModel):
    # Use proper numpydantic type annotation
    values: NDArray[Shape["* samples"], float]
    timestamps: List[float]
    name: str


@discriminated_model(DataType, DataType.IMAGE)
class ImageData(DiscriminatedBaseModel):
    # Use proper numpydantic type annotation for 2D image
    pixels: NDArray[Shape["* height, * width"], float]
    width: int
    height: int


@discriminated_model(DataType, DataType.SCALAR)
class ScalarData(DiscriminatedBaseModel):
    value: float
    unit: str


class Dataset(BaseModel):
    name: str
    data: List[Union[TimeseriesData, ImageData, ScalarData]]
    metadata: Dict[str, Any] = {}


class NumpydanticTests(unittest.TestCase):
    @unittest.skipIf(not NUMPYDANTIC_AVAILABLE, "numpydantic not installed")
    def setUp(self):
        # Reset to default state before each test
        DiscriminatedConfig.enable_monkey_patching()
        logger.debug("Test setup complete - monkey patching enabled")

        # Create test data
        self.timeseries = TimeseriesData(
            values=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            timestamps=[1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
            name="Temperature",
        )

        self.image = ImageData(pixels=np.random.rand(4, 4), width=4, height=4)  # Small 4x4 "image"

        self.scalar = ScalarData(value=42.0, unit="kg")

        # Create a dataset
        self.dataset = Dataset(
            name="Test Dataset",
            data=[self.timeseries, self.image, self.scalar],
            metadata={"created_by": "test", "version": 1.0},
        )

        logger.debug(f"Test objects created")

        # # Define a numpy-aware JSON encoder for our tests
        # class NumpyEncoder(json.JSONEncoder):
        #     def default(self, obj):
        #         if isinstance(obj, np.ndarray):
        #             return obj.tolist()
        #         return super().default(obj)

        # Define a numpy-aware JSON encoder function (not a class)
        def numpy_encoder(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            # Handle enum values
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        self.numpy_encoder = numpy_encoder

    @unittest.skipIf(not NUMPYDANTIC_AVAILABLE, "numpydantic not installed")
    def test_model_validation(self):
        """Test that numpydantic correctly validates array shapes"""
        logger.debug("Running test_model_validation")

        # Valid shapes should work
        valid_ts = TimeseriesData(
            values=np.array([1.0, 2.0, 3.0]), timestamps=[1.0, 2.0, 3.0], name="Valid TS"
        )

        # Invalid shape should fail
        with self.assertRaises(Exception):
            invalid_ts = TimeseriesData(
                values=np.array([[1.0, 2.0], [3.0, 4.0]]),  # 2D array, not 1D
                timestamps=[1.0, 2.0, 3.0, 4.0],
                name="Invalid TS",
            )

        # Valid 2D image
        valid_img = ImageData(pixels=np.random.rand(10, 20), width=20, height=10)

        # Invalid image dimension
        with self.assertRaises(Exception):
            invalid_img = ImageData(
                pixels=np.random.rand(10), width=10, height=1  # 1D array, not 2D
            )

        logger.debug("Shape validation tests passed")

    @unittest.skipIf(not NUMPYDANTIC_AVAILABLE, "numpydantic not installed")
    def test_model_dump(self):
        """Test model_dump with numpydantic arrays"""
        logger.debug("Running test_model_dump")

        # model_dump should preserve numpy arrays
        ts_dict = self.timeseries.model_dump()
        logger.debug(f"Timeseries model_dump successful")

        # Check if values is still a numpy array
        self.assertIn("values", ts_dict)
        self.assertTrue(isinstance(ts_dict["values"], np.ndarray))

        # Check discriminator fields
        self.assertIn("datatype", ts_dict)
        self.assertEqual(ts_dict["datatype"], DataType.TIMESERIES.value)

        # Nested model_dump should also preserve arrays
        dataset_dict = self.dataset.model_dump()
        logger.debug(f"Dataset model_dump successful")

        # Check if the nested array is still a numpy array
        self.assertTrue(isinstance(dataset_dict["data"][0]["values"], np.ndarray))

    @unittest.skipIf(not NUMPYDANTIC_AVAILABLE, "numpydantic not installed")
    def test_json_serialization_with_encoder(self):
        """Test JSON serialization using a custom encoder"""
        logger.debug("Running test_json_serialization_with_encoder")

        # Try to serialize with a custom encoder
        try:
            # Use our custom encoder
            ts_json = self.timeseries.model_dump_json(encoder=self.numpy_encoder)
            logger.debug("Timeseries JSON serialization successful with custom encoder")

            # Parse and verify
            ts_parsed = json.loads(ts_json)
            self.assertIn("values", ts_parsed)
            self.assertIsInstance(ts_parsed["values"], list)

            # Now try with the dataset
            dataset_json = self.dataset.model_dump_json(encoder=self.numpy_encoder)
            logger.debug("Dataset JSON serialization successful with custom encoder")

            # Parse and verify
            ds_parsed = json.loads(dataset_json)
            self.assertIn("data", ds_parsed)
            self.assertIsInstance(ds_parsed["data"][0]["values"], list)

            # Pretty print with indent
            pretty_json = self.dataset.model_dump_json(encoder=self.numpy_encoder, indent=2)
            logger.debug("Pretty JSON successful")
            self.assertIn("\n", pretty_json)

        except Exception as e:
            logger.error(f"JSON serialization with encoder failed: {str(e)}")
            self.fail(f"JSON serialization with encoder failed: {str(e)}")

    @unittest.skipIf(not NUMPYDANTIC_AVAILABLE, "numpydantic not installed")
    def test_json_serialization_fails_without_encoder(self):
        """Test that JSON serialization fails without a custom encoder"""
        logger.debug("Running test_json_serialization_fails_without_encoder")

        # Standard JSON serialization should fail due to numpy arrays
        with self.assertRaises(TypeError):
            self.timeseries.model_dump_json()

        # Explicitly test with various array dimensions
        with self.assertRaises(TypeError):
            # 1D array
            model = TimeseriesData(
                values=np.array([1.0, 2.0, 3.0]), timestamps=[1.0, 2.0, 3.0], name="TS"
            )
            model.model_dump_json()

        with self.assertRaises(TypeError):
            # 2D array
            model = ImageData(pixels=np.random.rand(5, 5), width=5, height=5)
            model.model_dump_json()

        logger.debug("As expected, JSON serialization fails without a custom encoder")

    @unittest.skipIf(not NUMPYDANTIC_AVAILABLE, "numpydantic not installed")
    def test_model_dump_with_discriminators(self):
        """Test model_dump with use_discriminators parameter"""
        logger.debug("Running test_model_dump_with_discriminators")

        # With discriminators (default)
        ts_with_disc = self.timeseries.model_dump()
        self.assertIn("datatype", ts_with_disc)

        # Without discriminators
        ts_no_disc = self.timeseries.model_dump(use_discriminators=False)
        self.assertNotIn("datatype", ts_no_disc)

        # Make sure this works with JSON too (when using an encoder)
        ts_json_with_disc = self.timeseries.model_dump_json(encoder=self.numpy_encoder)
        ts_parsed_with_disc = json.loads(ts_json_with_disc)
        self.assertIn("datatype", ts_parsed_with_disc)

        ts_json_no_disc = self.timeseries.model_dump_json(
            encoder=self.numpy_encoder, use_discriminators=False
        )
        ts_parsed_no_disc = json.loads(ts_json_no_disc)
        self.assertNotIn("datatype", ts_parsed_no_disc)

        logger.debug("Discriminator control tests passed")
