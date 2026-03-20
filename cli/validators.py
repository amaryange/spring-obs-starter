import re


def validate_service_name(name: str) -> bool | str:
    """questionary-compatible validator: return True or an error string."""
    if not name or not name.strip():
        return "Service name cannot be empty"
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9\-_]*$", name.strip()):
        return "Must start with a letter and contain only letters, digits, - or _"
    if len(name.strip()) > 64:
        return "Service name must be 64 characters or fewer"
    return True


def validate_output_dir(name: str) -> bool | str:
    """questionary-compatible validator for output directory names."""
    if not name or not name.strip():
        return "Directory name cannot be empty"
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-_.]*$", name.strip()):
        return "Invalid directory name — use letters, digits, -, _ or ."
    return True


def validate_package(package: str) -> bool | str:
    """questionary-compatible validator for Java base package names."""
    if not package or not package.strip():
        return "Package name cannot be empty"
    if not re.match(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)+$", package.strip()):
        return "Invalid package (e.g. com.example.myservice) — lowercase, dot-separated"
    return True
