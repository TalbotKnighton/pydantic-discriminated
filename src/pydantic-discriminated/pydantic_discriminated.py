from enum import Enum
from typing import (
    Any,
    Dict,
    Type,
    Union,
    Callable,
    ClassVar,
    List,
    Optional,
    get_args,
    get_origin,
    TypeVar,
    Generic,
    overload,
    cast,
    ClassVar,
)
from pydantic import BaseModel, Field, field_validator, ConfigDict
import json

T = TypeVar("T", bound="DiscriminatedBaseModel")


# Global configuration with defaults
class DiscriminatedConfig:
    """Global configuration for discriminated models."""

    use_standard_fields: bool = True
    standard_category_field: str = "discriminator_category"
    standard_value_field: str = "discriminator_value"


class DiscriminatedModelRegistry:
    """Registry to store and retrieve discriminated models."""

    _registry: Dict[str, Dict[Any, Type["DiscriminatedBaseModel"]]] = {}

    @classmethod
    def register(
        cls, category: str, value: Any, model_cls: Type["DiscriminatedBaseModel"]
    ) -> None:
        """Register a model class for a specific category and discriminator value."""
        if category not in cls._registry:
            cls._registry[category] = {}
        cls._registry[category][value] = model_cls

    @classmethod
    def get_model(cls, category: str, value: Any) -> Type["DiscriminatedBaseModel"]:
        """Get a model class by category and discriminator value."""
        if category not in cls._registry:
            raise ValueError(f"No models registered for category '{category}'")
        if value not in cls._registry[category]:
            raise ValueError(
                f"No model found for value '{value}' in category '{category}'"
            )
        return cls._registry[category][value]

    @classmethod
    def get_models_for_category(
        cls, category: str
    ) -> Dict[Any, Type["DiscriminatedBaseModel"]]:
        """Get all models registered for a specific category."""
        if category not in cls._registry:
            raise ValueError(f"No models registered for category '{category}'")
        return cls._registry[category]


def _dump_with_discriminators(obj: Any) -> Any:
    """
    Helper function to serialize an object with discriminators.
    """
    if isinstance(obj, DiscriminatedBaseModel):
        # For discriminated models, get standard serialization and add discriminator
        result = BaseModel.model_dump(obj)  # Use BaseModel's original method

        # Always add the domain-specific discriminator field
        if obj._discriminator_field and obj._discriminator_value is not None:
            result[obj._discriminator_field] = obj._discriminator_value

        # Add the standardized discriminator fields if configured
        use_standard_fields = getattr(
            obj, "_use_standard_fields", DiscriminatedConfig.use_standard_fields
        )
        if use_standard_fields:
            result[DiscriminatedConfig.standard_category_field] = (
                obj._discriminator_field
            )
            result[DiscriminatedConfig.standard_value_field] = obj._discriminator_value

        return result

    elif isinstance(obj, DiscriminatorAwareBaseModel):
        # For aware models, process each field directly
        result = {}

        # Process each field in the model
        for field_name, field_value in obj.__dict__.items():
            if field_name.startswith("_"):
                continue  # Skip private fields

            if isinstance(field_value, list):
                # Handle list fields
                result[field_name] = []
                for item in field_value:
                    result[field_name].append(_dump_with_discriminators(item))

            elif isinstance(field_value, BaseModel):
                # Handle nested model fields
                result[field_name] = _dump_with_discriminators(field_value)

            else:
                # Handle primitive fields
                result[field_name] = field_value

        return result

    elif isinstance(obj, BaseModel):
        # For other models, use standard serialization
        return obj.model_dump()

    elif isinstance(obj, list):
        # For lists, process each item
        return [_dump_with_discriminators(item) for item in obj]

    elif isinstance(obj, dict):
        # For dictionaries, process each value
        return {key: _dump_with_discriminators(value) for key, value in obj.items()}

    else:
        # Return other types as-is
        return obj


class DiscriminatorAwareBaseModel(BaseModel):
    """
    Base model that handles discriminators in serialization, including nested models.
    """

    def model_dump(self, **kwargs):
        """
        Override model_dump to include discriminators at all nesting levels.
        """
        return _dump_with_discriminators(self)

    def model_dump_json(self, **kwargs):
        """
        Override model_dump_json to include discriminators at all nesting levels.
        """
        # Get data with discriminators
        data = self.model_dump(**kwargs)

        # Use the encoder param if provided, otherwise use the default
        encoder = kwargs.pop("encoder", None)

        # Convert to JSON
        return json.dumps(data, default=encoder, **kwargs)


