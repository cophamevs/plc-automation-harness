# Hardware Parameter Catalog (TIA V19)

> Local strategy for hardware parameter discovery when Openness API coverage is incomplete.

## Problem

TIA Portal Openness V19 does not provide a single complete API to enumerate all hardware parameters, enum mappings, and module-specific notes across the full Siemens device catalog.

For automation workflows, we still need deterministic lookup for:

- parameter names (`EomAtom` / property names),
- expected data types,
- writable/readable hints (`R/W`, `R`, etc.),
- enum/value mappings,
- known unsupported sub-parameters and special notes.

## Decision

Use a local **SQLite catalog** generated from the converted manual:

- Source file:
  - `converted_md/TIA_Portal_Openness_Hardware_parameters.md`
- Builder:
  - `tools/hw_catalog/build_hw_catalog.py`
- Output DB:
  - `converted_md/hardware_catalog_v19.sqlite` (recommended path)

## Why SQLite

- Works offline and is easy to version with metadata (hash, import date, doc edition).
- Handles large semi-structured datasets (hundreds of thousands of lines) better than ad hoc markdown parsing at runtime.
- Supports indexed lookup and FTS text search for quick retrieval.
- Good fit for agent workflows that need repeatable queries and traceable results.

## Data Model

The catalog stores both normalized and traceable forms:

- `parameters`, `enum_values`, `modules`, `sections` for fast query/use.
- `raw_lines` with source line numbers for provenance and parser rework.

This dual model is important because the source formatting is irregular.

## Operational Guidance

1. Rebuild DB when source markdown changes.
2. Keep `tia_version` + `doc_edition` fields populated.
3. Track source hash to detect drift.
4. Treat catalog data as an assistive knowledge layer; always validate writes through actual Openness operations in target projects.

## Query Examples

```sql
SELECT property_name, data_type, label
FROM parameters
WHERE property_name = 'DpOperatingMode';
```

```sql
SELECT property_name, notes
FROM parameters
WHERE notes LIKE '%not supported%';
```

## Known Limits

- First-pass parser is heuristic. Some rows may be missed or mis-grouped in irregular sections.
- The DB is a catalog aid, not a formal Siemens API contract.
- For safety-critical automation, runtime validation in TIA remains mandatory.
