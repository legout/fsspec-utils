"""Core filesystem functionality for fsspec-utils.

DEPRECATED: This module is deprecated. Use 'fsspeckit.core' instead.
"""

import warnings

warnings.warn(
    "fsspec_utils.core is deprecated. Import from 'fsspeckit.core' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Try to import from fsspeckit, fall back to local implementations
try:
    from fsspeckit.core import (
        AbstractFileSystem,
        DirFileSystem,
        GitLabFileSystem,
        MonitoredSimpleCacheFileSystem,
        filesystem,
        get_filesystem,
    )
except (ImportError, ModuleNotFoundError):
    # Fallback to local implementations
    from .base import (
        GitLabFileSystem,
        MonitoredSimpleCacheFileSystem,
        filesystem,
        get_filesystem,
        DirFileSystem,
    )
    try:
        from .ext import AbstractFileSystem
    except ImportError:
        from fsspec import AbstractFileSystem

__all__ = [
    "GitLabFileSystem",
    "MonitoredSimpleCacheFileSystem",
    "DirFileSystem",
    "AbstractFileSystem",
    "filesystem",
    "get_filesystem",
]
