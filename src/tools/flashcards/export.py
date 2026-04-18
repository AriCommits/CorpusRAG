import random
from pathlib import Path

import genanki


class AnkiExporter:
    """Export flashcards to Anki .apkg format."""

    def __init__(self, deck_name: str):
        self.deck_name = deck_name
        self.model_id = random.randrange(1 << 30, 1 << 31)
        self.deck_id = random.randrange(1 << 30, 1 << 31)

        self.model = genanki.Model(
            self.model_id,
            "CorpusRAG Model",
            fields=[
                {"name": "Question"},
                {"name": "Answer"},
            ],
            templates=[
                {
                    "name": "Card 1",
                    "qfmt": "{{Question}}",
                    "afmt": '{{FrontSide}}<hr id="answer">{{Answer}}',
                },
            ],
        )

    def export(self, flashcards: list[dict[str, str]], output_path: Path | str):
        """Export list of flashcards to Anki package."""
        deck = genanki.Deck(self.deck_id, self.deck_name)

        for card in flashcards:
            note = genanki.Note(model=self.model, fields=[card["front"], card["back"]])
            deck.add_note(note)

        genanki.Package(deck).write_to_file(output_path)
