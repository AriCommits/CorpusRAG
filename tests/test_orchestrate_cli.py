"""Tests for the `orchestrate` CLI group wiring and dead-code removal."""

import importlib

import click
import pytest
from click.testing import CliRunner

from orchestrations.cli import orchestrate


def test_lecture_pipeline_help_exits_zero():
    """`corpus orchestrate lecture-pipeline --help` should exit 0."""
    runner = CliRunner()
    result = runner.invoke(orchestrate, ["lecture-pipeline", "--help"])
    assert result.exit_code == 0


def test_orchestrate_exposes_only_lecture_pipeline():
    """The orchestrate group should expose only the lecture-pipeline command."""
    ctx = click.Context(orchestrate)
    assert orchestrate.list_commands(ctx) == ["lecture-pipeline"]


def test_study_session_module_removed():
    """Importing the deleted study_session module should raise ModuleNotFoundError."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("orchestrations.study_session")


def test_knowledge_base_module_removed():
    """Importing the deleted knowledge_base module should raise ModuleNotFoundError."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("orchestrations.knowledge_base")
