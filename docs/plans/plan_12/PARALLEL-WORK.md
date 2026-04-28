# Plan 12: Parallel Work Assignments

## File Dependency Matrix

```
                         │ T1   T2   T3
─────────────────────────┼───────────────
pyproject.toml           │ ██
.docker/Dockerfile       │ ██
src/setup_wizard.py      │      ██
tests/unit/test_docker*  │           ██
tests/unit/test_setup*   │           ██
```

**Key insight:** T1 (pyproject + Dockerfile) and T2 (setup_wizard.py) touch completely different files. Perfect parallelism for Wave 1.

## Wave Execution Plan

```
Wave 1 (2 agents, PARALLEL):

┌──────────────────┐  ┌──────────────────┐
│    AGENT A       │  │    AGENT B       │
│                  │  │                  │
│  T1: server      │  │  T2: wizard      │
│  extra +         │  │  Docker compose  │
│  slim Dockerfile │  │  generation      │
│                  │  │                  │
│  Files:          │  │  Files:          │
│  - pyproject.toml│  │  - setup_wizard  │
│  - Dockerfile    │  │                  │
│                  │  │                  │
│  Time: 45 min    │  │  Time: 45 min    │
└──────────────────┘  └──────────────────┘
         │                     │
         └─────────────────────┘
                    │
               git merge
                    │
                    ▼

Wave 2 (1 agent, SERIAL):

┌──────────────────┐
│    AGENT A       │
│                  │
│  T3: Tests       │
│                  │
│  Time: 30 min    │
└──────────────────┘
```

## Conflict Table

| Task | Conflicts With | Safe With |
|------|----------------|-----------|
| T1 | — | T2 (different files) |
| T2 | — | T1 (different files) |
| T3 | — | None (needs T1+T2 done) |

## Recommended Agent Assignments

**2 agents:**
```
Agent A: T1 → T3
Agent B: T2
Total: ~1.25 hrs wall clock
```

**1 agent:**
```
T1 → T2 → T3
Total: ~2 hrs
```
