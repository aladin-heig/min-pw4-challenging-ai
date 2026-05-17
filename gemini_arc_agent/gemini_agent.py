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
from typing import Any, ClassVar

from arcengine import FrameData, GameAction, GameState
from google import genai
from google.genai import types as genai_types

from agents.agent import Agent  # type: ignore[import-not-found]

from .prompts import COT_PROMPT, SIMPLE_PROMPT

logger = logging.getLogger(__name__)

_VALID_ACTION_NAMES = {a.name for a in GameAction}


class GeminiAgent(Agent):
    """Gemini agent using a simple prompt (no CoT)."""

    MAX_ACTIONS: ClassVar[int] = 80
    MODEL: ClassVar[str] = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
    STRATEGY: ClassVar[str] = "simple"
    HISTORY_LIMIT: ClassVar[int] = 6  # last N actions kept in the prompt (CoT only)

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

        prompt = self._build_prompt(latest_frame)
        raw_text = self._call_gemini(prompt)
        parsed = self._parse_response(raw_text, latest_frame)

        action = self._to_game_action(parsed, latest_frame)
        self._record_history(action, parsed, latest_frame)
        return action

    # ---- prompt construction ------------------------------------------------

    def _build_prompt(self, latest_frame: FrameData) -> str:
        frame_text = self._render_frame_text(latest_frame.frame)
        available = [a.name for a in (latest_frame.available_actions or [])] or [
            a.name for a in GameAction if a is not GameAction.RESET
        ]
        return SIMPLE_PROMPT.format(
            state=latest_frame.state.name,
            levels_completed=latest_frame.levels_completed,
            action_counter=self.action_counter,
            available_actions=", ".join(available),
            frame_text=frame_text,
        )

    @staticmethod
    def _render_frame_text(frame: list[list[list[int]]]) -> str:
        """Render the last grid in the frame as plain text rows.

        ARC frames carry one or more sequential grids; the last one is current.
        """
        if not frame:
            return "(empty frame)"
        grid = frame[-1]
        return "\n".join(" ".join(f"{c:2d}" for c in row) for row in grid)

    # ---- LLM call -----------------------------------------------------------

    def _call_gemini(self, prompt: str) -> str:
        config = genai_types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        )
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
        available = [a.name for a in (latest_frame.available_actions or [])] or [
            a.name for a in GameAction if a is not GameAction.RESET
        ]
        if self._action_history:
            history_lines = [
                f"  step {h['step']}: {h['action']}"
                + (f" (x={h.get('x')},y={h.get('y')})" if "x" in h else "")
                + f" — {h['reasoning']}"
                for h in self._action_history
            ]
            history = "\n".join(history_lines)
        else:
            history = "  (no actions taken yet)"

        return COT_PROMPT.format(
            state=latest_frame.state.name,
            levels_completed=latest_frame.levels_completed,
            action_counter=self.action_counter,
            available_actions=", ".join(available),
            frame_text=frame_text,
            history=history,
        )
