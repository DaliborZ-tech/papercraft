"""Typed failures at the authoring boundary, independent from Qt."""


class ValidationError(ValueError):
    """A rejected authoring command leaves the document unchanged."""


class ProjectFormatError(ValidationError):
    """An unsupported or malformed project file."""


class UnsupportedOperationError(ValidationError):
    """A capability is not implemented for this construction yet."""
