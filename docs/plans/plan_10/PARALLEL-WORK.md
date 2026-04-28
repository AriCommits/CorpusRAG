# Plan 10: Parallel Work Assignments

## File Dependency Matrix

```
                                    │ T1   T2   T3   T4
────────────────────────────────────┼─────────────────────
src/setup_wizard.py                 │ ██   ██   ██
tests/unit/test_setup_wizard_config │                ██
```

Legend: ██ = Task modifies this file

**Key insight:** T1, T2, and T3 all modify the same file (`setup_wizard.py`). This plan cannot be parallelized. It must run as a single serial sprint.

---

## Wave Execution Plan

```
┌──────────────────────────────────────────────────────┐
│                    AGENT A (Serial)                  │
│                                                      │
│  T1: WizardConfig ──→ T2: BackendScreen ──→ T3: save_config ──→ T4: Tests │
│  (15 min)              (30 min)              (30 min)           (30 min)   │
│                                                      │
│  Total: ~1.75 hrs                                    │
└──────────────────────────────────────────────────────┘
```

There is only one wave. All tasks are serial because they modify the same file.

---

## Conflict Table

| Task | Conflicts With | Safe to run with |
|------|----------------|------------------|
| T1 | T2, T3 (setup_wizard.py) | T4 (different file, but T4 depends on T1+T3) |
| T2 | T1, T3 (setup_wizard.py) | T4 (different file, but T4 depends on T1+T3) |
| T3 | T1, T2 (setup_wizard.py) | T4 (different file, but T4 depends on T1+T3) |
| T4 | None (new file) | All (but logically depends on T1+T3) |

---

## Integration Workflow

Since this is a single-agent serial plan, no merge workflow is needed. Commit after each task:

```bash
# T1
git add src/setup_wizard.py
git commit -m "Plan 10 T1: Expand WizardConfig with full config fields"

# T2
git add src/setup_wizard.py
git commit -m "Plan 10 T2: Update BackendScreen for endpoint/api_key"

# T3
git add src/setup_wizard.py
git commit -m "Plan 10 T3: Rewrite save_config for complete config generation"

# T4
git add tests/unit/test_setup_wizard_config.py
git commit -m "Plan 10 T4: Add tests for setup wizard config generation"
```

---

## Recommended Agent Assignments

**Any number of agents: 1 agent**

This plan modifies a single file across 3 of 4 tasks. There is no way to split it across multiple agents without merge conflicts.

```
Agent A: T1 → T2 → T3 → T4
Total:   ~1.75 hrs
```

---

## Total Estimated Time

| Mode | Wall Clock | Agent Hours |
|------|-----------|-------------|
| 1 agent | ~1.75 hrs | 1.75 hrs |
| 2+ agents | ~1.75 hrs (no speedup) | 1.75 hrs |
