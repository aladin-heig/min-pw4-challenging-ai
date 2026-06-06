"""Reconstruct an animated GIF of what Gemini did in each ARC-AGI-3 game.

For every recording (*.recording.jsonl) we render each frame's 64x64 grid using
the official ARC 16-color palette, overlay a caption with the action Gemini chose
at that step (read from the run log), and assemble the frames into a GIF.

Usage:
    uv run scripts/make_gifs.py                      # all recordings in the repo
    uv run scripts/make_gifs.py --game ka59          # one game
    uv run scripts/make_gifs.py --fps 2 --cell 6     # tweak speed / size
"""

from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "report" / "figures" / "gifs"

# Official ARC 16-color palette (RGB), copied from the framework's
# agents/templates/multimodal.py so our rendering matches the real game.
PALETTE = [
    (0xFF, 0xFF, 0xFF),  # 0 White
    (0xCC, 0xCC, 0xCC),  # 1 Off-white
    (0x99, 0x99, 0x99),  # 2 Neutral light
    (0x66, 0x66, 0x66),  # 3 Neutral
    (0x33, 0x33, 0x33),  # 4 Off-black
    (0x00, 0x00, 0x00),  # 5 Black
    (0xE5, 0x3A, 0xA3),  # 6 Magenta
    (0xFF, 0x7B, 0xCC),  # 7 Magenta light
    (0xF9, 0x3C, 0x31),  # 8 Red
    (0x1E, 0x93, 0xFF),  # 9 Blue
    (0x88, 0xD8, 0xF1),  # 10 Blue light
    (0xFF, 0xDC, 0x00),  # 11 Yellow
    (0xFF, 0x85, 0x1B),  # 12 Orange
    (0x92, 0x12, 0x31),  # 13 Maroon
    (0x4F, 0xCC, 0x30),  # 14 Green
    (0xA3, 0x56, 0xD6),  # 15 Purple
]

CAPTION_H = 46  # px reserved at the bottom for the caption


def find_recordings(game: Optional[str]) -> list[Path]:
    pattern = f"{game}-*.recording.jsonl" if game else "*.recording.jsonl"
    return sorted(ROOT.glob(pattern))


def game_prefix(path: Path) -> str:
    # e.g. "ka59-38d34dbb.geminiagent...." -> "ka59"
    return path.name.split("-")[0]


def find_latest_log() -> Optional[Path]:
    logs = sorted(
        (ROOT / "results").glob("gemini_*/logs/run_*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return logs[0] if logs else None


def load_actions_for_game(log_path: Optional[Path], prefix: str) -> dict[int, str]:
    """Map step index -> action name (e.g. {0: 'ACTION4', 1: 'ACTION3', ...}).

    Parsed from log lines like:
      ka59-38d34dbb - ACTION4: count 0, levels completed 0, avg fps 0.0)
    """
    actions: dict[int, str] = {}
    if not log_path or not log_path.exists():
        return actions
    line_re = re.compile(
        rf"{re.escape(prefix)}-[a-f0-9]+ - (ACTION\d+|RESET): count (\d+)"
    )
    for line in log_path.read_text(errors="ignore").splitlines():
        m = line_re.search(line)
        if m:
            action, count = m.group(1), int(m.group(2))
            actions[count] = action
    return actions


def render_frame(
    grid: list[list[int]],
    cell: int,
    caption: str,
    progress: str,
) -> Image.Image:
    h = len(grid)
    w = len(grid[0]) if h else 0
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        row = grid[y]
        for x in range(w):
            v = row[x]
            px[x, y] = PALETTE[v] if 0 <= v < len(PALETTE) else (255, 0, 255)

    img = img.resize((w * cell, h * cell), Image.NEAREST)

    # Add caption strip at the bottom.
    canvas = Image.new("RGB", (img.width, img.height + CAPTION_H), (20, 20, 20))
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    draw.text((8, img.height + 6), caption, fill=(255, 255, 255), font=font)
    draw.text(
        (8, img.height + 27), progress, fill=(170, 170, 170), font=font_small
    )
    return canvas


def build_gif(
    recording: Path,
    actions: dict[int, str],
    cell: int,
    fps: float,
) -> Optional[Path]:
    lines = recording.read_text().splitlines()
    if not lines:
        return None

    prefix = game_prefix(recording)
    frames: list[Image.Image] = []
    for i, line in enumerate(lines):
        data = json.loads(line)["data"]
        frame = data.get("frame")
        if not frame:
            continue
        grid = frame[-1]  # last sub-grid is the current visible state
        state = data.get("state", "?")
        levels = data.get("levels_completed", 0)
        action = actions.get(i, "—")
        caption = f"Step {i + 1}/{len(lines)}  ·  Gemini → {action}"
        progress = f"game {prefix}   state={state}   levels={levels}"
        frames.append(render_frame(grid, cell, caption, progress))

    if not frames:
        return None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{prefix}.gif"
    duration_ms = int(1000 / fps)
    # Hold the last frame a bit longer so the ending is readable.
    durations = [duration_ms] * (len(frames) - 1) + [duration_ms * 4]
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Make GIFs from ARC recordings")
    parser.add_argument("--game", help="Only this game prefix (e.g. ka59).")
    parser.add_argument(
        "--cell", type=int, default=5, help="Pixels per grid cell (default 5)."
    )
    parser.add_argument(
        "--fps", type=float, default=2.0, help="Frames per second (default 2)."
    )
    parser.add_argument(
        "--log",
        help="Path to a run log for action labels (default: latest in results/).",
    )
    args = parser.parse_args()

    log_path = Path(args.log) if args.log else find_latest_log()
    if log_path:
        print(f"Using log for action labels: {log_path}")
    else:
        print("No run log found — captions will show '—' for actions.")

    recordings = find_recordings(args.game)
    if not recordings:
        print("No recordings found.")
        return

    for rec in recordings:
        prefix = game_prefix(rec)
        actions = load_actions_for_game(log_path, prefix)
        out = build_gif(rec, actions, args.cell, args.fps)
        if out:
            n = len(rec.read_text().splitlines())
            print(f"  {prefix}: {n} frames -> {out.relative_to(ROOT)}")
        else:
            print(f"  {prefix}: no usable frames, skipped")


if __name__ == "__main__":
    main()
