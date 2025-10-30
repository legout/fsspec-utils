"""Storage configuration options for different cloud providers and services.

DEPRECATED: This module is deprecated. Use 'fsspeckit.storage_options' instead.
"""

import warnings

warnings.warn(
    "fsspec_utils.storage_options is deprecated. Import from 'fsspeckit.storage_options' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Try to import from fsspeckit, fall back to local implementations
try:
    from fsspeckit.storage_options import (
        AwsStorageOptions,
        AzureStorageOptions,
        BaseStorageOptions,
        GcsStorageOptions,
        GitHubStorageOptions,
        GitLabStorageOptions,
        LocalStorageOptions,
        StorageOptions,
        from_dict,
        from_env,
        infer_protocol_from_uri,
        merge_storage_options,
        storage_options_from_uri,
    )
except (ImportError, ModuleNotFoundError):
    # Fallback to local implementations
    from .base import BaseStorageOptions
    from .cloud import AwsStorageOptions, AzureStorageOptions, GcsStorageOptions
    from .core import (
        LocalStorageOptions,
        StorageOptions,
        from_dict,
        from_env,
        infer_protocol_from_uri,
        merge_storage_options,
        storage_options_from_uri,
    )
    from .git import GitHubStorageOptions, GitLabStorageOptions

__all__ = [
    "BaseStorageOptions",
    "AwsStorageOptions",
    "AzureStorageOptions",
    "GcsStorageOptions",
    "GitHubStorageOptions",
    "GitLabStorageOptions",
    "LocalStorageOptions",
    "StorageOptions",
    "from_dict",
    "from_env",
    "merge_storage_options",
    "infer_protocol_from_uri",
    "storage_options_from_uri",
]
