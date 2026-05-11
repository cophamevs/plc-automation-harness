# Contributing to PLC Automation Harness

## Adding New Content

### 1. New Pattern
```bash
cp knowledge/patterns/_template.md knowledge/patterns/my-pattern.md
# Edit my-pattern.md with complete content
# Add entry to knowledge/patterns/_index.md
```

### 2. New Industry Example
```bash
cp knowledge/industry/_template.md knowledge/industry/my-example.md
# Edit with Requirements, Block Structure, SCL Code, Test Procedure
# Add entry to knowledge/industry/_index.md
```

### 3. New Success Case
```bash
cp case-db/success/_template.md case-db/success/011-my-case.md
# Edit with Requirements, SCL Code, MCP Commands, Test Procedure
# Add entry to case-db/_index.md
```

### 4. New Error Case
```bash
cp case-db/errors/_template.md case-db/errors/011-my-error.md
# Edit with Error Message, Bad Code, Good Code, Why
# Add entry to case-db/_index.md
```

### 5. New Workflow
```bash
cp workflows/_template.md workflows/my-workflow.md
# Edit with Prerequisites, Steps (exact MCP tool calls), Troubleshooting
# Add entry to workflows/_index.md
```

### 6. New Agent
Create `.claude/agents/my-agent.md` with agent instructions.
Add `/my-agent` to the Agents section in `CLAUDE.md`.

### 7. New Library Reference
```bash
cp knowledge/libraries/_template.md knowledge/libraries/my-library.md
# Add entry to knowledge/libraries/_index.md
```

## Quality Checklist

Before submitting:
- [ ] All SCL code compiles (tested with GenerateBlocksFromSource)
- [ ] _index.md updated with correct tags and CPU compatibility
- [ ] File follows the _template.md structure for its directory
- [ ] No placeholders ("TBD", "TODO", "implement later")
- [ ] S7-1200 compatibility noted (Both/1500/1200)

## SCL Code Quality
- Every FB has Error (BOOL) + ErrorID (INT) outputs
- Explicit type conversions (INT_TO_REAL, etc.)
- Timers in VAR (static), not VAR_TEMP
- STRING with length: STRING[80]
- VERSION declared on every block
- CASE has ELSE branch
