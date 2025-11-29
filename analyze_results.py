#!/usr/bin/env python3
"""Analyze partial evaluation results."""

import json
import sys
from pathlib import Path

def analyze_responses(responses_file):
    """Analyze responses from an evaluation run."""
    if not Path(responses_file).exists():
        print(f"❌ File not found: {responses_file}")
        return
    
    with open(responses_file, 'r') as f:
        responses = json.load(f)
    
    print("=" * 70)
    print(f"EVALUATION ANALYSIS - {len(responses)} questions processed")
    print("=" * 70)
    
    total = len(responses)
    successful = sum(1 for r in responses if r.get('success', False))
    answered = sum(1 for r in responses if r.get('agent_answer'))
    
    print(f"\n📊 Overall Statistics:")
    print(f"  Total questions: {total}")
    print(f"  Successful runs: {successful}")
    print(f"  Answered: {answered}")
    print(f"  Errors: {total - successful}")
    
    print(f"\n" + "=" * 70)
    print("QUESTION DETAILS")
    print("=" * 70)
    
    for i, resp in enumerate(responses, 1):
        qid = resp.get('question_id', 'unknown')
        question = resp.get('question_text', 'N/A')
        ground_truth = resp.get('ground_truth', 'N/A')
        agent_answer = resp.get('agent_answer', 'N/A')
        success = resp.get('success', False)
        trace = resp.get('full_trace', [])
        
        print(f"\n[{i}/{total}] {qid}")
        print(f"  Q: {question[:100]}...")
        print(f"  Expected: {ground_truth}")
        print(f"  Agent: {agent_answer}")
        print(f"  Status: {'✅ Success' if success else '❌ Error'}")
        print(f"  Steps: {len(trace)}")
        
        # Check if answer matches (simple check)
        if agent_answer and ground_truth:
            if ground_truth.lower() in agent_answer.lower() or agent_answer.lower() in ground_truth.lower():
                print(f"  Match: ✅ LIKELY CORRECT")
            else:
                print(f"  Match: ⚠️  NEEDS REVIEW")
        
        # Show last few steps
        if trace:
            print(f"  Last steps:")
            for step in trace[-3:]:
                tool = step.get('tool', 'unknown')
                thought = step.get('thought', 'N/A')[:80]
                print(f"    • Step {step.get('step')}: {tool} - {thought}...")
    
    print(f"\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Completion rate: {answered}/{total} = {100*answered/total if total > 0 else 0:.1f}%")
    print("=" * 70)

if __name__ == "__main__":
    run_dir = sys.argv[1] if len(sys.argv) > 1 else "evaluation/results/final_run_v2"
    responses_file = Path(run_dir) / "responses.json"
    analyze_responses(responses_file)
