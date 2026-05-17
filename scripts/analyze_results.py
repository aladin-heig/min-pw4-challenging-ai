"""Aggregate Gemini + human scorecards and produce comparison figures.

Inputs:
- results/gemini_simple/summary_*.json  (one per run)
- results/gemini_cot/summary_*.json
- results/human_scorecards.json         (manually exported from the ARC API)

Outputs:
- report/figures/win_rate.png
- report/figures/actions_used.png
- Pretty-printed table to stdout.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "report" / "figures"

console = Console()


@dataclass
class GameResult:
    condition: str       # "gemini_simple", "gemini_cot", "human"
    game_id: str
    won: bool
    actions: int


def _coerce_actions(card: dict[str, Any]) -> int:
    """Try several common keys to pull the action count out of a card entry."""
    for key in ("actions", "action_count", "num_actions", "total_actions"):
        if key in card and isinstance(card[key], int):
            return card[key]
    return 0


def _coerce_won(card: dict[str, Any]) -> bool:
    state = (card.get("state") or card.get("game_state") or "").upper()
    if state == "WIN":
        return True
    if "won" in card and isinstance(card["won"], bool):
        return card["won"]
    score = card.get("score")
    if isinstance(score, (int, float)) and score > 0:
        return True
    return False


def load_gemini_results(strategy: str) -> list[GameResult]:
    folder = RESULTS / f"gemini_{strategy}"
    if not folder.exists():
        return []
    results: list[GameResult] = []
    for path in sorted(folder.glob("summary_*.json")):
        data = json.loads(path.read_text())
        scorecard = data.get("scorecard") or {}
        # The exact scorecard shape depends on the framework version.
        # We look for per-game entries under a few common keys.
        cards = scorecard.get("cards") or scorecard.get("games") or {}
        if isinstance(cards, dict):
            iterable = cards.items()
        else:
            iterable = ((c.get("game_id", "?"), c) for c in cards)
        for game_id, card in iterable:
            results.append(
                GameResult(
                    condition=f"gemini_{strategy}",
                    game_id=game_id,
                    won=_coerce_won(card),
                    actions=_coerce_actions(card),
                )
            )
    return results


def load_human_results() -> list[GameResult]:
    path = RESULTS / "human_scorecards.json"
    if not path.exists():
        console.print(
            f"[yellow]Note:[/yellow] {path} not found — human results will be empty. "
            "Export your scorecard(s) from three.arcprize.org and save them there."
        )
        return []
    data = json.loads(path.read_text())
    # Accept either a single scorecard or a list of them.
    scorecards = data if isinstance(data, list) else [data]
    out: list[GameResult] = []
    for sc in scorecards:
        cards = sc.get("cards") or sc.get("games") or {}
        if isinstance(cards, dict):
            iterable = cards.items()
        else:
            iterable = ((c.get("game_id", "?"), c) for c in cards)
        for game_id, card in iterable:
            out.append(
                GameResult(
                    condition="human",
                    game_id=game_id,
                    won=_coerce_won(card),
                    actions=_coerce_actions(card),
                )
            )
    return out


def aggregate(results: list[GameResult]) -> dict[str, dict[str, float]]:
    by_cond: dict[str, list[GameResult]] = defaultdict(list)
    for r in results:
        by_cond[r.condition].append(r)
    summary: dict[str, dict[str, float]] = {}
    for cond, items in by_cond.items():
        n = len(items)
        wins = sum(1 for r in items if r.won)
        avg_actions = sum(r.actions for r in items) / n if n else 0.0
        summary[cond] = {
            "n": n,
            "win_rate": (wins / n * 100) if n else 0.0,
            "avg_actions": avg_actions,
        }
    return summary


def print_table(summary: dict[str, dict[str, float]]) -> None:
    table = Table(title="ARC-AGI-3: Gemini vs Human")
    table.add_column("Condition", style="cyan")
    table.add_column("Games", justify="right")
    table.add_column("Win rate (%)", justify="right")
    table.add_column("Avg actions", justify="right")
    order = ["human", "gemini_simple", "gemini_cot"]
    for cond in order:
        if cond not in summary:
            continue
        s = summary[cond]
        table.add_row(
            cond,
            f"{int(s['n'])}",
            f"{s['win_rate']:.1f}",
            f"{s['avg_actions']:.1f}",
        )
    console.print(table)


def plot_win_rate(summary: dict[str, dict[str, float]]) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    order = [c for c in ("human", "gemini_simple", "gemini_cot") if c in summary]
    values = [summary[c]["win_rate"] for c in order]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(order, values, color=["#2ca02c", "#1f77b4", "#ff7f0e"])
    ax.set_ylabel("Win rate (%)")
    ax.set_ylim(0, 105)
    ax.set_title("ARC-AGI-3 — Win rate by condition")
    for i, v in enumerate(values):
        ax.text(i, v + 2, f"{v:.0f}%", ha="center")
    fig.tight_layout()
    out = FIGURES / "win_rate.png"
    fig.savefig(out, dpi=150)
    console.print(f"[green]Wrote[/green] {out}")


def plot_actions(summary: dict[str, dict[str, float]]) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    order = [c for c in ("human", "gemini_simple", "gemini_cot") if c in summary]
    values = [summary[c]["avg_actions"] for c in order]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(order, values, color=["#2ca02c", "#1f77b4", "#ff7f0e"])
    ax.set_ylabel("Average actions per game")
    ax.set_title("ARC-AGI-3 — Actions used by condition")
    for i, v in enumerate(values):
        ax.text(i, v + 0.5, f"{v:.1f}", ha="center")
    fig.tight_layout()
    out = FIGURES / "actions_used.png"
    fig.savefig(out, dpi=150)
    console.print(f"[green]Wrote[/green] {out}")


def main() -> None:
    all_results: list[GameResult] = []
    all_results.extend(load_gemini_results("simple"))
    all_results.extend(load_gemini_results("cot"))
    all_results.extend(load_human_results())

    if not all_results:
        console.print("[red]No results found.[/red] Run scripts/run_gemini.py first.")
        sys.exit(1)

    summary = aggregate(all_results)
    print_table(summary)
    plot_win_rate(summary)
    plot_actions(summary)


if __name__ == "__main__":
    main()
