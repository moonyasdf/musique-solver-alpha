#!/usr/bin/env python3
"""Test script with a simple 2-hop question to verify the workflow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from src.web_search import WikipediaSearchClient
from src.wiki_fetcher import WikipediaArticleFetcher
from src.llm_client import LLMClient
from src.reasoning_engine import ReasoningEngine

def load_system_prompt():
    path = Path(config.PROMPTS_DIR) / "agent_system_prompt.txt"
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    print("=" * 70)
    print("Testing with a simple 2-hop question")
    print("=" * 70)
    
    # Simple question: Who directed Inception?
    question = "Who directed the movie Inception?"
    
    print(f"\nQuestion: {question}\n")
    print("Initializing components...")
    
    llm = LLMClient(
        api_key=config.OPENAI_API_KEY,
        model=config.OPENAI_MODEL,
        base_url=config.OPENAI_API_BASE,
        temperature=0.0,
        system_prompt=load_system_prompt(),
        streaming=config.STREAMING
    )
    
    searcher = WikipediaSearchClient(rate_limit=config.SEARCH_DELAY)
    fetcher = WikipediaArticleFetcher()
    engine = ReasoningEngine(llm, searcher, fetcher)
    
    print("✓ Components initialized\n")
    print("-" * 70)
    print("Starting reasoning process...")
    print("-" * 70)
    
    try:
        result = engine.solve(question)
        
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"\n🎯 FINAL ANSWER: {result.get('final_answer')}")
        print(f"\n📊 Total Steps: {len(result.get('trace', []))}")
        
        print("\n" + "-" * 70)
        print("REASONING TRACE")
        print("-" * 70)
        for step_data in result.get('trace', []):
            print(f"\nStep {step_data['step']}: {step_data['tool']}")
            print(f"  Thought: {step_data['thought']}")
            if step_data.get('args'):
                print(f"  Args: {step_data['args']}")
            print(f"  Result: {step_data['result'][:150]}...")
        
        print("\n" + "=" * 70)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
