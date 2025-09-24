import concurrent.futures

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.compute as pc
import re

# Pre-compiled regex patterns (identical to original)
INTEGER_REGEX = r"^[-+]?\d+$"
FLOAT_REGEX = r"^[-+]?(?:\d*[.,])?\d+(?:[eE][-+]?\d+)?$"
BOOLEAN_REGEX = r"^(true|false|1|0|yes|ja|no|nein|t|f|y|j|n|ok|nok)$"
BOOLEAN_TRUE_REGEX = r"^(true|1|yes|ja|t|y|j|ok)$"
DATETIME_REGEX = (
    r"^("
    r"\d{4}-\d{2}-\d{2}"  # ISO: 2023-12-31
    r"|"
    r"\d{2}/\d{2}/\d{4}"  # US: 12/31/2023
    r"|"
    r"\d{2}\.\d{2}\.\d{4}"  # German: 31.12.2023
    r"|"
    r"\d{8}"  # Compact: 20231231
    r")"
    r"([ T]\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?)?"  # Optional time: 23:59[:59[.123456]]
    r"([+-]\d{2}:?\d{2}|Z|UTC)?"  # Optional timezone: +01:00, -0500, Z, UTC
    r"$"
)

# Float32 range limits
F32_MIN = float(np.finfo(np.float32).min)
F32_MAX = float(np.finfo(np.float32).max)


def dominant_timezone_per_column(
    schemas: list[pa.Schema],
) -> dict[str, tuple[str | None, str | None]]:
    """
    For each timestamp column (by name) across all schemas, detect the most frequent timezone (including None).
    If None and a timezone are tied, prefer the timezone.
    Returns a dict: {column_name: dominant_timezone}
    """
    from collections import Counter, defaultdict

    tz_counts = defaultdict(Counter)
    units = {}

    for schema in schemas:
        for field in schema:
            if pa.types.is_timestamp(field.type):
                tz = field.type.tz
                name = field.name
                tz_counts[name][tz] += 1
                # Track unit for each column (assume consistent)
                if name not in units:
                    units[name] = field.type.unit

    dominant = {}
    for name, counter in tz_counts.items():
        most_common = counter.most_common()
        if not most_common:
            continue
        top_count = most_common[0][1]
        # Find all with top_count
        top_tzs = [tz for tz, cnt in most_common if cnt == top_count]
        # If tie and one is not None, prefer not-None
        if len(top_tzs) > 1 and any(tz is not None for tz in top_tzs):
            tz = next(tz for tz in top_tzs if tz is not None)
        else:
            tz = most_common[0][0]
        dominant[name] = (units[name], tz)
    return dominant


def standardize_schema_timezones_by_majority(
    schemas: list[pa.Schema],
) -> list[pa.Schema]:
    """
    For each timestamp column (by name) across all schemas, set the timezone to the most frequent (with tie-breaking).
    Returns a new list of schemas with updated timestamp timezones.
    """
    dom = dominant_timezone_per_column(schemas)
    new_schemas = []
    for schema in schemas:
        fields = []
        for field in schema:
            if pa.types.is_timestamp(field.type) and field.name in dom:
                unit, tz = dom[field.name]
                fields.append(
                    pa.field(
                        field.name,
                        pa.timestamp(unit, tz),
                        field.nullable,
                        field.metadata,
                    )
                )
            else:
                fields.append(field)
        new_schemas.append(pa.schema(fields, schema.metadata))
    return new_schemas


def standardize_schema_timezones(
    schemas: list[pa.Schema], timezone: str | None = None
) -> list[pa.Schema]:
    """
    Standardize timezone info for all timestamp columns in a list of PyArrow schemas.

    Args:
        schemas (list of pa.Schema): List of PyArrow schemas.
        timezone (str or None): If None, remove timezone from all timestamp columns.
                                If str, set this timezone for all timestamp columns.
                                If "auto", use the most frequent timezone across schemas.

    Returns:
        list of pa.Schema: New schemas with standardized timezone info.
    """
    if timezone == "auto":
        # Use the most frequent timezone for each column
        return standardize_schema_timezones_by_majority(schemas)
    new_schemas = []
    for schema in schemas:
        fields = []
        for field in schema:
            if pa.types.is_timestamp(field.type):
                fields.append(
                    pa.field(
                        field.name,
                        pa.timestamp(field.type.unit, timezone),
                        field.nullable,
                        field.metadata,
                    )
                )
            else:
                fields.append(field)
        new_schemas.append(pa.schema(fields, schema.metadata))
    return new_schemas


