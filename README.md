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
# Optionnel : ajuster GEMINI_MODEL et GEMINI_RPM (voir .env.example).
```

## Variables d'environnement

Toutes les variables sont lues par `scripts/run_gemini.py` / `gemini_arc_agent/`.

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `ARC_API_KEY` | *requis* | Clé d'accès à l'API ARC-AGI-3 (`https://three.arcprize.org`). |
| `GEMINI_API_KEY` | *requis* | Clé d'accès à Google AI Studio (`https://aistudio.google.com`). |
| `GEMINI_MODEL` | `gemini-3.1-pro-preview` | Modèle Gemini appelé par l'agent. Les noms `preview` changent vite — vérifier dans AI Studio. Peut aussi être forcé via `--model`. |
| `GEMINI_RPM` | `15` | Limite de requêtes/minute côté Gemini. Le framework lance un thread par jeu, tous sur le même quota, donc ce rate limiter partagé plafonne le rythme global. À augmenter uniquement en passant en tier payant (`60+`). |
| `SCHEME` | `https` | Schéma de l'URL de l'API ARC. |
| `HOST` | `three.arcprize.org` | Hôte de l'API ARC. |
| `PORT` | *(vide)* | Port éventuel (utile pour un proxy local ; omis dans l'URL si `80`/`443`). |
| `RECORDINGS_DIR` | *défini par le script* | Répertoire où le `Recorder` du framework écrit les `*.recording.jsonl`. `run_gemini.py` le fixe automatiquement à `<repo>/results/raw/` — pas besoin de l'exporter. |

## Usage

### `scripts/run_gemini.py`

Lance Gemini sur les jeux ARC-AGI-3.

```bash
python scripts/run_gemini.py --strategy simple --games 1
python scripts/run_gemini.py --strategy cot --games 5
```

| Flag | Défaut | Description |
| --- | --- | --- |
| `--strategy {simple,cot}` | `simple` | Stratégie de prompt. `simple` : envoi de la grille et d'une consigne concise. `cot` : ajoute une mémoire des 6 derniers tours + un champ de raisonnement explicite (chain-of-thought). |
| `--games N` | `5` | Nombre de jeux distincts à lancer. Plafonné par ce qu'expose l'API. |
| `--game-filter PREFIX[,PREFIX...]` | *(tous)* | Restreint la sélection à certains préfixes d'`game_id` (séparés par virgules). Ex. `--game-filter ka59,lp85` ne joue que `ka59-*` et `lp85-*`. |
| `--model MODEL` | `GEMINI_MODEL` puis `gemini-3.1-pro-preview` | Modèle Gemini à utiliser. Écrase `GEMINI_MODEL` pour ce run. |
| `--max-actions N` | `80` | Nombre maximal d'actions par partie (également la valeur par défaut du framework). |

À chaque exécution, `run_gemini.py` :
1. écrit les logs de run dans `results/gemini_<strategy>/logs/run_<timestamp>.log`,
2. fait écrire les recordings bruts par partie dans `results/raw/<game_id>.<guid>.recording.jsonl`,
3. dépose un résumé JSON dans `results/gemini_<strategy>/summary_<timestamp>.json`.

### `scripts/make_gifs.py`

Reconstruit, à partir des recordings bruts, un GIF par jeu avec la grille 64×64 recolorée selon la palette officielle ARC et l'action Gemini surimprimée.

```bash
python scripts/make_gifs.py                       # tous les jeux
python scripts/make_gifs.py --game ka59           # un seul jeu
python scripts/make_gifs.py --fps 2 --cell 6      # vitesse / taille des cellules
```

| Flag | Défaut | Description |
| --- | --- | --- |
| `--game PREFIX` | *(tous)* | Préfixe d'`game_id` à traiter (ex. `ka59`). |
| `--cell N` | `5` | Taille d'une cellule de la grille en pixels (rendu `NEAREST`). |
| `--fps N` | `2.0` | Cadence du GIF en images/seconde. La dernière frame est tenue 4× plus longtemps pour qu'on voie la fin. |
| `--log PATH` | dernier `results/gemini_*/logs/run_*.log` | Log de run utilisé pour annoter chaque frame avec l'action Gemini choisie. Si aucun log n'est trouvé, les frames sont annotées `—`. |

Sortie : `report/figures/gifs/<game>.gif`.

### Test humain

```bash
# Jouer sur le site officiel pour comparer
# https://arcprize.org/arc-agi/3
```

## Structure

- `gemini_arc_agent/` : implémentation `GeminiAgent` / `GeminiAgentCoT` (sous-classes du framework officiel) et templates de prompts. Le nom évite le conflit avec le `agents/` du framework cloné dans `external/`.
- `scripts/` : orchestration des runs et analyse
- `results/` : `raw/` (recordings brutes `*.recording.jsonl` un par jeu), `gemini_simple/` et `gemini_cot/` (logs de run + résumé JSON)
- `report/` : rapport final + figures