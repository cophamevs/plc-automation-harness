# Error 012: Data Block Size Exceeds S7-1200 Limit

## Frontmatter
- **Tags**: 1200, db-size, limit, memory, data-block
- **Error Type**: Compile

## Error Message
```
Data block size exceeds maximum (16384 bytes)
```
When compiling a data block for an S7-1200 target, the TIA Portal compiler rejects any DB whose total size exceeds 16,384 bytes (16 KB). The error may also appear as `Memory area exceeded` in some firmware versions. The same code compiles without issue on an S7-1500, which supports up to 64 MB per DB.

## Bad Code
```scl
// UDT: each instance is ~20 bytes
TYPE UDT_DataPoint
VERSION : 0.1
    STRUCT
        timestamp : TIME;       // 4 bytes
        value     : REAL;       // 4 bytes
        quality   : INT;        // 2 bytes
        channel   : INT;        // 2 bytes
        tag       : STRING[6];  // 8 bytes (2 header + 6 chars)
    END_STRUCT;
END_TYPE

// ERROR on S7-1200: 1000 entries x 20 bytes = 20,000 bytes > 16,384 byte limit
DATA_BLOCK DB_DataLog
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
    STRUCT
        entryCount : INT;                            // 2 bytes
        entries    : ARRAY[1..1000] OF UDT_DataPoint; // ~20,000 bytes
    END_STRUCT;
BEGIN
END_DATA_BLOCK
```

## Good Code
```scl
// UDT stays the same — each instance is ~20 bytes
TYPE UDT_DataPoint
VERSION : 0.1
    STRUCT
        timestamp : TIME;       // 4 bytes
        value     : REAL;       // 4 bytes
        quality   : INT;        // 2 bytes
        channel   : INT;        // 2 bytes
        tag       : STRING[6];  // 8 bytes (2 header + 6 chars)
    END_STRUCT;
END_TYPE

// FIX: helper FC abstracts the split across two DBs
FUNCTION FC_GetDataPoint : VOID
VERSION : 0.1
VAR_INPUT
    idx : INT;  // 1-based index into the logical 1..1000 range
END_VAR
VAR_OUTPUT
    dataPoint : UDT_DataPoint;
    error     : BOOL;
    errorID   : INT;
END_VAR
BEGIN
    #error   := FALSE;
    #errorID := 0;

    IF #idx < 1 OR #idx > 1000 THEN
        // Index out of range
        #error   := TRUE;
        #errorID := 1;
        RETURN;
    END_IF;

    IF #idx <= 400 THEN
        // First 400 entries live in DB_DataLog_Part1
        #dataPoint := "DB_DataLog_Part1".entries[#idx];
    ELSE
        // Remaining 600 entries live in DB_DataLog_Part2, re-indexed 1..600
        #dataPoint := "DB_DataLog_Part2".entries[#idx - 400];
    END_IF;
END_FUNCTION

// FIX: helper FC to write a data point to the correct split DB
FUNCTION FC_SetDataPoint : VOID
VERSION : 0.1
VAR_INPUT
    idx       : INT;  // 1-based index into the logical 1..1000 range
    dataPoint : UDT_DataPoint;
END_VAR
VAR_OUTPUT
    error   : BOOL;
    errorID : INT;
END_VAR
BEGIN
    #error   := FALSE;
    #errorID := 0;

    IF #idx < 1 OR #idx > 1000 THEN
        #error   := TRUE;
        #errorID := 1;
        RETURN;
    END_IF;

    IF #idx <= 400 THEN
        "DB_DataLog_Part1".entries[#idx] := #dataPoint;
    ELSE
        "DB_DataLog_Part2".entries[#idx - 400] := #dataPoint;
    END_IF;
END_FUNCTION

// Part 1: 400 entries x 20 bytes = 8,000 bytes + 2 bytes header = 8,002 bytes (< 16,384)
DATA_BLOCK DB_DataLog_Part1
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
    STRUCT
        entryCount : INT;                           // 2 bytes
        entries    : ARRAY[1..400] OF UDT_DataPoint; // ~8,000 bytes
    END_STRUCT;
BEGIN
END_DATA_BLOCK

// Part 2: 600 entries x 20 bytes = 12,000 bytes + 2 bytes header = 12,002 bytes (< 16,384)
DATA_BLOCK DB_DataLog_Part2
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
    STRUCT
        entryCount : INT;                           // 2 bytes
        entries    : ARRAY[1..600] OF UDT_DataPoint; // ~12,000 bytes
    END_STRUCT;
BEGIN
END_DATA_BLOCK
```

## Why
S7-1200 CPUs have a hardware-enforced 16 KB (16,384 bytes) maximum per data block. This is a physical limitation of the S7-1200 memory architecture and cannot be changed through configuration. S7-1500 CPUs allow up to 64 MB per data block. When code originally written for S7-1500 is retargeted to S7-1200 -- or when a developer does not account for this limit -- the compiler rejects any DB whose declared size exceeds 16,384 bytes.

The fix is to split the large data structure across multiple DBs, keeping each one under the 16 KB threshold. A helper FC (like `FC_GetDataPoint` / `FC_SetDataPoint` above) abstracts the split so that calling code works with a single logical index range (1..1000) without needing to know which physical DB holds each entry.

When choosing the split point, leave headroom for DB overhead bytes and alignment padding. A 50/50 split is simplest, but an uneven split (as shown: 400 + 600) is fine as long as each partition stays under 16,384 bytes.

## Detection
- Compile error referencing the DB name with message `Data block size exceeds maximum (16384 bytes)` or `Memory area exceeded`
- In TIA Portal: open the DB properties dialog and check the **Size** field -- any value above 16,384 bytes will fail on S7-1200
- Preventive check: before writing a large DB, calculate `element_count x element_size` and verify the total is under 16 KB
- Review checklist item: "S7-1200: max 16 KB per DB"

## Related
- `knowledge/s7-1200-limitations.md` -- full list of S7-1200 restrictions including DB size limits
- `.claude/rules/s7-1200-compat.md` -- S7-1200 compatibility rules table (max DB size row)