def unify_schemas(
    schemas: list[pa.Schema],
    use_large_dtypes: bool = False,
    timezone: str | None = None,
    standardize_timezones: bool = True,
) -> pa.Schema:
    """
    Unify a list of PyArrow schemas into a single schema.

    Args:
        schemas (list[pa.Schema]): List of PyArrow schemas to unify.
        use_large_dtypes (bool): If True, keep large types like large_string.
        timezone (str | None): If specified, standardize all timestamp columns to this timezone.
            If "auto", use the most frequent timezone across schemas.
            If None, remove timezone from all timestamp columns.
        standardize_timezones (bool): If True, standardize all timestamp columns to the most frequent timezone.

    Returns:
        pa.Schema: A unified PyArrow schema.
    """
    if standardize_timezones:
        schemas = standardize_schema_timezones(schemas, timezone)
    try:
        return pa.unify_schemas(schemas, promote_options="permissive")
    except (pa.ArrowInvalid, pa.ArrowTypeError) as e:
        _ = e.args[0]
        # If unify_schemas fails, we can try to create a schema with empty tables
        empty_tables = [pa.Table.from_arrays([], schema=schema) for schema in schemas]
        try:
            schema = pa.unify_schemas(empty_tables, promote_options="permissive")
        except Exception:
            # Fallback: nimm erste Schema
            schema = schemas[0]
        if not use_large_dtypes:
            return convert_large_types_to_normal(schema)
        return schema


def cast_schema(table: pa.Table, schema: pa.Schema) -> pa.Table:
    """
    Cast a PyArrow table to a given schema, updating the schema to match the table's columns.

    Args:
        table (pa.Table): The PyArrow table to cast.
        schema (pa.Schema): The target schema to cast the table to.

    Returns:
        pa.Table: A new PyArrow table with the specified schema.
    """
    # Filter schema fields to only those present in the table
    table_columns = set(table.schema.names)
    filtered_fields = [field for field in schema if field.name in table_columns]
    updated_schema = pa.schema(filtered_fields)
    return table.select(updated_schema.names).cast(updated_schema)


def convert_large_types_to_normal(schema: pa.Schema) -> pa.Schema:
    """
    Convert large types in a PyArrow schema to their standard types.

    Args:
        schema (pa.Schema): The PyArrow schema to convert.

    Returns:
        pa.Schema: A new PyArrow schema with large types converted to standard types.
    """
    # Define mapping of large types to standard types
    type_mapping = {
        pa.large_string(): pa.string(),
        pa.large_binary(): pa.binary(),
        pa.large_utf8(): pa.utf8(),
        pa.large_list(pa.null()): pa.list_(pa.null()),
        pa.large_list_view(pa.null()): pa.list_view(pa.null()),
    }
    # Convert fields
    new_fields = []
    for field in schema:
        field_type = field.type
        # Check if type exists in mapping
        if field_type in type_mapping:
            new_field = pa.field(
                name=field.name,
                type=type_mapping[field_type],
                nullable=field.nullable,
                metadata=field.metadata,
            )
            new_fields.append(new_field)
        # Handle large lists with nested types
        elif isinstance(field_type, pa.LargeListType):
            new_field = pa.field(
                name=field.name,
                type=pa.list_(
                    type_mapping[field_type.value_type]
                    if field_type.value_type in type_mapping
                    else field_type.value_type
                ),
                nullable=field.nullable,
                metadata=field.metadata,
            )
            new_fields.append(new_field)
        # Handle dictionary with large_string, large_utf8, or large_binary values
        elif isinstance(field_type, pa.DictionaryType):
            new_field = pa.field(
                name=field.name,
                type=pa.dictionary(
                    field_type.index_type,
                    type_mapping[field_type.value_type]
                    if field_type.value_type in type_mapping
                    else field_type.value_type,
                    field_type.ordered,
                ),
                # nullable=field.nullable,
                metadata=field.metadata,
            )
            new_fields.append(new_field)
        else:
            new_fields.append(field)

    return pa.schema(new_fields)


NULL_LIKE_STRINGS = {
    "",
    "-",
    "None",
    "none",
    "NONE",
    "NaN",
    "Nan",
    "nan",
    "NAN",
    "N/A",
    "n/a",
    "Null",
    "NULL",
    "null",
}


