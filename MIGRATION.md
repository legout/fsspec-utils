# Migration Guide: fsspec-utils → fsspeckit

**fsspec-utils is deprecated as of version 0.3.0** and has been superseded by [**fsspeckit**](https://github.com/legout/fsspeckit).

This guide will help you migrate your codebase from fsspec-utils to fsspeckit.

## Why Migrate?

- ✅ **Active Development**: fsspeckit is actively maintained and developed
- ✅ **Bug Fixes**: Receive timely bug fixes and security patches
- ✅ **New Features**: Access to new features and improvements
- ✅ **Performance**: Benefit from ongoing performance optimizations
- ✅ **Same API**: Migration requires only import changes (no code rewrite needed)

## Migration Overview

Migrating from fsspec-utils to fsspeckit is straightforward because:

1. **Same API**: All functions and classes work identically
2. **Minimal Changes**: Update imports, that's it!
3. **No Behavior Changes**: Your code will work exactly as before
4. **Drop-in Replacement**: fsspeckit is a true replacement

## Step-by-Step Migration

### Step 1: Update Your Package Manager

=== "pip"

    ```bash
    # Remove fsspec-utils
    pip uninstall fsspec-utils
    
    # Install fsspeckit
    pip install fsspeckit
    ```

=== "uv"

    ```bash
    # Update pyproject.toml
    # Change: fsspec-utils → fsspeckit
    
    # Then run:
    uv pip uninstall fsspec-utils
    uv pip install fsspeckit
    ```

=== "Poetry"

    ```bash
    # Update pyproject.toml
    poetry remove fsspec-utils
    poetry add fsspeckit
    ```

=== "Conda"

    ```bash
    conda remove fsspec-utils
    conda install -c conda-forge fsspeckit
    ```

### Step 2: Update Dependencies File

Update your dependency file:

=== "requirements.txt"

    ```diff
    - fsspec-utils>=0.2.0
    + fsspeckit>=0.3.1
    ```

=== "pyproject.toml"

    ```diff
    dependencies = [
    -   "fsspec-utils>=0.2.0",
    +   "fsspeckit>=0.3.1",
    ]
    ```

=== "setup.py"

    ```diff
    install_requires=[
    -   "fsspec-utils>=0.2.0",
    +   "fsspeckit>=0.3.1",
    ]
    ```

### Step 3: Update Imports

Replace all `fsspec_utils` imports with `fsspeckit`:

#### Main imports

```python
# OLD (Deprecated)
from fsspec_utils import filesystem, get_filesystem

# NEW (Recommended)
from fsspeckit import filesystem, get_filesystem
```

#### Core modules

```python
# OLD
from fsspec_utils.core import DirFileSystem, MonitoredSimpleCacheFileSystem

# NEW
from fsspeckit.core import DirFileSystem, MonitoredSimpleCacheFileSystem
```

#### Storage options

```python
# OLD
from fsspec_utils.storage_options import (
    AwsStorageOptions,
    GcsStorageOptions,
    AzureStorageOptions,
    GitHubStorageOptions,
)

# NEW
from fsspeckit.storage_options import (
    AwsStorageOptions,
    GcsStorageOptions,
    AzureStorageOptions,
    GitHubStorageOptions,
)
```

#### Utilities

```python
# OLD
from fsspec_utils.utils import (
    run_parallel,
    setup_logging,
    dict_to_dataframe,
    to_pyarrow_table,
    opt_dtype_pl,
    opt_dtype_pa,
)

# NEW
from fsspeckit.utils import (
    run_parallel,
    setup_logging,
    dict_to_dataframe,
    to_pyarrow_table,
    opt_dtype_pl,
    opt_dtype_pa,
)
```

#### Datetime utilities

```python
# OLD
from fsspec_utils.utils.datetime import (
    get_timestamp_column,
    get_timedelta_str,
)

# NEW
from fsspeckit.utils import (
    get_timestamp_column,
    get_timedelta_str,
)
```

#### SQL utilities

```python
# OLD
from fsspec_utils.utils.sql import sql2pyarrow_filter

# NEW
from fsspeckit.utils import sql2pyarrow_filter
```

### Step 4: Automated Migration (with sed/grep)

If you have many files to migrate, use a script:

=== "Bash"

    ```bash
    # Replace all imports
    find . -name "*.py" -type f -exec sed -i 's/from fsspec_utils/from fsspeckit/g' {} +
    find . -name "*.py" -type f -exec sed -i 's/import fsspec_utils/import fsspeckit/g' {} +
    ```

=== "Python Script"

    ```python
    import os
    import re

    def migrate_imports(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace imports
        content = re.sub(r'from fsspec_utils', 'from fsspeckit', content)
        content = re.sub(r'import fsspec_utils', 'import fsspeckit', content)
        
        with open(file_path, 'w') as f:
            f.write(content)

    # Iterate through all Python files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                migrate_imports(file_path)
                print(f"Migrated: {file_path}")
    ```

### Step 5: Test Your Code

Run your test suite to ensure everything works:

```bash
# Run tests
pytest tests/

# Or with coverage
pytest --cov=your_module tests/
```

## API Compatibility Table

| Feature | fsspec-utils | fsspeckit | Notes |
|---------|--------------|-----------|-------|
| `filesystem()` | ✅ | ✅ | Identical API |
| `get_filesystem()` | ✅ | ✅ | Identical API |
| `DirFileSystem` | ✅ | ✅ | Identical API |
| Storage options | ✅ | ✅ | Identical API |
| Utilities | ✅ | ✅ | Identical API |
| Caching | ✅ | ✅ | Identical API |
| PyArrow support | ✅ | ✅ | Identical API |
| Polars support | ✅ | ✅ | Identical API |

## Common Migration Patterns

### Pattern 1: Simple filesystem operations

```python
# BEFORE (fsspec-utils)
from fsspec_utils import filesystem

fs = filesystem("s3://my-bucket")
files = fs.ls("/path")

# AFTER (fsspeckit)
from fsspeckit import filesystem

fs = filesystem("s3://my-bucket")
files = fs.ls("/path")
```

### Pattern 2: Cloud storage with options

```python
# BEFORE (fsspec-utils)
from fsspec_utils import filesystem
from fsspec_utils.storage_options import AwsStorageOptions

options = AwsStorageOptions.from_env()
fs = filesystem("s3", storage_options=options)

# AFTER (fsspeckit)
from fsspeckit import filesystem
from fsspeckit.storage_options import AwsStorageOptions

options = AwsStorageOptions.from_env()
fs = filesystem("s3", storage_options=options)
```

### Pattern 3: Data I/O operations

```python
# BEFORE (fsspec-utils)
from fsspec_utils.core import read_parquet, write_parquet

# Note: read_parquet/write_parquet are in fsspec_utils.core.ext
# in the old version, but accessed via fsspec_utils.core

# AFTER (fsspeckit)
from fsspec.core import read_parquet, write_parquet
```

### Pattern 4: Utilities

```python
# BEFORE (fsspec-utils)
from fsspec_utils.utils import run_parallel, opt_dtype_pa

results = run_parallel(func, data)
optimized = opt_dtype_pa(table)

# AFTER (fsspeckit)
from fsspeckit.utils import run_parallel, opt_dtype_pa

results = run_parallel(func, data)
optimized = opt_dtype_pa(table)
```

## Troubleshooting

### Issue: ImportError after migration

**Problem**: You get `ImportError: cannot import name 'X' from 'fsspeckit'`

**Solution**: Check that:
1. fsspeckit is installed: `pip install fsspeckit`
2. You're using compatible versions
3. The function/class exists in fsspeckit (most do, but some utilities might not)

### Issue: Behavior differences

**Problem**: Your code behaves differently with fsspeckit

**Solution**:
1. Check fsspeckit changelog: [GitHub Releases](https://github.com/legout/fsspeckit/releases)
2. Open an issue on [fsspeckit](https://github.com/legout/fsspeckit/issues)
3. Report on [fsspec-utils](https://github.com/legout/fsspec-utils/issues) if it's a compat issue

### Issue: Missing functions

**Problem**: A function from fsspec-utils doesn't exist in fsspeckit

**Solution**:
1. Check the fsspeckit documentation
2. The function might have been moved or renamed
3. Open an issue to request it

## FAQ

**Q: Will fsspec-utils still receive updates?**
A: Only critical security and bug fixes. All new development is in fsspeckit.

**Q: Is the API identical?**
A: Yes, fsspeckit is designed to be a drop-in replacement.

**Q: Do I need to change my code (beyond imports)?**
A: No, just update the imports. The functionality is identical.

**Q: What about the `storage` submodule?**
A: Use `storage_options` instead. It was renamed for consistency.

**Q: When will fsspec-utils be removed?**
A: No specific date announced, but deprecation started at v0.3.0.

**Q: Can I use both packages together?**
A: Not recommended. Choose one or the other.

## Need Help?

- 📚 **fsspeckit Docs**: [GitHub Repository](https://github.com/legout/fsspeckit)
- 🐛 **Report Issues**: [fsspeckit Issues](https://github.com/legout/fsspeckit/issues)
- 💬 **Discussions**: [fsspeckit Discussions](https://github.com/legout/fsspeckit/discussions)
- 📖 **fsspec Docs**: [filesystem-spec.readthedocs.io](https://filesystem-spec.readthedocs.io/)

## Migration Checklist

- [ ] Install fsspeckit: `pip install fsspeckit`
- [ ] Update requirements.txt/pyproject.toml
- [ ] Replace all `fsspec_utils` imports with `fsspeckit`
- [ ] Run your tests to verify
- [ ] Update any internal documentation
- [ ] Update CI/CD pipeline if needed
- [ ] Deploy and monitor
- [ ] Uninstall fsspec-utils: `pip uninstall fsspec-utils`

## Summary

Migrating from fsspec-utils to fsspeckit is simple and risk-free:

1. ✅ Install fsspeckit
2. ✅ Update imports (optional: use a script)
3. ✅ Run tests
4. ✅ Done!

The vast majority of migrations take less than 5 minutes.

---

**Questions?** Open an issue on [fsspeckit](https://github.com/legout/fsspeckit/issues) or [fsspec-utils](https://github.com/legout/fsspec-utils/issues).
