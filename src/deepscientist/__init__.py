from . import editable_shared_bootstrap as _editable_shared_bootstrap
from importlib.metadata import PackageNotFoundError, version as _package_version

_editable_shared_bootstrap.ensure_editable_dependency_paths()

__all__ = ["__version__"]

try:
    __version__ = _package_version("deepscientist")
except PackageNotFoundError:  # pragma: no cover - source checkout fallback
    __version__ = "1.5.15"
