#!/usr/bin/env python3
"""
Build a local SQLite catalog from TIA Portal Openness hardware-parameter markdown.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


STRUCTURAL_TOKENS = {
    "TIA Portal Openness",
    "Channel",
    "Range",
    "Property",
    "DataType",
    "Label",
    "EomAtom",
    "Value",
    "EomAtom Description",
    "Step",
    "Description",
    "Command",
}

KNOWN_TYPES = {
    "Boolean",
    "Bool",
    "Byte",
    "SByte",
    "Int16",
    "Int32",
    "Int64",
    "UInt16",
    "UInt32",
    "UInt64",
    "Int",
    "UInt",
    "byte",
    "sbyte",
    "String",
    "Char",
    "DateTime",
    "TimeSpan",
    "Object",
    "Single",
    "Double",
    "Real",
    "LReal",
    "Float",
}

ACCESS_RE = re.compile(
    r"^(R/W|R|W|Read\s*/\s*Write|Read\s+only|Write\s+only|Read|Write)$",
    re.IGNORECASE,
)
PAGE_RE = re.compile(r"^##\s+Page\s+\d+", re.IGNORECASE)
SECTION_RE = re.compile(r"^HW parameters:\s*(.+)$", re.IGNORECASE)
SECONDARY_SECTION_RE = re.compile(r"^Openness for\s+(.+)$", re.IGNORECASE)
MODULE_RE = re.compile(
    r"^(Module|Submodule|Interface|Port|Device|Station|Rack|CPU|Head module|Power module)\s*-\s*(.+)$",
    re.IGNORECASE,
)
ENUM_VALUE_RE = re.compile(
    r"^(?:-?\d+(?:\.\d+)?|0x[0-9A-Fa-f]+|true|false|none|check:\s*\d+|uncheck:\s*\d+|value\d+.*)$",
    re.IGNORECASE,
)
POTENTIAL_FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:/-]*$")


@dataclass
class ParseState:
    section_id: int | None = None
    module_id: int | None = None


def is_noise_line(text: str) -> bool:
    if not text:
        return True
    if text.startswith("## Page"):
        return True
    if text.startswith("System Manual"):
        return True
    if text.startswith("Programming and Operating Manual"):
        return True
    if text.endswith("/ 5"):
        return True
    if text in STRUCTURAL_TOKENS:
        return True
    if text.startswith("Table "):
        return True
    return False


def looks_like_type(text: str) -> bool:
    if text in KNOWN_TYPES:
        return True
    lower = text.lower()
    if lower in {t.lower() for t in KNOWN_TYPES}:
        return True
    if re.match(r"^(?:u?int(?:16|32|64)?|l?real|float|double|bool(?:ean)?|string)$", text, re.IGNORECASE):
        return True
    return False


def clean_line(line: str) -> str:
    return line.replace("\u00ad", "").replace("\u2010", "-").strip()


def sha256_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;

        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY,
            source_path TEXT NOT NULL UNIQUE,
            source_sha256 TEXT NOT NULL,
            imported_at_utc TEXT NOT NULL,
            tia_version TEXT,
            doc_edition TEXT,
            line_count INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            line_no INTEGER NOT NULL,
            section_name TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES sources(id)
        );

        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            section_id INTEGER,
            line_no INTEGER NOT NULL,
            module_kind TEXT NOT NULL,
            module_name TEXT NOT NULL,
            raw_line TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES sources(id),
            FOREIGN KEY(section_id) REFERENCES sections(id)
        );

        CREATE TABLE IF NOT EXISTS parameters (
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            section_id INTEGER,
            module_id INTEGER,
            line_no INTEGER NOT NULL,
            property_name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            label TEXT,
            access_mode TEXT,
            value_hint TEXT,
            notes TEXT,
            meta_json TEXT,
            parse_confidence REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY(source_id) REFERENCES sources(id),
            FOREIGN KEY(section_id) REFERENCES sections(id),
            FOREIGN KEY(module_id) REFERENCES modules(id)
        );

        CREATE TABLE IF NOT EXISTS enum_values (
            id INTEGER PRIMARY KEY,
            parameter_id INTEGER NOT NULL,
            seq INTEGER NOT NULL,
            enum_value TEXT NOT NULL,
            enum_description TEXT,
            line_no INTEGER NOT NULL,
            FOREIGN KEY(parameter_id) REFERENCES parameters(id)
        );

        CREATE TABLE IF NOT EXISTS raw_lines (
            source_id INTEGER NOT NULL,
            line_no INTEGER NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY(source_id, line_no),
            FOREIGN KEY(source_id) REFERENCES sources(id)
        );

        CREATE INDEX IF NOT EXISTS idx_sections_source ON sections(source_id);
        CREATE INDEX IF NOT EXISTS idx_modules_source ON modules(source_id);
        CREATE INDEX IF NOT EXISTS idx_params_source ON parameters(source_id);
        CREATE INDEX IF NOT EXISTS idx_params_property ON parameters(property_name);
        CREATE INDEX IF NOT EXISTS idx_params_module ON parameters(module_id);
        CREATE INDEX IF NOT EXISTS idx_enums_param ON enum_values(parameter_id);
        """
    )


