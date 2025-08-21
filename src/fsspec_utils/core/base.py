"""Core filesystem functionality and utilities."""

import base64
import os
import posixpath
import urllib
import warnings
from pathlib import Path
from typing import Optional, Union

import fsspec
import requests
from fsspec import filesystem as fsspec_filesystem
from fsspec.implementations.cache_mapper import AbstractCacheMapper
from fsspec.implementations.cached import SimpleCacheFileSystem
from fsspec.implementations.dirfs import DirFileSystem
from fsspec.implementations.memory import MemoryFile

from ..storage_options.base import BaseStorageOptions
from ..storage_options.core import from_dict as storage_options_from_dict
from ..utils.logging import get_logger
# from fsspec.utils import infer_storage_options
from .ext import AbstractFileSystem

logger = get_logger(__name__)


class FileNameCacheMapper(AbstractCacheMapper):
    """Maps remote file paths to local cache paths while preserving directory structure.

    This cache mapper maintains the original file path structure in the cache directory,
    creating necessary subdirectories as needed.

    Attributes:
        directory (str): Base directory for cached files

    Example:
        >>> # Create cache mapper for S3 files
        >>> mapper = FileNameCacheMapper("/tmp/cache")
        >>>
        >>> # Map remote path to cache path
        >>> cache_path = mapper("bucket/data/file.csv")
        >>> print(cache_path)  # Preserves structure
        'bucket/data/file.csv'
    """

    def __init__(self, directory: str):
        """Initialize cache mapper with base directory.

        Args:
            directory: Base directory where cached files will be stored
        """
        self.directory = directory

    def __call__(self, path: str) -> str:
        """Map remote file path to cache file path.

        Creates necessary subdirectories in the cache directory to maintain
        the original path structure.

        Args:
            path: Original file path from remote filesystem

        Returns:
            str: Cache file path that preserves original structure

        Example:
            >>> mapper = FileNameCacheMapper("/tmp/cache")
            >>> # Maps maintain directory structure
            >>> print(mapper("data/nested/file.txt"))
            'data/nested/file.txt'
        """
        os.makedirs(
            posixpath.dirname(posixpath.join(self.directory, path)), exist_ok=True
        )
        return path


class MonitoredSimpleCacheFileSystem(SimpleCacheFileSystem):
    """Enhanced caching filesystem with monitoring and improved path handling.

    This filesystem extends SimpleCacheFileSystem to provide:
    - Verbose logging of cache operations
    - Improved path mapping for cache files
    - Enhanced synchronization capabilities
    - Better handling of parallel operations

    Attributes:
        _verbose (bool): Whether to print verbose cache operations
        _mapper (FileNameCacheMapper): Maps remote paths to cache paths
        storage (list[str]): List of cache storage locations
        fs (AbstractFileSystem): Underlying filesystem being cached

    Example:
        >>> from fsspec import filesystem
        >>> s3_fs = filesystem("s3")
        >>> cached_fs = MonitoredSimpleCacheFileSystem(
        ...     fs=s3_fs,
        ...     cache_storage="/tmp/cache",
        ...     verbose=True
        ... )
        >>> # Use cached_fs like any other filesystem
        >>> files = cached_fs.ls("my-bucket/")
    """

    def __init__(
        self,
        fs: Optional[fsspec.AbstractFileSystem] = None,
        cache_storage: Union[str, list[str]] = "~/.cache/fsspec",
        verbose: bool = False,
        **kwargs,
    ):
        """Initialize monitored cache filesystem.

        Args:
            fs: Underlying filesystem to cache. If None, creates a local filesystem.
            cache_storage: Cache storage location(s). Can be string path or list of paths.
            verbose: Whether to enable verbose logging of cache operations.
            **kwargs: Additional arguments passed to SimpleCacheFileSystem.

        Example:
            >>> # Cache S3 filesystem
            >>> s3_fs = filesystem("s3")
            >>> cached = MonitoredSimpleCacheFileSystem(
            ...     fs=s3_fs,
            ...     cache_storage="/tmp/s3_cache",
            ...     verbose=True
            ... )
        """
        self._verbose = verbose

        # Handle cache storage configuration
        if isinstance(cache_storage, str):
            cache_storage = [cache_storage]

        self.storage = cache_storage

        # Set up cache mapper for preserving directory structure
        if len(cache_storage) == 1:
            self._mapper = FileNameCacheMapper(cache_storage[0])
            kwargs["cache_mapper"] = self._mapper

        # Initialize with expanded cache storage paths
        expanded_storage = [os.path.expanduser(path) for path in cache_storage]
        super().__init__(fs=fs, cache_storage=expanded_storage, **kwargs)

        if self._verbose:
            logger.info(
                f"Initialized cache filesystem with storage: {expanded_storage}"
            )

    def _check_cache(self, path: str) -> Optional[str]:
        """Check if file exists in cache and return cache path if found.

        Args:
            path: Remote file path to check

        Returns:
            Cache file path if found, None otherwise
        """
        result = super()._check_cache(path)
        if self._verbose and result:
            logger.info(f"Cache hit for {path} -> {result}")
        return result

    def _check_file(self, path: str) -> str:
        """Ensure file is in cache, downloading if necessary.

        Args:
            path: Remote file path

        Returns:
            Local cache path for the file
        """
        if self._verbose:
            logger.info(f"Checking file: {path}")

        result = super()._check_file(path)

        if self._verbose:
            logger.info(f"File available at: {result}")

        return result


