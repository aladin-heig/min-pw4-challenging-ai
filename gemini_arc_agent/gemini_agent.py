"""Gemini-powered agent for ARC-AGI-3.

Two variants are exposed:
- GeminiAgent: simple prompt, no chain-of-thought scaffolding.
- GeminiAgentCoT: structured chain-of-thought prompt with history.

Both subclass the framework's Agent so they're auto-discovered via
Agent.__subclasses__() once this module is imported.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import threading
import time
from typing import Any, ClassVar, Optional

from arcengine import FrameData, GameAction, GameState
from google import genai
from google.genai import types as genai_types

from agents.agent import Agent  # type: ignore[import-not-found]

from .prompts import COT_PROMPT, SIMPLE_PROMPT

logger = logging.getLogger(__name__)

_VALID_ACTION_NAMES = {a.name for a in GameAction}


class _RateLimiter:
    """Token-free min-interval rate limiter, shared across agent threads.

    Guarantees at most `max_per_minute` calls per rolling minute by enforcing a
    minimum spacing between consecutive calls. Thread-safe because the framework
    runs one agent per game in parallel threads, all hitting the same API quota.
    """

    def __init__(self, max_per_minute: int) -> None:
        self._min_interval = 60.0 / max_per_minute
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._next_allowed - now
            if sleep_for > 0:
                time.sleep(sleep_for)
                now = time.monotonic()
            self._next_allowed = now + self._min_interval


class GeminiAgent(Agent):
    """Gemini agent using a simple prompt (no CoT)."""

    MAX_ACTIONS: ClassVar[int] = 80
    MODEL: ClassVar[str] = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
    STRATEGY: ClassVar[str] = "simple"
    HISTORY_LIMIT: ClassVar[int] = 6  # last N actions kept in the prompt (CoT only)

    # Free-tier rate limit (requests/minute). Override via GEMINI_RPM env var;
    # e.g. gemini-3.1-flash-lite free tier allows 15 RPM.
    RPM: ClassVar[int] = int(os.environ.get("GEMINI_RPM", "15"))

    # Shared across all agent threads so the whole swarm respects one quota.
    _rate_limiter: ClassVar[Optional[_RateLimiter]] = None
    _rate_limiter_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=api_key)
        self._action_history: list[dict[str, Any]] = []
        random.seed(int.from_bytes(os.urandom(4), "little"))

    @property
    def name(self) -> str:
        sanitized = self.MODEL.replace("/", "-").replace(":", "-")
        return f"{super().name}.{sanitized}.{self.STRATEGY}"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        # First call: framework requires a RESET to start.
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            return self._reset_action()

        # Attach the *result* of the previous action to its history entry
        # (Option B): compare the grid we acted on with the grid we now observe.
        # frames[-2] is the state the last action was chosen from; frames[-1] is
        # the resulting state. Only meaningful once we have >= 2 frames.
        self._update_last_result(frames, latest_frame)

        prompt = self._build_prompt(latest_frame)
        raw_text = self._call_gemini(prompt)
        parsed = self._parse_response(raw_text, latest_frame)

        action = self._to_game_action(parsed, latest_frame)
        self._record_history(action, parsed, latest_frame)
        return action

    def _update_last_result(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> None:
        """Record what the previous action changed, into the last history entry."""
        if not self._action_history or len(frames) < 2:
            return
        before = frames[-2].frame
        after = latest_frame.frame
        result = self._grid_diff(before, after)
        # Also surface level progress, the most important signal of success.
        prev_levels = self._action_history[-1].get("levels_completed", 0)
        if latest_frame.levels_completed > (prev_levels or 0):
            result = f"LEVEL UP (now {latest_frame.levels_completed}); " + result
        self._action_history[-1]["result"] = result

    # ---- prompt construction ------------------------------------------------

    def _build_prompt(self, latest_frame: FrameData) -> str:
        frame_text = self._render_frame_text(latest_frame.frame)
        return SIMPLE_PROMPT.format(
            state=latest_frame.state.name,
            levels_completed=latest_frame.levels_completed,
            action_counter=self.action_counter,
            available_actions=", ".join(self._available_action_names(latest_frame)),
            frame_text=frame_text,
        )

    @staticmethod
    def _available_action_names(latest_frame: FrameData) -> list[str]:
        raw = latest_frame.available_actions or []
        names: list[str] = []
        for a in raw:
            if isinstance(a, GameAction):
                names.append(a.name)
            else:
                try:
                    names.append(GameAction.from_id(int(a)).name)
                except (ValueError, TypeError):
                    continue
        if not names:
            names = [a.name for a in GameAction if a is not GameAction.RESET]
        return names

    @staticmethod
    def _render_frame_text(frame: list[list[list[int]]]) -> str:
        """Render the last grid in the frame as plain text rows.

        ARC frames carry one or more sequential grids; the last one is current.
        """
        if not frame:
            return "(empty frame)"
        grid = frame[-1]
        return "\n".join(" ".join(f"{c:2d}" for c in row) for row in grid)

    @staticmethod
    def _grid_diff(
        before: list[list[list[int]]], after: list[list[list[int]]]
    ) -> str:
        """Compact textual summary of how the grid changed (Option B).

        Returns a short phrase, not the full grids, to keep the prompt cheap.
        """
        if not before or not after:
            return "no comparable grid"
        b = before[-1]
        a = after[-1]
        if len(b) != len(a) or any(len(rb) != len(ra) for rb, ra in zip(b, a)):
            return "grid size changed"

        changed: list[tuple[int, int]] = []
        for y, (rb, ra) in enumerate(zip(b, a)):
            for x, (vb, va) in enumerate(zip(rb, ra)):
                if vb != va:
                    changed.append((x, y))

        if not changed:
            return "NO CHANGE (action had no visible effect)"

        n = len(changed)
        # Bounding box of the change gives the model a sense of *where*.
        xs = [x for x, _ in changed]
        ys = [y for _, y in changed]
        bbox = f"x[{min(xs)}-{max(xs)}], y[{min(ys)}-{max(ys)}]"
        return f"{n} cell(s) changed in region {bbox}"

    # ---- LLM call -----------------------------------------------------------

    @classmethod
    def _get_rate_limiter(cls) -> _RateLimiter:
        # Lazily build a single shared limiter for the whole swarm.
        with GeminiAgent._rate_limiter_lock:
            if GeminiAgent._rate_limiter is None:
                GeminiAgent._rate_limiter = _RateLimiter(cls.RPM)
            return GeminiAgent._rate_limiter

    def _call_gemini(self, prompt: str) -> str:
        config = genai_types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        )
        # Respect the free-tier rate limit before every call.
        self._get_rate_limiter().wait()
        try:
            response = self._client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
                config=config,
            )
        except Exception as e:
            logger.warning("Gemini call failed: %s — falling back to random action", e)
            return ""
        return response.text or ""

    # ---- response parsing ---------------------------------------------------

    def _parse_response(
        self, raw_text: str, latest_frame: FrameData
    ) -> dict[str, Any]:
        if not raw_text:
            return self._random_fallback(latest_frame, reason="empty_response")

        # Strip code fences if the model added them despite response_mime_type.
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract the first JSON object substring.
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                logger.warning("Gemini returned non-JSON: %r", raw_text[:200])
                return self._random_fallback(latest_frame, reason="invalid_json")
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning("Failed to parse Gemini JSON substring")
                return self._random_fallback(latest_frame, reason="invalid_json")

        action_name = str(data.get("action", "")).upper()
        if action_name not in _VALID_ACTION_NAMES:
            logger.warning("Gemini chose unknown action %r", action_name)
            return self._random_fallback(latest_frame, reason="unknown_action")

        return data

    def _random_fallback(
        self, latest_frame: FrameData, reason: str
    ) -> dict[str, Any]:
        choices = [a for a in GameAction if a is not GameAction.RESET]
        action = random.choice(choices)
        out: dict[str, Any] = {
            "action": action.name,
            "reasoning": f"[fallback: {reason}]",
            "_fallback": True,
        }
        if action.is_complex():
            out["x"] = random.randint(0, 63)
            out["y"] = random.randint(0, 63)
        return out

    def _to_game_action(
        self, parsed: dict[str, Any], latest_frame: FrameData
    ) -> GameAction:
        action = GameAction.from_name(parsed["action"])
        reasoning_text = parsed.get("reasoning", "")
        if action.is_complex():
            x = self._clamp_coord(parsed.get("x"))
            y = self._clamp_coord(parsed.get("y"))
            action.set_data({"x": x, "y": y})
            action.reasoning = {
                "text": reasoning_text,
                "x": x,
                "y": y,
                "fallback": parsed.get("_fallback", False),
            }
        else:
            action.reasoning = {
                "text": reasoning_text,
                "fallback": parsed.get("_fallback", False),
            }
        return action

    @staticmethod
    def _clamp_coord(value: Any) -> int:
        try:
            n = int(value)
        except (TypeError, ValueError):
            return random.randint(0, 63)
        return max(0, min(63, n))

    def _reset_action(self) -> GameAction:
        action = GameAction.RESET
        action.reasoning = {"text": "Starting/restarting the game."}
        return action

    # ---- history tracking (used by CoT subclass) ----------------------------

    def _record_history(
        self,
        action: GameAction,
        parsed: dict[str, Any],
        latest_frame: FrameData,
    ) -> None:
        entry = {
            "step": self.action_counter,
            "action": action.name,
            "reasoning": parsed.get("reasoning", ""),
            "state_before": latest_frame.state.name,
            "levels_completed": latest_frame.levels_completed,
        }
        if action.is_complex():
            entry["x"] = parsed.get("x")
            entry["y"] = parsed.get("y")
        self._action_history.append(entry)
        if len(self._action_history) > self.HISTORY_LIMIT:
            self._action_history = self._action_history[-self.HISTORY_LIMIT :]


class GeminiAgentCoT(GeminiAgent):
    """Gemini agent with chain-of-thought scaffolding and short action history."""

    STRATEGY: ClassVar[str] = "cot"

    def _build_prompt(self, latest_frame: FrameData) -> str:
        frame_text = self._render_frame_text(latest_frame.frame)
        if self._action_history:
            history_lines = []
            for h in self._action_history:
                coords = f" (x={h.get('x')},y={h.get('y')})" if "x" in h else ""
                # Result is filled in on the following turn (Option B); the most
                # recent action may not have it yet.
                result = h.get("result", "result pending")
                history_lines.append(
                    f"  step {h['step']}: {h['action']}{coords}"
                    f" — chose because: {h['reasoning']}"
                    f"\n      -> RESULT: {result}"
                )
            history = "\n".join(history_lines)
        else:
            history = "  (no actions taken yet)"

        return COT_PROMPT.format(
            state=latest_frame.state.name,
            levels_completed=latest_frame.levels_completed,
            action_counter=self.action_counter,
            available_actions=", ".join(self._available_action_names(latest_frame)),
            frame_text=frame_text,
            history=history,
        )
