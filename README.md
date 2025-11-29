# musique-solver

A state-of-the-art MuSiQue solver leveraging agentic deep-research methodology with iterative question decomposition and Wikipedia-only web search.

## Overview

This project implements a sophisticated multi-hop question answering system designed to solve complex 4-hop questions from the MuSiQue benchmark. The system uses:

- **Iterative Question Decomposition (IQD)**: Breaking complex questions into sequential sub-questions
- **Stepwise Evidence Accumulation (SEA)**: Search→Read→Reason loop for each hop
- **Wikipedia-Only Search**: Constrained to Wikipedia for verifiable information
- **Full Article Reading**: Processes complete Wikipedia articles in Markdown format
- **Self-Verification**: Validates reasoning chains and answers

## Architecture

```
musique-solver/
├── src/
│   ├── web_search.py          # Google search with Wikipedia filter
│   ├── wiki_fetcher.py         # Wikipedia content retrieval & Markdown conversion
│   ├── question_decomposer.py  # Iterative question decomposition
│   ├── reasoning_engine.py     # Main SEARCH→READ→REASON loop
│   ├── answer_synthesizer.py   # Final answer generation & verification
│   ├── memory_store.py         # Simple key-value store (no embeddings)
│   ├── llm_client.py          # OpenAI-compatible LLM client
│   └── utils.py               # Utility functions
│
├── prompts/
│   └── agent_system_prompt.txt # Static system prompt for all questions
│
├── evaluation/
│   ├── run_eval.py            # Main evaluation script
│   ├── random_sampler.py      # Random question sampler
│   └── results/               # Evaluation results
│
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
└── musique_4hop_all_questions.json  # Benchmark dataset
```

## Installation

1. **Clone the repository** (if not already in it):
```bash
git clone <repository-url>
cd musique-solver
```

