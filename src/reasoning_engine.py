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
        self.max_steps = 40
        self.last_search_results = []  # Track results for result_id selection
        self.last_inspected_url = None  # Track last inspected article
        self.history_window = 4  # Number of previous steps to show the LLM
        self.history_truncate_chars = 1600

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
            
            prompt = self._build_step_prompt(
                question, 
                tree_snapshot, 
                plan_snapshot, 
                reasoning_trace[-self.history_window:]
            )
            
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
                    self.last_search_results = results  # Store for result_id selection
                    # Format search results with numbered list showing metadata only
                    if results:
                        formatted = ["SEARCH RESULTS (Metadata Only - NO Full Content):"]
                        for i, r in enumerate(results, 1):
                            formatted.append(f"\n[{i}] Title: {r.title}")
                            formatted.append(f"    URL: {r.url}")
                            if r.snippet:
                                formatted.append(f"    Snippet: {r.snippet}")
                        formatted.append("\n⚠️ YOU MUST SELECT ONE result by calling inspect_article_structure with the URL or result number.")
                        tool_output = "\n".join(formatted)
                    else:
                        tool_output = "No results found. Try a different query."

                elif tool == "inspect_article_structure":
                    # Support both URL and result_id
                    url = args.get("url")
                    result_id = args.get("result_id")
                    
                    if result_id is not None:
                        # Convert result_id to int and get URL from last search
                        try:
                            idx = int(result_id) - 1
                            if 0 <= idx < len(self.last_search_results):
                                url = self.last_search_results[idx].url
                            else:
                                tool_output = f"❌ Invalid result_id: {result_id}. Must be 1-{len(self.last_search_results)}"
                                raise ValueError("Invalid result_id")
                        except (ValueError, TypeError):
                            tool_output = f"❌ Invalid result_id format: {result_id}"
                            raise
                    
                    if not url:
                        tool_output = "❌ Must provide either 'url' or 'result_id'"
                        raise ValueError("Missing URL")
                    
                    self.last_inspected_url = url  # Track for read_section
                    struct = self.fetcher.get_article_structure(url)
                    
                    # Format structure view (ToC) - Show full summary if short, truncate if long
                    formatted = [f"📄 ARTICLE: {struct.title}"]
                    formatted.append(f"    URL: {url}")
                    summary_text = struct.summary
                    if len(summary_text) > 1000:
                        formatted.append(f"\n📝 SUMMARY (Lead Section, truncated):\n{summary_text[:1000]}...")
                    else:
                        formatted.append(f"\n📝 SUMMARY (Lead Section):\n{summary_text}")
                    formatted.append(f"\n📑 TABLE OF CONTENTS (Sections):")
                    for i, sec in enumerate(struct.sections, 1):
                        formatted.append(f"  [{i}] {sec}")
                    formatted.append("\n⚠️ YOU MUST SELECT ONE SECTION TO READ (use read_section with section_name).")
                    formatted.append("💡 TIP: If the lead summary contains your answer, you can proceed to add_to_memory directly.")
                    tool_output = "\n".join(formatted)

                elif tool == "read_section":
                    # Use last inspected URL if not provided
                    url = args.get("url") or self.last_inspected_url
                    section_name = args.get("section_name", "").strip()
                    
                    if not url:
                        tool_output = "❌ No article currently inspected. Inspect an article first."
                        raise ValueError("No inspected article")
                    
                    # If no section name or requesting "lead"/"summary"/"intro", return lead section
                    if not section_name or section_name.lower() in ["lead", "summary", "intro", "introduction", "lead section"]:
                        struct = self.fetcher.get_article_structure(url)
                        tool_output = f"📖 LEAD SECTION CONTENT:\n{struct.summary}"
                    else:
                        content = self.fetcher.get_section_content(url, section_name)
                        if content:
                            tool_output = f"📖 SECTION CONTENT ({section_name}):\n{content}"
                        else:
                            tool_output = f"Section '{section_name}' not found or empty. Check the ToC again."

                elif tool == "add_to_memory":
                    source_url = args.get("source_url") or self.last_inspected_url or ""
                    node_id = self.memory.add_node(
                        args.get("parent_id", "root"), 
                        args.get("topic", "Info"), 
                        args.get("content", ""),
                        source_url
                    )
                    tool_output = f"✓ Info stored in node [{node_id}]."

                # NUEVA HERRAMIENTA EDR: Gestión de Tareas
                elif tool == "manage_tasks":
                    action = args.get("action") # add, complete
                    if action == "add":
                        description = args.get("description")
                        if not description:
                            raise ValueError("Description required when adding a task")
                        tid = self.todo.add_task(description, args.get("priority", 5))
                        tool_output = f"✓ Task added ID {tid}"
                    elif action == "complete":
                        task_id = args.get("task_id")
                        if not task_id:
                            raise ValueError("task_id required to complete a task")
                        result_note = args.get("result", "Done")
                        self.todo.complete_task(task_id, result_note)
                        tool_output = f"✓ Task {task_id} marked complete."
                    else:
                        raise ValueError("Unknown manage_tasks action")

                elif tool == "answer_question":
                    final_answer = args.get("answer")
                    self.todo.complete_all(final_answer or "Answered")
                    tool_output = f"✅ Final answer recorded: {final_answer}"
                    print(f"\n🎯 FINAL ANSWER: {final_answer}")
                    break

                else:
                    tool_output = f"❌ Unknown tool: {tool}"

            except Exception as e:
                tool_output = f"❌ Error: {e}"
                logger.error(f"Tool execution error: {e}", exc_info=True)

            reasoning_trace.append({
                "step": current_step, 
                "thought": thought,
                "tool": tool, 
                "args": args,
                "result": tool_output
            })

        return {
            "final_answer": final_answer, 
            "trace": reasoning_trace,
            "tree_state": self.memory.to_json(),
            "plan_state": self.todo.get_plan_view()
        }

    def _build_step_prompt(self, q, tree, plan, history):
        tree_view = tree.replace("KNOWLEDGE TREE:\n", "", 1) if tree.startswith("KNOWLEDGE TREE") else tree
        
        # Truncate history for better context window management
        if history:
            truncated_history = []
            for h in history:
                h_copy = dict(h)
                if 'result' in h_copy and len(str(h_copy['result'])) > self.history_truncate_chars:
                    h_copy['result'] = str(h_copy['result'])[:self.history_truncate_chars] + "... [truncated]"
                truncated_history.append(h_copy)
            history_text = json.dumps(truncated_history, ensure_ascii=False, indent=2)
        else:
            history_text = "[]"

        return f"""
GOAL: {q}

{plan}

RESEARCH TREE (ID :: TOPIC):
{tree_view}

REMINDERS:
- ALWAYS follow: REFLECT → SEARCH → SELECT → INSPECT → TARGET → READ → STORE → PLAN.
- Use search result_id (preferred) or exact URL when calling inspect_article_structure.
- The lead summary shown in inspect_article_structure IS THE FULL CONTENT - no need to read_section again if it's there.
- Only call read_section if you need a DIFFERENT section from the ToC, or if the lead was too short.
- Every verified fact must be saved with add_to_memory (include parent_id, topic, content, source_url).
- Keep the TODO list accurate with manage_tasks before launching new searches.
- Never fabricate URLs or section names.
- After finding a fact, IMMEDIATELY add_to_memory and manage_tasks to mark progress.

RECENT STEPS (Last {len(history)}):
{history_text}

Respond ONLY with JSON containing 'thought', 'tool', and 'args'.
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