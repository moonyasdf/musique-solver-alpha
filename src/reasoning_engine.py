"""Updated Reasoning Engine with EDR Todo Manager."""
from __future__ import annotations
import logging
import json
import re
from typing import Dict, Any

from .llm_client import LLMClient
from .web_search import WikipediaSearchClient
from .wiki_fetcher import WikipediaArticleFetcher
from .research_tree import ResearchTree
from .todo_manager import ResearchTodoManager # Importar el nuevo manager

logger = logging.getLogger(__name__)

class ReasoningEngine:
    def __init__(self, llm: LLMClient, searcher: WikipediaSearchClient, fetcher: WikipediaArticleFetcher):
        self.llm = llm
        self.searcher = searcher
        self.fetcher = fetcher
        self.memory = ResearchTree()
        self.todo = ResearchTodoManager() # Instancia del Todo Manager
        self.max_steps = 25

    def solve(self, question: str) -> Dict[str, Any]:
        self.memory.add_node("root", "Goal", question)
        # Tarea inicial EDR
        self.todo.add_task(f"Decompose and answer: {question}", priority=10)
        
        reasoning_trace = []
        current_step = 0
        final_answer = None

        while current_step < self.max_steps:
            current_step += 1
            
            # 1. Contexto EDR: Árbol + Plan (Todo.md)
            tree_snapshot = self.memory.get_tree_view()
            plan_snapshot = self.todo.get_plan_view()
            
            prompt = self._build_step_prompt(question, tree_snapshot, plan_snapshot, reasoning_trace[-2:])
            
            try:
                response_text = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
                action_data = self._parse_json_response(response_text)
            except Exception as e:
                logger.error(f"LLM Error: {e}")
                continue

            thought = action_data.get("thought", "No thought")
            tool = action_data.get("tool")
            args = action_data.get("args", {})
            
            print(f"\nStep {current_step} | Tool: {tool}")
            print(f"Thought: {thought}")

            # 2. Ejecución de Herramientas (Con Fix de None)
            tool_output: str = "" # Inicializar siempre
            
            try:
                if tool == "search_google":
                    results = self.searcher.search(args.get("query", ""))
                    tool_output = "\n".join([f"- [{r.title}]({r.url})" for r in results]) or "No results."

                elif tool == "inspect_article_structure":
                    struct = self.fetcher.get_article_structure(args.get("url", ""))
                    tool_output = f"Sections: {struct.sections}"

                elif tool == "read_section":
                    content = self.fetcher.get_section_content(args.get("url", ""), args.get("section_name", ""))
                    tool_output = content if content else "Section empty."

                elif tool == "add_to_memory":
                    self.memory.add_node(args.get("parent_id", "root"), args.get("topic", "Info"), args.get("content", ""))
                    tool_output = "Info stored."

                # NUEVA HERRAMIENTA EDR: Gestión de Tareas
                elif tool == "manage_tasks":
                    action = args.get("action") # add, complete
                    if action == "add":
                        tid = self.todo.add_task(args.get("description"), args.get("priority", 5))
                        tool_output = f"Task added ID {tid}"
                    elif action == "complete":
                        self.todo.complete_task(args.get("task_id"), "Done")
                        tool_output = "Task completed."

                elif tool == "answer_question":
                    final_answer = args.get("answer")
                    break

                else:
                    tool_output = "Unknown tool."

            except Exception as e:
                tool_output = f"Error: {e}"

            reasoning_trace.append({"step": current_step, "tool": tool, "result": str(tool_output)[:200]})

        return {"final_answer": final_answer, "trace": reasoning_trace}

    def _build_step_prompt(self, q, tree, plan, history):
        return f"""
GOAL: {q}

{plan}

KNOWLEDGE TREE:
{tree}

AVAILABLE TOOLS:
1. search_google(query)
2. inspect_article_structure(url)
3. read_section(url, section_name)
4. add_to_memory(parent_id, topic, content)
5. manage_tasks(action="add|complete", description="...", task_id="...") -> USE THIS TO UPDATE THE PLAN!
6. answer_question(answer)

HISTORY: {history}

Respond in JSON with 'thought', 'tool', and 'args'.
"""

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        clean_text = match.group(1) if match else text
        try:
            return json.loads(clean_text)
        except:
            # Fallback simple
            start = text.find('{')
            end = text.rfind('}') + 1
            return json.loads(text[start:end])