def _normalize_datetime_string(s: str) -> str:
    """
    Normalize a datetime string by removing timezone information.

    Args:
        s: Datetime string potentially containing timezone info

    Returns:
        str: Normalized datetime string without timezone
    """
    s = str(s).strip()
    s = re.sub(r'Z$', '', s)
    s = re.sub(r'UTC$', '', s)
    s = re.sub(r'([+-]\d{2}:\d{2})$', '', s)
    s = re.sub(r'([+-]\d{4})$', '', s)
    return s


def _detect_timezone_from_sample(series: pl.Series) -> str | None:
    """
    Detect the most common timezone from a sample of datetime strings.

    Args:
        series: Polars Series containing datetime strings

    Returns:
        str or None: Most common timezone found, or None if no timezone detected
    """
    import random

    # Sample up to 1000 values for performance
    sample_size = min(1000, len(series))
    if sample_size == 0:
        return None

    # Get random sample
    sample_indices = random.sample(range(len(series)), sample_size)
    sample_values = [series[i] for i in sample_indices if series[i] is not None]

    if not sample_values:
        return None

    # Extract timezones
    timezones = []
    for val in sample_values:
        val = str(val).strip()
        match = re.search(r"(Z|UTC|[+-]\d{2}:\d{2}|[+-]\d{4})$", val)
        if match:
            tz = match.group(1)
            if tz == "Z":
                timezones.append("UTC")
            elif tz == "UTC":
                timezones.append("UTC")
            elif tz.startswith("+") or tz.startswith("-"):
                # Normalize timezone format
                if ":" not in tz:
                    tz = tz[:3] + ":" + tz[3:]
                timezones.append(tz)

    if not timezones:
        return None

    # Count frequencies
    from collections import Counter
    tz_counts = Counter(timezones)

    # Return most common timezone
    return tz_counts.most_common(1)[0][0]


def _clean_string_array(array: pa.Array) -> pa.Array:
    """Trimmt Strings und ersetzt definierte Platzhalter durch Null (Python-basiert, robust)."""
    if len(array) == 0:
        return array
    # pc.utf8_trim_whitespace kann fehlen / unterschiedlich sein → fallback
    py = [None if v is None else str(v).strip() for v in array.to_pylist()]
    cleaned_list = [None if (v is None or v in NULL_LIKE_STRINGS) else v for v in py]
    return pa.array(cleaned_list, type=pa.string())


def _can_downcast_to_float32(array: pa.Array) -> bool:
    """Prüft Float32 Range (Python fallback)."""
    if len(array) == 0 or array.null_count == len(array):
        return True
    values = [v for v in array.to_pylist() if isinstance(v, (int, float)) and v not in (None, float("inf"), float("-inf"))]
    if not values:
        return True
    mn, mx = min(values), max(values)
    return F32_MIN <= mn <= mx <= F32_MAX


def _get_optimal_int_type(array: pa.Array, allow_unsigned: bool, allow_null: bool = True) -> pa.DataType:
    values = [v for v in array.to_pylist() if v is not None]
    if not values:
        return pa.null() if allow_null else pa.int8()
    min_val = min(values)
    max_val = max(values)
    if allow_unsigned and min_val >= 0:
        if max_val <= 255:
            return pa.uint8()
        if max_val <= 65535:
            return pa.uint16()
        if max_val <= 4294967295:
            return pa.uint32()
        return pa.uint64()
    if -128 <= min_val and max_val <= 127:
        return pa.int8()
    if -32768 <= min_val and max_val <= 32767:
        return pa.int16()
    if -2147483648 <= min_val and max_val <= 2147483647:
        return pa.int32()
    return pa.int64()


def _optimize_numeric_array(
    array: pa.Array, shrink: bool, allow_unsigned: bool = True, allow_null: bool = True
) -> pa.DataType:
    """
    Optimize numeric PyArrow array by downcasting when possible.
    Returns the optimal dtype.
    """

    if not shrink or len(array) == 0 or array.null_count == len(array):
        if allow_null:
            return pa.null()
        else:
            return array.type

    if pa.types.is_floating(array.type):
        if array.type == pa.float64() and _can_downcast_to_float32(array):
            return pa.float32()
        return array.type

    if pa.types.is_integer(array.type):
        return _get_optimal_int_type(array, allow_unsigned, allow_null)

    return array.type


_REGEX_CACHE: dict[str, re.Pattern] = {}


def _all_match_regex(array: pa.Array, pattern: str) -> bool:
    """Python Regex Matching (alle nicht-null Werte)."""
    if len(array) == 0 or array.null_count == len(array):
        return False
    if pattern not in _REGEX_CACHE:
        _REGEX_CACHE[pattern] = re.compile(pattern, re.IGNORECASE)
    rgx = _REGEX_CACHE[pattern]
    for v in array.to_pylist():
        if v is None:
            continue
        if not rgx.match(str(v)):
            return False
    return True