def upsert_source(
    conn: sqlite3.Connection,
    source_path: str,
    source_sha256: str,
    tia_version: str,
    doc_edition: str,
    line_count: int,
) -> int:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO sources (source_path, source_sha256, imported_at_utc, tia_version, doc_edition, line_count)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_path) DO UPDATE SET
            source_sha256=excluded.source_sha256,
            imported_at_utc=excluded.imported_at_utc,
            tia_version=excluded.tia_version,
            doc_edition=excluded.doc_edition,
            line_count=excluded.line_count
        """,
        (source_path, source_sha256, now, tia_version, doc_edition, line_count),
    )
    row = conn.execute("SELECT id FROM sources WHERE source_path = ?", (source_path,)).fetchone()
    if row is None:
        raise RuntimeError("Failed to create source row")
    return int(row[0])


def clear_source_payload(conn: sqlite3.Connection, source_id: int) -> None:
    conn.execute(
        "DELETE FROM enum_values WHERE parameter_id IN (SELECT id FROM parameters WHERE source_id = ?)",
        (source_id,),
    )
    conn.execute("DELETE FROM parameters WHERE source_id = ?", (source_id,))
    conn.execute("DELETE FROM modules WHERE source_id = ?", (source_id,))
    conn.execute("DELETE FROM sections WHERE source_id = ?", (source_id,))
    conn.execute("DELETE FROM raw_lines WHERE source_id = ?", (source_id,))


def insert_section(conn: sqlite3.Connection, source_id: int, line_no: int, name: str) -> int:
    cur = conn.execute(
        "INSERT INTO sections (source_id, line_no, section_name) VALUES (?, ?, ?)",
        (source_id, line_no, name),
    )
    return int(cur.lastrowid)


def insert_module(
    conn: sqlite3.Connection,
    source_id: int,
    section_id: int | None,
    line_no: int,
    kind: str,
    name: str,
    raw_line: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO modules (source_id, section_id, line_no, module_kind, module_name, raw_line)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_id, section_id, line_no, kind, name, raw_line),
    )
    return int(cur.lastrowid)


def iter_lines(lines: list[str]) -> Iterable[tuple[int, str]]:
    for idx, line in enumerate(lines, start=1):
        yield idx, clean_line(line)


def can_start_parameter(line: str, next_line: str) -> bool:
    if not line or not next_line:
        return False
    if line in STRUCTURAL_TOKENS:
        return False
    if is_noise_line(line):
        return False
    if PAGE_RE.match(line):
        return False
    if MODULE_RE.match(line):
        return False
    if SECTION_RE.match(line) or SECONDARY_SECTION_RE.match(line):
        return False
    if not POTENTIAL_FIELD_RE.match(line):
        return False
    return looks_like_type(next_line)


def parse_parameters(
    conn: sqlite3.Connection,
    source_id: int,
    lines: list[str],
    state: ParseState,
) -> None:
    i = 0
    total = len(lines)
    while i < total:
        line_no = i + 1
        line = clean_line(lines[i])

        section_match = SECTION_RE.match(line)
        if section_match:
            section_name = section_match.group(1).strip()
            state.section_id = insert_section(conn, source_id, line_no, section_name)
            state.module_id = None
            i += 1
            continue

        secondary_match = SECONDARY_SECTION_RE.match(line)
        if secondary_match:
            section_name = f"Openness for {secondary_match.group(1).strip()}"
            state.section_id = insert_section(conn, source_id, line_no, section_name)
            state.module_id = None
            i += 1
            continue

        module_match = MODULE_RE.match(line)
        if module_match:
            kind = module_match.group(1).strip()
            name = module_match.group(2).strip()
            state.module_id = insert_module(
                conn,
                source_id,
                state.section_id,
                line_no,
                kind,
                name,
                line,
            )
            i += 1
            continue

        next_line = clean_line(lines[i + 1]) if i + 1 < total else ""
        if not can_start_parameter(line, next_line):
            i += 1
            continue

        property_name = line
        data_type = next_line
        cursor = i + 2
        label = None
        access_mode = None
        value_hint = None
        enum_buffer: list[tuple[int, str, str | None]] = []
        notes: list[str] = []

        if cursor < total:
            candidate = clean_line(lines[cursor])
            if candidate and not is_noise_line(candidate) and not PAGE_RE.match(candidate):
                label = candidate
                cursor += 1

        if cursor < total:
            candidate = clean_line(lines[cursor])
            if ACCESS_RE.match(candidate):
                access_mode = candidate
                cursor += 1

        if cursor < total:
            candidate = clean_line(lines[cursor])
            if (
                candidate
                and not is_noise_line(candidate)
                and not PAGE_RE.match(candidate)
                and not SECTION_RE.match(candidate)
                and not SECONDARY_SECTION_RE.match(candidate)
                and not MODULE_RE.match(candidate)
            ):
                value_hint = candidate
                cursor += 1

        while cursor < total:
            v_line = clean_line(lines[cursor])
            if (
                not v_line
                or PAGE_RE.match(v_line)
                or SECTION_RE.match(v_line)
                or SECONDARY_SECTION_RE.match(v_line)
                or MODULE_RE.match(v_line)
            ):
                break

            next_after_v = clean_line(lines[cursor + 1]) if cursor + 1 < total else ""

            if can_start_parameter(v_line, next_after_v):
                break

            if not ENUM_VALUE_RE.match(v_line):
                if v_line not in STRUCTURAL_TOKENS:
                    notes.append(v_line)
                cursor += 1
                continue

            enum_desc = None
            if next_after_v and not is_noise_line(next_after_v):
                if not can_start_parameter(next_after_v, clean_line(lines[cursor + 2]) if cursor + 2 < total else ""):
                    enum_desc = next_after_v
                    enum_buffer.append((cursor + 1, v_line, enum_desc))
                    cursor += 2
                    continue

            enum_buffer.append((cursor + 1, v_line, enum_desc))
            cursor += 1

        confidence = 0.4
        if looks_like_type(data_type):
            confidence += 0.3
        if label:
            confidence += 0.2
        if access_mode:
            confidence += 0.1
        confidence = min(confidence, 1.0)

        meta = {
            "enum_count": len(enum_buffer),
            "note_lines": len(notes),
        }
        cur = conn.execute(
            """
            INSERT INTO parameters (
                source_id, section_id, module_id, line_no, property_name, data_type, label,
                access_mode, value_hint, notes, meta_json, parse_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                state.section_id,
                state.module_id,
                line_no,
                property_name,
                data_type,
                label,
                access_mode,
                value_hint,
                "\n".join(notes) if notes else None,
                json.dumps(meta, ensure_ascii=True),
                confidence,
            ),
        )
        parameter_id = int(cur.lastrowid)

        for seq, (enum_line_no, enum_value, enum_desc) in enumerate(enum_buffer, start=1):
            conn.execute(
                """
                INSERT INTO enum_values (parameter_id, seq, enum_value, enum_description, line_no)
                VALUES (?, ?, ?, ?, ?)
                """,
                (parameter_id, seq, enum_value, enum_desc, enum_line_no),
            )

        i = cursor if cursor > i else i + 1


