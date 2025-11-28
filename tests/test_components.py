import json
from pathlib import Path

import pytest

from src.utils import chunk_text
from src.memory_store import MemoryStore
from src.web_search import WikipediaSearchClient


def test_chunk_text_splits_with_overlap():
    text = "abcdefghij" * 100  # 1000 chars
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert len(chunks) > 1
    # Ensure overlap by checking second chunk shares prefix with first chunk suffix
    assert chunks[0][-10:] == chunks[1][:10]


def test_memory_store_round_trip(tmp_path: Path):
    store_path = tmp_path / "memory.json"
    store = MemoryStore(store_path)
    store.store_fact("key1", "value1")
    store.save()
    assert store.retrieve_fact("key1") == "value1"

    # Load into new instance
    new_store = MemoryStore(store_path)
    assert new_store.retrieve_fact("key1") == "value1"


def test_wikipedia_search_client_site_filter():
    client = WikipediaSearchClient()
    query = "Albert Einstein"
    filtered = client._apply_site_filter(query)
    assert "site:wikipedia.org" in filtered
    assert filtered.endswith(query)

    already_filtered = "site:wikipedia.org Nikola Tesla"
    filtered2 = client._apply_site_filter(already_filtered)
    assert filtered2 == already_filtered