2. **Create a virtual environment** (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:

Create a `.env` file in the project root:

```bash
# Required: LLM API Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1  # Or your custom endpoint
OPENAI_MODEL=gpt-4  # Or gpt-4-turbo, gpt-3.5-turbo, etc.

# Optional: Search Configuration (choose one)
# Option 1: Google Custom Search API
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_custom_search_engine_id

# Option 2: SerpAPI
SERPAPI_KEY=your_serpapi_key

# Optional: Adjust these if needed
SEARCH_DELAY=2.0
MAX_SEARCH_RESULTS=5
MAX_HOPS=6
MAX_RETRIES=3
TEMPERATURE=0.2
```

## Usage

### Quick Connection Test
Make sure the configured LLM endpoint is reachable before running expensive evaluations:

```bash
python test_connection.py
```

### Running Evaluation

To evaluate the system on 10 random questions:

```bash
python evaluation/run_eval.py
```

With custom parameters:

```bash
python evaluation/run_eval.py --sample-size 10 --seed 42 --run-name my_first_run
```

Parameters:
- `--sample-size`: Number of questions to sample (default: 10)
- `--seed`: Random seed for reproducibility (default: 42)
- `--run-name`: Name for the evaluation run (default: auto-generated timestamp)

### Results

After running evaluation, results are saved in `evaluation/results/<run_name>/`:

- `questions.json`: Sampled questions with ground truth
- `responses.json`: Agent responses with full reasoning traces
- `summary.json`: Run metadata and configuration

### Manual Evaluation

After running the evaluation, you need to manually assess correctness:

1. Review `responses.json` to check if agent answers match ground truth
2. Analyze reasoning traces for each question
3. Create an `evaluation.json` file with your assessment:

```json
{
  "run_name": "run_001",
  "evaluator": "Your Name",
  "date": "2024-XX-XX",
  "results": [
    {
      "question_id": "...",
      "correct": true,
      "reasoning_quality": "good",
      "notes": "..."
    }
  ],
  "summary": {
    "total_correct": 7,
    "accuracy": 0.70
  }
}
```

## Key Design Principles

### 1. No Cheating
- **No embeddings or vector databases**: Only key-value storage
- **Wikipedia-only**: Search is strictly filtered to `site:wikipedia.org`
- **Full article reading**: Complete articles are processed, not snippets
- **Evidence-based**: Every claim must be backed by article text

### 2. Iterative Decomposition
- Sub-questions are generated **one at a time** as answers are found
- Each sub-question incorporates answers from previous hops
- Dynamic adjustment based on intermediate results

### 3. Static System Prompt
- The same system prompt is used for **all questions**
- No question-specific hints or modifications
- Prompts focus on reasoning process, not domain knowledge

### 4. Search-Read-Reason Loop
For each sub-question:
1. **SEARCH**: Formulate queries and search Wikipedia
2. **READ**: Fetch and read the complete article
3. **REASON**: Extract answer with evidence
4. **VERIFY**: Check if answer addresses the sub-question
5. **BACKTRACK**: If needed, try alternative queries or articles

### 5. Selector-Based Multi-Resolution Retrieval
To avoid context flooding, the agent now uses a strictly enforced selector workflow:
1. **Search (Macro)** – `search_google` returns metadata-only results (Title, URL, 2-line snippet) in a numbered list.
2. **Select** – The agent must pick exactly one `result_id` based on the snippets provided.
3. **Inspect (Meso)** – `inspect_article_structure(result_id)` reveals the article's lead summary and Table of Contents.
4. **Target** – The agent chooses the most relevant section header.
5. **Read (Micro)** – `read_section(section_name)` fetches the full text for that specific section only.
6. **Store & Plan** – Extracted facts are stored via `add_to_memory`, and the TODO plan is updated with `manage_tasks`.
7. **Answer** – Once all hops are satisfied with evidence, the agent calls `answer_question`.

This multi-resolution loop dramatically reduces token usage while improving reasoning precision.

## Configuration

Edit `config.py` or use environment variables to customize:

- `MAX_HOPS`: Maximum number of sub-questions (default: 6)
- `MAX_RETRIES`: Maximum search attempts per sub-question (default: 3)
- `TEMPERATURE`: LLM temperature for reasoning (default: 0.2)
- `SEARCH_DELAY`: Delay between searches in seconds (default: 2.0)
- `MAX_SEARCH_RESULTS`: Number of search results to consider (default: 5)

## Iteration Process

The system is designed to be iteratively improved:

1. **Run evaluation** on 10 random questions
2. **Analyze failures**: Identify patterns in incorrect answers
3. **Diagnose issues**:
   - Question decomposition failures?
   - Search query formulation problems?
   - Article reading/comprehension issues?
   - Answer synthesis errors?
4. **Make improvements** to:
   - System prompt
   - Query generation logic
   - Answer extraction prompts
   - Verification mechanisms
5. **Re-evaluate** with different random sample
6. **Document changes** and impact

## Search Configuration Options

The system supports multiple search backends:

### Option 1: Google Custom Search API (Recommended)
1. Create a Custom Search Engine at https://cse.google.com/
2. Restrict it to `*.wikipedia.org`
3. Get API key from Google Cloud Console
4. Set `GOOGLE_API_KEY` and `GOOGLE_CSE_ID`

### Option 2: SerpAPI
1. Sign up at https://serpapi.com/
2. Get API key
3. Set `SERPAPI_KEY`

### Option 3: HTML Scraping (Fallback)
If neither API is configured, the system will attempt HTML scraping (less reliable, respects rate limits).

## Troubleshooting

### ImportError: No module named 'openai'
```bash
pip install openai
```

### Search not working
- Verify API keys are correct in `.env`
- Check rate limits and quotas
- Ensure `site:wikipedia.org` filter is applied

### LLM responses incomplete
- Increase `max_tokens` in LLM client
- Check if your model supports the context size needed for full articles

### Out of memory
- Reduce `MAX_SEARCH_RESULTS`
- Implement article truncation (with caution - may hurt accuracy)

## Example Question Flow

**Question**: "Who is the president of the newly declared independent country that established the Timor Leste Commission of Truth and Friendship?"

**Decomposition**:
1. Q1: "What country established the Timor Leste Commission of Truth and Friendship?"
   - Search: `site:wikipedia.org Timor Leste Commission Truth Friendship`
   - Answer: "East Timor"

2. Q2: "Who is the president of East Timor?"
   - Search: `site:wikipedia.org East Timor president`
   - Answer: "Francisco Guterres"

**Final Answer**: "Francisco Guterres"

## Performance Expectations

- **Initial accuracy**: 30-50% (typical for first run)
- **Target accuracy**: 60-70% (after iteration)
- **Time per question**: 1-3 minutes (depending on complexity and API speed)

## Contributing

When improving the system:
1. Test changes on a new random sample
2. Document what was changed and why
3. Compare accuracy before/after
4. Update this README if configuration changes

## License

This project is released under the [MIT License](LICENSE).

## Acknowledgments

Based on research in multi-hop question answering and iterative decomposition methods for complex reasoning tasks.
