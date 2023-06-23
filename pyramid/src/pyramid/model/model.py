from typing import Any, Self


class InteropData():
    """Utility methods to convert instances to and from standard types, for interop with other environments.

    The goal of this is to be able to read and write instances of InteropData classes as JSON or similar
    for sharing with other environments like Matlab.  Automatic, field-by-field serializers would expose
    implementation details that don't make sense in other environments, for example numpy array internals
    that make no sense int Matlab.  To avoid this, InteropData instances must convert themselves to and
    from standard types that can be represented in exchange formats like JSON, and which make sense in other
    environments -- types like int, float, str, dict, and list.
    """

    def to_interop(self) -> Any:
        """Convert this instance to a standard types / collections like int, float, str, dict, or list."""
        pass # pragma: no cover

    @classmethod
    def from_interop(cls, interop) -> Self:
        """Create a new instance of this class from standard types / collections, as from to_interop()"""
        pass # pragma: no cover
