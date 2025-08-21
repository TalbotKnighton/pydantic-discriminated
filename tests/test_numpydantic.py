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
    from numpydantic import NDArray as NumpyNDArray

    NUMPYDANTIC_AVAILABLE = True
except ImportError:
    NUMPYDANTIC_AVAILABLE = False

    # Create a mock for the test to skip if numpydantic isn't installed
    class NumpyNDArray:
        pass


from pydantic_discriminated import (
    discriminated_model,
    DiscriminatedBaseModel,
    DiscriminatedConfig,
    DiscriminatorAwareBaseModel,
    # _process_discriminators,
)
from pydantic_discriminated.api import _process_discriminators

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
    values: NumpyNDArray
    timestamps: List[float]
    name: str


@discriminated_model(DataType, DataType.IMAGE)
class ImageData(DiscriminatedBaseModel):
    pixels: NumpyNDArray
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

    # Update the test_direct_serialization method
    @unittest.skipIf(not NUMPYDANTIC_AVAILABLE, "numpydantic not installed")
    def test_direct_serialization(self):
        """Test direct serialization of models with numpy arrays"""
        logger.debug("Running test_direct_serialization")

        # Try direct model_dump
        try:
            timeseries_dict = self.timeseries.model_dump()
            logger.debug(f"Timeseries model_dump successful")
            logger.debug(f"Keys in dump: {list(timeseries_dict.keys())}")
            self.assertIn("values", timeseries_dict)

            # Verify it's a numpy array (we now keep numpy arrays as-is during model_dump)
            import numpy as np

            self.assertTrue(isinstance(timeseries_dict["values"], np.ndarray))
        except Exception as e:
            logger.error(f"model_dump failed: {str(e)}")
            self.fail(f"model_dump failed: {str(e)}")

        # Try model_dump_json
        try:
            timeseries_json = self.timeseries.model_dump_json()
            logger.debug(f"Timeseries model_dump_json successful")
            # Parse the JSON to verify it's valid
            parsed = json.loads(timeseries_json)
            self.assertIn("values", parsed)
            # Now it should be a list in the JSON
            self.assertIsInstance(parsed["values"], list)
        except Exception as e:
            logger.error(f"model_dump_json failed: {str(e)}")
            self.fail(f"model_dump_json failed: {str(e)}")

    # Update the test_nested_serialization method
    @unittest.skipIf(not NUMPYDANTIC_AVAILABLE, "numpydantic not installed")
    def test_nested_serialization(self):
        """Test serialization of nested models with numpy arrays"""
        logger.debug("Running test_nested_serialization")

        # Try dataset model_dump
        try:
            dataset_dict = self.dataset.model_dump()
            logger.debug(f"Dataset model_dump successful")
            logger.debug(f"Top-level keys: {list(dataset_dict.keys())}")
            self.assertIn("data", dataset_dict)
            self.assertEqual(len(dataset_dict["data"]), 3)

            # Check the first item (timeseries)
            self.assertIn("values", dataset_dict["data"][0])

            # Verify it's a numpy array (we now keep numpy arrays as-is during model_dump)
            import numpy as np

            self.assertTrue(isinstance(dataset_dict["data"][0]["values"], np.ndarray))

            # Check discriminator fields
            self.assertIn("datatype", dataset_dict["data"][0])
            self.assertEqual(dataset_dict["data"][0]["datatype"], DataType.TIMESERIES.value)

        except Exception as e:
            logger.error(f"Dataset model_dump failed: {str(e)}")
            self.fail(f"Dataset model_dump failed: {str(e)}")

        # Try dataset model_dump_json
        try:
            dataset_json = self.dataset.model_dump_json()
            logger.debug(f"Dataset model_dump_json successful")
            # Parse the JSON to verify it's valid
            parsed = json.loads(dataset_json)
            self.assertIn("data", parsed)

            # Check that numpy arrays were converted to lists in the JSON
            self.assertIsInstance(parsed["data"][0]["values"], list)
        except Exception as e:
            logger.error(f"Dataset model_dump_json failed: {str(e)}")
            self.fail(f"Dataset model_dump_json failed: {str(e)}")

    @unittest.skipIf(not NUMPYDANTIC_AVAILABLE, "numpydantic not installed")
    def test_process_discriminators_with_numpy(self):
        """Test _process_discriminators function with numpy arrays"""
        logger.debug("Running test_process_discriminators_with_numpy")

        # First get the serialized data
        timeseries_dict = self.timeseries.model_dump()

        # Process with discriminators enabled
        try:
            processed_with_disc = _process_discriminators(
                self.timeseries, timeseries_dict, use_discriminators=True
            )
            logger.debug("_process_discriminators successful with discriminators enabled")
            self.assertIn("datatype", processed_with_disc)
            self.assertEqual(processed_with_disc["datatype"], DataType.TIMESERIES.value)
            self.assertIn("values", processed_with_disc)
        except Exception as e:
            logger.error(f"_process_discriminators failed with discriminators enabled: {str(e)}")
            self.fail(f"_process_discriminators failed: {str(e)}")

        # Process with discriminators disabled
        try:
            processed_no_disc = _process_discriminators(
                self.timeseries, timeseries_dict, use_discriminators=False
            )
            logger.debug("_process_discriminators successful with discriminators disabled")
            self.assertNotIn("datatype", processed_no_disc)
            self.assertIn("values", processed_no_disc)
        except Exception as e:
            logger.error(f"_process_discriminators failed with discriminators disabled: {str(e)}")
            self.fail(f"_process_discriminators failed: {str(e)}")

    @unittest.skipIf(not NUMPYDANTIC_AVAILABLE, "numpydantic not installed")
    def test_manual_json_serialization(self):
        """Test manually converting to JSON"""
        logger.debug("Running test_manual_json_serialization")

        # Get the dict representation
        timeseries_dict = self.timeseries.model_dump()

        # Standard json.dumps should fail with numpy arrays
        with self.assertRaises(TypeError):
            json_str = json.dumps(timeseries_dict)
            logger.debug("This should not succeed: Standard json.dumps successful")

        logger.debug("As expected, standard json.dumps failed with numpy arrays")

        # Try with custom encoder - this should work
        try:

            class NumpyEncoder(json.JSONEncoder):
                def default(self, obj):
                    import numpy as np

                    if isinstance(obj, np.ndarray):
                        return obj.tolist()
                    return json.JSONEncoder.default(self, obj)

            json_str = json.dumps(timeseries_dict, cls=NumpyEncoder)
            logger.debug("json.dumps with custom encoder successful")
            parsed = json.loads(json_str)
            self.assertIn("values", parsed)
            self.assertIsInstance(parsed["values"], list)
        except Exception as e:
            logger.error(f"json.dumps with custom encoder failed: {str(e)}")
            self.fail(f"JSON serialization with custom encoder failed: {str(e)}")

        # Now test using model_dump_json directly - our patched version should handle numpy arrays
        try:
            json_str = self.timeseries.model_dump_json()
            logger.debug("model_dump_json successful")
            parsed = json.loads(json_str)
            self.assertIn("values", parsed)
            self.assertIsInstance(parsed["values"], list)
        except Exception as e:
            logger.error(f"model_dump_json failed: {str(e)}")
            self.fail(f"model_dump_json failed: {str(e)}")


if __name__ == "__main__":
    unittest.main()
