# Project Summary: musique-solver

## Overview

This is a comprehensive implementation of a state-of-the-art MuSiQue multi-hop question answering system. The system uses **Iterative Question Decomposition (IQD)** and **Stepwise Evidence Accumulation (SEA)** to solve complex 4-hop questions by breaking them into sequential sub-questions, searching Wikipedia, reading complete articles, and synthesizing final answers.

## Architecture Overview

The system is organized into modular components following best practices:

```
musique-solver/
├── src/                    # Core implementation
│   ├── web_search.py       # Google search with Wikipedia filter
│   ├── wiki_fetcher.py     # Article retrieval and Markdown conversion
│   ├── question_decomposer.py  # Iterative question breakdown
│   ├── reasoning_engine.py     # Main SEARCH→READ→REASON loop
│   ├── answer_synthesizer.py   # Final answer generation
│   ├── memory_store.py         # Simple key-value storage
│   ├── llm_client.py          # OpenAI-compatible LLM wrapper
│   ├── logger.py              # Result logging
│   └── utils.py               # Utility functions
│
├── prompts/
│   └── agent_system_prompt.txt  # Static system prompt
│
├── evaluation/
│   ├── run_eval.py           # Main evaluation script
│   ├── random_sampler.py     # Question sampling
│   ├── iteration_log.md      # Template for documenting iterations
│   └── results/              # Evaluation results directory
│
├── tests/
│   └── test_components.py    # Unit tests
│
├── config.py                 # Configuration management
├── query_single.py           # CLI for single questions
├── musique_4hop_all_questions.json  # Benchmark dataset
│
└── Documentation:
    ├── README.md             # Full documentation
    ├── GETTING_STARTED.md    # Quick start guide
    └── PROJECT_SUMMARY.md    # This file
```

## Key Components Explained

### 1. Question Decomposer (`src/question_decomposer.py`)
- **Purpose**: Break complex questions into simpler sub-questions
- **Method**: Iterative decomposition (one sub-question at a time)
- **Key Feature**: Each new sub-question uses answers from previous hops

### 2. Web Search Client (`src/web_search.py`)
- **Purpose**: Search Google with Wikipedia-only filter
- **Support**: Multiple backends (Google Custom Search, SerpAPI, HTML scraping)
- **Key Feature**: Enforces `site:wikipedia.org` filter on all queries

### 3. Wikipedia Fetcher (`src/wiki_fetcher.py`)
- **Purpose**: Retrieve and process Wikipedia articles
- **Output**: Full article text converted to clean Markdown
- **Key Feature**: Preserves complete article context, removes only navigation elements

### 4. Reasoning Engine (`src/reasoning_engine.py`)
- **Purpose**: Coordinate the entire reasoning process
- **Process**: 
  1. Decompose question
  2. For each sub-question: SEARCH → READ → REASON
  3. Synthesize final answer
  4. Verify answer
- **Key Feature**: Maintains full reasoning trace for transparency

### 5. Answer Synthesizer (`src/answer_synthesizer.py`)
- **Purpose**: Generate final answers from reasoning chains
- **Method**: LLM synthesis with verification
- **Key Feature**: Checks if proposed answer is supported by evidence

### 6. Memory Store (`src/memory_store.py`)
- **Purpose**: Cache articles and facts within a session
- **Method**: Simple key-value store (JSON-based)
- **Key Feature**: NO embeddings, NO vector databases (per requirements)

### 7. LLM Client (`src/llm_client.py`)
- **Purpose**: Wrapper for OpenAI-compatible APIs
- **Support**: OpenAI, Azure OpenAI, custom endpoints
- **Key Feature**: Configurable system prompts and parameters

## System Workflow

### Processing a Single Question

```
1. Question Input: "Who is the president of the country that established the Timor Leste Commission?"

2. Decomposition (First Hop):
   └─> Sub-Q1: "What country established the Timor Leste Commission of Truth and Friendship?"

3. Search-Read-Reason Loop (Hop 1):
   ├─> SEARCH: "site:wikipedia.org Timor Leste Commission Truth Friendship"
   ├─> RESULTS: [Wikipedia URL list]
   ├─> READ: Fetch and convert full article to Markdown
   ├─> REASON: Extract answer from article
   └─> ANSWER: "East Timor"

4. Decomposition (Second Hop):
   └─> Sub-Q2: "Who is the president of East Timor?" (incorporates previous answer)

5. Search-Read-Reason Loop (Hop 2):
   ├─> SEARCH: "site:wikipedia.org East Timor president"
   ├─> READ: Full article on East Timor
   ├─> REASON: Find president information
   └─> ANSWER: "Francisco Guterres"

6. Synthesis:
   └─> FINAL ANSWER: "Francisco Guterres"

7. Verification:
   └─> Check if reasoning chain supports answer
```

## Design Principles

### 1. No Cheating
- **Only Wikipedia**: All information must come from Wikipedia
- **Full Reading**: Complete articles are processed, not snippets
- **Evidence Required**: Every answer must cite specific evidence
- **No Pre-Training Leakage**: Agent must search and read, not recall from training

### 2. Transparency
- **Full Traces**: Every reasoning step is logged
- **Search Queries**: All queries are recorded
- **Articles Read**: URLs of all accessed articles are saved
- **Evidence Chains**: Clear path from question to answer

