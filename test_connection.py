#!/usr/bin/env python3
"""Test script to verify LLM connection and basic functionality."""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from src.llm_client import LLMClient

def test_connection():
    """Test basic connection to the LLM."""
    print("=" * 60)
    print("Testing LLM Connection")
    print("=" * 60)
    print(f"API Base: {config.OPENAI_API_BASE}")
    print(f"Model: {config.OPENAI_MODEL}")
    print(f"API Key: {config.OPENAI_API_KEY[:10]}...")
    print(f"Streaming: {config.STREAMING}")
    print("=" * 60)
    
    try:
        client = LLMClient(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            base_url=config.OPENAI_API_BASE,
            temperature=0.0,
            streaming=config.STREAMING,
        )
        
        print("\n✓ Client initialized successfully")
        print("\nSending test message...")
        
        response = client.chat(
            messages=[{"role": "user", "content": "Say 'Hello, I am working!' in exactly 5 words."}],
            max_tokens=50
        )
        
        print("\n✓ Response received:")
        print(f"  {response}")
        print("\n" + "=" * 60)
        print("✓ CONNECTION TEST PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Connection test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
