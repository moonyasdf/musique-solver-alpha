#!/usr/bin/env python3
"""Script to query the agent with a single question."""

"""Script to query the agent with a single question (Updated for v0.2)."""

import sys
import json
import argparse
import logging
from pathlib import Path
import config
from src.web_search import WikipediaSearchClient
from src.wiki_fetcher import WikipediaArticleFetcher
from src.llm_client import LLMClient
from src.reasoning_engine import ReasoningEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def load_system_prompt() -> str:
    path = Path(config.PROMPTS_DIR) / "agent_system_prompt.txt"
    with open(path, 'r', encoding='utf-8') as f: return f.read()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?")
    args = parser.parse_args()

    question = args.question or input("Enter question: ")
    
    # Init components (Simplified)
    llm = LLMClient(
        api_key=config.OPENAI_API_KEY, 
        model=config.OPENAI_MODEL, 
        temperature=0.0,
        system_prompt=load_system_prompt()
    )
    searcher = WikipediaSearchClient(rate_limit=config.SEARCH_DELAY)
    fetcher = WikipediaArticleFetcher()
    
    # Engine now manages its own memory per solve() call
    engine = ReasoningEngine(llm, searcher, fetcher)
    
    print(f"\nThinking about: {question}...\n")
    
    result = engine.solve(question)
    
    print("-" * 50)
    print(f"FINAL ANSWER: {result.get('final_answer')}")
    print("-" * 50)
    print("REASONING TRACE SUMMARY:")
    for step in result.get('trace', []):
        print(f"Step {step.get('step')}: {step.get('thought')}")
        print(f"  -> Action: {step.get('tool')}")
    
    print("-" * 50)
    print("FINAL KNOWLEDGE TREE (JSON Structure):")
    print(result.get('tree_state'))

if __name__ == "__main__":
    main()