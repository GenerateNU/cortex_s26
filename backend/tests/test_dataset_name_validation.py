import pytest

from app.utils.validation import sanitize_dataset_name, validate_dataset_name


class TestValidateDatasetName:
    """Test suite for validate_dataset_name function."""

    # ========== Valid Cases ==========
    def test_valid_simple_name(self):
        """Test valid single-word lowercase name."""
        assert validate_dataset_name("main") == "main"

    def test_valid_name_with_underscores(self):
        """Test valid name with underscores separating words."""
        assert validate_dataset_name("fast_food") == "fast_food"

    def test_valid_name_with_numbers(self):
        """Test valid name with numbers."""
        assert validate_dataset_name("dataset123") == "dataset123"

    def test_valid_name_mixed_with_underscores_and_numbers(self):
        """Test valid name with numbers and underscores."""
        assert validate_dataset_name("fast_food_123") == "fast_food_123"

    def test_valid_name_uppercase(self):
        """Test valid name with uppercase letters."""
        assert validate_dataset_name("FastFood") == "FastFood"

    def test_valid_name_starts_with_number(self):
        """Test valid name starting with a number."""
        assert validate_dataset_name("123_dataset") == "123_dataset"

    def test_valid_name_starts_with_letter(self):
        """Test valid name starting with a letter."""
        assert validate_dataset_name("Acme_Corp") == "Acme_Corp"

    # ========== Invalid: Empty ==========
    def test_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Dataset name cannot be empty"):
            validate_dataset_name("")

    # ========== Invalid: Special Characters ==========
    def test_hyphen_not_allowed(self):
        """Test that hyphens are rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("fast-food")

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

    # ========== Invalid: Underscore Placement ==========
    def test_leading_underscore(self):
        """Test that leading underscores are rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("_fast_food")

    def test_only_underscore(self):
        """Test that only an underscore is rejected."""
        with pytest.raises(ValueError, match="Invalid dataset name"):
            validate_dataset_name("_")

    # ========== Error Message Validation ==========
    def test_error_message_includes_name(self):
        """Test that error message includes invalid name."""
        invalid_name = "Invalid@Name"
        with pytest.raises(ValueError, match=f"Invalid dataset name '{invalid_name}'"):
            validate_dataset_name(invalid_name)

    def test_error_message_includes_guidance(self):
        """Test that error message includes guidance."""
        with pytest.raises(
            ValueError, match="Use letters, numbers, and underscores only"
        ):
            validate_dataset_name("@INVALID")


class TestSanitizeDatasetName:
    """Test suite for sanitize_dataset_name function."""

    def test_simple_name(self):
        assert sanitize_dataset_name("Acme") == "Acme"

    def test_name_with_spaces(self):
        assert sanitize_dataset_name("Acme Corp") == "Acme_Corp"

    def test_name_with_special_chars(self):
        assert sanitize_dataset_name("Acme & Co.") == "Acme___Co"

    def test_empty_string_returns_unknown(self):
        assert sanitize_dataset_name("") == "Unknown"

    def test_only_special_chars_returns_unknown(self):
        assert sanitize_dataset_name("@#$") == "Unknown"

    def test_strips_leading_trailing_underscores(self):
        assert sanitize_dataset_name("__test__") == "test"

    def test_preserves_numbers(self):
        assert sanitize_dataset_name("client_123") == "client_123"
