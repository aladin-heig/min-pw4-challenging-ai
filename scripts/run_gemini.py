"""Run the Gemini agent on ARC-AGI-3 games.

Usage:
    python scripts/run_gemini.py --strategy simple --games 5
    python scripts/run_gemini.py --strategy cot --games 5 --model gemini-3-flash-preview
    python scripts/run_gemini.py --strategy cot --game-filter ls20
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---- env loading (must happen before importing framework code) -------------
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# ---- path setup so we can import both the framework and our agents ---------
FRAMEWORK = ROOT / "external" / "ARC-AGI-3-Agents"
sys.path.insert(0, str(FRAMEWORK))
sys.path.insert(0, str(ROOT))

# The framework's `agents/__init__.py` eagerly imports every LLM template
# (langchain, smolagents, openai, ...), which we don't need. We bypass that by
# pre-registering a minimal `agents` package in sys.modules before any
# `agents.*` import is triggered. The framework's submodules (agent.py,
# swarm.py, recorder.py, tracing.py) only need arc_agi + pydantic.
import importlib  # noqa: E402
import types  # noqa: E402

_pkg = types.ModuleType("agents")
_pkg.__path__ = [str(FRAMEWORK / "agents")]
sys.modules["agents"] = _pkg

# Now load the minimal submodules we need (this skips the __init__.py).
agent_module = importlib.import_module("agents.agent")
swarm_module = importlib.import_module("agents.swarm")
Swarm = swarm_module.Swarm
Agent = agent_module.Agent

# Expose a minimal AVAILABLE_AGENTS dict on the fake package, used by Swarm.
_pkg.AVAILABLE_AGENTS = {}  # type: ignore[attr-defined]

# Import our agent. It subclasses `agents.agent.Agent` — same object we just
# loaded — so Agent.__subclasses__() picks it up.
from gemini_arc_agent import GeminiAgent, GeminiAgentCoT  # noqa: E402, F401

logger = logging.getLogger("run_gemini")


def list_available_games(root_url: str, api_key: str) -> list[str]:
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    r = requests.get(f"{root_url}/api/games", headers=headers, timeout=10)
    r.raise_for_status()
    return [g["game_id"] for g in r.json()]


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"run_{int(time.time())}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Gemini on ARC-AGI-3")
    parser.add_argument(
        "--strategy",
        choices=["simple", "cot"],
        default="simple",
        help="Prompt strategy.",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=5,
        help="How many distinct games to play (capped by what the API exposes).",
    )
    parser.add_argument(
        "--game-filter",
        type=str,
        default=None,
        help="Optional comma-separated prefix(es) to restrict game_ids.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview"),
        help="Gemini model name (preview tags change — verify in AI Studio).",
    )
    parser.add_argument(
        "--max-actions",
        type=int,
        default=80,
        help="Max actions per game (framework default is 80).",
    )
    args = parser.parse_args()

    setup_logging(ROOT / "results" / f"gemini_{args.strategy}" / "logs")

    api_key = os.environ.get("ARC_API_KEY")
    if not api_key:
        sys.exit("ARC_API_KEY is not set (see .env.example)")
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY is not set (see .env.example)")

    # Make the chosen model visible to GeminiAgent (it reads GEMINI_MODEL).
    os.environ["GEMINI_MODEL"] = args.model

    scheme = os.environ.get("SCHEME", "https")
    host = os.environ.get("HOST", "three.arcprize.org")
    port = os.environ.get("PORT")
    if port and str(port) not in ("80", "443"):
        root_url = f"{scheme}://{host}:{port}"
    else:
        root_url = f"{scheme}://{host}"

    logger.info("Listing available games from %s", root_url)
    all_games = list_available_games(root_url, api_key)
    logger.info("API exposes %d games", len(all_games))

    if args.game_filter:
        prefixes = [p.strip() for p in args.game_filter.split(",")]
        all_games = [g for g in all_games if any(g.startswith(p) for p in prefixes)]
    games = all_games[: args.games]
    if not games:
        sys.exit("No games selected. Check --game-filter and your API key.")
    logger.info("Selected %d games: %s", len(games), games)

    # Pick the agent class based on strategy.
    agent_cls = GeminiAgentCoT if args.strategy == "cot" else GeminiAgent
    agent_cls.MAX_ACTIONS = args.max_actions
    agent_cls.MODEL = args.model
    agent_key = agent_cls.__name__.lower()

    # Register the agent in the framework's AVAILABLE_AGENTS so Swarm can find it.
    _pkg.AVAILABLE_AGENTS[agent_key] = agent_cls  # type: ignore[attr-defined]

    tags = [
        "gemini-vs-human",
        f"strategy={args.strategy}",
        f"model={args.model}",
    ]

    swarm = Swarm(
        agent=agent_key,
        ROOT_URL=root_url,
        games=games,
        tags=tags,
    )

    scorecard = swarm.main()

    # Save a JSON summary of the run.
    out_dir = ROOT / "results" / f"gemini_{args.strategy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"summary_{int(time.time())}.json"
    summary = {
        "strategy": args.strategy,
        "model": args.model,
        "games": games,
        "tags": tags,
        "scorecard": scorecard.model_dump() if scorecard else None,
    }
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    logger.info("Wrote summary to %s", summary_path)


if __name__ == "__main__":
    main()
