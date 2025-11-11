"""Snapshot tests for prompt building and citation formatting."""

import pytest
import os
from pathlib import Path
from app.services.prompting import build_chat_prompt, build_citation_footer


# Snapshot directory
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _get_snapshot_path(test_name):
    """Get the path to a snapshot file."""
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    return SNAPSHOT_DIR / f"{test_name}.snapshot"


def _read_snapshot(test_name):
    """Read a snapshot file."""
    snapshot_path = _get_snapshot_path(test_name)
    if snapshot_path.exists():
        return snapshot_path.read_text()
    return None


def _write_snapshot(test_name, content):
    """Write a snapshot file."""
    snapshot_path = _get_snapshot_path(test_name)
    snapshot_path.write_text(content)
    return snapshot_path


def test_build_chat_prompt_basic():
    """Test basic chat prompt building."""
    query = "What is machine learning?"
    contexts = [
        {
            "doc_id": "doc1",
            "page": "1",
            "content": "Machine learning is a subset of artificial intelligence."
        },
        {
            "doc_id": "doc2",
            "page": "5",
            "content": "Deep learning uses neural networks."
        }
    ]
    
    result = build_chat_prompt(query, contexts)
    
    # Convert to string for snapshot comparison
    import json
    result_str = json.dumps(result, indent=2)
    
    snapshot = _read_snapshot("test_build_chat_prompt_basic")
    if snapshot is None:
        _write_snapshot("test_build_chat_prompt_basic", result_str)
        pytest.fail(f"Snapshot created. Please review and run tests again.")
    
    assert result_str == snapshot, "Prompt format does not match snapshot"


def test_build_chat_prompt_custom_system_style():
    """Test chat prompt with custom system style."""
    query = "Explain neural networks"
    contexts = [
        {
            "doc_id": "ai_book",
            "page": "42",
            "content": "Neural networks are computational models."
        }
    ]
    
    custom_style = "You are an AI expert assistant."
    result = build_chat_prompt(query, contexts, system_style=custom_style)
    
    import json
    result_str = json.dumps(result, indent=2)
    
    snapshot = _read_snapshot("test_build_chat_prompt_custom_system_style")
    if snapshot is None:
        _write_snapshot("test_build_chat_prompt_custom_system_style", result_str)
        pytest.fail(f"Snapshot created. Please review and run tests again.")
    
    assert result_str == snapshot, "Prompt format does not match snapshot"


def test_build_chat_prompt_empty_contexts():
    """Test chat prompt with empty contexts."""
    query = "What is AI?"
    contexts = []
    
    result = build_chat_prompt(query, contexts)
    
    import json
    result_str = json.dumps(result, indent=2)
    
    snapshot = _read_snapshot("test_build_chat_prompt_empty_contexts")
    if snapshot is None:
        _write_snapshot("test_build_chat_prompt_empty_contexts", result_str)
        pytest.fail(f"Snapshot created. Please review and run tests again.")
    
    assert result_str == snapshot, "Prompt format does not match snapshot"


def test_build_chat_prompt_citation_markers():
    """Test that citation markers are correctly formatted in prompts."""
    query = "What are the main concepts?"
    contexts = [
        {
            "doc_id": "paper1",
            "page": "10",
            "content": "First concept explanation."
        },
        {
            "doc_id": "paper2",
            "page": "3",
            "content": "Second concept explanation."
        }
    ]
    
    result = build_chat_prompt(query, contexts)
    
    # Check that citation markers are present
    user_message = result[-1]["content"]
    assert "[paper1:10]" in user_message, "Citation marker [paper1:10] not found"
    assert "[paper2:3]" in user_message, "Citation marker [paper2:3] not found"
    
    import json
    result_str = json.dumps(result, indent=2)
    
    snapshot = _read_snapshot("test_build_chat_prompt_citation_markers")
    if snapshot is None:
        _write_snapshot("test_build_chat_prompt_citation_markers", result_str)
        pytest.fail(f"Snapshot created. Please review and run tests again.")
    
    assert result_str == snapshot, "Prompt format does not match snapshot"


def test_build_citation_footer_basic():
    """Test basic citation footer building."""
    contexts = [
        {
            "doc_id": "doc1",
            "page": "1",
            "content": "Some content"
        },
        {
            "doc_id": "doc2",
            "page": "5",
            "content": "More content"
        },
        {
            "doc_id": "doc1",
            "page": "1",
            "content": "Duplicate citation"
        }
    ]
    
    result = build_citation_footer(contexts)
    
    snapshot = _read_snapshot("test_build_citation_footer_basic")
    if snapshot is None:
        _write_snapshot("test_build_citation_footer_basic", result)
        pytest.fail(f"Snapshot created. Please review and run tests again.")
    
    assert result == snapshot, "Citation footer does not match snapshot"
    
    # Verify deduplication
    assert result.count("doc1:1") == 1, "Citations should be deduplicated"


def test_build_citation_footer_empty():
    """Test citation footer with empty contexts."""
    contexts = []
    
    result = build_citation_footer(contexts)
    
    assert result == "", "Empty contexts should return empty footer"
    
    snapshot = _read_snapshot("test_build_citation_footer_empty")
    if snapshot is None:
        _write_snapshot("test_build_citation_footer_empty", result)
        pytest.fail(f"Snapshot created. Please review and run tests again.")
    
    assert result == snapshot, "Citation footer does not match snapshot"


def test_build_citation_footer_missing_fields():
    """Test citation footer with contexts missing doc_id or page."""
    contexts = [
        {
            "doc_id": "doc1",
            "page": "1",
            "content": "Valid citation"
        },
        {
            "doc_id": "",
            "page": "2",
            "content": "Missing doc_id"
        },
        {
            "doc_id": "doc3",
            "page": "",
            "content": "Missing page"
        },
        {
            "content": "Missing both"
        }
    ]
    
    result = build_citation_footer(contexts)
    
    snapshot = _read_snapshot("test_build_citation_footer_missing_fields")
    if snapshot is None:
        _write_snapshot("test_build_citation_footer_missing_fields", result)
        pytest.fail(f"Snapshot created. Please review and run tests again.")
    
    assert result == snapshot, "Citation footer does not match snapshot"
    
    # Only valid citation should appear
    assert "[doc1:1]" in result, "Valid citation should be present"
    assert "[doc3:]" not in result, "Invalid citations should be excluded"


def test_build_citation_footer_sorted():
    """Test that citations are sorted in footer."""
    contexts = [
        {
            "doc_id": "doc_z",
            "page": "10",
            "content": "Z document"
        },
        {
            "doc_id": "doc_a",
            "page": "1",
            "content": "A document"
        },
        {
            "doc_id": "doc_m",
            "page": "5",
            "content": "M document"
        }
    ]
    
    result = build_citation_footer(contexts)
    
    snapshot = _read_snapshot("test_build_citation_footer_sorted")
    if snapshot is None:
        _write_snapshot("test_build_citation_footer_sorted", result)
        pytest.fail(f"Snapshot created. Please review and run tests again.")
    
    assert result == snapshot, "Citation footer does not match snapshot"
    
    # Verify sorting
    a_pos = result.find("doc_a:1")
    m_pos = result.find("doc_m:5")
    z_pos = result.find("doc_z:10")
    
    assert a_pos < m_pos < z_pos, "Citations should be sorted alphabetically"
