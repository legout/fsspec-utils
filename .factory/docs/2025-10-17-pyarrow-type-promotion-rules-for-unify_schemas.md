# PyArrow `unify_schemas` Type Promotion Analysis

## Overview
When using `pyarrow.unify_schemas` with `promote_options="permissive"`, PyArrow attempts to promote incompatible types to a common denominator. However, not all type combinations can be unified.

## Supported Type Promotions

### Numeric Types (Within same category)
- **Integer promotion**: int8 → int16 → int32 → int64
- **Unsigned integer promotion**: uint8 → uint16 → uint32 → uint64  
- **Float promotion**: float32 → float64
- **Mixed numeric**: Integer types can be promoted to float types when necessary
  - int8/int16/int32/int64 → float32/float64
  - uint8/uint16/uint32/uint64 → float32/float64

### Temporal Types
- **Date promotion**: date32 → date64
- **Time promotion**: time32 → time64
- **Timestamp promotion**: Different timestamp precisions can be unified to higher precision

### Null Type Compatibility
- **Null with any type**: null type can be promoted to any other type

## Unsupported Type Promotions (Incompatible)

### Numeric vs String Types
- **String ↔ Numeric**: Cannot promote between string types and any numeric types (int, uint, float)
- This is the most common source of `ArrowInvalid` errors

### Binary vs Non-Binary Types
- **Binary ↔ Non-binary**: Binary types cannot be promoted to non-binary types and vice versa

### Complex Nested Types
- **Struct ↔ Struct**: Only if field names and types are compatible
- **List ↔ List**: Only if element types are compatible
- **Struct ↔ List**: Never compatible

### Logical vs Physical Types
- **Dictionary ↔ Plain types**: Generally incompatible unless explicitly cast

## Error Scenarios
The function raises `ArrowInvalid` when:
1. Numeric and string types are mixed
2. Binary and non-binary types are mixed  
3. Struct fields have incompatible types
4. List elements have incompatible types
5. Any other fundamentally incompatible type combinations

## Best Practices
1. Ensure compatible types across schemas for the same field names
2. Use explicit casting before unification for known incompatible types
3. Consider null types as universal promotable targets
4. Test with sample schemas before full dataset processing