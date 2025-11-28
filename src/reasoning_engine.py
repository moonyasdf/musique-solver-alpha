"""
Updated Reasoning Engine to support the v0.2.1 Agent Prompt logic.
Handles the 'thought' field and executes the new suite of tools.
"""
from __future__ import annotations

import logging
import json
import re
from typing import Dict, Any, Optional

from .llm_client import LLMClient
from .web_search import WikipediaSearchClient
from .wiki_fetcher import WikipediaArticleFetcher
from .research_tree import ResearchTree

logger = logging.getLogger(__name__)

class ReasoningEngine:
    def __init__(self, llm: LLMClient, searcher: WikipediaSearchClient, fetcher: WikipediaArticleFetcher):
        self.llm = llm
        self.searcher = searcher
        self.fetcher = fetcher
        self.memory = ResearchTree()
        self.max_steps = 20  # Increased for granular steps (Inspect -> Read -> Store takes more turns)

    def solve(self, question: str) -> Dict[str, Any]:
        """
        Executes the agent loop. Returns a dict with the final answer and the full trace.
        """
        # Initialize Memory with the Goal
        self.memory.add_node("root", "Research Goal", question)
        
        reasoning_trace = []
        current_step = 0
        final_answer = None

        while current_step < self.max_steps:
            current_step += 1
            
            # 1. Build Context (The "State" of the agent)
            # We show the Tree Structure to help it plan
            tree_snapshot = self.memory.get_tree_view()
            
            # 2. Construct Prompt for this turn
            # We append the history of the LAST few actions to avoid loops, 
            # but rely primarily on the Tree for long-term context.
            prompt = self._build_step_prompt(question, tree_snapshot, reasoning_trace[-3:])
            
            # 3. Get LLM Decision
            try:
                response_text = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
                action_data = self._parse_json_response(response_text)
            except Exception as e:
                logger.error(f"LLM Error: {e}")
                reasoning_trace.append({"step": current_step, "error": str(e)})
                continue

            thought = action_data.get("thought", "No thought provided")
            tool = action_data.get("tool")
            args = action_data.get("args", {})
            
            logger.info(f"Step {current_step} | Thought: {thought} | Tool: {tool}")
            
            # 4. Execute Tool
            tool_output = "Error: Tool execution failed"
            
            try:
                if tool == "search_google":
                    results = self.searcher.search(args.get("query", ""))
                    tool_output = "\n".join([f"{i+1}. [{r.title}]({r.url})\n   Snippet: {r.snippet}" for i, r in enumerate(results)])
                    if not tool_output: tool_output = "No results found."

                elif tool == "inspect_article_structure":
                    struct = self.fetcher.get_article_structure(args.get("url", ""))
                    tool_output = f"TITLE: {struct.title}\nSUMMARY: {struct.summary[:500]}...\nSECTIONS:\n" + "\n".join([f"- {s}" for s in struct.sections])

                elif tool == "read_section":
                    content = self.fetcher.get_section_content(args.get("url", ""), args.get("section_name", ""))
                    tool_output = content if content else "Section empty or not found."

                elif tool == "add_to_memory":
                    parent_id = args.get("parent_id", "root")
                    new_id = self.memory.add_node(
                        parent_id=parent_id,
                        topic=args.get("topic", "General"),
                        content=args.get("content", ""),
                        source_url=args.get("source_url")
                    )
                    tool_output = f"Success. Info stored in node ID: {new_id}"

                elif tool == "read_memory_tree":
                    tool_output = self.memory.get_tree_view()

                elif tool == "answer_question":
                    final_answer = args.get("answer")
                    tool_output = "Task Completed."
                    reasoning_trace.append({
                        "step": current_step,
                        "thought": thought,
                        "tool": tool,
                        "args": args,
                        "result": tool_output
                    })
                    break # EXIT LOOP

                else:
                    tool_output = f"Unknown tool: {tool}"

            except Exception as e:
                tool_output = f"Tool Error: {str(e)}"

            # 5. Log Step
            reasoning_trace.append({
                "step": current_step,
                "thought": thought,
                "tool": tool,
                "args": args,
                "result": tool_output[:1000] + "..." if len(str(tool_output)) > 1000 else tool_output
            })

        return {
            "question": question,
            "final_answer": final_answer,
            "trace": reasoning_trace,
            "tree_state": self.memory.to_json()
        }

    def _build_step_prompt(self, question: str, tree_snapshot: str, recent_history: list) -> str:
        history_text = ""
        for item in recent_history:
            history_text += f"Step {item['step']}:\n  Thought: {item.get('thought')}\n  Action: {item.get('tool')}({item.get('args')})\n  Result: {item.get('result')}\n\n"
        
        return f"""
Current Task: {question}

KNOWLEDGE TREE (Your Memory):
{tree_snapshot}

RECENT HISTORY:
{history_text}

Analyze the Tree and History. Decide the next step.
Remember:
1. Search if you have gaps.
2. Inspect Structure -> Read Section to verify details.
3. add_to_memory is REQUIRED to save progress.
4. answer_question only when the Tree proves the answer.

Respond in JSON.
"""

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Robust JSON extraction from LLM response."""
        # 1. Try direct parsing
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # 2. Try extracting from code blocks
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
                
        # 3. Try finding the first '{' and last '}'
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
                
        raise ValueError(f"Could not parse valid JSON from response: {text[:100]}...")