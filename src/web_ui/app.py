"""CorpusRAG Web Application Entry Point.

This module provides a Streamlit-based web interface for CorpusRAG.
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Ensure src is in python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from config.base import BaseConfig
from config.loader import load_config


def init_session_state():
    """Initialize Streamlit session state."""
    if "config" not in st.session_state:
        config_path = Path("configs/base.yaml")
        if not config_path.parent.exists():
            config_path.parent.mkdir(exist_ok=True, parents=True)

        try:
            st.session_state.config = load_config(config_path, config_class=BaseConfig)
        except Exception as e:
            st.warning(f"Failed to load config, starting with defaults: {e}")
            st.session_state.config = BaseConfig()


def page_settings():
    """Settings page."""
    st.header("⚙️ Configuration")

    config: BaseConfig = st.session_state.config

    st.markdown("Use this panel to configure your AI providers and application settings.")

    with st.expander("🤖 LLM Backend Settings", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            backend = st.selectbox(
                "Backend Provider",
                ["ollama", "openai", "anthropic"],
                index=["ollama", "openai", "anthropic"].index(config.llm.backend)
                if config.llm.backend in ["ollama", "openai", "anthropic"]
                else 0,
            )

            # Detect if the user changed the backend provider to reset dependent fields
            is_new_backend = backend != config.llm.backend

            # Primary model blanked out if backend changes
            default_model = "" if is_new_backend else config.llm.model
            model = st.text_input("Primary Model", value=default_model)

        with col2:
            if is_new_backend:
                if backend == "ollama":
                    default_endpoint = "http://localhost:11434"
                elif backend == "openai":
                    default_endpoint = "https://api.openai.com/v1"
                else:
                    default_endpoint = ""
            else:
                default_endpoint = config.llm.endpoint

            endpoint = st.text_input(
                "Endpoint (e.g., http://localhost:11434)", value=default_endpoint
            )
            api_key = st.text_input(
                "API Key (leave blank if local)",
                value="" if is_new_backend else (config.llm.api_key or ""),
                type="password",
            )

        # Slider limited to 0 to 1
        temperature = st.slider(
            "Temperature", 0.0, 1.0, min(1.0, float(config.llm.temperature)), 0.1
        )

    with st.expander("📚 Database Settings"):
        db_mode = st.radio(
            "ChromaDB Mode",
            ["persistent (Local File/SQLite)", "http (Docker)"],
            index=0 if config.database.mode == "persistent" else 1,
        )
        persist_dir = st.text_input(
            "Persist Directory", value=str(config.database.persist_directory)
        )

    with st.expander("📁 Paths Settings"):
        scratch_dir = st.text_input("Scratch Directory", value=str(config.paths.scratch_dir))
        output_dir = st.text_input("Output Directory", value=str(config.paths.output_dir))

    if st.button("Save Configuration", type="primary"):
        # Update session state config
        config.llm.backend = backend
        config.llm.model = model
        config.llm.endpoint = endpoint
        config.llm.api_key = api_key if api_key.strip() else None
        config.llm.temperature = temperature

        config.database.mode = "persistent" if "persistent" in db_mode else "http"
        config.database.persist_directory = Path(persist_dir)
        config.paths.scratch_dir = Path(scratch_dir)
        config.paths.output_dir = Path(output_dir)

        try:
            config.save_to_yaml(Path("configs/base.yaml"))
            st.success("Configuration saved successfully!")
            st.rerun()  # Refresh the page state to lock in changes
        except Exception as e:
            st.error(f"Failed to save configuration: {e}")


def get_sessions_dir():
    d = Path(".corpus_sessions")
    d.mkdir(exist_ok=True)
    return d


def load_all_sessions():
    sessions = []
    for f in get_sessions_dir().glob("*.json"):
        try:
            with open(f, "r") as file:
                sessions.append(json.load(file))
        except Exception:
            pass
    sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return sessions


def save_session(session_data):
    sid = session_data["session_id"]
    with open(get_sessions_dir() / f"{sid}.json", "w") as f:
        json.dump(session_data, f)


def page_chat():
    """Chat and Interaction page."""
    st.header("💬 Chat & Query")

    config = st.session_state.config

    # Check if Ollama is running
    if config.llm.backend == "ollama":
        import urllib.request
        import urllib.error

        try:
            # Simple GET request to root endpoint which returns "Ollama is running"
            req = urllib.request.Request(config.llm.endpoint)
            urllib.request.urlopen(req, timeout=0.5)
        except Exception:
            st.warning(
                f"⚠️ **Ollama does not appear to be running!** \n\nCorpusRAG is configured to use Ollama at `{config.llm.endpoint}`. Please make sure you have [downloaded Ollama](https://ollama.com) and it is currently running on your machine."
            )

    collections = []
    try:
        from db.chroma import ChromaDBBackend

        db = ChromaDBBackend(config.database)
        collections = db.list_collections()
    except Exception as e:
        db = None
        st.error(f"Database connection failed. RAG features will be disabled. Error: {e}")

    collection_opts = ["No Collection (Direct Chat)"] + collections

    # Sidebar for Sessions
    st.sidebar.markdown("---")
    st.sidebar.subheader("Chat Sessions")

    all_sessions = load_all_sessions()

    if st.sidebar.button("➕ New Chat"):
        new_sid = str(uuid.uuid4())
        st.session_state.current_session_id = new_sid
        st.session_state.current_session_data = {
            "session_id": new_sid,
            "collection": collection_opts[0],
            "updated_at": datetime.now().isoformat(),
            "messages": [],
        }
        save_session(st.session_state.current_session_data)
        st.rerun()

    session_opts = {
        s[
            "session_id"
        ]: f"{s.get('collection', 'Unknown')} - {s.get('updated_at', '')[:16].replace('T', ' ')}"
        for s in all_sessions
    }
    current_sid = st.session_state.get("current_session_id")

    if all_sessions:
        try:
            default_index = (
                list(session_opts.keys()).index(current_sid) if current_sid in session_opts else 0
            )
        except ValueError:
            default_index = 0

        selected_sid = st.sidebar.radio(
            "Recent Chats",
            list(session_opts.keys()),
            format_func=lambda x: session_opts[x],
            index=default_index,
        )

        if selected_sid != current_sid:
            st.session_state.current_session_id = selected_sid
            st.rerun()

    if not current_sid:
        current_sid = str(uuid.uuid4())
        st.session_state.current_session_id = current_sid
        st.session_state.current_session_data = {
            "session_id": current_sid,
            "collection": collection_opts[0],
            "updated_at": datetime.now().isoformat(),
            "messages": [],
        }
        save_session(st.session_state.current_session_data)
        st.rerun()

    session_file = get_sessions_dir() / f"{current_sid}.json"
    if session_file.exists():
        with open(session_file, "r") as f:
            session_data = json.load(f)
    else:
        session_data = st.session_state.current_session_data

    collection = st.selectbox(
        "Collection",
        collections,
        index=collections.index(session_data["collection"])
        if session_data["collection"] in collections
        else 0,
    )

    if collection != session_data["collection"]:
        session_data["collection"] = collection
        save_session(session_data)
        st.rerun()

    # Token counting logic (1 token = ~4 chars)
    total_tokens = sum(
        len(m["content"]) // 4 for m in session_data["messages"] if m.get("included", True)
    )
    MAX_TOKENS = config.llm.max_tokens or 4096
    usage_pct = min(1.0, total_tokens / MAX_TOKENS)

    st.progress(
        usage_pct,
        text=f"Context Window Usage: {total_tokens} / {MAX_TOKENS} tokens ({int(usage_pct * 100)}%)",
    )
    if usage_pct > 0.8:
        st.warning("⚠️ Context window is getting full. Exclude some messages below to save tokens.")

    st.markdown("---")

    for idx, msg in enumerate(session_data["messages"]):
        with st.chat_message(msg["role"]):
            cols = st.columns([0.85, 0.15])
            with cols[0]:
                if not msg.get("included", True):
                    st.caption("*(Excluded from context)*")
                st.markdown(msg["content"])
            with cols[1]:
                included = msg.get("included", True)
                if (
                    st.toggle("Include", value=included, key=f"toggle_{current_sid}_{idx}")
                    != included
                ):
                    session_data["messages"][idx]["included"] = not included
                    save_session(session_data)
                    st.rerun()

    if prompt := st.chat_input("Ask a question..."):
        active_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in session_data["messages"]
            if m.get("included", True)
        ]

        new_user_msg = {"role": "user", "content": prompt, "included": True}
        session_data["messages"].append(new_user_msg)
        session_data["updated_at"] = datetime.now().isoformat()
        save_session(session_data)

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    if collection == "No Collection (Direct Chat)" or db is None:
                        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

                        from tools.rag.pipeline.llm import create_llm

                        llm = create_llm(config.llm)

                        lc_messages = [SystemMessage(content="You are a helpful AI assistant.")]
                        for m in active_messages:
                            if m["role"] == "user":
                                lc_messages.append(HumanMessage(content=m["content"]))
                            else:
                                lc_messages.append(AIMessage(content=m["content"]))
                        lc_messages.append(HumanMessage(content=prompt))

                        resp = llm.invoke(lc_messages)
                        response = resp.content
                    else:
                        from tools.rag.agent import RAGAgent

                        agent = RAGAgent(config, db)
                        response = agent.query(
                            prompt, collection, top_k=5, conversation_history=active_messages
                        )

                    st.markdown(response)
                    session_data["messages"].append(
                        {"role": "assistant", "content": response, "included": True}
                    )
                    session_data["updated_at"] = datetime.now().isoformat()
                    save_session(session_data)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error querying backend: {e}")


def page_ingestion():
    """Document Ingestion page."""
    st.header("📄 Document Ingestion")

    config = st.session_state.config
    try:
        from db.chroma import ChromaDBBackend

        db = ChromaDBBackend(config.database)
        existing_collections = db.list_collections()
    except Exception as e:
        st.error(f"Failed to connect to Database: {e}")
        return

    st.markdown("Ingest documents, PDFs, or Markdown files into a ChromaDB collection.")

    col1, col2 = st.columns(2)
    with col1:
        collection_mode = st.radio("Collection", ["Existing", "New"], horizontal=True)

        if collection_mode == "Existing":
            if not existing_collections:
                st.warning("No existing collections.")
                collection_name = None
            else:
                collection_name = st.selectbox("Select Collection", existing_collections)
        else:
            collection_name = st.text_input("New Collection Name")

    with col2:
        source_path = st.text_input(
            "Source Directory or File Path", placeholder="/path/to/my/documents"
        )

    if st.button("Ingest Documents", type="primary"):
        if not collection_name or not str(collection_name).strip():
            st.error("Please specify a collection name.")
            return
        if not source_path or not str(source_path).strip():
            st.error("Please specify a source path.")
            return

        with st.spinner(
            f"Ingesting documents into '{collection_name}'... This may take a while depending on size."
        ):
            try:
                from kernel import Corpus

                corpus_app = Corpus.from_loaded(config, db)
                result = corpus_app.ingest_path(
                    str(source_path).strip(), str(collection_name).strip()
                )
                st.success(
                    f"Successfully indexed {result.files_indexed} files and {result.chunks_indexed} chunks!"
                )
                if collection_mode == "New":
                    import time

                    time.sleep(2)
                    st.rerun()
            except Exception as e:
                import traceback

                st.error(f"Ingestion failed: {e}\n\n{traceback.format_exc()}")


def main():
    st.set_page_config(
        page_title="CorpusRAG",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Increase base text size via custom CSS
    st.markdown(
        """
        <style>
            html, body, [class*="css"]  {
                font-size: 1.25rem !important;
            }
            p, span, div {
                font-weight: 500 !important;
            }
            h1 { font-size: 2.8rem !important; font-weight: 800 !important; }
            h2 { font-size: 2.2rem !important; font-weight: 700 !important; }
            h3 { font-size: 1.8rem !important; font-weight: 600 !important; }
            .stButton > button {
                font-size: 1.25rem !important;
                padding: 0.6rem 1.2rem !important;
                font-weight: 600 !important;
            }
            .stMarkdown p {
                font-size: 1.25rem !important;
                line-height: 1.6 !important;
            }
            .stChatMessage p {
                font-size: 1.3rem !important;
                font-weight: 500 !important;
                line-height: 1.6 !important;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    init_session_state()

    st.sidebar.title("🧠 CorpusRAG")
    st.sidebar.markdown("---")

    pages = {
        "Chat & Query": page_chat,
        "Ingestion": page_ingestion,
        "Settings": page_settings,
    }

    selection = st.sidebar.radio("Navigation", list(pages.keys()))

    st.sidebar.markdown("---")
    st.sidebar.caption("CorpusRAG Web UI • Running Locally")

    # Render selected page
    pages[selection]()


if __name__ == "__main__":
    main()
