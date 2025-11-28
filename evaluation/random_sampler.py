"""Random question sampling from the MuSiQue benchmark."""

import json
import random
from typing import List, Dict


def sample_questions(
    filepath: str,
    n: int = 10,
    seed: int = None,
) -> List[Dict]:
    """
    Sample n random questions from the benchmark file.
    
    Args:
        filepath: Path to musique_4hop_all_questions.json
        n: Number of questions to sample
        seed: Random seed for reproducibility
    
    Returns:
        List of question objects
    """
    if seed is not None:
        random.seed(seed)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        all_questions = json.load(f)
    
    # Filter for answerable questions
    answerable = [q for q in all_questions if q.get('answerable', True)]
    
    if len(answerable) < n:
        print(f"Warning: Only {len(answerable)} answerable questions available, sampling all")
        return answerable
    
    return random.sample(answerable, n)
