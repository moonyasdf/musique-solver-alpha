"""Main evaluation script for the MuSiQue solver."""

import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path to find 'src'
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src.web_search import WikipediaSearchClient
from src.wiki_fetcher import WikipediaArticleFetcher
from src.llm_client import LLMClient
from src.reasoning_engine import ReasoningEngine
from src.utils import ensure_directory, save_json, get_timestamp
from evaluation.random_sampler import sample_questions

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evaluation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_system_prompt() -> str:
    prompt_path = Path(config.PROMPTS_DIR) / "agent_system_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"System prompt not found at {prompt_path}")
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def initialize_components() -> ReasoningEngine:
    """Initialize the Agent Stack."""
    system_prompt = load_system_prompt()
    llm_client = LLMClient(
        api_key=config.OPENAI_API_KEY,
        model=config.OPENAI_MODEL,
        base_url=config.OPENAI_API_BASE if config.OPENAI_API_BASE != "https://api.openai.com/v1" else None,
        temperature=0.0,
        system_prompt=system_prompt,
        streaming=config.STREAMING,
    )
    
    search_client = WikipediaSearchClient(
        api_key=config.GOOGLE_API_KEY,
        cse_id=config.GOOGLE_CSE_ID,
        serpapi_key=config.SERPAPI_KEY,
        rate_limit=config.SEARCH_DELAY,
    )
    
    fetcher = WikipediaArticleFetcher()
    
    engine = ReasoningEngine(
        llm=llm_client,
        searcher=search_client,
        fetcher=fetcher
    )
    
    return engine

def evaluate_question(engine: ReasoningEngine, question_data: dict) -> dict:
    """Evaluate a single question."""
    question_id = question_data['id']
    question_text = question_data['question']
    ground_truth = question_data['answer']
    
    logger.info(f"Evaluating QID: {question_id}")
    logger.info(f"Question: {question_text}")
    
    try:
        result_data = engine.solve(question_text)
        
        final_answer = result_data.get("final_answer")
        trace = result_data.get("trace", [])
        tree_state = result_data.get("tree_state")
        
        record = {
            "question_id": question_id,
            "question_text": question_text,
            "ground_truth": ground_truth,
            "agent_answer": final_answer,
            "trace_summary": f"Used {len(trace)} steps.",
            "full_trace": trace,
            "knowledge_tree": tree_state,
            "success": True
        }
        
        logger.info(f"Agent Answer: {final_answer}")
        logger.info(f"Steps Taken: {len(trace)}")
        logger.info("---")
        
    except Exception as e:
        logger.error(f"Error evaluating question {question_id}: {e}", exc_info=True)
        record = {
            "question_id": question_id,
            "question_text": question_text,
            "ground_truth": ground_truth,
            "agent_answer": None,
            "error": str(e),
            "success": False
        }
    
    return record

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=config.SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    parser.add_argument("--run-name", type=str, default=None)
    args = parser.parse_args()
    
    # 1. Load Questions
    try:
        # Explicit string conversion for path
        bench_file = str(config.BENCHMARK_FILE)
        questions = sample_questions(bench_file, n=args.sample_size, seed=args.seed)
    except Exception as e:
        logger.error(f"Failed to load benchmark file: {e}")
        return

    # 2. Init Engine
    logger.info("Initializing Agent Engine...")
    try:
        engine = initialize_components()
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        return
    
    # 3. Setup Paths
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_name_str = args.run_name if args.run_name else f"run_{timestamp}"
    
    # Construct Path object first
    results_path_obj = Path(config.RESULTS_DIR) / run_name_str
    # Convert to string for functions that might be picky
    results_dir_str = str(results_path_obj)
    
    ensure_directory(results_dir_str)
    
    # Save Questions
    save_json(questions, str(results_path_obj / "questions.json"))
    
    # 4. Main Loop
    # Type hint explicitly to fix "append" errors
    results: List[Dict[str, Any]] = []
    
    for i, q in enumerate(questions, 1):
        logger.info(f"Processing {i}/{len(questions)}...")
        res = evaluate_question(engine, q)
        results.append(res)
        
        # Save incrementally (always cast path to string)
        save_json(results, str(results_path_obj / "responses.json"))
    
    logger.info(f"Run complete. Saved to {results_dir_str}")

if __name__ == "__main__":
    main()