class DiscriminatedBaseModel(DiscriminatorAwareBaseModel):
    """
    Base class for discriminated models that ensures discriminator fields are included
    in serialization.
    """

    # Legacy fields for compatibility
    _discriminator_field: ClassVar[str] = ""
    _discriminator_value: ClassVar[Any] = None
    _use_standard_fields: ClassVar[bool] = DiscriminatedConfig.use_standard_fields

    def __getattr__(self, name):
        """
        Custom attribute access to handle discriminator field.
        """
        # Handle access to the legacy discriminator field
        if name == self._discriminator_field:
            return self._discriminator_value

        # Handle access to standard discriminator fields
        if name == DiscriminatedConfig.standard_category_field:
            return self._discriminator_field
        if name == DiscriminatedConfig.standard_value_field:
            return self._discriminator_value

        # Default behavior for other attributes
        return super().__getattr__(name)

    @classmethod
    def model_validate(cls: Type[T], obj: Any, **kwargs) -> T:
        """
        Validate the given object and return an instance of this model.
        Enhanced to handle discriminator validation.

        Args:
            obj: The object to validate
            **kwargs: Additional arguments to pass to the original model_validate

        Returns:
            An instance of this model
        """
        use_standard_fields = getattr(
            cls, "_use_standard_fields", DiscriminatedConfig.use_standard_fields
        )

        if isinstance(obj, dict):
            new_obj = obj.copy()  # Create a copy to avoid modifying the original

            # Check if we have standard discriminator fields
            if (
                use_standard_fields
                and DiscriminatedConfig.standard_category_field in new_obj
                and DiscriminatedConfig.standard_value_field in new_obj
            ):

                # Use standard fields for validation
                if (
                    new_obj[DiscriminatedConfig.standard_category_field]
                    != cls._discriminator_field
                ):
                    raise ValueError(
                        f"Invalid discriminator category: expected {cls._discriminator_field}, "
                        f"got {new_obj[DiscriminatedConfig.standard_category_field]}"
                    )
                if (
                    new_obj[DiscriminatedConfig.standard_value_field]
                    != cls._discriminator_value
                ):
                    raise ValueError(
                        f"Invalid discriminator value: expected {cls._discriminator_value}, "
                        f"got {new_obj[DiscriminatedConfig.standard_value_field]}"
                    )

            # Check legacy field if present
            elif cls._discriminator_field and cls._discriminator_field in new_obj:
                if new_obj[cls._discriminator_field] != cls._discriminator_value:
                    raise ValueError(
                        f"Invalid discriminator value: expected {cls._discriminator_value}, "
                        f"got {new_obj[cls._discriminator_field]}"
                    )

            # Add domain-specific discriminator field if missing
            if cls._discriminator_field and cls._discriminator_field not in new_obj:
                new_obj[cls._discriminator_field] = cls._discriminator_value

            # Add standard discriminator fields if configured and missing
            if use_standard_fields:
                if DiscriminatedConfig.standard_category_field not in new_obj:
                    new_obj[DiscriminatedConfig.standard_category_field] = (
                        cls._discriminator_field
                    )
                if DiscriminatedConfig.standard_value_field not in new_obj:
                    new_obj[DiscriminatedConfig.standard_value_field] = (
                        cls._discriminator_value
                    )

            obj = new_obj

        # Call the original model_validate
        instance = super().model_validate(obj, **kwargs)

        # Set the discriminator values on the instance
        object.__setattr__(instance, "_discriminator_field", cls._discriminator_field)
        object.__setattr__(instance, "_discriminator_value", cls._discriminator_value)
        object.__setattr__(instance, "_use_standard_fields", use_standard_fields)

        # For backward compatibility, also set the domain-specific field
        if cls._discriminator_field:
            object.__setattr__(
                instance, cls._discriminator_field, cls._discriminator_value
            )

        # Set standard fields if configured
        if use_standard_fields:
            object.__setattr__(
                instance,
                DiscriminatedConfig.standard_category_field,
                cls._discriminator_field,
            )
            object.__setattr__(
                instance,
                DiscriminatedConfig.standard_value_field,
                cls._discriminator_value,
            )

        return instance

    @classmethod
    def model_validate_json(cls: Type[T], json_data: Union[str, bytes], **kwargs) -> T:
        """
        Validate the given JSON data and return an instance of this model.
        Enhanced to handle discriminator validation.

        Args:
            json_data: The JSON data to validate
            **kwargs: Additional arguments to pass to the original model_validate_json

        Returns:
            An instance of this model
        """
        # Parse JSON first
        if isinstance(json_data, bytes):
            json_data = json_data.decode()
        data = json.loads(json_data)

        # Now validate with our enhanced model_validate
        return cls.model_validate(data, **kwargs)

    @classmethod
    def validate_discriminated(cls, data: Dict[str, Any]) -> "DiscriminatedBaseModel":
        """
        Validate and return the appropriate discriminated model based on the discriminator value.

        Args:
            data: The data to validate

        Returns:
            An instance of the appropriate discriminated model
        """
        use_standard_fields = getattr(
            cls, "_use_standard_fields", DiscriminatedConfig.use_standard_fields
        )

        # First check standard discriminator fields if configured
        if (
            use_standard_fields
            and DiscriminatedConfig.standard_category_field in data
            and DiscriminatedConfig.standard_value_field in data
        ):

            category = data[DiscriminatedConfig.standard_category_field]
            value = data[DiscriminatedConfig.standard_value_field]

        # Fall back to domain-specific field
        elif cls._discriminator_field and cls._discriminator_field in data:
            category = cls._discriminator_field
            value = data[cls._discriminator_field]
        else:
            raise ValueError(f"No discriminator fields found in data")

        # Get the appropriate model class
        model_cls = DiscriminatedModelRegistry.get_model(category, value)

        # Validate with the model class
        return model_cls.model_validate(data)


