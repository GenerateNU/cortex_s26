import re


def sanitize_dataset_name(raw: str) -> str:
    """Sanitize a raw string into a valid Cognee dataset name."""
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", raw).strip("_")
    return sanitized or "Unknown"


def validate_dataset_name(name: str) -> str:
    if not name:
        raise ValueError("Dataset name cannot be empty")
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_]*$", name):
        raise ValueError(
            f"Invalid dataset name '{name}'. "
            "Use letters, numbers, and underscores only (e.g. 'Acme_Corp')."
        )
    return name
