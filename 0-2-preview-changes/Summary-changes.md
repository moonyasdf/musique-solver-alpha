# Project Summary: musique-solver

## Current Version: v0.2.3

## Core Components

### 1. Reasoning Engine (`src/reasoning_engine.py`)
The central controller. It implements an autonomous loop that:
1.  Snapshots the current **Research Tree**.
2.  Sends the state to the LLM.
3.  Parses JSON actions.
4.  Executes tools (`search`, `inspect`, `read`, `store`).
5.  Updates the Tree.

### 2. Research Tree (`src/research_tree.py`)
A dynamic data structure inspired by *ChatIndex*. It allows the agent to:
- Create nodes for specific topics (e.g., "Director", "Location").
- Store evidence linked to those nodes.
- Retrieve a "Tree View" to understand the global state of the investigation without rereading text.

### 3. Wikipedia Fetcher (`src/wiki_fetcher.py`)
Updated to support **Multi-Resolution Access**:
- **Structure Mode:** Returns Title, Summary, and Section Headers.
- **Content Mode:** Returns text for a single requested section.

## Design Decisions

*   **Removal of Linear Decomposition:** We removed `question_decomposer.py`. The decomposition is now performed dynamically by the agent storing intermediate nodes in the Research Tree.
*   **JSON Protocol:** All agent-system communication happens via strict JSON to ensure complex arguments (like storing multi-line evidence) are handled correctly.