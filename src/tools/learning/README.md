# Learning Tools

Study material generation from RAG collections: flashcards and quizzes.

## CLI Commands

### Flashcards

```bash
corpus tools learning flashcards generate -c <collection> --count 15
corpus tools learning flashcards generate -c <collection> --export anki -o cards.apkg
```

### Quizzes

```bash
corpus tools learning quizzes generate -c <collection> --count 10
corpus tools learning quizzes generate -c <collection> --format json -o quiz.json
```

## Features

### Flashcards
- Configurable count
- Anki export (`.apkg`)
- Collection-aware generation
- LLM-powered intelligent card creation

### Quizzes
- Question types: multiple choice, true/false, short answer
- Export formats: JSON, CSV
- Difficulty control
- Topic filtering within collections

## Architecture

```
learning/
├── cli.py              # Learning group CLI
└── __init__.py

flashcards/             # (sibling under tools/)
├── cli.py
├── generator.py
├── export.py
└── config.py

quizzes/                # (sibling under tools/)
├── cli.py
├── generator.py
├── export.py
└── config.py
```

## Requirements

```bash
pip install corpusrag[generators]  # Core generation
pip install corpusrag[export]      # Anki export (genanki)
```
