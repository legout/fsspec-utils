"""Core filesystem functionality for fsspec-utils."""

from .base import (GitLabFileSystem, MonitoredSimpleCacheFileSystem,
                   filesystem, get_filesystem)

# Conditional imports for extended functionality
try:
    from .ext import AbstractFileSystem
except ImportError:
    from fsspec import AbstractFileSystem

__all__ = [
    "GitLabFileSystem",
    "MonitoredSimpleCacheFileSystem",
    "AbstractFileSystem",
    "filesystem",
    "get_filesystem",
]
