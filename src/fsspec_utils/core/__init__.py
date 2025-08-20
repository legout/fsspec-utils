"""Core filesystem functionality for fsspec-utils."""

from .base import filesystem, get_filesystem

# Conditional imports for extended functionality
try:
    from .ext import AbstractFileSystem
except ImportError:
    from fsspec import AbstractFileSystem

__all__ = [
    "AbstractFileSystem",
    "filesystem",
    "get_filesystem",
]