def maybe_insert_raw_lines(
    conn: sqlite3.Connection, source_id: int, lines: list[str], include_raw_lines: bool
) -> None:
    if not include_raw_lines:
        return
    rows = [(source_id, idx, clean_line(line)) for idx, line in enumerate(lines, start=1)]
    conn.executemany(
        "INSERT INTO raw_lines (source_id, line_no, text) VALUES (?, ?, ?)",
        rows,
    )


def build_fts(conn: sqlite3.Connection) -> None:
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS parameters_fts
            USING fts5(property_name, data_type, label, notes, content='parameters', content_rowid='id')
            """
        )
        conn.execute("INSERT INTO parameters_fts(parameters_fts) VALUES('rebuild')")
    except sqlite3.OperationalError:
        # Some sqlite builds omit FTS5; schema still works without it.
        pass


def summarize(conn: sqlite3.Connection, source_id: int) -> dict[str, int]:
    counts = {}
    direct_tables = ("sections", "modules", "parameters", "raw_lines")
    for table in direct_tables:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        counts[table] = int(row[0]) if row else 0

    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM enum_values ev
        JOIN parameters p ON p.id = ev.parameter_id
        WHERE p.source_id = ?
        """,
        (source_id,),
    ).fetchone()
    counts["enum_values"] = int(row[0]) if row else 0
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to converted markdown file")
    parser.add_argument("--db", required=True, help="Path to output SQLite DB")
    parser.add_argument("--tia-version", default="v19")
    parser.add_argument("--doc-edition", default="09/2023")
    parser.add_argument(
        "--no-raw-lines",
        action="store_true",
        help="Skip loading raw_lines table to reduce DB size",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    db_path = Path(args.db)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8", errors="replace")
    lines = raw_text.splitlines()
    source_hash = sha256_of_text(raw_text)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        init_db(conn)
        with conn:
            source_id = upsert_source(
                conn,
                str(input_path.resolve()),
                source_hash,
                args.tia_version,
                args.doc_edition,
                len(lines),
            )
            clear_source_payload(conn, source_id)
            maybe_insert_raw_lines(conn, source_id, lines, not args.no_raw_lines)
            parse_parameters(conn, source_id, lines, ParseState())
            build_fts(conn)

        counts = summarize(conn, source_id)
    finally:
        conn.close()

    print("Catalog build complete")
    print(f"Input: {input_path}")
    print(f"DB:    {db_path}")
    print(f"SHA:   {source_hash}")
    for key in ("sections", "modules", "parameters", "enum_values", "raw_lines"):
        print(f"{key}: {counts.get(key, 0)}")


if __name__ == "__main__":
    main()
