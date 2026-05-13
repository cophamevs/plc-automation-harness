# Hardware Parameter Catalog Builder

Builds a local SQLite catalog from Siemens TIA Openness hardware-parameter markdown.

## Why

TIA Portal V19 Openness does not expose a complete discoverable hardware-parameter catalog API.  
This tool creates a queryable local catalog as a knowledge layer.

## Input

- Converted markdown document, for example:
  - `converted_md/TIA_Portal_Openness_Hardware_parameters.md`

## Output

- SQLite database, for example:
  - `converted_md/hardware_catalog_v19.sqlite`

## Usage

```powershell
python tools/hw_catalog/build_hw_catalog.py `
  --input converted_md/TIA_Portal_Openness_Hardware_parameters.md `
  --db converted_md/hardware_catalog_v19.sqlite `
  --tia-version v19 `
  --doc-edition 09/2023
```

Optional:

```powershell
python tools/hw_catalog/build_hw_catalog.py `
  --input converted_md/TIA_Portal_Openness_Hardware_parameters.md `
  --db converted_md/hardware_catalog_v19.sqlite `
  --no-raw-lines
```

## Schema

- `sources`: source file metadata (hash, import timestamp, TIA version, doc edition)
- `sections`: parsed sections (for example `HW parameters: ...`)
- `modules`: parsed module anchors (for example `Module - 6ES7 ...`)
- `parameters`: normalized parameter rows (property, datatype, label, access, notes)
- `enum_values`: normalized enum/value descriptions bound to each parameter
- `raw_lines`: optional raw line store with line number for traceability

When available, an FTS5 index `parameters_fts` is built for fast text search.

## Example queries

Find a parameter:

```sql
SELECT p.property_name, p.data_type, p.label, m.module_name, s.section_name
FROM parameters p
LEFT JOIN modules m ON m.id = p.module_id
LEFT JOIN sections s ON s.id = p.section_id
WHERE p.property_name = 'DpOperatingMode'
LIMIT 20;
```

Find unsupported/special notes:

```sql
SELECT p.property_name, p.notes
FROM parameters p
WHERE p.notes LIKE '%not supported%'
LIMIT 50;
```

FTS search (if FTS5 exists):

```sql
SELECT rowid, property_name, label
FROM parameters_fts
WHERE parameters_fts MATCH 'watchdog OR diagnostics';
```
