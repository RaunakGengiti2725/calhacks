"""dryrun_providers — the abstraction layer between business logic and the world.

Import the factory getters from here; never import a live API client directly in
business logic.

Importing this package also loads the repo `.env` (see `config`), so any key the
user pastes there is live before the first `os.getenv`.
"""

# Side effect: load .env before anything reads os.getenv. Keep this first.
from dryrun_providers import config, provenance
from dryrun_providers.config import is_strict, load_env
from dryrun_providers.factory import (
    get_cost_provider,
    get_generation_provider,
    get_llm_provider,
    get_mode,
    get_structure_provider,
    get_viability_provider,
    is_live,
)

__all__ = [
    "config",
    "provenance",
    "is_strict",
    "load_env",
    "get_cost_provider",
    "get_generation_provider",
    "get_llm_provider",
    "get_mode",
    "get_structure_provider",
    "get_viability_provider",
    "is_live",
]