### 3. Modularity
- **Independent Components**: Each module has single responsibility
- **Easy Testing**: Components can be tested in isolation
- **Swappable Backends**: Search and LLM backends are configurable
- **Configuration-Driven**: Behavior controlled via config, not code

### 4. Iteration-Friendly
- **Result Logging**: Structured output for analysis
- **Failure Tracking**: Errors are captured with context
- **Prompt Versioning**: System prompt is in separate file
- **Reproducibility**: Random seeds ensure repeatable evaluations

## Evaluation Process

### 1. Sampling
```python
# Sample 10 random questions from benchmark
python evaluation/run_eval.py --sample-size 10 --seed 42
```

### 2. Execution
- Agent processes each question independently
- Full reasoning trace is captured
- Results saved incrementally

### 3. Manual Review
- Compare agent answers to ground truth
- Assess reasoning quality
- Identify failure patterns

### 4. Iteration
- Analyze failures
- Make targeted improvements
- Re-evaluate on NEW random sample
- Document changes and impact

## Configuration

All behavior is controlled via environment variables or `config.py`:

### LLM Configuration
- `OPENAI_API_KEY`: API key for LLM
- `OPENAI_API_BASE`: API endpoint (default: OpenAI)
- `OPENAI_MODEL`: Model name (e.g., gpt-4)
- `TEMPERATURE`: Sampling temperature (default: 0.2)

### Search Configuration
- `GOOGLE_API_KEY` / `GOOGLE_CSE_ID`: Google Custom Search
- `SERPAPI_KEY`: SerpAPI alternative
- `SEARCH_DELAY`: Rate limiting (default: 2.0 seconds)
- `MAX_SEARCH_RESULTS`: Results per query (default: 5)

### Agent Behavior
- `MAX_HOPS`: Maximum reasoning steps (default: 6)
- `MAX_RETRIES`: Search attempts per sub-question (default: 3)

## Usage Examples

### Single Question Query
```bash
python query_single.py "What is the capital of France?"
```

### Full Evaluation
```bash
python evaluation/run_eval.py --sample-size 10 --seed 42 --run-name first_run
```

### Custom Configuration
```bash
MAX_HOPS=8 TEMPERATURE=0.1 python evaluation/run_eval.py
```

## Expected Performance

### Initial Run (Baseline)
- **Accuracy**: 30-50%
- **Common Issues**: 
  - Decomposition errors
  - Failed searches
  - Incomplete article reading
  - Answer extraction problems

### After Iteration
- **Target Accuracy**: 60-70%
- **Improvements**:
  - Better query formulation
  - Refined prompts
  - Enhanced verification
  - Robust error handling

## System Requirements

### Dependencies
- Python 3.8+
- openai (LLM client)
- requests (HTTP)
- beautifulsoup4 (HTML parsing)
- html2text (Markdown conversion)
- googlesearch-python (optional, for search)
- python-dotenv (optional, for config)

### External APIs
- LLM API (OpenAI-compatible)
- Search API (Google Custom Search or SerpAPI recommended)

### Hardware
- Standard CPU (no GPU needed)
- ~4GB RAM minimum
- Internet connection required

## Extensibility

The system is designed to be extended:

### Add New Search Backend
1. Implement search method in `WikipediaSearchClient`
2. Add configuration options
3. Update documentation

### Customize Question Decomposition
1. Edit `src/question_decomposer.py`
2. Modify decomposition prompts
3. Adjust `should_continue` logic

### Enhance Article Processing
1. Edit `src/wiki_fetcher.py`
2. Adjust what content to keep/remove
3. Change Markdown conversion settings

### Improve Answer Synthesis
1. Edit `src/answer_synthesizer.py`
2. Refine synthesis prompts
3. Add additional verification steps

## Limitations and Constraints

### By Design
- **Wikipedia Only**: Cannot access other sources
- **No Embeddings**: Simple key-value storage only
- **Static Prompt**: Same prompt for all questions
- **Sequential Processing**: One question at a time

### Technical
- **Token Limits**: Long articles may hit LLM context limits
- **API Costs**: Each question requires multiple LLM calls
- **Rate Limits**: Search APIs have quotas
- **Latency**: Network requests add processing time

## Future Enhancements

Potential improvements (not yet implemented):

1. **Parallel Article Reading**: Read multiple articles simultaneously
2. **Adaptive Hop Count**: Dynamic stopping based on confidence
3. **Multi-Model Ensemble**: Use multiple LLMs for verification
4. **Caching Layer**: Persistent article cache across sessions
5. **Automatic Evaluation**: NLU-based answer comparison
6. **Fine-Tuning**: Custom prompts per question type

## Development Status

✅ **Complete**:
- Core reasoning engine
- Wikipedia search and retrieval
- Question decomposition
- Answer synthesis
- Evaluation framework
- Documentation

⏳ **Pending** (awaiting API credentials):
- End-to-end testing
- Accuracy benchmarking
- Iterative optimization

## Next Steps

1. ✅ Set up API credentials in `.env`
2. ✅ Run `query_single.py` for quick test
3. ✅ Execute `run_eval.py` for full evaluation
4. ✅ Review results and identify failure patterns
5. ✅ Iterate on prompts and logic
6. ✅ Document improvements in `iteration_log.md`

## Contact and Support

For issues or questions:
- Check `GETTING_STARTED.md` for troubleshooting
- Review `README.md` for detailed documentation
- Examine code comments for implementation details

## License

MIT License - See [LICENSE](LICENSE) file.
