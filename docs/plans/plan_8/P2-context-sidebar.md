# P2: Context Window Visualization Sidebar

**Time:** 2-3 hrs  
**Priority:** HIGH  
**Prerequisites:** P1 (needs MessageMetadata)

---

## Goal

Add toggleable right sidebar showing context window usage as a vertical stack. Each message block sized proportionally to token count.

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/utils/tokens.py` | **NEW** — Token estimation utilities |
| `src/tools/rag/tui_context.py` | **NEW** — Context sidebar widget |
| `src/tools/rag/tui.py` | Integrate sidebar, add F3 keybinding |

---

## Session 1: Create Token Estimation Utilities (30 min)

### Subtasks

- [ ] Create `src/utils/tokens.py`
- [ ] Implement `estimate_tokens()` with tiktoken + fallback
- [ ] Implement `format_tokens()` for display

### Session Prompt

```
I'm implementing Plan 8, Task P2 from docs/plans/plan_8/P2-context-sidebar.md.

Goal: Create token estimation utilities.

Please create src/utils/tokens.py:

"""Token counting utilities for context window visualization."""

from functools import lru_cache

@lru_cache(maxsize=1)
def _get_tokenizer():
    """Get cached tokenizer, with fallback."""
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except ImportError:
        return None

def estimate_tokens(text: str) -> int:
    """Estimate token count for text.
    
    Uses tiktoken when available, falls back to ~4 chars per token.
    """
    enc = _get_tokenizer()
    if enc:
        return len(enc.encode(text))
    # Fallback heuristic
    return max(1, len(text) // 4)

def format_tokens(count: int) -> str:
    """Format token count for display (e.g., 1500 -> '1.5k')."""
    if count >= 1000:
        return f"{count/1000:.1f}k"
    return str(count)

Also add estimate_tokens and format_tokens to src/utils/__init__.py exports.
```

### Verification

```bash
python -c "
from utils.tokens import estimate_tokens, format_tokens
text = 'Hello world, this is a test message.'
tokens = estimate_tokens(text)
print(f'Tokens: {tokens} ({format_tokens(tokens)})')
assert tokens > 0
print('PASS')
"
```

---

## Session 2: Create ContextSidebar Widget (45 min)

### Subtasks

- [ ] Create `src/tools/rag/tui_context.py`
- [ ] Implement `ContextBlock` widget for each message
- [ ] Implement `ContextSidebar` container with progress bar

### Session Prompt

```
I'm implementing Plan 8, Task P2 (Session 2) from docs/plans/plan_8/P2-context-sidebar.md.

Goal: Create the context visualization sidebar widget.

Please create src/tools/rag/tui_context.py:

"""Context window visualization sidebar."""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static, Label, ProgressBar
from textual.reactive import reactive

from utils.tokens import estimate_tokens, format_tokens


class ContextBlock(Static):
    """A single message block in the context visualization."""
    
    DEFAULT_CSS = """
    ContextBlock {
        height: auto;
        min-height: 3;
        margin: 0 0 1 0;
        padding: 0 1;
    }
    ContextBlock.user { background: $primary-darken-3; }
    ContextBlock.assistant { background: $secondary-darken-3; }
    .block-stats { color: $text-muted; }
    """
    
    def __init__(self, message_id: str, role: str, preview: str, 
                 tokens: int, percentage: float, time_ms: float):
        super().__init__()
        self.message_id = message_id
        self.role = role
        self.preview = preview[:40] + "..." if len(preview) > 40 else preview
        self.tokens = tokens
        self.percentage = percentage
        self.time_ms = time_ms
        self.add_class(role)
    
    def compose(self) -> ComposeResult:
        yield Label(f"{self.role.title()}: {self.preview}")
        stats = f"{format_tokens(self.tokens)} ({self.percentage:.1f}%)"
        if self.time_ms > 0:
            stats += f" | {self.time_ms/1000:.1f}s"
        yield Label(stats, classes="block-stats")


class ContextSidebar(Vertical):
    """Sidebar showing context window visualization."""
    
    DEFAULT_CSS = """
    ContextSidebar {
        width: 35;
        background: $surface;
        border-left: tall $primary;
        display: none;
    }
    ContextSidebar.visible { display: block; }
    #context-header {
        padding: 1;
        text-style: bold;
        color: $accent;
    }
    #context-total { padding: 0 1; color: $text-muted; }
    #context-bar { margin: 1; }
    #context-blocks { height: 1fr; }
    """
    
    total_tokens = reactive(0)
    max_tokens = reactive(8192)
    
    def __init__(self):
        super().__init__(id="context-sidebar")
    
    def compose(self) -> ComposeResult:
        yield Label("Context Window", id="context-header")
        yield Label("0 / 8192 tokens", id="context-total")
        yield ProgressBar(total=100, show_eta=False, id="context-bar")
        yield VerticalScroll(id="context-blocks")
    
    def toggle_visibility(self) -> None:
        self.toggle_class("visible")
    
    def update_blocks(self, messages: list[dict]) -> None:
        """Rebuild context blocks from message list."""
        container = self.query_one("#context-blocks", VerticalScroll)
        
        # Clear existing
        for child in list(container.children):
            child.remove()
        
        # Calculate tokens
        total = 0
        block_data = []
        for msg in messages:
            tokens = estimate_tokens(msg.get("content", ""))
            total += tokens
            block_data.append({
                "id": msg.get("id", str(hash(msg.get("content", "")))),
                "role": msg.get("role", "user"),
                "preview": msg.get("content", "")[:50],
                "tokens": tokens,
                "time_ms": msg.get("generation_time_ms", 0),
            })
        
        # Mount blocks with percentages
        self.total_tokens = total
        for data in block_data:
            pct = (data["tokens"] / total * 100) if total > 0 else 0
            container.mount(ContextBlock(
                data["id"], data["role"], data["preview"],
                data["tokens"], pct, data["time_ms"]
            ))
        
        # Update totals
        self.query_one("#context-total", Label).update(
            f"{format_tokens(total)} / {format_tokens(self.max_tokens)} tokens"
        )
        usage_pct = min(100, (total / self.max_tokens * 100)) if self.max_tokens else 0
        self.query_one("#context-bar", ProgressBar).update(progress=usage_pct)
```

---

## Session 3: Integrate Sidebar into TUI (30 min)

### Subtasks

- [ ] Add ContextSidebar to RAGApp layout
- [ ] Add F3 keybinding to toggle
- [ ] Add sync method to update sidebar from chat

### Session Prompt

```
I'm implementing Plan 8, Task P2 (Session 3) from docs/plans/plan_8/P2-context-sidebar.md.

Goal: Integrate ContextSidebar into the main TUI.

Please update src/tools/rag/tui.py:

1. Import at top:
   from .tui_context import ContextSidebar

2. Add to BINDINGS:
   ("f3", "toggle_context", "Context [F3]"),

3. Update compose() - add ContextSidebar after main-chat:
   with Horizontal():
       # ... existing sidebar ...
       with Vertical(id="main-chat"):
           # ... existing chat ...
       yield ContextSidebar()  # NEW - right sidebar

4. Add action method:
   def action_toggle_context(self) -> None:
       self.query_one(ContextSidebar).toggle_visibility()

5. Add sync method:
   def _sync_context_sidebar(self) -> None:
       chat_log = self.query_one("#chat-log", VerticalScroll)
       messages = []
       for child in chat_log.children:
           if isinstance(child, ChatMessage):
               messages.append({
                   "id": child.message_id,
                   "role": child.role,
                   "content": child.content,
                   "generation_time_ms": child.metadata.generation_time_ms,
               })
       self.query_one(ContextSidebar).update_blocks(messages)

6. Call _sync_context_sidebar() at the end of display_response()
```

---

## Done When

- [ ] `src/utils/tokens.py` exists with working estimation
- [ ] `src/tools/rag/tui_context.py` exists
- [ ] F3 toggles context sidebar visibility
- [ ] Sidebar shows all messages with token counts
- [ ] Progress bar shows total context usage
- [ ] Committed: `Plan 8 P2: Add context window visualization sidebar`
