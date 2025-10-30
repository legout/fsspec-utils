"""fsspec-utils: Enhanced utilities and extensions for fsspec filesystems.

DEPRECATED: This package is deprecated and will be removed in a future version.
Please use 'fsspeckit' instead: https://github.com/legout/fsspeckit

This package now acts as a compatibility wrapper, re-exporting all functionality
from fsspeckit (or local implementations as fallback) to allow for gradual migration of existing code.
"""

import importlib.metadata
import warnings

__version__ = importlib.metadata.version("fsspec-utils")

# Show deprecation warning on import
warnings.warn(
    "fsspec-utils is deprecated and will be removed in a future version. "
    "Please migrate to 'fsspeckit' instead: https://github.com/legout/fsspeckit. "
    "All functionality is now provided by fsspeckit.",
    DeprecationWarning,
    stacklevel=2,
)

# Try to import from fsspeckit, fall back to local implementations
try:
    from fsspeckit.core import AbstractFileSystem, DirFileSystem, filesystem, get_filesystem
    from fsspeckit.storage_options import (
        AwsStorageOptions,
        AzureStorageOptions,
        BaseStorageOptions,
        GcsStorageOptions,
        GitHubStorageOptions,
        GitLabStorageOptions,
        LocalStorageOptions,
        StorageOptions,
    )
except (ImportError, ModuleNotFoundError):
    # Fallback to local implementations if fsspeckit is not available or broken
    from .core import AbstractFileSystem, DirFileSystem, filesystem, get_filesystem
    from .storage_options import (
        AwsStorageOptions,
        AzureStorageOptions,
        BaseStorageOptions,
        GcsStorageOptions,
        GitHubStorageOptions,
        GitLabStorageOptions,
        LocalStorageOptions,
        StorageOptions,
    )

__all__ = [
    "filesystem",
    "get_filesystem",
    "AbstractFileSystem",
    "DirFileSystem",
    "AwsStorageOptions",
    "AzureStorageOptions",
    "BaseStorageOptions",
    "GcsStorageOptions",
    "GitHubStorageOptions",
    "GitLabStorageOptions",
    "LocalStorageOptions",
    "StorageOptions",
]
