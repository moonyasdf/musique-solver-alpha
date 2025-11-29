# Changelog - Multi-Resolution Retrieval (EDR) Implementation

## Version 0.2.1 - Agentic Multi-Resolution Retrieval Refactor (2024)

### 🎯 **Core Objective**
Transitioned from "retrieve-and-dump" approach to **selective, multi-resolution retrieval workflow** to maximize reasoning accuracy while minimizing context usage.

### ✨ **Major Changes**

#### 1. **Selector Logic (No Context Flooding)**
- **Before**: System loaded full content or snippets from all top-k results immediately
- **After**: Agent receives **lightweight metadata only** (Title, URL, 2-line Snippet)
- Agent must **explicitly select** which single URL to inspect
- No full content delivered until agent requests specific sections

#### 2. **Multi-Resolution Retrieval Pipeline**
Enforced strict "Search → Select → Inspect → Target → Read" loop:
- **Macro (Search)**: Returns numbered list of Wikipedia results with titles/URLs/snippets
- **Meso (Inspect)**: Agent calls `inspect_article_structure(result_id)` to see Table of Contents
- **Micro (Read)**: Agent calls `read_section(section_name)` for specific section only

#### 3. **LLM Client Updates**
- Added support for **streaming mode** (configurable via `STREAMING` setting)
- Default configuration updated for ngrok endpoint support
- Base URL: `https://947d76b87e86.ngrok-free.app/v1`
- Default model: `deepseek-v3.1` (also supports `glm-4.6`, `deepseek-v3.2`)
- Increased default `max_tokens` to 2048 for longer reasoning chains

#### 4. **Enhanced Search Client**
- Rewrote `WikipediaSearchClient` with multiple backends:
  - Wikipedia API search (primary, with User-Agent headers)
  - Google Custom Search API (optional)
  - SerpAPI (optional)
  - HTML scraping fallback (with version compatibility fixes)
- Automatic snippet formatting to 2 lines maximum
- Better error handling and backend fallback logic

#### 5. **Reasoning Engine Improvements**
- Added `last_search_results` tracking for result_id-based selection
- Added `last_inspected_url` to automatically carry URL context
- Enhanced tool output formatting with emojis and clear warnings
- Support for both `url` and `result_id` parameters in `inspect_article_structure`
- Automatic URL inference for `read_section` from last inspected article
- Increased trace retention from 200 to 500 characters
- Extended `max_steps` from 25 to 30 to accommodate more thorough research

#### 6. **System Prompt Overhaul**
Completely rewrote `agent_system_prompt.txt` to emphasize:
- **Selector-based workflow** (no automatic content flooding)
- **Multi-resolution retrieval** with explicit state machine
- **Evidence-first verification** (never trust pre-training)
- **Structured memory** with hierarchical knowledge tree
- **Plan-driven reasoning** with TODO task management

Key sections:
1. Role & Principles (selective retrieval, structured memory)
2. Tool Interface with strict contracts
3. Question Decomposition Rules
4. Mandatory State Machine (8-step reasoning loop)
5. Planning & Reflection Protocol
6. Output Format & Traceability
7. Verification & Backtracking

#### 7. **TODO Task Management**
- Enhanced `ResearchTodoManager` with `complete_all()` method
- Better error handling (raises error if task_id not found)
- Improved plan view formatting for LLM

#### 8. **Testing Infrastructure**
- Added `test_connection.py`: Quick connectivity test for LLM endpoint
- Added `test_simple_question.py`: Validation with simple 1-hop question
- Both tests verify the full pipeline without expensive multi-hop evaluations

### 🔧 **Configuration Changes**

#### Updated Defaults in `config.py`:
```python
openai_api_key = "sk-local-master"  # Changed from empty
openai_api_base = "https://947d76b87e86.ngrok-free.app/v1"  # Updated for ngrok
openai_model = "deepseek-v3.1"  # Changed from gpt-4
temperature = 0.0  # Changed from 0.2 for more deterministic reasoning
streaming = true  # New setting for streaming mode
```

#### New Environment Variables:
- `STREAMING`: Enable/disable streaming mode (default: true)

### 📝 **Tool Contract Changes**

#### `search_google(query)`
- Returns formatted numbered list: `[1] Title: ... URL: ... Snippet: ...`
- Adds warning: "⚠️ YOU MUST SELECT ONE result by calling inspect_article_structure"

#### `inspect_article_structure(result_id?, url?)`
- **New**: Accepts `result_id` (1-based index from last search)
- Falls back to explicit `url` if provided
- Returns: Title, URL, Summary (500 chars), numbered TOC
- Adds warning: "⚠️ YOU MUST SELECT ONE SECTION TO READ"

#### `read_section(section_name, url?)`
- **New**: Automatically uses last inspected URL if not provided
- Requires `section_name` from inspected TOC
- Returns: Full section content with header

#### `add_to_memory(parent_id, topic, content, source_url?)`
- **New**: Auto-fills `source_url` from last inspected article if omitted

#### `manage_tasks(action, description?, priority?, task_id?, result?)`
- Enhanced error handling (validates required parameters)
- Better output messages with task IDs

#### `answer_question(answer)`
- **New**: Auto-completes all pending tasks when called
- Prevents finishing with open TODO items

### 🐛 **Bug Fixes**
- Fixed Wikipedia API 403 errors by adding proper User-Agent headers
- Fixed googlesearch-python version compatibility (supports `stop`, `num_results`, and no-param versions)
- Fixed search backend fallback logic to gracefully handle failures
- Fixed JSON parsing to handle both code-fenced and raw JSON responses

### 📊 **Expected Impact**
- **Context Usage**: Reduced from 10k+ tokens (full articles) to <2k tokens (selective sections)
- **Precision**: Higher accuracy due to focused reading and reduced "lost-in-the-middle" errors
- **Reasoning Quality**: Clearer chains with explicit selection decisions
- **Transparency**: Full trace shows which URLs were chosen and why

### 🧪 **Testing**
Run the test suite:
```bash
# Quick connection test
python test_connection.py

# Simple 1-hop question
python test_simple_question.py

# Full evaluation (10 random questions)
python evaluation/run_eval.py --sample-size 10 --seed 42
```

### 🚀 **Usage**
Single question:
```bash
python query_single.py "Who directed Inception?"
```

The system will now:
1. Search Wikipedia and show 5 results with snippets
2. Agent selects the most relevant result (e.g., result #1)
3. Inspect that article's structure (TOC)
4. Agent identifies the relevant section (e.g., lead summary)
5. Read only that section
6. Store fact in memory
7. Answer the question

No context flooding, no irrelevant content—only deliberate, selective retrieval.

---

## Migration Notes

### For Users
- Update `.env` file with new defaults (or let config.py use ngrok endpoint)
- No breaking changes to external API

### For Developers
- `search_google` now returns SearchResult objects with title, URL, snippet
- `inspect_article_structure` accepts `result_id` (preferred) or `url`
- `read_section` can omit `url` if article was just inspected
- System prompt is now the single source of truth for agent behavior

---

## Known Limitations
- Wikipedia API has rate limits (handled with 1s delay between requests)
- Some Wikipedia pages have complex TOC structures that may confuse section matching
- Streaming mode collects full response before returning (not true chunk-by-chunk streaming to user)

---

## Next Steps
- Implement caching layer for frequently accessed Wikipedia articles
- Add support for disambiguation page handling
- Implement multi-LLM support (different models for different hops)
- Add confidence scoring for each hop
- Implement automatic backtracking on low-confidence answers
