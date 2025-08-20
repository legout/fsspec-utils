"""Miscellaneous utility functions for fsspec-utils."""

import importlib
import os
import posixpath
from typing import Any, Callable, Optional, Union

from joblib import Parallel, delayed
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

# from ..utils.logging import get_logger

# logger = get_logger(__name__)


def run_parallel(
    func: Callable,
    *args,
    n_jobs: int = -1,
    backend: str = "threading",
    verbose: bool = True,
    **kwargs,
) -> list[Any]:
    """Run a function for a list of parameters in parallel.

    Provides parallel execution with progress tracking and flexible
    argument handling.

    Args:
        func: Function to run in parallel.
        *args: Positional arguments. Can be single values or iterables.
        n_jobs: Number of joblib workers. Defaults to -1 (all cores).
        backend: Joblib backend. Options: 'loky', 'threading',
                'multiprocessing', 'sequential'. Defaults to 'threading'.
        verbose: Show progress bar. Defaults to True.
        **kwargs: Keyword arguments. Can be single values or iterables.

    Returns:
        List of function outputs in the same order as inputs.

    Raises:
        ValueError: If no iterable arguments provided or length mismatch.

    Examples:
        >>> # Single iterable argument
        >>> run_parallel(str.upper, ["hello", "world"])
        ['HELLO', 'WORLD']

        >>> # Multiple iterables in args and kwargs
        >>> def add(x, y, offset=0):
        ...     return x + y + offset
        >>> run_parallel(add, [1, 2, 3], y=[4, 5, 6], offset=10)
        [15, 17, 19]

        >>> # Fixed and iterable arguments
        >>> run_parallel(pow, [2, 3, 4], exp=2)
        [4, 9, 16]
    """
    parallel_kwargs = {"n_jobs": n_jobs, "backend": backend, "verbose": 0}

    iterables = []
    fixed_args = []
    iterable_kwargs = {}
    fixed_kwargs = {}

    first_iterable_len = None

    # Process positional arguments
    for arg in args:
        if isinstance(arg, (list, tuple)) and not isinstance(arg[0], (list, tuple)):
            iterables.append(arg)
            if first_iterable_len is None:
                first_iterable_len = len(arg)
            elif len(arg) != first_iterable_len:
                raise ValueError(
                    f"Iterable length mismatch: argument has length {len(arg)}, expected {first_iterable_len}"
                )
        else:
            fixed_args.append(arg)

    # Process keyword arguments
    for key, value in kwargs.items():
        if isinstance(value, (list, tuple)) and not isinstance(value[0], (list, tuple)):
            if first_iterable_len is None:
                first_iterable_len = len(value)
            elif len(value) != first_iterable_len:
                raise ValueError(
                    f"Iterable length mismatch: {key} has length {len(value)}, expected {first_iterable_len}"
                )
            iterable_kwargs[key] = value
        else:
            fixed_kwargs[key] = value

    if first_iterable_len is None:
        raise ValueError("At least one iterable argument is required")

    # Combine all iterables and create parameter combinations
    all_iterables = iterables + list(iterable_kwargs.values())
    param_combinations = list(zip(*all_iterables))

    # Execute without progress bar
    if not verbose:
        return Parallel(**parallel_kwargs)(
            delayed(func)(
                *(list(param_tuple[: len(iterables)]) + fixed_args),
                **{
                    k: v
                    for k, v in zip(
                        iterable_kwargs.keys(), param_tuple[len(iterables) :]
                    )
                },
                **fixed_kwargs,
            )
            for param_tuple in param_combinations
        )

    # Execute with progress bar
    else:
        results = [None] * len(param_combinations)
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task(
                "Running in parallel...", total=len(param_combinations)
            )

            def wrapper(idx, param_tuple):
                res = func(
                    *(list(param_tuple[: len(iterables)]) + fixed_args),
                    **{
                        k: v
                        for k, v in zip(
                            iterable_kwargs.keys(), param_tuple[len(iterables) :]
                        )
                    },
                    **fixed_kwargs,
                )
                progress.update(task, advance=1)
                return idx, res

            for idx, result in Parallel(**parallel_kwargs)(
                delayed(wrapper)(i, param_tuple)
                for i, param_tuple in enumerate(param_combinations)
            ):
                results[idx] = result
        return results


def get_partitions_from_path(
    path: str, partitioning: Union[str, list[str], None] = None
) -> list[tuple]:
    """Extract dataset partitions from a file path.

    Parses file paths to extract partition information based on
    different partitioning schemes.

    Args:
        path: File path potentially containing partition information.
        partitioning: Partitioning scheme:
            - "hive": Hive-style partitioning (key=value)
            - str: Single partition column name
            - list[str]: Multiple partition column names
            - None: Return empty list

    Returns:
        List of tuples containing (column, value) pairs.

    Examples:
        >>> # Hive-style partitioning
        >>> get_partitions_from_path("data/year=2023/month=01/file.parquet", "hive")
        [('year', '2023'), ('month', '01')]

        >>> # Single partition column
        >>> get_partitions_from_path("data/2023/01/file.parquet", "year")
        [('year', '2023')]

        >>> # Multiple partition columns
        >>> get_partitions_from_path("data/2023/01/file.parquet", ["year", "month"])
        [('year', '2023'), ('month', '01')]
    """
    if "." in path:
        path = os.path.dirname(path)

    parts = path.split("/")

    if isinstance(partitioning, str):
        if partitioning == "hive":
            return [tuple(p.split("=")) for p in parts if "=" in p]
        else:
            return [(partitioning, parts[0])]
    elif isinstance(partitioning, list):
        return list(zip(partitioning, parts[-len(partitioning) :]))
    else:
        return []


def path_to_glob(path: str, format: str | None = None) -> str:
    """Convert a path to a glob pattern for file matching.

    Intelligently converts paths to glob patterns that match files of the specified
    format, handling various directory and wildcard patterns.

    Args:
        path: Base path to convert. Can include wildcards (* or **).
            Examples: "data/", "data/*.json", "data/**"
        format: File format to match (without dot). If None, inferred from path.
            Examples: "json", "csv", "parquet"

    Returns:
        str: Glob pattern that matches files of specified format.
            Examples: "data/**/*.json", "data/*.csv"

    Example:
        >>> # Basic directory
        >>> path_to_glob("data", "json")
        'data/**/*.json'
        >>>
        >>> # With wildcards
        >>> path_to_glob("data/**", "csv")
        'data/**/*.csv'
        >>>
        >>> # Format inference
        >>> path_to_glob("data/file.parquet")
        'data/file.parquet'
    """
    path = path.rstrip("/")
    if format is None:
        if ".json" in path:
            format = "json"
        elif ".csv" in path:
            format = "csv"
        elif ".parquet" in path:
            format = "parquet"

    if format in path:
        return path
    else:
        if path.endswith("**"):
            return posixpath.join(path, f"*.{format}")
        elif path.endswith("*"):
            if path.endswith("*/*"):
                return path + f".{format}"
            return posixpath.join(path.rstrip("/*"), f"*.{format}")
        return posixpath.join(path, f"**/*.{format}")


def check_optional_dependency(package_name: str, feature_name: str) -> None:
    """Check if an optional dependency is available.

    Args:
        package_name: Name of the package to check
        feature_name: Name of the feature that requires this package

    Raises:
        ImportError: If the package is not available
    """
    if not importlib.util.find_spec(package_name):
        raise ImportError(
            f"{package_name} is required for {feature_name}. "
            f"Install with: pip install fsspec-utils[full]"
        )
