"""Anti-Silo portable trust engine."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("anti-silo")
except PackageNotFoundError:  # pragma: no cover - editable/source fallback
    __version__ = "0.4.0"
