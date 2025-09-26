"""Basic tests for fsspec-utils package."""

from pathlib import Path

import pytest

def test_imports():
    """Test that basic imports work."""
    from fsspec_utils import filesystem, DirFileSystem, AbstractFileSystem
    from fsspec_utils.storage_options import AwsStorageOptions, LocalStorageOptions
    from fsspec_utils.utils import setup_logging
    
    assert filesystem is not None
    assert DirFileSystem is not None
    assert AbstractFileSystem is not None
    assert AwsStorageOptions is not None
    assert LocalStorageOptions is not None
    assert setup_logging is not None


def test_local_filesystem():
    """Test local filesystem creation."""
    from fsspec_utils import filesystem
    
    fs = filesystem("file")
    assert fs is not None
    assert hasattr(fs, "ls")
    assert hasattr(fs, "open")


def test_storage_options():
    """Test storage options creation."""
    from fsspec_utils.storage_options import LocalStorageOptions, AwsStorageOptions
    
    # Local options
    local_opts = LocalStorageOptions()
    assert local_opts.protocol == "file"
    
    # AWS options
    aws_opts = AwsStorageOptions(region="us-east-1")
    assert aws_opts.protocol == "s3"
    assert aws_opts.region == "us-east-1"


def test_logging_setup():
    """Test logging setup."""
    from fsspec_utils.utils import setup_logging

    # Should not raise any errors
    setup_logging(level="INFO", disable=False)


def test_filesystem_preserves_directory_without_trailing_slash(tmp_path):
    """Ensure filesystem() keeps the last directory component by default."""
    from fsspec_utils import DirFileSystem, filesystem

    root = tmp_path / "path" / "to" / "root"
    root.mkdir(parents=True)

    fs = filesystem(root.as_posix())

    assert isinstance(fs, DirFileSystem)
    assert Path(fs.path).resolve() == root.resolve()


def test_filesystem_infers_directory_from_file_path(tmp_path):
    """Ensure filesystem() detects file inputs and returns the parent directory."""
    from fsspec_utils import DirFileSystem, filesystem

    root = tmp_path / "data"
    root.mkdir()
    file_path = root / "file.csv"
    file_path.write_text("content", encoding="utf-8")

    fs = filesystem(file_path.as_posix())

    assert isinstance(fs, DirFileSystem)
    assert Path(fs.path).resolve() == root.resolve()


def test_filesystem_directory_with_dotted_parent(tmp_path):
    """Directories with dots in parent names should be preserved."""
    from fsspec_utils import DirFileSystem, filesystem

    root = tmp_path / "dataset.v1" / "partition"
    root.mkdir(parents=True)

    fs = filesystem(root.as_posix())

    assert isinstance(fs, DirFileSystem)
    assert Path(fs.path).resolve() == root.resolve()
