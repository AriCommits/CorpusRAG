"""Tests for /context slash command."""

import pytest

from src.tools.rag.slash_commands import SlashCommandRouter


@pytest.fixture
def router():
    """Create a slash command router."""
    return SlashCommandRouter()


def test_context_command_no_args(router):
    """Test /context with no arguments shows help."""
    result = router.dispatch(router.parse("/context"))
    assert result.type == "text"
    assert "context" in result.content.lower()


def test_context_show_command(router):
    """Test /context show command."""
    result = router.dispatch(router.parse("/context show"))
    assert result.type == "toast"
    assert result.toast_message == "context:show"


def test_context_clear_command(router):
    """Test /context clear command."""
    result = router.dispatch(router.parse("/context clear"))
    assert result.type == "toast"
    assert result.toast_message == "context:clear"


def test_context_include_all_command(router):
    """Test /context include all command."""
    result = router.dispatch(router.parse("/context include all"))
    assert result.type == "toast"
    assert result.toast_message == "context:include_all"


def test_context_invalid_subcommand(router):
    """Test /context with invalid subcommand."""
    result = router.dispatch(router.parse("/context invalid"))
    assert result.type == "error"
    assert "Unknown context command" in result.content


def test_context_include_without_all(router):
    """Test /context include without 'all' is an error."""
    result = router.dispatch(router.parse("/context include"))
    assert result.type == "error"


def test_context_command_case_insensitive(router):
    """Test /context command is case insensitive."""
    result = router.dispatch(router.parse("/context SHOW"))
    assert result.type == "toast"
    assert result.toast_message == "context:show"

    result = router.dispatch(router.parse("/context CLEAR"))
    assert result.type == "toast"
    assert result.toast_message == "context:clear"


def test_context_include_all_case_insensitive(router):
    """Test /context include ALL is case insensitive."""
    result = router.dispatch(router.parse("/context include ALL"))
    assert result.type == "toast"
    assert result.toast_message == "context:include_all"


def test_slash_command_router_recognizes_context(router):
    """Test that router recognizes /context as a slash command."""
    assert router.is_slash_command("/context")
    assert router.is_slash_command("/context show")


def test_context_help_message_contains_options(router):
    """Test that /context shows available options."""
    result = router.dispatch(router.parse("/context"))
    content = result.content.lower()
    assert "show" in content
    assert "clear" in content
    assert "include" in content