def _optimize_string_array(
    array: pa.Array,
    col_name: str,
    shrink_numerics: bool,
    time_zone: str | None = None,
    allow_unsigned: bool = True,
    allow_null: bool = True,
    force_timezone: str | None = None,
) -> tuple[pa.Array, pa.DataType]:
    """Analysiere String-Array und bestimme Ziel-Datentyp.

    Rückgabe: (bereinigtes_array, ziel_datentyp)
    Platzhalter-/Leerwerte blockieren keine Erkennung mehr.
    """
    if len(array) == 0 or array.null_count == len(array):
        return array, (pa.null() if allow_null else array.type)

    cleaned_array = _clean_string_array(array)

    # Werte für Erkennung: nur nicht-null
    non_null_list = [v for v in cleaned_array.to_pylist() if v is not None]
    if not non_null_list:
        return cleaned_array, (pa.null() if allow_null else array.type)
    non_null = pa.array(non_null_list, type=pa.string())

    try:
        # Boolean
        if _all_match_regex(non_null, BOOLEAN_REGEX):
            bool_values = [
                True
                if re.match(BOOLEAN_TRUE_REGEX, v, re.IGNORECASE)
                else False
                for v in non_null_list
            ]
            # Rekonstruiere vollständige Länge unter Erhalt der Nulls
            it = iter(bool_values)
            casted_full = [next(it) if v is not None else None for v in cleaned_array.to_pylist()]
            return pa.array(casted_full, type=pa.bool_()), pa.bool_()

        # Integer
        if _all_match_regex(non_null, INTEGER_REGEX):
            int_values = [int(v) for v in non_null_list]
            optimized_type = _get_optimal_int_type(pa.array(int_values, type=pa.int64()), allow_unsigned, allow_null)
            it = iter(int_values)
            casted_full = [next(it) if v is not None else None for v in cleaned_array.to_pylist()]
            return pa.array(casted_full, type=optimized_type), optimized_type

        # Float
        if _all_match_regex(non_null, FLOAT_REGEX):
            float_values = [float(v.replace(',', '.')) for v in non_null_list]
            base_arr = pa.array(float_values, type=pa.float64())
            target_type = pa.float64()
            if shrink_numerics and _can_downcast_to_float32(base_arr):
                target_type = pa.float32()
            it = iter(float_values)
            casted_full = [next(it) if v is not None else None for v in cleaned_array.to_pylist()]
            return pa.array(casted_full, type=target_type), target_type

        # Datetime
        if _all_match_regex(non_null, DATETIME_REGEX):
            # Nutzung Polars für tolerant parsing mit erweiterter Format-Unterstützung
            pl_series = pl.Series(col_name, cleaned_array)

            # Prüfe ob gemischte Zeitzonen vorhanden sind
            has_tz = pl_series.str.contains(r"(Z|UTC|[+-]\d{2}:\d{2}|[+-]\d{4})$").any()

            if has_tz:
                # Bei gemischten Zeitzonen, verwende eager parsing auf Series-Ebene
                normalized_series = pl_series.map_elements(
                    _normalize_datetime_string, return_dtype=pl.String
                )

                if force_timezone is not None:
                    dt_series = normalized_series.str.to_datetime(time_zone=force_timezone, time_unit="us")
                else:
                    detected_tz = _detect_timezone_from_sample(pl_series)
                    if detected_tz is not None:
                        dt_series = normalized_series.str.to_datetime(time_zone=detected_tz, time_unit="us")
                    else:
                        dt_series = normalized_series.str.to_datetime(time_unit="us")

                converted = dt_series
            else:
                # Bei konsistenten Zeitzonen, verwende Polars' eingebaute Format-Erkennung
                if force_timezone is not None:
                    converted = pl_series.str.to_datetime(time_zone=force_timezone, time_unit="us")
                else:
                    # Prüfe ob Zeitzonen vorhanden sind
                    has_any_tz = pl_series.str.contains(r"(Z|UTC|[+-]\d{2}:\d{2}|[+-]\d{4})$").any()
                    if has_any_tz:
                        # Automatische Zeitzonenerkennung
                        converted = pl_series.str.to_datetime(time_unit="us")
                    else:
                        # Ohne Zeitzonen
                        converted = pl_series.str.to_datetime(time_unit="us")

            return converted.to_arrow(), converted.to_arrow().type
    except Exception:  # pragma: no cover
        pass

    # Kein Cast
    return cleaned_array, pa.string()


