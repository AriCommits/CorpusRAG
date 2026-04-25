# P1: Per-Message Metadata & Live Response Timer

**Time:** 2 hrs  
**Priority:** HIGH  
**Prerequisites:** Foundation phases (A1-A4) recommended first

---

## Goal

Display tags and timing alongside each message. Show live-updating timer during response generation (like Grok/Claude).

---

## Files to Modify

| File | Action |
|------|--------|
| `src/tools/rag/tui.py` | Add MessageMetadata, ResponseTimer, extend ChatMessage |
| `src/tools/rag/agent.py` | Add `chat_with_metadata()` method |

---

## Session 1: Create MessageMetadata Dataclass (20 min)

### Subtasks

- [ ] Add `MessageMetadata` dataclass to tui.py
- [ ] Extend `ChatMessage` to accept metadata

### Session Prompt

```
I'm implementing Plan 8, Task P1 from docs/plans/plan_8/P1-message-metadata.md.

Goal: Create MessageMetadata dataclass and extend ChatMessage.

Please:
1. Read src/tools/rag/tui.py

2. Add this dataclass near the top (after imports):

   from dataclasses import dataclass, field
   from uuid import uuid4
   
   @dataclass
   class MessageMetadata:
       """Metadata associated with a chat message."""
       tags: list[str] = field(default_factory=list)
       tag_prefixes: list[str] = field(default_factory=list)
       generation_time_ms: float = 0.0
       retrieval_time_ms: float = 0.0
       prompt_tokens: int = 0
       completion_tokens: int = 0
       timestamp: str = ""

3. Update ChatMessage.__init__ to accept:
   - metadata: MessageMetadata | None = None
   - message_id: str | None = None
   
   Store as self.metadata = metadata or MessageMetadata()
   Store as self.message_id = message_id or str(uuid4())

4. Update ChatMessage.compose() to show tags as badges if present:
   - After the role prefix, if self.metadata.tags exists, add inline code badges
   - Example: "### Assistant `tag1` `tag2`"

Keep existing functionality working. Show diff before applying.
```

### Verification

```bash
python -c "
from tools.rag.tui import MessageMetadata, ChatMessage
m = MessageMetadata(tags=['Math', 'CS/ML'], generation_time_ms=1500)
c = ChatMessage('assistant', 'Hello', metadata=m)
print(f'Tags: {c.metadata.tags}')
print(f'Time: {c.metadata.generation_time_ms}ms')
"
```

---

## Session 2: Create ResponseTimer Widget (30 min)

### Subtasks

- [ ] Create `ResponseTimer` widget with reactive elapsed time
- [ ] Add start/stop methods
- [ ] Add CSS styling

### Session Prompt

```
I'm implementing Plan 8, Task P1 (Session 2) from docs/plans/plan_8/P1-message-metadata.md.

Goal: Create a live-updating timer widget.

Please add to src/tools/rag/tui.py:

1. Create ResponseTimer class (after ChatMessage):

   from textual.reactive import reactive
   from textual.timer import Timer
   
   class ResponseTimer(Static):
       """Live-updating timer shown during response generation."""
       
       elapsed_ms = reactive(0.0)
       running = reactive(False)
       
       def __init__(self):
           super().__init__(id="response-timer")
           self._timer: Timer | None = None
           self._start_time: float = 0.0
       
       def start(self) -> None:
           import time
           self._start_time = time.perf_counter()
           self.running = True
           self.elapsed_ms = 0
           self._timer = self.set_interval(0.1, self._tick)
       
       def stop(self) -> float:
           if self._timer:
               self._timer.stop()
               self._timer = None
           self.running = False
           return self.elapsed_ms
       
       def _tick(self) -> None:
           import time
           if self.running:
               self.elapsed_ms = (time.perf_counter() - self._start_time) * 1000
       
       def watch_elapsed_ms(self, value: float) -> None:
           if self.running:
               self.update(f"Generating... {value/1000:.1f}s")
           else:
               self.update("")

2. Add CSS for the timer:
   #response-timer {
       height: auto;
       color: $accent;
       text-style: italic;
       padding: 0 0 0 1;
   }

3. Add ResponseTimer to compose() in RAGApp, before the input field.
```

