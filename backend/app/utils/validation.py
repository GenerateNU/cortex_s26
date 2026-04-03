import re

def validate_dataset_name(name: str) -> str:
    if not name:
        raise ValueError("Dataset name cannot be empty")
    if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name):
        raise ValueError(
            f"Invalid dataset name '{name}'. "
            "Use lowercase letters, numbers, and hyphens only (e.g. 'fast-food')."
        )
    return name