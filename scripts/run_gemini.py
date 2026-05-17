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

# Import framework first so that `agents` resolves to the submodule.
import agents as framework_agents  # noqa: E402  # the submodule's `agents/`
from agents.swarm import Swarm  # noqa: E402

# Now import our agent. The class must be a subclass of `agents.agent.Agent`,
# so by importing it AFTER the framework, we ensure both refer to the same
# base class object (otherwise Agent.__subclasses__() would not list it).
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

    # Make sure the agent is registered in the framework's AVAILABLE_AGENTS.
    framework_agents.AVAILABLE_AGENTS[agent_key] = agent_cls

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
