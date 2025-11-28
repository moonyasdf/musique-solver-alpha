# musique-solver (v0.2)

A state-of-the-art MuSiQue solver leveraging **Dynamic Knowledge Trees** and **Multi-Resolution Retrieval**.

## Architecture Overview (v0.2)

Unlike standard RAG pipelines that retrieve chunks based on semantic similarity, this system acts as an **Autonomous Research Agent**. It builds a hierarchical mental model of the information it finds, classifying insights dynamically as it navigates Wikipedia.

### Key Features
1.  **Research Tree Memory**: Data is stored in a structured tree (Nodes/Topics), not a flat list.
2.  **Multi-Resolution Reading**: The agent inspects Article Structures (TOCs) before reading specific sections, drastically reducing noise.
3.  **JSON-Control Flow**: The agent drives its own loop using structured actions (`inspect`, `read`, `add_to_memory`).

## Directory Structure

```
musique-solver/
├── src/
│   ├── reasoning_engine.py     # The Agent Loop (JSON Logic)
│   ├── research_tree.py        # Dynamic Knowledge Graph implementation
│   ├── wiki_fetcher.py         # Structured Wikipedia Parser (TOC/Section)
│   ├── web_search.py           # Google Search wrapper
│   ├── llm_client.py           # OpenAI Client
│   └── utils.py                # Type-safe utilities
│
├── prompts/
│   └── agent_system_prompt.txt # The "Brain" instructions
│
├── evaluation/
│   └── run_eval.py             # Evaluation script
```

## Quick Start

1.  **Install Requirements:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure `.env`**:
    (See `config.py` for required keys: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.)
3.  **Run a Single Query:**
    ```bash
    python query_single.py "Who is the director of Inception?"
    ```
4.  **Run Benchmark:**
    ```bash
    python evaluation/run_eval.py --sample-size 10
    ```