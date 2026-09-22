"""CorpusRAG Web Application Entry Point.

This module provides a Streamlit-based web interface for CorpusRAG.
"""

import sys
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

    if st.button("Save Configuration", type="primary"):
        # Update session state config
        config.llm.backend = backend
        config.llm.model = model
        config.llm.endpoint = endpoint
        config.llm.api_key = api_key if api_key.strip() else None
        config.llm.temperature = temperature

        config.database.mode = "persistent" if "persistent" in db_mode else "http"
        config.database.persist_directory = Path(persist_dir)

        try:
            config.save_to_yaml(Path("configs/base.yaml"))
            st.success("Configuration saved successfully!")
            st.rerun()  # Refresh the page state to lock in changes
        except Exception as e:
            st.error(f"Failed to save configuration: {e}")


def page_chat():
    """Chat and Interaction page."""
    st.header("💬 Chat & Query")
    
    config = st.session_state.config
    try:
        from db.chroma import ChromaDBBackend
        db = ChromaDBBackend(config.database)
        collections = db.list_collections()
    except Exception as e:
        st.error(f"Failed to connect to Database: {e}")
        return

    if not collections:
        st.warning("No collections found. Please go to the Ingestion page to add documents.")
        return

    collection = st.selectbox("Select a Collection", collections)

    if "messages" not in st.session_state:
        st.session_state.messages = {}
        
    if collection not in st.session_state.messages:
        st.session_state.messages[collection] = []

    for msg in st.session_state.messages[collection]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a question about your documents..."):
        st.session_state.messages[collection].append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    from kernel import Corpus
                    corpus_app = Corpus.from_loaded(config, db)
                    response = corpus_app.ask(prompt, collection, top_k=5)
                    st.markdown(response)
                    st.session_state.messages[collection].append({"role": "assistant", "content": response})
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
        source_path = st.text_input("Source Directory or File Path", placeholder="/path/to/my/documents")

    if st.button("Ingest Documents", type="primary"):
        if not collection_name or not str(collection_name).strip():
            st.error("Please specify a collection name.")
            return
        if not source_path or not str(source_path).strip():
            st.error("Please specify a source path.")
            return

        with st.spinner(f"Ingesting documents into '{collection_name}'... This may take a while depending on size."):
            try:
                from kernel import Corpus
                corpus_app = Corpus.from_loaded(config, db)
                result = corpus_app.ingest_path(str(source_path).strip(), str(collection_name).strip())
                st.success(f"Successfully indexed {result.files_indexed} files and {result.chunks_indexed} chunks!")
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
                font-size: 1.15rem !important;
            }
            h1 { font-size: 2.5rem !important; }
            h2 { font-size: 2rem !important; }
            .stButton > button {
                font-size: 1.15rem !important;
                padding: 0.5rem 1rem !important;
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