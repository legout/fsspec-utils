# Examples

This section provides a series of examples demonstrating various functionalities of `fsspec-utils`. Each example includes an executable Python code block and a clear explanation of its purpose.

## 1. Flexible Storage Configuration

`fsspec-utils` simplifies configuring connections to various storage systems, including local filesystems, AWS S3, Azure Storage, and Google Cloud Storage, using `StorageOptions` classes. These options can then be converted into `fsspec` filesystems.

```python
import os
import tempfile
from fsspec_utils.storage_options import (
    LocalStorageOptions,
    AwsStorageOptions,
    AzureStorageOptions,
    GcsStorageOptions,
    StorageOptions,
)

def main():
    print("=== StorageOptions to fsspec Filesystem Example ===\n")

    # 1. LocalStorageOptions Example
    print("1. LocalStorageOptions Example:")
    print("-" * 40)
    
    local_options = LocalStorageOptions(auto_mkdir=True)
    local_fs = local_options.to_filesystem()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = os.path.join(temp_dir, "test_file.txt")
        with local_fs.open(temp_file, "w") as f:
            f.write("Hello, LocalStorageOptions!")
        files = local_fs.ls(temp_dir)
        print(f"Files in {temp_dir}: {[os.path.basename(f) for f in files]}")
        with local_fs.open(temp_file, "r") as f:
            content = f.read()
        print(f"File content: '{content}'")
    print("Local storage example completed.\n")

    # 2. Conceptual S3 Configuration (using a dummy endpoint)
    print("2. Conceptual AwsStorageOptions Example (using a dummy endpoint):")
    print("-" * 40)
    aws_options = AwsStorageOptions(
        endpoint_url="http://s3.dummy-endpoint.com",
        access_key_id="DUMMY_KEY",
        secret_access_key="DUMMY_SECRET",
        allow_http=True,
        region="us-east-1"
    )
    try:
        aws_fs = aws_options.to_filesystem()
        print(f"Created fsspec filesystem for S3: {type(aws_fs).__name__}")
    except Exception as e:
        print(f"Could not create S3 filesystem (expected for dummy credentials): {e}")
    print("AWS storage example completed.\n")

    # 3. Conceptual Azure Configuration (using a dummy connection string)
    print("3. Conceptual AzureStorageOptions Example (using a dummy connection string):")
    print("-" * 40)
    azure_options = AzureStorageOptions(
        protocol="az",
        account_name="demoaccount",
        connection_string="DefaultEndpointsProtocol=https;AccountName=demoaccount;AccountKey=demokey==;EndpointSuffix=core.windows.net"
    )
    try:
        azure_fs = azure_options.to_filesystem()
        print(f"Created fsspec filesystem for Azure: {type(azure_fs).__name__}")
    except Exception as e:
        print(f"Could not create Azure filesystem (expected for dummy credentials): {e}")
    print("Azure storage example completed.\n")
    
    # 4. Conceptual GCS Configuration (using a dummy token path)
    print("4. Conceptual GcsStorageOptions Example (using a dummy token path):")
    print("-" * 40)
    gcs_options = GcsStorageOptions(
        protocol="gs",
        project="demo-project",
        token="path/to/dummy-service-account.json"
    )
    try:
        gcs_fs = gcs_options.to_filesystem()
        print(f"Created fsspec filesystem for GCS: {type(gcs_fs).__name__}")
    except Exception as e:
        print(f"Could not create GCS filesystem (expected for dummy credentials): {e}")
    print("GCS storage example completed.\n")

    print("=== All StorageOptions Examples Completed ===")

if __name__ == "__main__":
    main()
```

This example demonstrates how to initialize `StorageOptions` for local, AWS S3, Azure, and Google Cloud Storage. While the AWS, Azure, and GCS examples use dummy credentials and might not connect to actual services, they illustrate the configuration pattern.

## 2. Enhanced Caching for Improved Performance

`fsspec-utils` provides an enhanced caching mechanism that improves performance for repeated file operations, especially useful for remote filesystems.

