# Installation

!!! danger "⚠️ PACKAGE DEPRECATED"
    **fsspec-utils is no longer maintained.** Development has moved to [**fsspeckit**](https://github.com/legout/fsspeckit).
    
    **New projects**: Use fsspeckit instead
    **Existing projects**: Follow the [migration guide below](#migration-to-fsspeckit)

## Migration to fsspeckit

If you're using `fsspec-utils`, migrating to `fsspeckit` is straightforward since the APIs are identical.

### Step 1: Update Installation

=== "pip"
    ```bash
    # Remove fsspec-utils
    pip uninstall fsspec-utils
    
    # Install fsspeckit
    pip install fsspeckit
    ```

=== "uv"
    ```bash
    # Remove fsspec-utils
    uv pip uninstall fsspec-utils
    
    # Install fsspeckit
    uv pip install fsspeckit
    ```

=== "pixi"
    ```bash
    # Remove fsspec-utils
    pixi remove fsspec-utils
    
    # Add fsspeckit
    pixi add fsspeckit
    ```

### Step 2: Update Your Imports

Simply replace `fsspec_utils` with `fsspeckit` in all imports:

| Old (Deprecated) | New (Recommended) |
|-----------------|------------------|
| `from fsspec_utils import ...` | `from fsspeckit import ...` |
| `from fsspec_utils.core import ...` | `from fsspeckit.core import ...` |
| `from fsspec_utils.storage_options import ...` | `from fsspeckit.storage_options import ...` |
| `from fsspec_utils.utils import ...` | `from fsspeckit.utils import ...` |

### Example Migration

```python
# BEFORE (fsspec-utils - deprecated)
from fsspec_utils import filesystem
from fsspec_utils.storage_options import AwsStorageOptions

# AFTER (fsspeckit - recommended)
from fsspeckit import filesystem
from fsspeckit.storage_options import AwsStorageOptions
```

### Compatibility

✅ **All functionality is identical** - No code changes needed beyond import statements
✅ **Same API** - All functions and classes work the same way
✅ **Active support** - fsspeckit is actively maintained and developed

### Migration Checklist

- [ ] Update `pip install fsspec-utils` to `pip install fsspeckit` in requirements.txt or pyproject.toml
- [ ] Replace all `from fsspec_utils import` with `from fsspeckit import`
- [ ] Replace all `from fsspec_utils.storage_options import` with `from fsspeckit.storage_options import`
- [ ] Replace all `from fsspec_utils.utils import` with `from fsspeckit.utils import`
- [ ] Replace all `from fsspec_utils.core import` with `from fsspeckit.core import`
- [ ] Run your tests to verify everything works
- [ ] Update your documentation and examples

---

## Legacy Installation (fsspec-utils only)

If you must maintain legacy code using `fsspec-utils`, follow the instructions below. **Note**: This is not recommended for new projects.

### Prerequisites

- Python 3.11 or higher is required.

### Install with pip

```bash
pip install fsspec-utils
```

### Upgrading

```bash
pip install --upgrade fsspec-utils
```

### Environment Management

#### Using `uv`

```bash
uv pip install fsspec-utils
```

#### Using `pixi`

```bash
pixi add fsspec-utils
```

### Troubleshooting

If you encounter issues during installation:

- **Python Version**: Ensure Python 3.11 or higher (`python --version`)
- **Virtual Environments**: Use a virtual environment (venv, conda, uv, pixi)
- **Permissions**: Avoid using `sudo` with pip; use a virtual environment instead
- **Network Issues**: Check your internet connection

For assistance, refer to the [fsspec-utils GitHub repository](https://github.com/legout/fsspec-utils) or [fsspeckit repository](https://github.com/legout/fsspeckit).

---

## Additional Resources

- **fsspeckit Documentation**: [https://github.com/legout/fsspeckit](https://github.com/legout/fsspeckit)
- **fsspec Documentation**: [https://filesystem-spec.readthedocs.io/](https://filesystem-spec.readthedocs.io/)
- **Migration Support**: Open an issue on [fsspeckit GitHub](https://github.com/legout/fsspeckit/issues)