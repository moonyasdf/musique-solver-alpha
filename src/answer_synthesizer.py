"""Answer synthesis from evidence chain."""

from __future__ import annotations

import logging
from typing import Dict

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class AnswerSynthesizer:
    """Synthesizes final answers from the reasoning chain."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    def synthesize(
        self,
        original_question: str,
        reasoning_chain: list[Dict],
    ) -> str:
        """
        Synthesize the final answer from the complete reasoning chain.
        
        Args:
            original_question: The original multi-hop question
            reasoning_chain: List of dict with sub_questions, answers, and evidence
        
        Returns:
            The final synthesized answer
        """
        # Build the evidence chain context
        chain_context = ""
        for i, hop in enumerate(reasoning_chain, 1):
            chain_context += f"\nHop {i}:\n"
            chain_context += f"  Sub-Question: {hop.get('sub_question', '')}\n"
            chain_context += f"  Answer: {hop.get('answer', '')}\n"
            if hop.get('evidence'):
                chain_context += f"  Evidence: {hop.get('evidence', '')[:200]}...\n"

        prompt = f"""You are synthesizing a final answer from a multi-hop reasoning chain.

Original Question: {original_question}

Reasoning Chain:
{chain_context}

Task: Based on the reasoning chain above, provide a concise final answer to the original question. Return ONLY the answer, no explanation."""

        messages = [{"role": "user", "content": prompt}]
        final_answer = self.llm.chat(
            messages=messages,
            temperature=0.0,
        )
        
        return final_answer.strip()

    def verify_answer(
        self,
        original_question: str,
        proposed_answer: str,
        reasoning_chain: list[Dict],
    ) -> tuple[bool, str]:
        """
        Verify if the proposed answer is supported by the evidence chain.
        
        Returns:
            (is_valid, explanation)
        """
        chain_context = ""
        for i, hop in enumerate(reasoning_chain, 1):
            chain_context += f"\nHop {i}: {hop.get('sub_question', '')} → {hop.get('answer', '')}\n"

        prompt = f"""You are verifying a proposed answer against the evidence chain.

Original Question: {original_question}

Proposed Answer: {proposed_answer}

Reasoning Chain:
{chain_context}

Question: Is the proposed answer logically consistent with and supported by the reasoning chain? Answer with YES or NO, followed by a brief explanation."""

        messages = [{"role": "user", "content": prompt}]
        verification = self.llm.chat(
            messages=messages,
            temperature=0.0,
        )
        
        is_valid = "YES" in verification.upper()[:10]
        return is_valid, verification
