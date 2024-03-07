# SPDX-License-Identifier: GPL-2.0+
import importlib.metadata as importlib_metadata

try:
    __version__ = importlib_metadata.version(__name__)
except importlib_metadata.PackageNotFoundError:
    # If the app is not installed but run from git repository clone, get the
    # version from pyproject.toml.
    try:
        import tomllib
    except ImportError:
        import toml as tomllib  # type: ignore

    with open("pyproject.toml", "r") as f:
        pyproject = tomllib.load(f)  # type: ignore

    __version__ = pyproject["tool"]["poetry"]["version"]