### Verification

```bash
# Start TUI briefly to see timer appears
timeout 3 corpus rag chat --collection test 2>/dev/null || echo "TUI launched"
```

---

## Session 3: Integrate Timer with Response Generation (30 min)

### Subtasks

- [ ] Start timer when user submits
- [ ] Stop timer when response arrives
- [ ] Pass elapsed time to MessageMetadata

### Session Prompt

```
I'm implementing Plan 8, Task P1 (Session 3) from docs/plans/plan_8/P1-message-metadata.md.

Goal: Wire the ResponseTimer into the response generation flow.

Please update src/tools/rag/tui.py:

1. Add helper methods to RAGApp:
   
   def _start_timer(self) -> None:
       self.query_one(ResponseTimer).start()
   
   def _stop_timer(self) -> float:
       return self.query_one(ResponseTimer).stop()

2. Update generate_response() method:
   - At start: self.call_from_thread(self._start_timer)
   - At end (in display callback): elapsed = self._stop_timer()

3. Update display_response() to:
   - Accept elapsed_ms parameter
   - Create MessageMetadata with generation_time_ms=elapsed_ms
   - Pass metadata to ChatMessage

4. Remove the old benchmarker-based timing display (lines ~324-329 that add latency_info)
   - The new timer replaces this
```

---

## Session 4: Add chat_with_metadata to Agent (30 min)

### Subtasks

- [ ] Add method that returns both response and metadata
- [ ] Extract tags from retrieved documents

### Session Prompt

```
I'm implementing Plan 8, Task P1 (Session 4) from docs/plans/plan_8/P1-message-metadata.md.

Goal: Add chat_with_metadata() method to RAGAgent.

Please update src/tools/rag/agent.py:

1. Store retrieved docs for tag extraction:
   - In query() method, after self.retriever.retrieve(), store: self._last_retrieved_docs = documents

2. Add new method chat_with_metadata():
   
   def chat_with_metadata(
       self,
       message: str,
       collection: str,
       session_id: str | None = None,
       where: dict[str, Any] | None = None,
   ) -> tuple[str, dict]:
       """Chat and return response with metadata.
       
       Returns:
           Tuple of (response_text, metadata_dict)
       """
       # Load history
       history = []
       if session_id:
           history = self.session_manager.load_session(session_id)
       
       # Query with timing
       import time
       start = time.perf_counter()
       response = self.query(message, collection, conversation_history=history, where=where)
       query_time = (time.perf_counter() - start) * 1000
       
       # Extract tags from retrieved docs
       tags = set()
       tag_prefixes = set()
       for doc in getattr(self, '_last_retrieved_docs', []):
           doc_tags = doc.metadata.get('tags', [])
           doc_prefixes = doc.metadata.get('tag_prefixes', [])
           if isinstance(doc_tags, list):
               tags.update(doc_tags)
           if isinstance(doc_prefixes, list):
               tag_prefixes.update(doc_prefixes)
       
       metadata = {
           'tags': sorted(tags),
           'tag_prefixes': sorted(tag_prefixes),
           'retrieval_time_ms': query_time,
       }
       
       # Save session
       if session_id:
           history.append({"role": "user", "content": message})
           history.append({"role": "assistant", "content": response})
           self.session_manager.save_session(session_id, history)
       
       return response, metadata
```

---

## Done When

- [ ] `MessageMetadata` dataclass exists
- [ ] `ChatMessage` displays tags as badges
- [ ] `ResponseTimer` counts up during generation
- [ ] Timer stops and shows final time when response arrives
- [ ] Tags from retrieved docs shown on messages
- [ ] Committed: `Plan 8 P1: Add message metadata and live response timer`
