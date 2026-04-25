# Plan 8: Parallel Work Assignments

## File Dependency Matrix

```
                    │ A1  A2  A3  A4  P1  P2  P3  P4  P5  P6
────────────────────┼──────────────────────────────────────
flashcards/         │ ██                                  
summaries/          │ ██                                  
quizzes/            │ ██                                  
config/base.py      │     ██                              
llm/backend.py      │     ██              ██              
configs/base.yaml   │     ██                              
mcp_server/         │         ██                          
orchestrations/     │         ██                          
utils/manage_*.py   │             ██                      
pyproject.toml      │             ██                      
config/schema.py    │             ██                      
utils/tokens.py     │                 ██                  
rag/tui.py          │                 ██  ██  ██      ██  
rag/tui_context.py  │                     ██  ██          
rag/agent.py        │                 ██      ██  ██      
rag/session.py      │                         ██          
rag/slash_commands  │                         ██          
tests/              │                                 ██  
```

Legend: ██ = Task modifies this file

---

## Parallel Execution Plan

### Wave 1 (Day 1) - 3 Agents, No Conflicts

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    AGENT A      │  │    AGENT B      │  │    AGENT C      │
│                 │  │                 │  │                 │
│  A1: Fix        │  │  A3: Fix MCP    │  │  P2.1: Create   │
│  Generators     │  │  server attrs   │  │  utils/tokens.py│
│                 │  │                 │  │                 │
│  Files:         │  │  Files:         │  │  Files:         │
│  - flashcards/  │  │  - mcp_server/  │  │  - utils/tokens │
│  - summaries/   │  │  - orchestrat/  │  │    (NEW file)   │
│  - quizzes/     │  │                 │  │                 │
│                 │  │  Time: 30min    │  │  Time: 30min    │
│  Time: 2-3hr    │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Wave 2 (Day 1-2) - 2 Agents

```
┌─────────────────┐  ┌─────────────────┐
│    AGENT A      │  │    AGENT B      │
│                 │  │                 │
│  A2: Rate       │  │  A4: Dead code  │
│  Limiting       │  │  removal        │
│                 │  │                 │
│  Files:         │  │  Files:         │
│  - config/base  │  │  - pyproject    │
│  - llm/backend  │  │  - schema.py    │
│  - base.yaml    │  │  - manage_*.py  │
│                 │  │                 │
│  Time: 1-2hr    │  │  Time: 1hr      │
└─────────────────┘  └─────────────────┘
```

### Wave 3 (Day 2-3) - Serial with Checkpoints

TUI work has high file contention (tui.py touched by P1, P2, P3, P5).
**Run serially with merge points:**

```
P1 (metadata) ──commit──→ P2 (sidebar) ──commit──→ P3 (selective)
     │                         │
     └── P2.1 done in Wave 1 ──┘
```

### Wave 4 (Day 3) - 2 Agents

```
┌─────────────────┐  ┌─────────────────┐
│    AGENT A      │  │    AGENT B      │
│                 │  │                 │
│  P4: Token      │  │  P5: Security   │
│  counting       │  │  hardening      │
│                 │  │                 │
│  Files:         │  │  Files:         │
│  - llm/backend  │  │  - rag/tui.py   │
│  - rag/agent    │  │  - rag/session  │
│                 │  │                 │
│  Time: 1hr      │  │  Time: 1hr      │
└─────────────────┘  └─────────────────┘
        │                    │
        └────────────────────┘
                 ↓
              P6: Tests (single agent, needs all code)
```

---

## Heuristics for Splitting Work

### 1. File-Level Independence
```
grep -l "def function_name" src/**/*.py
```
If two tasks modify different files → safe to parallelize.

### 2. Import-Level Independence
```
# Check what a file imports
grep "^from\|^import" src/tools/rag/tui.py

# Check what imports a file
grep -r "from tools.rag.tui import" src/
```
If A imports from B, A must wait for B.

### 3. Test-Level Independence
If tests pass independently, code is independent.

### 4. The "Merge Conflict" Heuristic
If you'd expect a git merge conflict → don't parallelize.

---

## Conflict Resolution Protocol

When agents work in parallel:

1. **Before starting:** `git pull && git checkout -b agent-a-task`
2. **After completing:** Don't merge directly
3. **Integration agent:** Reviews both branches, resolves conflicts, merges

```bash
# Integration workflow
git checkout main
git merge agent-a-task --no-commit
git merge agent-b-task --no-commit
# Resolve any conflicts
pytest tests/
git commit -m "Merge Wave 1: A1, A3, P2.1"
```

---

## Quick Reference: Which Tasks Conflict?

| Task | Conflicts With | Safe With |
|------|----------------|-----------|
| A1 | - | A2, A3, A4, P2.1 |
| A2 | P4 (llm/backend) | A1, A3, A4, P1, P2, P3 |
| A3 | - | Everything |
| A4 | - | A1, A2, A3 |
| P1 | P2, P3, P5 (tui.py) | A1, A2, A3, A4, P4 |
| P2 | P1, P3 (tui.py) | A*, P4 |
| P3 | P1, P2, P5 (tui.py) | A*, P4 |
| P4 | A2 (backend) | P1, P2, P3 |
| P5 | P1, P2, P3 (tui.py) | A*, P4 |
| P6 | All (needs final code) | None |

---

## Recommended Agent Assignments

**If you have 2 agents:**
```
Agent 1: A1 → A2 → P1 → P2 → P3
Agent 2: A3 → A4 → P2.1 → P4 → P5
Final:   Both → P6
```

**If you have 3 agents:**
```
Agent 1: A1 → P1 → P3
Agent 2: A2 → A4 → P4
Agent 3: A3 → P2 → P5
Final:   All → P6
```