def discriminated_model(
    category: Union[str, Type[Enum]],
    discriminator: Any,
    use_standard_fields: Optional[bool] = None,
) -> Callable[[Type[T]], Type[T]]:
    """
    Decorator to create a discriminated model.

    Args:
        category: The category field name or Enum class
        discriminator: The discriminator value for this model
        use_standard_fields: Whether to use standard discriminator fields (default: global setting)

    Returns:
        A decorator function that registers the model class
    """
    category_field = category
    if isinstance(category, type) and issubclass(category, Enum):
        category_field = category.__name__.lower()

    field_name = str(category_field)

    def decorator(cls: Type[T]) -> Type[T]:
        # Make sure the class inherits from DiscriminatedBaseModel
        if not issubclass(cls, DiscriminatedBaseModel):
            raise TypeError(f"{cls.__name__} must inherit from DiscriminatedBaseModel")

        # Register the model
        DiscriminatedModelRegistry.register(field_name, discriminator, cls)

        # Store the discriminator information as class variables
        cls._discriminator_field = field_name
        cls._discriminator_value = discriminator

        # Set standard fields configuration
        if use_standard_fields is not None:
            cls._use_standard_fields = use_standard_fields
        elif hasattr(cls, "model_config") and "use_standard_fields" in cls.model_config:
            cls._use_standard_fields = cls.model_config["use_standard_fields"]
        else:
            cls._use_standard_fields = DiscriminatedConfig.use_standard_fields

        # Add the discriminator fields to the model's annotations
        if not hasattr(cls, "__annotations__"):
            cls.__annotations__ = {}

        # Determine the type of the discriminator field
        if isinstance(discriminator, Enum):
            field_type = type(discriminator)
        else:
            field_type = type(discriminator)

        # Add domain-specific field to annotations
        cls.__annotations__[field_name] = field_type

        # Add standard fields to annotations if configured
        if cls._use_standard_fields:
            cls.__annotations__[DiscriminatedConfig.standard_category_field] = str
            cls.__annotations__[DiscriminatedConfig.standard_value_field] = field_type

        # Override __init__ to set the discriminator values
        original_init = cls.__init__

        def init_with_discriminator(self, **data):
            # Add domain-specific discriminator field if missing
            if field_name not in data:
                data[field_name] = discriminator

            # Add standard fields if configured
            use_std_fields = cls._use_standard_fields
            if use_std_fields:
                if DiscriminatedConfig.standard_category_field not in data:
                    data[DiscriminatedConfig.standard_category_field] = field_name
                if DiscriminatedConfig.standard_value_field not in data:
                    data[DiscriminatedConfig.standard_value_field] = discriminator

            original_init(self, **data)

            # Ensure discriminator values are set as instance attributes
            object.__setattr__(self, field_name, discriminator)
            object.__setattr__(self, "_discriminator_field", field_name)
            object.__setattr__(self, "_discriminator_value", discriminator)
            object.__setattr__(self, "_use_standard_fields", use_std_fields)

            # Set standard fields if configured
            if use_std_fields:
                object.__setattr__(
                    self, DiscriminatedConfig.standard_category_field, field_name
                )
                object.__setattr__(
                    self, DiscriminatedConfig.standard_value_field, discriminator
                )

        cls.__init__ = init_with_discriminator

        return cls

    return decorator
