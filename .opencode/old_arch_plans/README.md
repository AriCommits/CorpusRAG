# Homeschool

A personal knowledge management and learning assistant that helps you process educational notes into effective study materials using local AI tools.

## Overview

Homeschool is a privacy-focused, local-first system that transforms your class notes into:
- Anki flashcards (cloze deletion, image occlusion, multiple choice)
- Short answer review questions
- Concept summaries and extensions
- Answers to your questions

The system emphasizes manual control, privacy, and ease of use.

## Key Features

- **Manual Sync Control**: Run `python -m homeschool sync` when you want to process notes
- **Privacy-First**: All processing happens locally by default
- **Flexible AI Integration**: Works with Jan AI, AnythingLLM, and other local tools
- **Obsidian Compatible**: Designed to work with your existing note-taking workflow
- **Anki Integration**: Generates flashcards ready for import into Anki
- **Configurable**: Adjust behavior through `config.yaml`

## Project Structure

```
.
├── .docker/                 # Docker configuration and files
├ .env.example              # Environment variables template
├ config.yaml               # Main configuration file
├ docs/                     # Documentation (workflows, guides)
├ homeschool/               # Main Python package
│   ├── __init__.py
│   ├── __main__.py         # Enables `python -m homeschool sync`
│   ├── config.py
│   ├── generate_compose_env.py
│   ├── sync.py
│   └── transaction.py
└ refactoring_summary.md    # Summary of recent refactoring
```

## Quick Start

### 1. Configuration
Edit `config.yaml` to set:
- `paths.vault`: Path to your Obsidian vault
- `paths.model_store`: Directory containing your .gguf model files  
- `chromadb.auth_token`: Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`

### 2. Start Required Services
```bash
# Start Jan AI (load your preferred model)
# Start AnythingLLM Desktop (optional, for RAG)

# Start Homeschool services
cd .docker
docker compose up -d chromadb
```

### 3. Process Your Notes
```bash
# From project root
python -m homeschool sync
```

### 4. Review Results
- Check Anki for new flashcards (requires manual confirmation)
- Review generated questions and summaries in your vault
- Process continues until you stop it

## Workflows

See the `docs/` directory for detailed workflows:
- [Learning Workflow](docs/Learning%20Workflow.md) - How to generate study materials from notes
- [Local AI Workflow](docs/Local%20AI%20Workflow.md) - Local-first AI setup for development

## Development

Homeschool is structured as a Python package. For development:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install pyyaml structlog

# Run tests (when available)
# python -m pytest
```

## Contributing

See `.opencode/plans/improvement_plan.md` for planned enhancements.

## License

[Specify your license here]

## Acknowledgments

- Built with open-source tools including ChromaDB, Jan AI, and Continue
- Inspired by privacy-focused, local-first AI workflows