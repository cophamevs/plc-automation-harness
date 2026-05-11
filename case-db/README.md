# Case Database — How to Use

## Purpose
The case database provides annotated input→output examples for **few-shot learning**.
Before writing new SCL code, search this database for similar cases. Reading 2-3
related cases before coding significantly improves output quality.

## How Agents Should Use This

1. **Read `_index.md`** to see all available cases with tags
2. **Search by tags** — match the user's requirements to case tags
3. **Read 2-3 similar cases** — focus on:
   - Block structure (what blocks were needed)
   - SCL patterns used (state machine? timer? communication?)
   - Key decisions (why certain choices were made)
4. **Adapt, don't copy** — use cases as reference, not boilerplate

## Case Format

### Success Cases (`success/`)
Each case contains:
- **Requirements**: what the program should do
- **Block Structure**: table of blocks with types and purposes
- **SCL Code**: complete, compilable source (all blocks in correct order)
- **MCP Commands**: exact tool calls to deploy
- **Key Decisions**: why certain design choices were made
- **Test Procedure**: S7ReadVariable addresses to verify

### Error Cases (`errors/`)
Each case contains:
- **Error Message**: exact compiler or runtime error
- **Bad Code**: minimal code that produces the error
- **Good Code**: corrected version with fix applied
- **Why**: root cause explanation
- **Detection**: how to recognize this error
- **Related**: link to knowledge file explaining the rule

## Adding New Cases
1. Copy the appropriate `_template.md`
2. Fill in all sections completely
3. Add an entry to `case-db/_index.md`
4. Number sequentially: `011-`, `012-`, etc.
