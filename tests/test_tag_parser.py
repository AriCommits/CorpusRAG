"""Tests for hierarchical tag parsing."""

import pytest

from src.tools.rag.pipeline.parsers import (
    ParsedTag,
    build_tag_metadata,
    extract_tags_from_text,
    parse_hierarchical_tags,
)


class TestParseHierarchicalTags:
    """Tests for parse_hierarchical_tags function."""

    def test_flat_tag_parsing(self):
        """Flat #Tag tags parse correctly."""
        content = """- #Python
        - #JavaScript
        """
        tags = parse_hierarchical_tags(content)
        assert len(tags) == 2
        assert any(t.full == "Python" and t.prefix == "Python" and t.leaf == "Python" for t in tags)
        assert any(t.full == "JavaScript" and t.prefix == "JavaScript" for t in tags)

    def test_hierarchical_two_level_tags(self):
        """Two-level hierarchical tags parse correctly."""
        content = "- #Skill/ML\n- #Skill/Statistics"
        tags = parse_hierarchical_tags(content)
        assert len(tags) == 2

        ml_tag = next(t for t in tags if t.full == "Skill/ML")
        assert ml_tag.prefix == "Skill"
        assert ml_tag.leaf == "ML"
        assert ml_tag.parts == ["Skill", "ML"]

    def test_hierarchical_three_level_tags(self):
        """Three-level hierarchical tags parse correctly."""
        content = "- #Subject/Area/Topic"
        tags = parse_hierarchical_tags(content)
        assert len(tags) == 1

        tag = tags[0]
        assert tag.full == "Subject/Area/Topic"
        assert tag.prefix == "Subject"
        assert tag.leaf == "Topic"
        assert tag.parts == ["Subject", "Area", "Topic"]

    def test_mixed_flat_and_hierarchical(self):
        """Mix of flat and hierarchical tags works."""
        content = """- #Python #Skill/ML
        - #CS/Algorithms
        """
        tags = parse_hierarchical_tags(content)
        assert len(tags) == 3

        # Flat tag
        assert any(t.full == "Python" and t.prefix == "Python" for t in tags)
        # Hierarchical tags
        assert any(t.full == "Skill/ML" for t in tags)
        assert any(t.full == "CS/Algorithms" for t in tags)

    def test_duplicate_tags_deduplicated(self):
        """Duplicate tags appear only once."""
        content = """- #Python #Python #JavaScript
        - #Python
        """
        tags = parse_hierarchical_tags(content)
        assert len(tags) == 2

    def test_empty_content(self):
        """Empty content returns empty tag list."""
        tags = parse_hierarchical_tags("")
        assert tags == []

    def test_content_without_tags(self):
        """Content without tags returns empty list."""
        content = "This is a paragraph without tags."
        tags = parse_hierarchical_tags(content)
        assert tags == []

    def test_non_bulleted_tags_ignored(self):
        """Tags not in bulleted lists are ignored."""
        content = """This #ignoredTag is in a paragraph.
        - #python is in a list
        """
        tags = parse_hierarchical_tags(content)
        assert len(tags) == 1
        assert tags[0].full == "python"


class TestBuildTagMetadata:
    """Tests for build_tag_metadata function."""

    def test_metadata_structure(self):
        """Metadata dict has correct structure."""
        tags = [
            ParsedTag(full="Skill/ML", parts=["Skill", "ML"], prefix="Skill", leaf="ML"),
            ParsedTag(full="Skill/Statistics", parts=["Skill", "Statistics"], prefix="Skill", leaf="Statistics"),
        ]
        metadata = build_tag_metadata(tags)

        assert "tags" in metadata
        assert "tag_prefixes" in metadata
        assert "tag_leaves" in metadata

    def test_metadata_fields_are_lists(self):
        """All metadata fields are list[str]."""
        tags = [
            ParsedTag(full="Python", parts=["Python"], prefix="Python", leaf="Python"),
        ]
        metadata = build_tag_metadata(tags)

        assert isinstance(metadata["tags"], list)
        assert isinstance(metadata["tag_prefixes"], list)
        assert isinstance(metadata["tag_leaves"], list)
        assert all(isinstance(t, str) for t in metadata["tags"])

    def test_metadata_values(self):
        """Metadata values are correct."""
        tags = [
            ParsedTag(full="Skill/ML", parts=["Skill", "ML"], prefix="Skill", leaf="ML"),
            ParsedTag(full="Skill/Statistics", parts=["Skill", "Statistics"], prefix="Skill", leaf="Statistics"),
            ParsedTag(full="CS/Algorithms", parts=["CS", "Algorithms"], prefix="CS", leaf="Algorithms"),
        ]
        metadata = build_tag_metadata(tags)

        # Check full tags
        assert set(metadata["tags"]) == {"Skill/ML", "Skill/Statistics", "CS/Algorithms"}

        # Check prefixes (top-level categories)
        assert set(metadata["tag_prefixes"]) == {"CS", "Skill"}

        # Check leaves (most specific)
        assert set(metadata["tag_leaves"]) == {"Algorithms", "ML", "Statistics"}

    def test_empty_tags_returns_empty_dict(self):
        """Empty tag list returns empty dict."""
        metadata = build_tag_metadata([])
        assert metadata == {}

    def test_single_flat_tag(self):
        """Single flat tag works correctly."""
        tags = [ParsedTag(full="Python", parts=["Python"], prefix="Python", leaf="Python")]
        metadata = build_tag_metadata(tags)

        assert metadata["tags"] == ["Python"]
        assert metadata["tag_prefixes"] == ["Python"]
        assert metadata["tag_leaves"] == ["Python"]


class TestExtractTagsFromText:
    """Tests for extract_tags_from_text function."""

    def test_return_type(self):
        """Return type is (str, dict) as documented."""
        content = "- #Python"
        text, metadata = extract_tags_from_text(content)

        assert isinstance(text, str)
        assert isinstance(metadata, dict)

    def test_text_preserved(self):
        """Original text is preserved."""
        content = "# Header\n- #Python\nSome content"
        text, _ = extract_tags_from_text(content)
        assert text == content

    def test_metadata_structure(self):
        """Metadata has tags, tag_prefixes, tag_leaves."""
        content = "- #Skill/ML"
        _, metadata = extract_tags_from_text(content)

        assert "tags" in metadata
        assert "tag_prefixes" in metadata
        assert "tag_leaves" in metadata

    def test_backward_compatibility_flat_tags(self):
        """Flat tags from old format work with new parser."""
        content = "- #python #machine-learning"
        text, metadata = extract_tags_from_text(content)

        # New format should have the tags
        assert "tags" in metadata
        assert isinstance(metadata["tags"], list)

    def test_chromadb_compatibility(self):
        """Metadata is compatible with ChromaDB (all list[str])."""
        content = "- #Skill/ML\n- #CS/Algorithms"
        _, metadata = extract_tags_from_text(content)

        # ChromaDB requires list[str] for array metadata
        for key in ["tags", "tag_prefixes", "tag_leaves"]:
            if key in metadata:
                assert isinstance(metadata[key], list)
                assert all(isinstance(v, str) for v in metadata[key])
