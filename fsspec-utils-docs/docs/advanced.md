# Advanced Usage

`fsspec-utils` extends the capabilities of `fsspec` to provide a more robust and feature-rich experience for handling diverse file systems and data formats. This section delves into advanced features, configurations, and performance tips to help you get the most out of the library.

## Unified Filesystem Creation with `filesystem`

The `fsspec_utils.core.filesystem` function offers a centralized and enhanced way to instantiate `fsspec` filesystem objects. It supports:

-   **Intelligent Caching**: Automatically wraps filesystems with `MonitoredSimpleCacheFileSystem` for improved performance and verbose logging of cache operations.
-   **Structured Storage Options**: Integrates seamlessly with `fsspec_utils.storage_options` classes, allowing for type-safe and organized configuration of cloud and Git-based storage.
-   **Protocol Inference**: Can infer the filesystem protocol directly from a URI or path, reducing boilerplate.

**Example: Cached S3 Filesystem with Structured Options**

```python
from fsspec_utils.core import filesystem
from fsspec_utils.storage_options import AwsStorageOptions

# Configure S3 options using the structured class
s3_opts = AwsStorageOptions(
    region="us-east-1",
    access_key_id="YOUR_ACCESS_KEY",
    secret_access_key="YOUR_SECRET_KEY"
)

# Create a cached S3 filesystem using the 'filesystem' helper
fs = filesystem(
    "s3",
    storage_options=s3_opts,
    cached=True,
    cache_storage="/tmp/s3_cache", # Optional: specify cache directory
    verbose=True # Enable verbose cache logging
)

# Use the filesystem as usual
print(fs.ls("s3://your-bucket/"))
```

## Custom Filesystem Implementations

`fsspec-utils` provides specialized filesystem implementations for unique use cases:

### GitLab Filesystem (`GitLabFileSystem`)

Access files directly from GitLab repositories. This is particularly useful for configuration files, datasets, or code stored in private or public GitLab instances.

**Example: Reading from a GitLab Repository**

```python
from fsspec_utils.core import filesystem

# Instantiate a GitLab filesystem
gitlab_fs = filesystem(
    "gitlab",
    storage_options={
        "project_name": "your-group/your-project", # Or "project_id": 12345
        "ref": "main", # Branch, tag, or commit SHA
        "token": "glpat_YOUR_PRIVATE_TOKEN" # Required for private repos
    }
)

# List files in the repository root
print(gitlab_fs.ls("/"))

# Read a specific file
content = gitlab_fs.cat("README.md").decode("utf-8")
print(content[:200]) # Print first 200 characters
```

## Advanced Data Reading and Writing (`read_files`, `write_files`)

The `fsspec_utils.core.ext` module (exposed via `AbstractFileSystem` extensions) provides powerful functions for reading and writing various data formats (JSON, CSV, Parquet) with advanced features like:

-   **Batch Processing**: Efficiently handle large datasets by processing files in configurable batches.
-   **Parallel Processing**: Leverage multi-threading to speed up file I/O operations.
-   **Schema Unification & Optimization**: Automatically unifies schemas when concatenating multiple files and optimizes data types for memory efficiency (e.g., using Polars' `opt_dtypes` or PyArrow's schema casting).
-   **File Path Tracking**: Optionally include the source file path as a column in the resulting DataFrame/Table.

### Universal `read_files`

The `read_files` function acts as a universal reader, delegating to format-specific readers (JSON, CSV, Parquet) while maintaining consistent options.

**Example: Reading CSVs in Batches with Parallelism**

```python
from fsspec_utils.core import filesystem

# Assuming you have multiple CSV files like 'data/part_0.csv', 'data/part_1.csv', etc.
# on your local filesystem
fs = filesystem("file")

# Read CSV files in batches of 10, using multiple threads, and including file path
for batch_df in fs.read_files(
    "data/*.csv",
    format="csv",
    batch_size=10,
    include_file_path=True,
    use_threads=True,
    verbose=True
):
    print(f"Processed batch with {len(batch_df)} rows. Columns: {batch_df.columns}")
    print(batch_df.head(2))
```

### Advanced Parquet Handling

`fsspec-utils` enhances Parquet operations with deep integration with PyArrow and Pydala, enabling efficient dataset management, partitioning, and delta lake capabilities.

-   **`pyarrow_dataset`**: Create PyArrow datasets for optimized querying, partitioning, and predicate pushdown.
-   **`pyarrow_parquet_dataset`**: Specialized for Parquet, handling `_metadata` files for overall dataset schemas.
-   **`pydala_dataset`**: Integrates with `pydala` for advanced features like Delta Lake operations (upserts, schema evolution).

**Example: Writing to a PyArrow Dataset with Partitioning**