class GitLabFileSystem(AbstractFileSystem):
    """Filesystem interface for GitLab repositories.

    Provides read-only access to files in GitLab repositories, including:
    - Public and private repositories
    - Self-hosted GitLab instances
    - Branch/tag/commit selection
    - Token-based authentication

    Attributes:
        protocol (str): Always "gitlab"
        base_url (str): GitLab instance URL
        project_id (str): Project ID
        project_name (str): Project name/path
        ref (str): Git reference (branch, tag, commit)
        token (str): Access token
        api_version (str): API version

    Example:
        >>> # Public repository
        >>> fs = GitLabFileSystem(
        ...     project_name="group/project",
        ...     ref="main"
        ... )
        >>> files = fs.ls("/")
        >>>
        >>> # Private repository with token
        >>> fs = GitLabFileSystem(
        ...     project_id="12345",
        ...     token="glpat_xxxx",
        ...     ref="develop"
        ... )
        >>> content = fs.cat("README.md")
    """

    protocol = "gitlab"

    def __init__(
        self,
        base_url: str = "https://gitlab.com",
        project_id: Optional[Union[str, int]] = None,
        project_name: Optional[str] = None,
        ref: str = "main",
        token: Optional[str] = None,
        api_version: str = "v4",
        **kwargs,
    ):
        """Initialize GitLab filesystem.

        Args:
            base_url: GitLab instance URL
            project_id: Project ID number
            project_name: Project name/path (alternative to project_id)
            ref: Git reference (branch, tag, or commit SHA)
            token: GitLab personal access token
            api_version: API version to use
            **kwargs: Additional filesystem arguments

        Raises:
            ValueError: If neither project_id nor project_name is provided
        """
        super().__init__(**kwargs)

        if project_id is None and project_name is None:
            raise ValueError("Either project_id or project_name must be provided")

        self.base_url = base_url.rstrip("/")
        self.project_id = str(project_id) if project_id else None
        self.project_name = project_name
        self.ref = ref
        self.token = token
        self.api_version = api_version

        # Build API URL
        self.api_url = f"{self.base_url}/api/{self.api_version}"

        # Determine project identifier for API calls
        if self.project_id:
            self.project_identifier = self.project_id
        else:
            # URL encode project name
            self.project_identifier = urllib.parse.quote(self.project_name, safe="")

        # Setup session with authentication
        self.session = requests.Session()
        if self.token:
            self.session.headers["Private-Token"] = self.token

    def _get_file_content(self, path: str) -> bytes:
        """Get file content from GitLab API.

        Args:
            path: File path in repository

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            requests.HTTPError: For other HTTP errors
        """
        # Remove leading slash for API consistency
        path = path.lstrip("/")

        url = f"{self.api_url}/projects/{self.project_identifier}/repository/files/{urllib.parse.quote(path, safe='')}"
        params = {"ref": self.ref}

        response = self.session.get(url, params=params)

        if response.status_code == 404:
            raise FileNotFoundError(f"File not found: {path}")

        response.raise_for_status()
        data = response.json()

        # Decode content (GitLab returns base64-encoded content)
        content = base64.b64decode(data["content"])
        return content

    def _open(
        self,
        path: str,
        mode: str = "rb",
        block_size: Optional[int] = None,
        cache_options: Optional[dict] = None,
        **kwargs,
    ):
        """Open file for reading.

        Args:
            path: File path to open
            mode: File mode (only 'rb' and 'r' supported)
            block_size: Block size for reading (unused)
            cache_options: Cache options (unused)
            **kwargs: Additional options

        Returns:
            File-like object for reading

        Raises:
            ValueError: If mode is not supported
        """
        if mode not in ["rb", "r"]:
            raise ValueError(
                f"Mode '{mode}' not supported. Only 'rb' and 'r' are supported."
            )

        content = self._get_file_content(path)

        if mode == "r":
            content = content.decode("utf-8")

        return MemoryFile(None, None, content)

    def cat(self, path: str, **kwargs) -> bytes:
        """Get file contents as bytes.

        Args:
            path: File path
            **kwargs: Additional options

        Returns:
            File content as bytes
        """
        return self._get_file_content(path)

    def ls(self, path: str = "", detail: bool = True, **kwargs) -> list:
        """List directory contents.

        Args:
            path: Directory path to list
            detail: Whether to return detailed information
            **kwargs: Additional options

        Returns:
            List of files/directories or their details
        """
        path = path.lstrip("/")

        url = f"{self.api_url}/projects/{self.project_identifier}/repository/tree"
        params = {"ref": self.ref, "path": path, "recursive": False}

        response = self.session.get(url, params=params)
        response.raise_for_status()

        items = response.json()

        if detail:
            return [
                {
                    "name": posixpath.join(path, item["name"])
                    if path
                    else item["name"],
                    "size": None,  # GitLab API doesn't provide size in tree endpoint
                    "type": "directory" if item["type"] == "tree" else "file",
                    "id": item["id"],
                }
                for item in items
            ]
        else:
            return [
                posixpath.join(path, item["name"]) if path else item["name"]
                for item in items
            ]

    def exists(self, path: str, **kwargs) -> bool:
        """Check if file or directory exists.

        Args:
            path: Path to check
            **kwargs: Additional options

        Returns:
            True if path exists, False otherwise
        """
        try:
            self._get_file_content(path)
            return True
        except FileNotFoundError:
            return False

    def info(self, path: str, **kwargs) -> dict:
        """Get file information.

        Args:
            path: File path
            **kwargs: Additional options

        Returns:
            Dictionary with file information
        """
        # For simplicity, we'll use the file content request
        # In a production implementation, you might want to use a more efficient endpoint
        try:
            content = self._get_file_content(path)
            return {
                "name": path,
                "size": len(content),
                "type": "file",
            }
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")


