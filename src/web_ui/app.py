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
                index=["ollama", "openai", "anthropic"].index(config.llm.backend) if config.llm.backend in ["ollama", "openai", "anthropic"] else 0
            )
            model = st.text_input("Primary Model", value=config.llm.model)
        with col2:
            endpoint = st.text_input("Endpoint (e.g., http://localhost:11434)", value=config.llm.endpoint)
            api_key = st.text_input("API Key (leave blank if local)", value=config.llm.api_key or "", type="password")

        temperature = st.slider("Temperature", 0.0, 2.0, float(config.llm.temperature), 0.1)

    with st.expander("📚 Database Settings"):
        db_mode = st.radio("ChromaDB Mode", ["persistent", "http"], index=0 if config.database.mode == "persistent" else 1)
        persist_dir = st.text_input("Persist Directory", value=str(config.database.persist_directory))

    if st.button("Save Configuration", type="primary"):
        # Update session state config
        config.llm.backend = backend
        config.llm.model = model
        config.llm.endpoint = endpoint
        config.llm.api_key = api_key if api_key.strip() else None
        config.llm.temperature = temperature
        
        config.database.mode = db_mode
        config.database.persist_directory = Path(persist_dir)

        try:
            config.save_to_yaml(Path("configs/base.yaml"))
            st.success("Configuration saved successfully!")
        except Exception as e:
            st.error(f"Failed to save configuration: {e}")


def page_chat():
    """Chat and Interaction page."""
    st.header("💬 Chat & Query")
    st.info("The Chat interface will be migrated here soon. You will be able to query your RAG collections directly from the browser.")


def page_ingestion():
    """Document Ingestion page."""
    st.header("📄 Ingestion Pipeline")
    st.info("The Document and Video ingestion tools will be migrated here soon.")


def main():
    st.set_page_config(
        page_title="CorpusRAG",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
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