```python
import polars as pl
from fsspec_utils.core import filesystem

fs = filesystem("file")
base_path = "output/my_partitioned_data"

# Sample data
data = pl.DataFrame({
    "id": [1, 2, 3, 4],
    "value": ["A", "B", "C", "D"],
    "year": [2023, 2023, 2024, 2024],
    "month": [10, 11, 1, 2]
})

# Write data as a partitioned PyArrow dataset
fs.write_pyarrow_dataset(
    data=data,
    path=base_path,
    partition_by=["year", "month"], # Partition by year and month
    format="parquet",
    compression="zstd",
    mode="overwrite" # Overwrite if path exists
)

print(f"Data written to {base_path} partitioned by year/month.")
# Expected structure: output/my_partitioned_data/year=2023/month=10/data-*.parquet
```

**Example: Delta Lake Operations with Pydala Dataset**

```python
import polars as pl
from fsspec_utils.core import filesystem

fs = filesystem("file")
delta_path = "output/my_delta_table"

# Initial data
initial_data = pl.DataFrame({
    "id": [1, 2],
    "name": ["Alice", "Bob"],
    "version": [1, 1]
})

# Write initial data to a Pydala dataset
fs.write_pydala_dataset(
    data=initial_data,
    path=delta_path,
    mode="overwrite"
)
print("Initial Delta table created.")

# New data for an upsert: update Alice, add Charlie
new_data = pl.DataFrame({
    "id": [1, 3],
    "name": ["Alicia", "Charlie"],
    "version": [2, 1]
})

# Perform a delta merge (upsert)
fs.write_pydala_dataset(
    data=new_data,
    path=delta_path,
    mode="delta",
    delta_subset=["id"] # Column(s) to use for merging
)
print("Delta merge completed.")

# Read the updated table
updated_df = fs.pydala_dataset(delta_path).to_polars()
print("Updated Delta table:")
print(updated_df)
# Expected: id=1 Alicia version=2, id=2 Bob version=1, id=3 Charlie version=1
```

## Storage Options Management

`fsspec-utils` provides a robust system for managing storage configurations, simplifying credential handling and environment setup.

### Loading from Environment Variables

Instead of hardcoding credentials, you can load storage options directly from environment variables.

**Example: Loading AWS S3 Configuration from Environment**

Set these environment variables before running your script:
```bash
export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY"
export AWS_DEFAULT_REGION="us-west-2"
```

Then in Python:
```python
from fsspec_utils.storage_options import AwsStorageOptions

# Load AWS options directly from environment variables
aws_opts = AwsStorageOptions.from_env()
print(f"Loaded AWS region: {aws_opts.region}")

# Use it to create a filesystem
# fs = aws_opts.to_filesystem()
```

### Merging Storage Options

Combine multiple storage option configurations, useful for layering default settings with user-specific overrides.

**Example: Merging S3 Options**

```python
from fsspec_utils.storage_options import AwsStorageOptions, merge_storage_options

# Base configuration
base_opts = AwsStorageOptions(
    protocol="s3",
    region="us-east-1",
    access_key_id="DEFAULT_KEY"
)

# User-provided overrides
user_overrides = {
    "access_key_id": "USER_KEY",
    "allow_http": True # New setting
}

# Merge, with user_overrides taking precedence
merged_opts = merge_storage_options(base_opts, user_overrides, overwrite=True)

print(f"Merged Access Key ID: {merged_opts.access_key_id}") # USER_KEY
print(f"Merged Region: {merged_opts.region}") # us-east-1
print(f"Allow HTTP: {merged_opts.allow_http}") # True
```

## Performance Tips

-   **Caching**: Always consider using `cached=True` with the `filesystem` function, especially for remote filesystems, to minimize repeated downloads.
-   **Parallel Reading**: For multiple files, set `use_threads=True` in `read_json`, `read_csv`, and `read_parquet` to leverage concurrent I/O.
-   **Batch Processing**: When dealing with a very large number of files or extremely large individual files, use the `batch_size` parameter in reading functions to process data in chunks, reducing memory footprint.
-   **`opt_dtypes`**: Utilize `opt_dtypes=True` in reading functions when converting to Polars or PyArrow to automatically optimize column data types, leading to more efficient memory usage and faster subsequent operations.
-   **Parquet Datasets**: For large, partitioned Parquet datasets, use `pyarrow_dataset` or `pydala_dataset`. These leverage PyArrow's dataset API for efficient metadata handling, partition pruning, and predicate pushdown, reading only the necessary data.
-   **Compression**: When writing Parquet files, choose an appropriate compression codec (e.g., `zstd`, `snappy`) to reduce file size and improve I/O performance. `zstd` often provides a good balance of compression ratio and speed.