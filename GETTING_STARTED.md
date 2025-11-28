# Getting Started with musique-solver

This guide will help you set up and test the MuSiQue solver system immediately after receiving your API credentials.

## Quick Start (5 minutes)

### Step 1: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

### Step 2: Configure API Credentials

Create a `.env` file in the project root with your API credentials:

```bash
# Copy the example
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Minimum required configuration:**
```bash
OPENAI_API_KEY=your_actual_api_key
OPENAI_API_BASE=https://your-api-endpoint.com/v1  # If custom endpoint
OPENAI_MODEL=gpt-4  # Or whatever model you're using
```

### Step 3: Test with a Single Question

Test the system with one question to verify everything works:

```bash
python query_single.py "Who directed the movie Inception?"
```

Expected output:
- Reasoning trace showing sub-questions
- Search queries attempted
- Articles read
- Final answer with evidence

### Step 4: Run Mini Evaluation (3 questions)

Test on a small sample to verify the full pipeline:

```bash
python evaluation/run_eval.py --sample-size 3 --run-name test_run
```

This will:
- Sample 3 random questions
- Process each question through the agent
- Save results to `evaluation/results/test_run/`

### Step 5: Review Results

```bash
# View the results
cat evaluation/results/test_run/responses.json
```

Look for:
- ✅ Did the agent generate sub-questions?
- ✅ Did search find relevant articles?
- ✅ Did the agent extract answers from articles?
- ✅ Is the final answer reasonable?

## Troubleshooting First Run

### Issue: "OPENAI_API_KEY is required"
**Solution**: Ensure `.env` file exists and contains `OPENAI_API_KEY=...`

### Issue: "googlesearch-python not installed" or search errors
**Solution**: The system will fall back to trying different search methods. If all fail, you may need to configure one of:
- Google Custom Search API (recommended for production)
- SerpAPI (easiest for testing)
- Or the system will attempt HTML scraping (may be unreliable)

For quick testing without search API setup, you can temporarily modify the code to use mock search results, but this won't give accurate evaluation results.

### Issue: LLM responses are incomplete or truncated
**Solution**: Some models have context limits. Try:
- Using a model with larger context window
- Reducing article length (though this may hurt accuracy)
- Increasing `max_tokens` in `LLMClient` initialization

### Issue: "Rate limit exceeded"
**Solution**: 
- Increase `SEARCH_DELAY` in .env (default is 2.0 seconds)
- Reduce `SAMPLE_SIZE` for initial tests
- Check your API rate limits

## Running Full Evaluation

Once basic tests pass, run a full evaluation:

```bash
# 10 questions with specific seed for reproducibility
python evaluation/run_eval.py --sample-size 10 --seed 42 --run-name run_001
```

This typically takes 10-30 minutes depending on question complexity and API speed.

## Understanding Results

### Files Created

After each run, you'll find:

```
evaluation/results/run_001/
├── questions.json         # Sampled questions with ground truth
├── responses.json         # Agent answers with reasoning traces
└── summary.json          # Run metadata
```

### Manual Evaluation

You must manually evaluate correctness:

1. Open `responses.json`
2. For each question, compare:
   - `agent_answer` vs `ground_truth`
   - Review `reasoning_steps` for soundness
3. Mark correct/incorrect
4. Calculate accuracy

Example evaluation entry:
```json
{
  "question_id": "4hop1__93963_170667_443779_52195",
  "correct": true,
  "notes": "Found correct answer through valid reasoning chain"
}
```

## Next Steps

### If Accuracy < 50%

Common issues and fixes:

1. **Sub-questions not being generated properly**
   - Review system prompt in `prompts/agent_system_prompt.txt`
   - Check if LLM is following decomposition instructions
   - May need to adjust prompt wording

2. **Search not finding relevant articles**
   - Check if `site:wikipedia.org` filter is working
   - Review generated search queries in `responses.json`
   - May need to improve query generation prompt

3. **Agent not extracting answers from articles**
   - Articles might be too long (token limits)
   - Answer extraction prompt may need refinement
   - Verify articles actually contain the information

4. **Answer synthesis failures**
   - Check if sub-question answers are correct
   - Review evidence chain
   - May need to improve synthesis prompt

### If Accuracy > 50%

Great! Now focus on:

1. **Analyzing failure patterns**: What types of questions fail?
2. **Iterative improvements**: Document changes in `evaluation/iteration_log.md`
3. **Running multiple evaluations**: Try different random seeds
4. **Confidence assessment**: How certain is the agent of each answer?

## Advanced Configuration

### Using Different Models

Test with different models to compare performance:

```bash
# In .env
OPENAI_MODEL=gpt-4-turbo
# or
OPENAI_MODEL=gpt-3.5-turbo
```

### Adjusting Agent Behavior

```bash
# In .env
MAX_HOPS=8              # Allow more reasoning steps
TEMPERATURE=0.1         # More deterministic responses
MAX_RETRIES=5           # More search attempts per sub-question
```

### Search Configuration

If using Google Custom Search API:

```bash
GOOGLE_API_KEY=your_key
GOOGLE_CSE_ID=your_cse_id
```

The CSE should be configured to only search `*.wikipedia.org`

## Testing Tips

### Start Small
- Begin with 3-5 questions
- Verify system works end-to-end
- Then scale to 10+ questions

### Check Logs
- Monitor `evaluation.log` for errors
- Look for API errors, timeout issues
- Check for JSON parsing failures

### Validate Reasoning
- Don't just check final accuracy
- Review the reasoning traces
- Ensure agent is actually reading articles (not guessing)

### Iterate Systematically
1. Run evaluation
2. Analyze failures
3. Make ONE targeted change
4. Re-evaluate on NEW random sample
5. Document impact

## Common Customizations

### Change System Prompt

Edit `prompts/agent_system_prompt.txt` to adjust agent behavior. Remember:
- Keep it general (no question-specific hints)
- Focus on reasoning process
- Emphasize evidence-based answers

### Adjust Search Results

In `config.py`:
```python
MAX_SEARCH_RESULTS = 10  # Try more results per query
```

### Modify Article Processing

Edit `src/wiki_fetcher.py` to change how articles are processed:
- Keep/remove tables
- Truncate long articles
- Extract specific sections

## Getting Help

If you encounter issues:

1. Check `evaluation.log` for detailed error messages
2. Review the code comments in source files
3. Verify your `.env` configuration
4. Test with a simple question first using `query_single.py`

## Success Checklist

- [ ] Dependencies installed successfully
- [ ] `.env` file configured with API credentials
- [ ] Single question test works (`query_single.py`)
- [ ] Mini evaluation (3 questions) completes
- [ ] Results files are generated
- [ ] Can review reasoning traces
- [ ] Ready for full 10-question evaluation

Once all items are checked, you're ready to iterate toward better accuracy!
