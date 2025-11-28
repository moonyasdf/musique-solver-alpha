"""Question decomposition for multi-hop reasoning."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class SubQuestion:
    question: str
    dependencies: List[str]  # Keys of previous answers this depends on
    answer: Optional[str] = None
    evidence: Optional[str] = None


@dataclass
class QuestionPlan:
    original_question: str
    sub_questions: List[SubQuestion]
    current_hop: int = 0


class QuestionDecomposer:
    """Decomposes complex multi-hop questions into simpler sub-questions."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    def decompose_next(
        self,
        original_question: str,
        previous_answers: dict[str, str],
    ) -> str:
        """
        Generate the next sub-question based on previous answers.
        
        This follows the iterative decomposition approach where we don't
        generate all sub-questions at once, but one at a time as we get answers.
        """
        if not previous_answers:
            # First sub-question
            prompt = f"""You are performing iterative question decomposition for a multi-hop research agent.

Original Question: {original_question}

Task: Generate ONLY the FIRST single-hop sub-question that should be answered via Wikipedia. Return only the sub-question text.
"""
        else:
            # Subsequent sub-questions
            answers_context = "\n".join([f"- {k}: {v}" for k, v in previous_answers.items()])
            
            prompt = f"""You are continuing the decomposition sequence.

Original Question: {original_question}

Answers Found So Far:
{answers_context}

Task: Generate the NEXT logical single-hop sub-question that depends on the answers above. Return only the sub-question text.
"""

        messages = [{"role": "user", "content": prompt}]
        sub_question = self.llm.chat(
            messages=messages,
        )
        
        return sub_question.strip()

    def should_continue(
        self,
        original_question: str,
        previous_answers: dict[str, str],
        max_hops: int = 6,
    ) -> bool:
        """
        Determine if we need to continue decomposing or if we have enough to answer.
        """
        if len(previous_answers) >= max_hops:
            return False

        if not previous_answers:
            return True

        # Ask the LLM if we have enough information to answer the original question
        answers_context = "\n".join([f"- {v}" for v in previous_answers.values()])
        
        prompt = f"""Original Question: {original_question}

Information Found:
{answers_context}

Can the original question be fully answered with this information alone? Answer with YES or NO only."""

        messages = [{"role": "user", "content": prompt}]
        response = self.llm.chat(
            messages=messages,
            system_prompt="You are a reasoning expert. Determine if enough information has been gathered.",
            temperature=0.0,
        )
        
        answer = response.strip().upper()
        return "NO" in answer or "NOT" in answer
