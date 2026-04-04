import pytest
from app.utils.validation import validate_dataset_name


class TestValidateDatasetName:
    """Test suite for validate_dataset_name function."""

    # ========== Valid Cases ==========
    def test_valid_simple_name(self):
        """Test valid single-word lowercase name."""
        assert validate_dataset_name("main") == "main"

    def test_valid_name_with_hyphens(self):
        """Test valid name with hyphens separating words."""
        assert validate_dataset_name("fast-food") == "fast-food"

    def test_valid_name_with_numbers(self):
        """Test valid name with numbers."""
        assert validate_dataset_name("dataset123") == "dataset123"

    def test_valid_name_mixed_with_hyphens_and_numbers(self):
        """Test valid name with numbers and hyphens."""
        assert validate_dataset_name("fast-food-123") == "fast-food-123"

    def test_valid_name_multiple_hyphens(self):
        """Test valid name with multiple hyphen-separated segments."""
        assert validate_dataset_name("my-fast-food-dataset") == "my-fast-food-dataset"

    def test_valid_name_starts_with_number(self):
        """Test valid name starting with a number."""
        assert validate_dataset_name("123-dataset") == "123-dataset"

    # ========== Invalid: Empty ==========
    def test_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Dataset name cannot be empty"):
            validate_dataset_name("")

    # ========== Invalid: Uppercase ==========
    def test_uppercase_letters(self):
        """Test that uppercase letters are rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("FastFood")

    def test_mixed_case(self):
        """Test that mixed case is rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("Fast-food")

    # ========== Invalid: Special Characters ==========
    def test_underscore_not_allowed(self):
        """Test that underscores are rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("fast_food")

    def test_space_not_allowed(self):
        """Test that spaces are rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("fast food")

    def test_dot_not_allowed(self):
        """Test that dots are rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("fast.food")

    def test_special_characters_not_allowed(self):
        """Test that special characters are rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("fast@food")

    # ========== Invalid: Hyphen Placement ==========
    def test_leading_hyphen(self):
        """Test that leading hyphens are rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("-fast-food")

    def test_trailing_hyphen(self):
        """Test that trailing hyphens are rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("fast-food-")


    def test_only_hyphen(self):
        """Test that only a hyphen is rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("-")

    # ========== Error Message Validation ==========
    def test_error_message_includes_name(self):
        """Test that error message includesinvalid name."""
        invalid_name = "Invalid@Name"
        with pytest.raises(ValueError, match=f"Invalid dataset name '{invalid_name}'"):
            validate_dataset_name(invalid_name)

    def test_error_message_includes_guidance(self):
        """Test that error message includes guidance."""
        with pytest.raises(ValueError, match="Use lowercase letters, numbers, and hyphens only"):
            validate_dataset_name("INVALID")