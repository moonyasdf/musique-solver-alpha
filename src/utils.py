"""Utility functions for the musique-solver project."""

import os
import json
from typing import List, Union
from datetime import datetime
from pathlib import Path

def ensure_directory(path: Union[str, Path]) -> None:
    """Ensure that a directory exists, creating it if necessary."""
    # Convert Path to str to be safe across all python versions/OS
    os.makedirs(str(path), exist_ok=True)


def chunk_text(text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if not text:
        return []
        
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks


def save_json(data: dict, filepath: Union[str, Path], indent: int = 2) -> None:
    """Save data to a JSON file."""
    path_obj = Path(filepath)
    # Ensure parent directory exists
    ensure_directory(path_obj.parent)
    
    with open(path_obj, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_json(filepath: Union[str, Path]) -> dict:
    """Load data from a JSON file."""
    with open(str(filepath), 'r', encoding='utf-8') as f:
        return json.load(f)


def get_timestamp() -> str:
    """Get current timestamp as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")