```python
import tempfile
import time
import os
import json
from fsspec_utils import filesystem

def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = os.path.join(tmpdir, "sample_data.json")
        sample_data = {
            "name": "fsspec-utils caching example",
            "timestamp": time.time(),
            "items": [{"id": i, "value": f"item_{i}"} for i in range(100)] 
        }
        with open(sample_file, 'w') as f:
            json.dump(sample_data, f)
        print(f"Created sample file: {sample_file}")
        
        cache_dir = os.path.join(tmpdir, "cache")
        fs = filesystem(
            protocol_or_path="file",
            cached=True,
            cache_storage=cache_dir,
            verbose=True
        )
        
        print("\n=== First read (populating cache) ===")
        start_time = time.time()
        data1 = fs.read_json(sample_file)
        first_read_time = time.time() - start_time
        print(f"First read completed in {first_read_time:.4f} seconds")
        
        print("\n=== Second read (using cache) ===")
        start_time = time.time()
        data2 = fs.read_json(sample_file)
        second_read_time = time.time() - start_time
        print(f"Second read completed in {second_read_time:.4f} seconds")
        
        print("\n=== Demonstrating cache effectiveness ===")
        print("Removing original file...")
        os.remove(sample_file)
        print(f"Original file exists: {os.path.exists(sample_file)}")
        
        print("\n=== Third read (from cache only) ===")
        try:
            start_time = time.time()
            data3 = fs.read_json(sample_file)
            third_read_time = time.time() - start_time
            print(f"Third read completed in {third_read_time:.4f} seconds")
            print("✓ Successfully read from cache even after original file was removed")
        except Exception as e:
            print(f"Error reading from cache: {e}")
        
        print("\n=== Performance Comparison ===")
        print(f"First read (from disk): {first_read_time:.4f} seconds")
        print(f"Second read (from cache): {second_read_time:.4f} seconds")
        print(f"Third read (from cache): {third_read_time:.4f} seconds")

if __name__ == "__main__":
    main()
```

This example demonstrates how caching improves read performance. The first read populates the cache, while subsequent reads retrieve data directly from the cache, significantly reducing access time. It also shows that data can still be retrieved from the cache even if the original source becomes unavailable.

## 3. Reading Folders of Files into PyArrow Tables

`fsspec-utils` simplifies reading multiple files of various formats (Parquet, CSV, JSON) from a folder into a single PyArrow Table or Polars DataFrame.

```python
import tempfile
import shutil
import os
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import json
from fsspec_utils import filesystem

def create_sample_data(temp_dir):
    print(f"Creating sample data in {temp_dir}")
    subdir1 = os.path.join(temp_dir, "subdir1")
    subdir2 = os.path.join(temp_dir, "subdir2")
    os.makedirs(subdir1, exist_ok=True)
    os.makedirs(subdir2, exist_ok=True)
    
    data1 = {"id": [1, 2], "name": ["Alice", "Bob"], "value": [10.5, 20.3]}
    data2 = {"id": [3, 4], "name": ["Charlie", "Diana"], "value": [30.7, 40.2]}
    
    pl.DataFrame(data1).write_parquet(os.path.join(subdir1, "data1.parquet"))
    pl.DataFrame(data2).write_parquet(os.path.join(subdir2, "data2.parquet"))
    pl.DataFrame(data1).write_csv(os.path.join(subdir1, "data1.csv"))
    pl.DataFrame(data2).write_csv(os.path.join(subdir2, "data2.csv"))
    with open(os.path.join(subdir1, "data1.json"), "w") as f:
        json.dump(data1, f)
    with open(os.path.join(subdir2, "data2.json"), "w") as f:
        json.dump(data2, f)
    print("Sample data created.")

def demonstrate_parquet_reading(temp_dir):
    print("\n=== Reading Parquet Files ===")
    fs = filesystem(temp_dir)
    parquet_table = fs.read_parquet("**/*.parquet", concat=True)
    print(f"Successfully read Parquet files into PyArrow Table")
    print(f"Table shape: {parquet_table.num_rows} rows x {parquet_table.num_columns} columns")
    print("First 3 rows:")
    print(parquet_table.slice(0, 3).to_pandas())
    return parquet_table

def demonstrate_csv_reading(temp_dir):
    print("\n=== Reading CSV Files ===")
    fs = filesystem(temp_dir)
    csv_df = fs.read_csv("**/*.csv", concat=True)
    print(f"Successfully read CSV files into Polars DataFrame")
    print(f"DataFrame shape: {csv_df.shape}")
    print("First 3 rows:")
    print(csv_df.head(3))
    return csv_df.to_arrow()

def demonstrate_json_reading(temp_dir):
    print("\n=== Reading JSON Files ===")
    fs = filesystem(temp_dir)
    json_df = fs.read_json("**/*.json", as_dataframe=True, concat=True)
    print(f"Successfully read JSON files into Polars DataFrame")
    print(f"DataFrame shape: {json_df.shape}")
    print("First 3 rows:")
    print(json_df.head(3))
    return json_df.to_arrow()

def main():
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")
    try:
        create_sample_data(temp_dir)
        parquet_table = demonstrate_parquet_reading(temp_dir)
        csv_table = demonstrate_csv_reading(temp_dir)
        json_table = demonstrate_json_reading(temp_dir)
        print("\n=== Verification ===")
        print(f"All tables have the same number of rows: {parquet_table.num_rows == csv_table.num_rows == json_table.num_rows}")
    finally:
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary directory: {temp_dir}")

if __name__ == "__main__":
    main()
```

This example shows how to read various file formats from a directory, including subdirectories, into a unified PyArrow Table or Polars DataFrame. It highlights the flexibility of `fsspec-utils` in handling different data sources and formats.

## 4. Efficient Batch Processing

`fsspec-utils` enables efficient batch processing of large datasets by reading files in smaller, manageable chunks. This is particularly useful for memory-constrained environments or when processing streaming data.

