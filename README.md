# ARC-AGI-3 — Gemini vs Human

Projet final du cours **MIN2026** (HEIG-VD) : *How much intelligence is there in AI?*

Cette expérience compare les performances de **Gemini 3.1** (Google AI Studio) et d'un **joueur humain** sur les jeux interactifs du benchmark **ARC-AGI-3**. L'objectif est de reproduire empiriquement le constat publié par ARC Prize : les humains atteignent ~100% là où les meilleurs LLMs, à la sortie du benchmark, (GPT-5, Claude 4.6, Gemini 3.1) scoraient 0%. Récemment, Claude 4.8 Opus a atteint un score impressionnant de 2% ! 

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Cloner le framework officiel
git submodule add https://github.com/arcprize/ARC-AGI-3-Agents external/ARC-AGI-3-Agents

cp .env.example .env
# Remplir ARC_API_KEY (https://three.arcprize.org)
# et GEMINI_API_KEY (https://aistudio.google.com)
```

## Usage

```bash
# Lancer Gemini sur 1 jeux avec prompt simple
python scripts/run_gemini.py --strategy simple --games 1

# Avec Chain-of-Thought
python scripts/run_gemini.py --strategy cot --games 1

# Test humain : jouer sur https://arcprize.org/arc-agi/3

# Générer les GIFs des parties (à partir des recordings)
python scripts/make_gifs.py
```

## Structure

- `gemini_arc_agent/` : implémentation `GeminiAgent` / `GeminiAgentCoT` (sous-classes du framework officiel) et templates de prompts. Le nom évite le conflit avec le `agents/` du framework cloné dans `external/`.
- `scripts/` : orchestration des runs et analyse
- `results/` : logs par run
- `report/` : rapport final + figures