def _process_column(
    array: pa.Array,
    col_name: str,
    shrink_numerics: bool,
    allow_unsigned: bool,
    time_zone: str | None = None,
    force_timezone: str | None = None,
) -> tuple[pa.Field, pa.Array]:
    """
    Process a single column for type optimization.
    Returns a pyarrow.Field with the optimal dtype.
    """
    # array = table[col_name]
    if array.null_count == len(array):
        return pa.field(col_name, pa.null()), array

    if pa.types.is_floating(array.type) or pa.types.is_integer(array.type):
        dtype = _optimize_numeric_array(array, shrink_numerics, allow_unsigned)
        return pa.field(col_name, dtype, nullable=array.null_count > 0), array
    elif (
        pa.types.is_string(array.type)
        or pa.types.is_large_string(array.type)
    ):
        casted_array, dtype = _optimize_string_array(
            array,
            col_name,
            shrink_numerics,
            time_zone,
            allow_unsigned=allow_unsigned,
            allow_null=True,
            force_timezone=force_timezone,
        )
        return pa.field(col_name, dtype, nullable=casted_array.null_count > 0), casted_array
    else:
        return pa.field(col_name, array.type, nullable=array.null_count > 0), array


def _process_column_for_opt_dtype(args):
    (
        array,
        col_name,
        cols_to_process,
        shrink_numerics,
        allow_unsigned,
        time_zone,
        strict,
        allow_null,
        force_timezone,
    ) = args
    try:
        if col_name in cols_to_process:
            field, array = _process_column(
                array, col_name, shrink_numerics, allow_unsigned, time_zone, force_timezone
            )
            if pa.types.is_null(field.type):
                if allow_null:
                    array = pa.nulls(array.length(), type=pa.null())
                    return (col_name, field, array)
                else:
                    orig_type = array.type
                    # array = table[col_name]
                    field = pa.field(col_name, orig_type, nullable=True)
                    return (col_name, field, array)
            return (col_name, field, array)
        else:
            field = pa.field(col_name, array.type, nullable=True)
            # array = table[col_name]
            return (col_name, field, array)
    except Exception as e:
        if strict:
            raise e
        field = pa.field(col_name, array.type, nullable=True)
        return (col_name, field, array)


def opt_dtype(
    table: pa.Table,
    include: str | list[str] | None = None,
    exclude: str | list[str] | None = None,
    time_zone: str | None = None,
    shrink_numerics: bool = True,
    allow_unsigned: bool = True,
    use_large_dtypes: bool = False,
    strict: bool = False,
    allow_null: bool = True,
    *,
    force_timezone: str | None = None,
) -> pa.Table:
    """
    Optimize data types of a PyArrow Table for performance and memory efficiency.
    Returns a new table casted to the optimal schema.

    Args:
        table: The PyArrow table to optimize.
        include: Column(s) to include in optimization (default: all columns).
        exclude: Column(s) to exclude from optimization.
        time_zone: Optional time zone hint during datetime parsing.
        shrink_numerics: Whether to downcast numeric types when possible.
        allow_unsigned: Whether to allow unsigned integer types.
        use_large_dtypes: If True, keep large types like large_string.
        strict: If True, will raise an error if any column cannot be optimized.
        allow_null: If False, columns that only hold null-like values will not be converted to pyarrow.null().
        force_timezone: If set, ensure all parsed datetime columns end up with this timezone.
    """
    if isinstance(include, str):
        include = [include]
    if isinstance(exclude, str):
        exclude = [exclude]

    cols_to_process = table.column_names
    if include:
        cols_to_process = [col for col in include if col in table.column_names]
    if exclude:
        cols_to_process = [col for col in cols_to_process if col not in exclude]

    # Prepare arguments for parallel processing
    args_list = [
        (
            table[col_name],
            col_name,
            cols_to_process,
            shrink_numerics,
            allow_unsigned,
            time_zone,
            strict,
            allow_null,
            force_timezone,
        )
        for col_name in table.column_names
    ]

    # Parallelize column processing
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(_process_column_for_opt_dtype, args_list))

    # Sort results to preserve column order
    results.sort(key=lambda x: table.column_names.index(x[0]))
    fields = [field for _, field, _ in results]
    arrays = [array for _, _, array in results]

    schema = pa.schema(fields)
    if use_large_dtypes:
        schema = convert_large_types_to_normal(schema)
    return pa.Table.from_arrays(arrays, schema=schema)