fsspec.register_implementation("gitlab", GitLabFileSystem)

# Original ls Methode speichern
dirfs_ls_o = DirFileSystem.ls
mscf_ls_o = MonitoredSimpleCacheFileSystem.ls


# Neue ls Methode definieren
def dir_ls_p(self, path, detail=False, **kwargs):
    return dirfs_ls_o(self, path, detail=detail, **kwargs)


def mscf_ls_p(self, path, detail=False, **kwargs):
    return mscf_ls_o(self, path, detail=detail, **kwargs)


# patchen
DirFileSystem.ls = dir_ls_p
MonitoredSimpleCacheFileSystem.ls = mscf_ls_p


def filesystem(
    protocol_or_path: str,
    storage_options: Optional[Union[BaseStorageOptions, dict]] = None,
    cached: bool = False,
    cache_storage: Optional[str] = None,
    verbose: bool = False,
    dirfs: bool = True,
    base_fs: AbstractFileSystem = None,
    **kwargs,
) -> AbstractFileSystem:
    """Get filesystem instance with enhanced configuration options.

    Creates filesystem instances with support for storage options classes,
    intelligent caching, and protocol inference from paths.

    Args:
        protocol_or_path: Filesystem protocol (e.g., "s3", "file") or path with protocol prefix
        storage_options: Storage configuration as BaseStorageOptions instance or dict
        cached: Whether to wrap filesystem in caching layer
        cache_storage: Cache directory path (if cached=True)
        verbose: Enable verbose logging for cache operations
        **kwargs: Additional filesystem arguments

    Returns:
        AbstractFileSystem: Configured filesystem instance

    Example:
        >>> # Basic local filesystem
        >>> fs = filesystem("file")
        >>>
        >>> # S3 with storage options
        >>> from fsspec_utils.storage import AwsStorageOptions
        >>> opts = AwsStorageOptions(region="us-west-2")
        >>> fs = filesystem("s3", storage_options=opts, cached=True)
        >>>
        >>> # Infer protocol from path
        >>> fs = filesystem("s3://my-bucket/", cached=True)
        >>>
        >>> # GitLab filesystem
        >>> fs = filesystem("gitlab", storage_options={
        ...     "project_name": "group/project",
        ...     "token": "glpat_xxxx"
        ... })
    """
    if isinstance(protocol_or_path, Path):
        protocol_or_path = protocol_or_path.as_posix()
    if not protocol_or_path:
        # protocol_or_path = "file://"
        base_path = ""
        protocol = "file"

    elif "://" in protocol_or_path:
        base_path = protocol_or_path.split("://")[-1]
        protocol = protocol_or_path.split("://")[0]
    elif "/" in protocol_or_path or "." in protocol_or_path:
        base_path = protocol_or_path
        protocol = "file"
    else:
        protocol = protocol_or_path if protocol_or_path is not None else "file"
        base_path = ""

    if "." in base_path:
        base_path = posixpath.dirname(base_path)

    #print(f"Base path: {base_path}, Protocol: {protocol}")

    if base_fs is not None:
        if dirfs:
            # base_path = protocol_or_path.split("://")[-1]
            if base_fs.protocol == "dir":
                if base_path != base_fs.path:
                    fs = DirFileSystem(
                        path=posixpath.join(
                            base_fs.path,
                            base_path.replace(base_fs.path, "").lstrip("/"),
                        ),
                        fs=base_fs.fs,
                    )
            else:
                fs = DirFileSystem(path=base_path, fs=base_fs)
        if cached:
            if fs.is_cache_fs:
                return fs
            fs = MonitoredSimpleCacheFileSystem(fs=fs, cache_storage=cache_storage)

        return fs

    protocol = (
        protocol
        or kwargs.get("protocol", None)
        or (
            storage_options.get("protocol", None)
            if isinstance(storage_options, dict)
            else getattr(storage_options, "protocol", None)
        )
    )

    if protocol == "file" or protocol == "local":
        fs = fsspec_filesystem(protocol)
        fs.is_cache_fs = False
        if dirfs:
            fs = DirFileSystem(path=base_path or Path.cwd(), fs=fs)
            fs.is_cache_fs = False
        return fs

    if isinstance(storage_options, dict):
        storage_options = storage_options_from_dict(protocol, storage_options)

    if storage_options is None:
        storage_options = storage_options_from_dict(protocol, kwargs)

    fs = storage_options.to_filesystem()
    fs.is_cache_fs = False
    if dirfs and len(base_path):
        fs = DirFileSystem(path=base_path, fs=fs)
        fs.is_cache_fs = False
    if cached:
        if cache_storage is None:
            cache_storage = (Path.cwd() / base_path).as_posix()
        fs = MonitoredSimpleCacheFileSystem(fs=fs, cache_storage=cache_storage)
        fs.is_cache_fs = True

    return fs


