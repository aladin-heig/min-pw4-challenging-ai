"""Prompt templates for the Gemini ARC-AGI-3 agent.

Two strategies:
- SIMPLE: minimal instructions, just describe the game and ask for one action.
- COT: explicit chain-of-thought scaffolding (observe → hypothesize → decide).

Both return a strict JSON object so the response is easy to parse.
"""

SHARED_GAME_DESCRIPTION = """\
You are playing an ARC-AGI-3 interactive game.

GAME MECHANICS:
- The game state is a grid of integers 0-15 (each value represents a color).
- The grid is up to 64x64 cells. Origin (0,0) is top-left.
- A frame may contain one or more sequential grids; the last grid is the current state.
- You receive frames after each action. You must discover the rules by experimenting.
- You WIN by reaching the win condition (which you must infer), or GAME_OVER if you fail.

AVAILABLE ACTIONS:
- RESET: only used to start or restart a game (do not call mid-play unless GAME_OVER).
- ACTION1: simple input (often "up" or "W").
- ACTION2: simple input (often "down" or "S").
- ACTION3: simple input (often "left" or "A").
- ACTION4: simple input (often "right" or "D").
- ACTION5: simple input (often "select" / spacebar).
- ACTION6: complex input — click at coordinates (x, y), both integers in [0, 63].

OBJECTIVE: WIN the game using as few actions as possible.
"""

# Note: braces are doubled so they survive the later str.format() pass on
# SIMPLE_PROMPT / COT_PROMPT. (This is a normal string, not an f-string, so the
# f-string interpolation that inlines it into the templates does not consume them.)
OUTPUT_FORMAT = """\
RESPONSE FORMAT (strict JSON, no markdown, no extra text):
{{
  "action": "ACTION1" | "ACTION2" | "ACTION3" | "ACTION4" | "ACTION5" | "ACTION6" | "RESET",
  "x": <int 0-63, only if action is ACTION6>,
  "y": <int 0-63, only if action is ACTION6>,
  "reasoning": "<one short sentence explaining your choice>"
}}
"""

SIMPLE_PROMPT = f"""\
{SHARED_GAME_DESCRIPTION}

Current game state:
- State: {{state}}
- Levels completed: {{levels_completed}}
- Action #{{action_counter}}
- Available actions: {{available_actions}}

Latest frame (the current grid):
{{frame_text}}

Choose the single best next action.

{OUTPUT_FORMAT}
"""

COT_PROMPT = f"""\
{SHARED_GAME_DESCRIPTION}

Current game state:
- State: {{state}}
- Levels completed: {{levels_completed}}
- Action #{{action_counter}}
- Available actions: {{available_actions}}

Latest frame (the current grid):
{{frame_text}}

History of your recent actions and their effects:
{{history}}

Think step by step BEFORE answering:
1. OBSERVE: What do you see in the current grid? Identify distinct objects, colors, regions.
2. HYPOTHESIZE: Based on what changed (or did not change) after your previous actions, what is your best current hypothesis about the rules of this game?
3. PLAN: What action would test or exploit that hypothesis to make progress toward winning?
4. DECIDE: Pick exactly one action.

Put your reasoning inside the "reasoning" field of the JSON (keep it under 3 sentences).

{OUTPUT_FORMAT}
"""
