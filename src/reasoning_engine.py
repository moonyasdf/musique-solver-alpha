"""Reasoning Engine with Anti-Looping Mechanism and Full Debug Visibility."""
from __future__ import annotations
import logging
import json
import re
import time
from typing import Dict, Any, List

from .llm_client import LLMClient
from .web_search import WikipediaSearchClient
from .wiki_fetcher import WikipediaArticleFetcher
from .research_tree import ResearchTree
from .todo_manager import ResearchTodoManager

logger = logging.getLogger(__name__)

class ReasoningEngine:
    def __init__(self, llm: LLMClient, searcher: WikipediaSearchClient, fetcher: WikipediaArticleFetcher):
        self.llm = llm
        self.searcher = searcher
        self.fetcher = fetcher
        self.memory = ResearchTree()
        self.todo = ResearchTodoManager()
        self.max_steps = 40
        self.history_window = 15
        
        # State tracking for Anti-Looping
        self.last_action_hash = None
        self.loop_counter = 0

    def solve(self, question: str) -> Dict[str, Any]:
        self.memory.add_node("root", "Goal", question)
        self.todo.add_task(f"Decompose and answer: {question}", priority=10)
        
        reasoning_trace = []
        current_step = 0
        final_answer = None

        print(f"\n{'='*60}")
        print(f"🚀 STARTING QUESTION: {question}")
        print(f"{'='*60}")

        while current_step < self.max_steps:
            current_step += 1
            
            tree_snapshot = self.memory.get_tree_view(include_content=True)
            plan_snapshot = self.todo.get_plan_view()
            
            prompt = self._build_step_prompt(
                question, 
                tree_snapshot, 
                plan_snapshot, 
                reasoning_trace[-self.history_window:]
            )
            
            # --- LLM CALL WITH RETRY ---
            response_text = ""
            for attempt in range(3):
                try:
                    response_text = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
                    break
                except Exception as e:
                    if "429" in str(e) or "Rate limit" in str(e):
                        wait = 5 * (attempt + 1)
                        print(f"\n⚠️ Rate Limit. Waiting {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"❌ LLM ERROR: {e}")
                        time.sleep(2)
                        break
            
            if not response_text:
                continue

            action_data = self._parse_json_response(response_text)
            thought = action_data.get("thought", "No thought")
            tool = action_data.get("tool")
            args = action_data.get("args", {})
            
            print(f"\nStep {current_step} | Tool: \033[94m{tool}\033[0m") 
            print(f"Thought: {thought}")

            # --- ANTI-LOOPING MECHANISM ---
            # Creamos una firma de la acción actual
            current_action_hash = f"{tool}:{json.dumps(args, sort_keys=True)}"
            
            if current_action_hash == self.last_action_hash:
                self.loop_counter += 1
            else:
                self.loop_counter = 0
                self.last_action_hash = current_action_hash

            # Si intenta lo mismo 2 veces seguidas, bloqueamos
            if self.loop_counter >= 1:
                print(f"\033[91m⛔ LOOP DETECTED ({self.loop_counter}). FORCING STOP.\033[0m")
                tool_output = "SYSTEM ERROR: You are stuck in a loop repeating the EXACT same action. STOP. Do not inspect the same article again. Do not search the same query again. Try reading a specific section or searching for something else."
            
            else:
                # --- TOOL EXECUTION ---
                try:
                    tool_output = self._execute_tool(tool, args)
                except Exception as e:
                    tool_output = f"❌ Execution Error: {e}"
                    logger.error(f"Tool error: {e}", exc_info=True)

            # --- DEBUG OUTPUT (FULL VISIBILITY) ---
            # Imprimimos TODO lo que sea Table of Contents para que veas qué recibe
            if "TABLE OF CONTENTS" in tool_output:
                print(f"Result (DEBUG VIEW):\n{tool_output}") 
            else:
                # Para otros resultados, truncamos para no ensuciar tanto
                clean_out = tool_output.replace('\n', ' ')
                print(f"Result: \033[92m{clean_out[:300]}\033[0m" + ("..." if len(clean_out)>300 else ""))

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

    def _execute_tool(self, tool, args) -> str:
        """Helper to keep main loop clean."""
        if tool == "search_google":
            results = self.searcher.search(args.get("query", ""))
            self.last_search_results = results
            if results:
                formatted = ["SEARCH RESULTS (Metadata Only):"]
                for i, r in enumerate(results, 1):
                    formatted.append(f"\n[{i}] Title: {r.title}")
                    formatted.append(f"    URL: {r.url}")
                    if r.snippet: formatted.append(f"    Snippet: {r.snippet}")
                formatted.append("\n⚠️ YOU MUST SELECT ONE result by calling inspect_article_structure.")
                return "\n".join(formatted)
            return "No results found. Try a different query."

        elif tool == "inspect_article_structure":
            url = args.get("url")
            result_id = args.get("result_id")
            
            target_url = None
            if result_id is not None:
                try:
                    idx = int(result_id) - 1
                    if 0 <= idx < len(self.last_search_results):
                        target_url = self.last_search_results[idx].url
                    else: return f"❌ Invalid result_id: {result_id}."
                except: return f"❌ Invalid result_id format."
            elif url: target_url = url
            
            if not target_url: return "❌ Must provide either 'url' or 'result_id'"
            
            self.last_inspected_url = target_url
            struct = self.fetcher.get_article_structure(target_url)
            
            formatted = [f"📄 ARTICLE: {struct.title}"]
            formatted.append(f"    URL: {target_url}")
            
            # Resumen con límite amplio
            summary_text = struct.summary
            if len(summary_text) > 4000:
                formatted.append(f"\n📝 SUMMARY (Lead, truncated):\n{summary_text[:4000]}...")
            else:
                formatted.append(f"\n📝 SUMMARY (Lead Section):\n{summary_text}")
            
            formatted.append(f"\n📑 TABLE OF CONTENTS (Sections):")
            if not struct.sections:
                formatted.append("  (No specific sections found via API. The Lead Section contains the content.)")
            else:
                for i, sec in enumerate(struct.sections, 1):
                    formatted.append(f"  [{i}] {sec}")
                    
            formatted.append("\n⚠️ ACTION REQUIRED: Select a section to read (use read_section).")
            return "\n".join(formatted)

        elif tool == "read_section":
            url = args.get("url") or self.last_inspected_url
            section_name = args.get("section_name", "").strip()
            
            if not url: return "❌ No article inspected. You must Inspect first."
            
            lead_aliases = ["", "lead", "summary", "intro", "introduction", "lead section", "overview", "0"]
            
            if section_name.lower() in lead_aliases:
                struct = self.fetcher.get_article_structure(url)
                return f"📖 LEAD SECTION CONTENT:\n{struct.summary}"
            else:
                content = self.fetcher.get_section_content(url, section_name)
                if "not found" in content.lower():
                        return f"❌ {content} -> Please check the ToC list again exactly."
                return f"📖 SECTION CONTENT ({section_name}):\n{content}"

        elif tool == "add_to_memory":
            source_url = args.get("source_url") or self.last_inspected_url or ""
            node_id = self.memory.add_node(
                args.get("parent_id", "root"), args.get("topic", "Info"), 
                args.get("content", ""), source_url
            )
            return f"✓ Info stored in node [{node_id}]."

        elif tool == "manage_tasks":
            action = args.get("action")
            if action == "add":
                tid = self.todo.add_task(args.get("description", ""), args.get("priority", 5))
                return f"✓ Task added ID {tid}"
            elif action == "complete":
                self.todo.complete_task(args.get("task_id"), args.get("result", "Done"))
                return f"✓ Task {args.get('task_id')} marked complete."
            return "❌ Unknown action"

        elif tool == "answer_question":
            final_answer = args.get("answer")
            self.todo.complete_all(final_answer or "Answered")
            return f"✅ Final answer recorded: {final_answer}"

        return f"❌ Unknown tool: {tool}"

    def _build_step_prompt(self, q, tree, plan, history: List[Dict]):
        # Convertir historial a narrativa de texto
        history_text_list = []
        for h in history:
            entry = f"Step {h['step']}: {h['thought']}\n"
            args_str = ", ".join([f"{k}='{v}'" for k, v in h['args'].items() if k != 'content']) 
            entry += f"Action: {h['tool']}({args_str})\n"
            
            # Truncado inteligente para el prompt
            result_preview = str(h.get('result', ''))
            if len(result_preview) > 1200: # Un poco más de contexto para ToCs largos
                result_preview = result_preview[:1200] + "... [Content truncated for memory]"
            entry += f"Observation: {result_preview}"
            history_text_list.append(entry)
            
        history_text = "\n\n".join(history_text_list) if history_text_list else "(No actions taken yet)"
        if tree.startswith("KNOWLEDGE TREE"):
            tree_view = tree.split("\n", 1)[1] if "\n" in tree else ""
        else:
            tree_view = tree

        return f"""
GOAL: {q}

{plan}

*** KNOWLEDGE GATHERED SO FAR (Research Tree) ***
{tree_view}
*************************************************

PAST ACTIONS (Last {len(history)} steps):
{history_text}

INSTRUCTIONS:
1. REVIEW the "KNOWLEDGE GATHERED". If you already have the answer to a sub-question there, DO NOT SEARCH AGAIN.
2. If the summary says a search failed, try a completely different query.
3. If you inspect an article and the section you want isn't there, READ THE LEAD SECTION AGAIN or search for a new article.
4. DO NOT LOOP. If you just did an action and it didn't help, trying it again won't help. Change strategy.

Respond ONLY with JSON containing 'thought', 'tool', and 'args'.
"""

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        clean_text = match.group(1) if match else text
        try:
            return json.loads(clean_text)
        except:
            try:
                start = text.find('{')
                end = text.rfind('}') + 1
                return json.loads(text[start:end])
            except:
                return {"tool": "error", "thought": "Failed to parse JSON", "args": {}}