def get_filesystem(
    protocol_or_path: str,
    storage_options: Optional[Union[BaseStorageOptions, dict]] = None,
    cached: bool = False,
    cache_storage: Optional[str] = None,
    verbose: bool = False,
    **kwargs,
) -> fsspec.AbstractFileSystem:
    """Get filesystem instance with enhanced configuration options.

    .. deprecated:: 0.1.0
        Use :func:`filesystem` instead. This function will be removed in a future version.

    Creates filesystem instances with support for storage options classes,
    intelligent caching, and protocol inference from paths.

    Args:
        protocol_or_path: Filesystem protocol (e.g., "s3", "file") or path with protocol prefix
        storage_options: Storage configuration as BaseStorageOptions instance or dict
        cached: Whether to wrap filesystem in caching layer
        cache_storage: Cache directory path (if cached=True)
        verbose: Enable verbose logging for cache operations
        **kwargs: Additional filesystem arguments

    Returns:
        AbstractFileSystem: Configured filesystem instance

    Example:
        >>> # Basic local filesystem
        >>> fs = get_filesystem("file")
        >>>
        >>> # S3 with storage options
        >>> from fsspec_utils.storage import AwsStorageOptions
        >>> opts = AwsStorageOptions(region="us-west-2")
        >>> fs = get_filesystem("s3", storage_options=opts, cached=True)
        >>>
        >>> # Infer protocol from path
        >>> fs = get_filesystem("s3://my-bucket/", cached=True)
        >>>
        >>> # GitLab filesystem
        >>> fs = get_filesystem("gitlab", storage_options={
        ...     "project_name": "group/project",
        ...     "token": "glpat_xxxx"
        ... })
    """
    warnings.warn(
        "get_filesystem() is deprecated and will be removed in a future version. "
        "Use filesystem() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return filesystem(
        protocol_or_path=protocol_or_path,
        storage_options=storage_options,
        cached=cached,
        cache_storage=cache_storage,
        verbose=verbose,
        **kwargs,
    )
