"""Simple key-value memory store for facts and articles."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Simple key-value store for session-based memory.
    
    No embeddings, vector databases, or semantic search - just key-based retrieval.
    """

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self.store: Dict[str, str] = {}
        self.persist_path = persist_path
        
        if self.persist_path and self.persist_path.exists():
            self.load()

    def store_fact(self, key: str, value: str) -> None:
        """Store a fact with the given key."""
        self.store[key] = value
        logger.debug(f"Stored fact: {key} = {value[:100]}...")
        if self.persist_path:
            self.save()

    def retrieve_fact(self, key: str) -> Optional[str]:
        """Retrieve a fact by key."""
        value = self.store.get(key)
        if value:
            logger.debug(f"Retrieved fact: {key} = {value[:100]}...")
        else:
            logger.debug(f"Fact not found: {key}")
        return value

    def has_fact(self, key: str) -> bool:
        """Check if a fact exists."""
        return key in self.store

    def list_keys(self) -> list[str]:
        """List all stored keys."""
        return list(self.store.keys())

    def clear(self) -> None:
        """Clear all stored facts."""
        self.store.clear()
        if self.persist_path and self.persist_path.exists():
            self.persist_path.unlink(missing_ok=True)
        logger.debug("Memory store cleared")

    def save(self) -> None:
        """Save the memory store to disk."""
        if not self.persist_path:
            return
        
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, 'w', encoding='utf-8') as f:
            json.dump(self.store, f, indent=2, ensure_ascii=False)
        logger.debug(f"Memory store saved to {self.persist_path}")

    def load(self) -> None:
        """Load the memory store from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        with open(self.persist_path, 'r', encoding='utf-8') as f:
            self.store = json.load(f)
        logger.debug(f"Memory store loaded from {self.persist_path}")

    def __len__(self) -> int:
        return len(self.store)

    def __repr__(self) -> str:
        return f"MemoryStore(items={len(self.store)})"
