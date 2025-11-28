"""Configuration module for the musique-solver project."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

BASE_DIR = Path(__file__).parent
load_dotenv()


@dataclass
class Settings:
    # LLM
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4")
    temperature: float = float(os.getenv("TEMPERATURE", "0.2"))

    # Search
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    google_cse_id: str = os.getenv("GOOGLE_CSE_ID", "")
    serpapi_key: str = os.getenv("SERPAPI_KEY", "")
    search_delay: float = float(os.getenv("SEARCH_DELAY", "2.0"))
    max_search_results: int = int(os.getenv("MAX_SEARCH_RESULTS", "5"))

    # Agent behaviour
    max_hops: int = int(os.getenv("MAX_HOPS", "6"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))

    # Evaluation defaults
    random_seed: int = int(os.getenv("RANDOM_SEED", "42"))
    sample_size: int = int(os.getenv("SAMPLE_SIZE", "10"))

    # Paths
    benchmark_file: Path = BASE_DIR / "musique_4hop_all_questions.json"
    results_dir: Path = BASE_DIR / "evaluation" / "results"
    prompts_dir: Path = BASE_DIR / "prompts"
    memory_store_path: Path = BASE_DIR / "data" / "memory_store.json"


settings = Settings()

# Backwards-compatible constants
OPENAI_API_KEY = settings.openai_api_key
OPENAI_API_BASE = settings.openai_api_base
OPENAI_MODEL = settings.openai_model
TEMPERATURE = settings.temperature

GOOGLE_API_KEY = settings.google_api_key
GOOGLE_CSE_ID = settings.google_cse_id
SERPAPI_KEY = settings.serpapi_key
SEARCH_DELAY = settings.search_delay
MAX_SEARCH_RESULTS = settings.max_search_results

MAX_HOPS = settings.max_hops
MAX_RETRIES = settings.max_retries

RANDOM_SEED = settings.random_seed
SAMPLE_SIZE = settings.sample_size

BENCHMARK_FILE = settings.benchmark_file
RESULTS_DIR = settings.results_dir
PROMPTS_DIR = settings.prompts_dir
MEMORY_STORE_PATH = settings.memory_store_path