```python
import tempfile
import shutil
import os
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import json
from fsspec_utils import filesystem

def create_sample_data(temp_dir):
    print(f"Creating sample data in {temp_dir}")
    sample_data = [
        {"id": i, "name": f"Name_{i}", "value": float(i * 10)} for i in range(10)
    ]
    for i in range(3):
        file_path = os.path.join(temp_dir, f"data_{i+1}.parquet")
        df = pl.DataFrame(sample_data[i*3:(i+1)*3])
        df.write_parquet(file_path)
        print(f"Created Parquet file: {file_path}")
    for i in range(3):
        file_path = os.path.join(temp_dir, f"data_{i+1}.csv")
        df = pl.DataFrame(sample_data[i*3:(i+1)*3])
        df.write_csv(file_path)
        print(f"Created CSV file: {file_path}")
    for i in range(3):
        file_path = os.path.join(temp_dir, f"data_{i+1}.json")
        with open(file_path, 'w') as f:
            json.dump(sample_data[i*3:(i+1)*3], f)
        print(f"Created JSON file: {file_path}")

def demonstrate_parquet_batch_reading(temp_dir):
    print("\n=== Parquet Batch Reading ===")
    fs = filesystem("file")
    parquet_path = os.path.join(temp_dir, "*.parquet")
    print("\nReading Parquet files in batches (batch_size=2):")
    for i, batch in enumerate(fs.read_parquet(parquet_path, batch_size=2)):
        print(f"   Batch {i+1}: rows={batch.num_rows}")
        print(f"   - Data preview: {batch.to_pandas().head(1).to_dict('records')}")

def demonstrate_csv_batch_reading(temp_dir):
    print("\n=== CSV Batch Reading ===")
    fs = filesystem("file")
    csv_path = os.path.join(temp_dir, "*.csv")
    print("\nReading CSV files in batches (batch_size=2):")
    for i, batch in enumerate(fs.read_csv(csv_path, batch_size=2)):
        print(f"   Batch {i+1}: shape={batch.shape}")
        print(f"   - Data preview: {batch.head(1).to_dicts()}")

def demonstrate_json_batch_reading(temp_dir):
    print("\n=== JSON Batch Reading ===")
    fs = filesystem("file")
    json_path = os.path.join(temp_dir, "*.json")
    print("\nReading JSON files in batches (batch_size=2):")
    for i, batch in enumerate(fs.read_json(json_path, batch_size=2)):
        print(f"   Batch {i+1}: shape={batch.shape}")
        print(f"   - Data preview: {batch.head(1).to_dicts()}")

def main():
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")
    try:
        create_sample_data(temp_dir)
        demonstrate_parquet_batch_reading(temp_dir)
        demonstrate_csv_batch_reading(temp_dir)
        demonstrate_json_batch_reading(temp_dir)
    finally:
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary directory: {temp_dir}")

if __name__ == "__main__":
    main()
```

This example illustrates how to read Parquet, CSV, and JSON files in batches using the `batch_size` parameter. This approach allows for processing of large datasets without loading the entire dataset into memory at once.

## 5. Integrating with Delta Lake DeltaTable

`fsspec-utils` facilitates integration with Delta Lake by providing `StorageOptions` that can be used to configure `deltalake`'s `DeltaTable` for various storage backends.

```python
from deltalake import DeltaTable
from fsspec_utils.storage_options import LocalStorageOptions
import tempfile
import shutil
import os
import polars as pl

def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        delta_table_path = os.path.join(temp_dir, "my_delta_table")
        print(f"Creating a dummy Delta table at: {delta_table_path}")

        # Create a simple Polars DataFrame
        data = pl.DataFrame({
            "id": [1, 2, 3],
            "value": ["A", "B", "C"]
        })
        
        # Write initial data to create the Delta table
        data.write_delta(delta_table_path, mode="overwrite")
        print("Initial data written to Delta table.")

        # Create a LocalStorageOptions object for the temporary directory
        local_options = LocalStorageOptions(path=temp_dir)

        # Create a DeltaTable instance, passing storage options
        # Note: deltalake expects storage_options as a dict, which to_object_store_kwargs provides
        try:
            dt = DeltaTable(delta_table_path, storage_options=local_options.to_object_store_kwargs())
            print(f"\nSuccessfully created DeltaTable instance from: {delta_table_path}")
            print(f"DeltaTable version: {dt.version()}")
            print(f"DeltaTable files: {dt.files()}")
            
            # Read data from the DeltaTable
            table_data = dt.to_pyarrow_table()
            print("\nData read from DeltaTable:")
            print(table_data.to_pandas())

        except Exception as e:
            print(f"Error creating DeltaTable: {e}")

if __name__ == "__main__":
    main()
```

This example demonstrates how to use `LocalStorageOptions` with `deltalake`'s `DeltaTable`. It shows how to initialize a `DeltaTable` instance by passing the `fsspec-utils` storage options, enabling seamless interaction with Delta Lake tables across different storage types.