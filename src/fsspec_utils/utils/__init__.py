"""Utility modules for fsspec-utils.

DEPRECATED: This module is deprecated. Use 'fsspeckit.utils' instead.
"""

import warnings

warnings.warn(
    "fsspec_utils.utils is deprecated. Import from 'fsspeckit.utils' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Try to import from fsspeckit, fall back to local implementations
try:
    from fsspeckit.utils import (
        cast_schema,
        convert_large_types_to_normal,
        dict_to_dataframe,
        get_partitions_from_path,
        opt_dtype as opt_dtype_pa,
        opt_dtype_pl,
        pl,
        run_parallel,
        setup_logging,
        sync_dir,
        sync_files,
        to_pyarrow_table,
    )
except (ImportError, ModuleNotFoundError):
    # Fallback to local implementations
    from .logging import setup_logging
    from .misc import get_partitions_from_path, run_parallel, sync_dir, sync_files
    from .polars import opt_dtype as opt_dtype_pl
    from .polars import pl
    from .pyarrow import cast_schema, convert_large_types_to_normal
    from .pyarrow import opt_dtype as opt_dtype_pa
    from .types import dict_to_dataframe, to_pyarrow_table

__all__ = [
    "setup_logging",
    "run_parallel",
    "get_partitions_from_path",
    "to_pyarrow_table",
    "dict_to_dataframe",
    "opt_dtype_pl",
    "opt_dtype_pa",
    "cast_schema",
    "convert_large_types_to_normal",
    "pl",
    "sync_dir",
    "sync_files",
]
