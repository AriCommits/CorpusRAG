# TUI and Persistent Chat Plan

## Objective
Transition the RAG tool from a basic print/input command-line interface to a rich Terminal User Interface (TUI) and implement persistent conversational memory across sessions. The architecture must strictly separate the presentation layer from the core logic so that a GUI (e.g., a web app) can be implemented later without rewriting the underlying mechanics.

## Proposed Framework: Textual
To avoid getting locked into a simple text-formatter like `rich`, we will use **Textual** (a framework built *by* the creators of `rich`). 
- **Why Textual?** It is a comprehensive, event-driven TUI framework (similar to React, but for the terminal). It provides ready-to-use widgets like Inputs, Scrollable Containers, Sidebars, and native Markdown renderers.
- **Future-Proofing:** By designing the TUI as just another "client," the core `RAGAgent` remains completely independent. If you want a GUI later, the `RAGAgent` will still just take text and history, and return text and sources, requiring zero changes to the backend.

## Implementation Steps

### Phase 1: Persistent Sessions (Core Logic)
1. **Session Storage:** Create a `SessionManager` (e.g., in `src/tools/rag/session.py`) that saves and loads conversation histories as JSON files in a local `.sessions/` directory.
2. **Agent Update:** Refactor `RAGAgent.chat` to properly accept, append to, and return structured conversation history (e.g., `[{"role": "user", "content": "..."}, ...]`).
3. **Context Window Management:** Implement a sliding window in the `RAGAgent` to retain only the last *N* messages (or a token-limit based truncation) when feeding history to the LLM, preventing context overflow during long chats.

### Phase 2: Building the TUI (Presentation Layer)
1. **App Structure:** Create `src/tools/rag/tui.py` to house the Textual application (`class RAGApp(App):`).
2. **Layout Design:**
   - **Sidebar (Left):** A list of saved sessions, allowing you to click and resume a previous chain of conversation.
   - **Main Chat Area:** A scrollable log displaying the chat history, with beautifully rendered Markdown for the LLM's responses and expandable sections for "Sources Retrieved."
   - **Input Bar (Bottom):** A text input field for typing queries.
3. **Asynchronous Execution:** Use Textual's `@work` decorators to run the `RAGAgent` queries in a background thread. This ensures the UI remains responsive (and can show a loading animation) while the LLM generates the response.

### Phase 3: CLI Integration
Update `src/tools/rag/cli.py` to add a new command: `python -m tools.rag.cli ui`. This will launch the Textual application, while leaving the existing headless `query` and `chat` commands intact for scripting or quick one-off uses.

## Alternatives Considered
- **Prompt Toolkit:** A solid TUI library, but Textual offers superior native Markdown rendering and a much more modern, CSS-like styling approach.
- **Pure Rich (while loop):** Using `rich` inside our current `while True` loop would make the text prettier, but it wouldn't allow for fixed UI elements like a persistent sidebar, scrollable chat history, or a static input bar at the bottom. Textual solves this.