# PLC Automation Harness — Evaluation & Improvement Roadmap

**Date:** 2026-05-11
**Type:** Comprehensive audit + improvement roadmap
**Status:** Roadmap implemented — all P1 and P2 items complete

---

## Evaluation Summary

5-layer audit of the PLC Automation Harness, evaluating completeness, quality,
gaps, usability, and extensibility. All immediate fixes have been applied in
commit `17e09c7`.

### Scores

| Layer | Before | After Audit | After Roadmap | Description |
|-------|--------|-------------|---------------|-------------|
| 1. Foundation | 4.0 | 4.5 | 4.5 | CLAUDE.md, rules, settings |
| 2. Knowledge | 3.5 | 4.0 | 4.8 | References, patterns, industry (8), cases (25), libraries (2) |
| 3. Workflows | 4.0 | 4.5 | 5.0 | 7 skills (added tag-management, project-backup) |
| 4. Agents | 3.5 | 4.5 | 4.5 | 4 specialized agents |
| 5. DX | 4.0 | 4.5 | 4.7 | Docs, extensibility, onboarding |
| **Overall** | **3.8** | **4.4** | **4.7** | |

---

## Fixes Applied (commit 17e09c7)

### Layer 1: Foundation
- Removed hardcoded "102 tools" count across 6 files (brittle if MCP server changes)
- Expanded safety rule: added `PlcSimStop` and `PlcSimDeleteInstance`
- Added 2 mandatory SCL rules: Error/ErrorID on every FB, block name prefixes MUST
- Strengthened naming convention table language

### Layer 2: Knowledge
- Fixed 9 broken cross-references across all 10 error case files (23 instances)
- Updated libraries/_index.md with candidate list (OSCAT, LGF, LSim)
- Added 4 planned industry examples to index (valve, multi-plc, HMI, profinet)
- Added 5 planned case studies to index (3 advanced success, 2 advanced error)

### Layer 3: Workflows
- Consolidated workflows/ as redirects to skills/ (eliminated duplication)
- Added Step 0 to scl-inject: cleanup existing blocks before re-injection
- Added backup step (Step 1b) to modify-program skill
- Updated architecture.md to reflect skills as single source of truth

### Layer 4: Agents
- Added frontmatter to all 4 agents (description, tools, when_to_use)
- Clarified scope: developer writes new code (1 fix max), debugger does iterative repair
- Added severity weighting to reviewer: 30 items tagged CRITICAL/MAJOR/MINOR
- Added handoff section to architect: how to transition to developer + reviewer

### Layer 5: DX
- Created docs/cheat-sheet.md (one-page quick reference)
- Updated CONTRIBUTING.md: agent frontmatter requirements, workflow consolidation
- Added agent pipeline diagram to getting-started.md
- Deprecated prompts/ with pointers to authoritative sources (rules, agents, skills)
- Updated README structure table

---

## Remaining Roadmap

### Priority 1: Missing Content (High Impact)

These are gaps that will improve Claude's code generation quality directly.

#### P1.1 — Create 4 industry examples
- `knowledge/industry/valve-control.md` — on/off and modulating valve with feedback
- `knowledge/industry/multi-plc-comm.md` — S7 communication between PLCs (PUT/GET, I-Device)
- `knowledge/industry/hmi-interface.md` — HMI data exchange patterns
- `knowledge/industry/profinet-diagnostics.md` — PROFINET device diagnostics

**Effort:** ~2 hours each (research + SCL code + test procedure)
**Impact:** Covers 4 of the most common real-world use cases currently missing

#### P1.2 — Create 5 advanced case studies
Success cases:
- `case-db/success/011-multi-plc-comm.md` — S7 communication with handshake
- `case-db/success/012-multi-fb-system.md` — Complex system with error propagation
- `case-db/success/013-valve-sequence.md` — Valve sequencing with interlocks

Error cases:
- `case-db/errors/011-comm-timeout.md` — PUT/GET timeout not handled
- `case-db/errors/012-db-size-exceeded.md` — S7-1200 16KB DB limit

**Effort:** ~1 hour each
**Impact:** Fills the Advanced complexity gap (currently only 1 of 10 success cases is Advanced)

#### P1.3 — Create library references
- `knowledge/libraries/lgf.md` — Siemens Library of General Functions
- `knowledge/libraries/oscat.md` — OSCAT Basic library

**Effort:** ~3 hours each (catalog key FBs, usage patterns, version compatibility)
**Impact:** LGF is shipped with TIA Portal — most projects should use it

### Priority 2: New Skills/Agents (Medium Impact)

#### P2.1 — Tag management skill
10 MCP tools for tags exist but no skill guides their use. Create:
- `.claude/skills/tag-management/SKILL.md`
- Steps: create tag table, add tags, export/import, bulk operations

**Effort:** ~1 hour
**Impact:** Tag management is a common workflow currently undocumented

#### P2.2 — Project comparison/backup skill
Leverage `CompareToOnline`, `SaveAsProject` for version management.

**Effort:** ~1 hour
**Impact:** Safety improvement for modification workflows

### Priority 3: Quality Polish (Lower Impact)

#### P3.1 — End-to-end scenario testing
Run the 5 skills against a real TIA Portal + PLCSim setup to verify:
- All MCP tool calls work with current tiaportal-mcp version
- Expected responses match actual responses
- Troubleshooting tables cover real failure modes

**Prerequisite:** TIA Portal V19/V20 + PLCSim Advanced installed and running
**Effort:** ~4 hours
**Impact:** Validates everything works in practice (currently untested)

#### P3.2 — Remove or consolidate prompts/ directory
The 3 prompt files now have deprecation notes. Options:
- A) Delete them entirely (content lives in rules and agents)
- B) Keep as-is with deprecation notes (backward compat)
- Recommendation: **B** for now, **A** after confirming no external references

#### P3.3 — Settings.json portability
The hardcoded path in settings.json (`E:\Software_Siemens\...`) is documented
but still annoying for new users. Options:
- A) Use relative path if tiaportal-mcp supports it
- B) Add a setup script that auto-detects the path
- C) Keep as-is with documentation (current)
- Recommendation: **C** until tiaportal-mcp supports relative paths

---

## Implementation Order

```
Week 1:  P1.1 (4 industry examples)
Week 2:  P1.2 (5 case studies) + P2.1 (tag skill)
Week 3:  P1.3 (library refs) + P2.2 (backup skill)
Week 4:  P3.1 (end-to-end testing with real TIA Portal)
```

Each deliverable follows: write content → update _index.md → test compile (if SCL) → commit.
