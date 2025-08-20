"""fsspec-utils: Enhanced utilities and extensions for fsspec filesystems.

This package provides enhanced filesystem utilities built on top of fsspec,
including:
- Multi-format data I/O (JSON, CSV, Parquet)
- Cloud storage configuration utilities
- Enhanced caching and monitoring
- Batch processing and parallel operations
"""
import importlib.metadata
__version__ = importlib.metadata.version("fsspec-utils")

# Always import from fsspec for now
from fsspec import AbstractFileSystem

from .core.base import DirFileSystem, filesystem, get_filesystem
from .storage_options.core import (AwsStorageOptions, AzureStorageOptions,
                                   GcsStorageOptions, LocalStorageOptions,
                                   StorageOptions)
from .storage_options.git import GitHubStorageOptions, GitLabStorageOptions

__all__ = [
    "filesystem",
    "get_filesystem",
    "DirFileSystem",
    "AbstractFileSystem",
    "AwsStorageOptions",
    "AzureStorageOptions",
    "GcsStorageOptions",
    "GitHubStorageOptions",
    "GitLabStorageOptions",
    "LocalStorageOptions",
    "StorageOptions",
]
