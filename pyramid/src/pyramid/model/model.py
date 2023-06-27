import sys
from importlib import import_module
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


class DynamicImport():
    """Utility for creating class instances from a dynamically imported module and class."""

    @classmethod
    def from_dynamic_import(cls, import_spec: str, external_package_path: str = None, **kwargs) -> Self:
        """Create a class instance from a dynamically imported module and class.

        The given import_spec should be of the form "package.subpackage.module.ClassName".
        The "package.subpackage.module" will be imported dynamically via importlib.
        Then "ClassName" from the imported module will be invoked as a class constructor.

        This should be equivalent to the static statement "from package.subpackage.module import ClassName",
        followed by instance = ClassName(**kwargs)

        Returns a new instance of the imported class.

        Provide external_package_path in order to import a class from a module that was not
        already installed by the usual means, eg conda or pip.  The external_package_path will
        be added temporarily to the Python import search path, then removed when done here.
        """
        last_dot = import_spec.rfind(".")
        module_spec = import_spec[0:last_dot]

        try:
            original_sys_path = sys.path
            if external_package_path:
                sys.path = original_sys_path.copy()
                sys.path.append(external_package_path)
            imported_module = import_module(module_spec, package=None)
        finally:
            sys.path = original_sys_path

        class_name = import_spec[last_dot+1:]
        imported_class = getattr(imported_module, class_name)
        instance = imported_class(**kwargs)
        return instance


# What's the same between buffer types?
# What's the same between event and signal types?
