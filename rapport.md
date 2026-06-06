# Quelle  "intelligence" dans l'IA ? Tester Gemini 3 sur ARC-AGI-3

**Cours MIN2026 — Travail pratique 4 "How much intelligence is there in AI?"**

Auteur : Aladin  
Date : mai 2026

---

## 1. Le problème et ce que l'on veut évaluer

Les grands modèles de langage (LLM) obtiennent des scores spectaculaires sur des tests conçus pour les humains : ChatGPT atteint par exemple un QI verbal de 155, supérieur à 99,9 % des testeurs (Scientific American, 2023). Pourtant, comme le souligne François Chollet, "l'intelligence d'un système se mesure à son efficacité d'acquisition de compétences sur un éventail de tâches, relativement aux a priori, à l'expérience et à la difficulté de généralisation" (*On the Measure of Intelligence*, 2019). Autrement dit, **l'intelligence n'est pas la compétence elle-même, mais la capacité à acquérir de nouvelles compétences et à généraliser**, y compris à des problèmes jamais vus.

Le benchmark **ARC-AGI** est précisément construit autour de cette définition. Sa troisième version, **ARC-AGI-3** (ARC Prize, 2025), va plus loin que les versions 1 et 2 (grilles statiques entrée → sortie) : ce sont des **jeux interactifs**. L'agent observe une grille, choisit une action, observe le résultat, et doit **découvrir les règles du jeu par l'expérimentation seule**, sans instruction préalable. C'est exactement ce qu'un enfant fait devant un jeu vidéo inconnu.

Le résultat publié par ARC Prize est frappant :

| Benchmark | Humains | Meilleurs LLM (2025-2026) |
|---|---|---|
| ARC-AGI-1 | ~98 % | ~90 % (Claude/GPT) |
| ARC-AGI-2 | ~100 % | ~50-70 % |
| **ARC-AGI-3** | **~100 %** | **0 %** (GPT-5, Claude 4.6, Gemini 3) |

**Question évaluée dans ce travail :** un LLM de pointe (Gemini 3) est-il capable de *découvrir et exploiter* les règles d'un jeu ARC-AGI-3 inédit, c'est-à-dire de faire preuve de la flexibilité que Chollet identifie comme le coeur de l'intelligence ? Notre hypothèse, fondée sur le leaderboard officiel, est que **non**, et nous cherchons à le **reproduire nous-mêmes** plutôt qu'à le citer, puis à observer *comment* le modèle échoue.

---

## 2. Méthode

### 2.1 Dispositif technique

Nous avons construit un harnais d'évaluation reproductible (code fourni dans le dépôt) :

- **Framework officiel** [`arcprize/ARC-AGI-3-Agents`](https://github.com/arcprize/ARC-AGI-3-Agents), qui gère la connexion à l'API des jeux (`https://three.arcprize.org`), les sessions, et   le scoring officiel.
- **Agent `GeminiAgent`** (que nous avons écrit, fichier `gemini_arc_agent/gemini_agent.py`) :
  une sous-classe de l'`Agent` du framework. À chaque tour, elle sérialise la grille courante (matrice 64×64 d'entiers 0-15, chaque entier = une couleur) en texte, l'envoie à Gemini via l'API Google AI Studio (SDK `google-genai`), puis analyse la réponse JSON pour en extraire l'action à jouer (`ACTION1`–`ACTION7`, ou `ACTION6`/`ACTION7` avec coordonnées de clic).
- **Modèle :** `gemini-3.1-pro-preview` (le modèle le plus capable de Google au moment du test).
- **Budget :** 80 actions maximum par jeu (valeur standard du framework, comparable aux baselines officielles).

### 2.2 Agent officiel « riche » vs. notre agent « allégé »

Le framework officiel fournit un agent LLM de référence (`LLM` dans `agents/templates/llm_agents.py`) dont le fonctionnement est notablement plus coûteux que le nôtre. Il est utile de le décrire pour situer nos choix.

**L'agent officiel** traite chaque tour de jeu comme un échange dans une **conversation continue** (rôles *user* / *assistant* / *tool*), et effectue **deux appels API par tour** :

1. un premier appel « *observation* » où le modèle commente la grille courante et formule une stratégie ;
2. un second appel « *action* » où, sur la base de cette observation, le modèle choisit l'action à jouer.

Cette conversation s'accumule au fil des tours, avec une fenêtre glissante (`MESSAGE_LIMIT = 10` messages, soit en pratique l'historique des **2-3 derniers tours**, dont leurs grilles). Le modèle dispose donc d'une certaine mémoire de ce qu'il vient de faire.

**Notre agent (`GeminiAgent`, mode `simple`)** est délibérément allégé pour réduire le coût :

- **un seul appel API par tour** (pas de phase d'observation séparée) ;
- **aucune mémoire** : chaque appel est *stateless*. On ne transmet que le **dernier état** (la grille courante), sans historique des actions ni des frames précédentes.

Concrètement, là où l'agent officiel coûte ~2 appels et un contexte qui grossit à chaque tour, le nôtre coûte 1 appel avec un prompt court et constant. Ce choix a un revers important, discuté en section 4 : notre agent est plus faible que l'agent de référence (pas de boucle observe→agit, pas de mémoire), ce qui amplifie mécaniquement les comportements répétitifs observés au §3.2. Le modèle ne « sait » littéralement pas qu'il vient de jouer la même action.

### 2.3 Un agent amélioré : CoT + mémoire du résultat des actions

L'objection ci-dessus — « et si le modèle échoue simplement parce qu'il n'a pas de mémoire ? » — méritait d'être testée directement. Nous avons donc développé une seconde variante, `GeminiAgentCoT`, qui corrige les deux faiblesses du mode `simple` :

- **Mémoire glissante des 6 derniers tours** (fenêtre FIFO), réinjectée en texte dans le prompt -> coût borné, indépendant du numéro de tour.
- **Raisonnement explicite** (*chain-of-thought*) : on demande au modèle d'observer, formuler une hypothèse sur les règles, planifier, puis décider.
- **Surtout, le résultat de chaque action passée.** Pour chaque tour de l'historique, nous calculons le *diff* entre la grille avant et après l'action, et nous l'injectons sous forme compacte : par exemple `RESULT: NO CHANGE (action sans effet visible)`, `RESULT: 12 cellules modifiées en région x[10-14], y[5-7]`, ou `RESULT: LEVEL UP`. Le prompt instruit explicitement le modèle de **ne pas répéter une action marquée NO CHANGE**.

L'intuition : c'est précisément ce signal causal (« cette action n'a rien fait ») qui manque au mode `simple`, et qui devrait permettre au modèle d'inférer les règles (« je viens de buter contre un mur, essayons autre chose »). Nous n'injectons que le *résumé* du diff, jamais les grilles entières, pour rester à un coût linéaire en O(N).

Ce run a été mené avec `gemini-3.1-flash-lite` (modèle plus léger que le Pro), en limitant les appels à **15 requêtes/minute** pour rester dans le quota gratuit. Donc à coût quasi nul (abonnement Google AI Pro), contrairement à l'essai initial.

### 2.4 Le prompt

Chaque tour, Gemini reçoit la description du jeu, les actions disponibles, l'état courant et la grille. Le prompt "simple" (fichier `gemini_arc_agent/prompts.py`) est :

```
You are playing an ARC-AGI-3 interactive game.

GAME MECHANICS:
- The game state is a grid of integers 0-15 (each value represents a color).
- The grid is up to 64x64 cells. Origin (0,0) is top-left.
- You receive frames after each action. You must discover the rules by experimenting.
- You WIN by reaching the win condition (which you must infer), or GAME_OVER if you fail.

AVAILABLE ACTIONS:
- ACTION1: simple input (often "up").    - ACTION4: simple input (often "right").
- ACTION2: simple input (often "down").  - ACTION5: simple input (often "select").
- ACTION3: simple input (often "left").  - ACTION6: click at coordinates (x, y).

OBJECTIVE: WIN the game using as few actions as possible.

Current game state:
- State: NOT_FINISHED   - Levels completed: 0   - Action #3
- Available actions: ACTION1, ACTION2, ..., ACTION6
Latest frame (the current grid):
<la grille 64×64 en texte>

RESPONSE FORMAT (strict JSON):
{ "action": "...", "x": <0-63>, "y": <0-63>, "reasoning": "..." }
```

À titre d'illustration, voici un extrait de ce que Gemini "voit" en entrée : un fragment central (lignes 24-38, colonnes 16-44) de la grille de départ du jeu `ls20`, chaque nombre désignant une couleur :

```
 4  4  4  4  4  4  4  4  4  4  4  4  4  4  4  4  4  4  3  3  3  3  3  4  4  4  4  4
 3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  3  3  3  3  3  3  3  3  4  4  4  4  4  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  0  3  3  3  3  3  3  3  4  4  4  4  4  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  1  0  0  3  3  3  3  3  3  4  4  4  4  4  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  1  3  3  3  3  3  3  3  4  4  4  4  4  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  3  3  3  3  3  3  3  3  4  4  4  4  4  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  3  3  3  3  3  3  3  3  4  4  4  4  4  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  3  3  3  3  3  3  3  3  4  4  4  4  4  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  3  3  3  3  3  3  3  3  4  4  4  4  4  3  3  3  3  3  3  3  3  3  3
 3  3  3  3  3  3  3  3  3  3  3  3  3  4  4  4  4  4  3  3  3  3  3  3  3  3  3  3
```

Ici, les grandes zones uniformes de `3` sont le sol du labyrinthe et les blocs de `4` sont des murs/structures ; le petit amas de `1` et `0` (vers la colonne 20) est un élément interactif du jeu. Dans `ls20`, il s'agit d'un *rotateur* qui modifie l'orientation de la cible lorsqu'on s'y place (la « croix » blanche visible sur le GIF du §3.3). Ces motifs, qu'un oeil humain regroupe spontanément en objets (murs, rotateurs, clé, porte…), ne parviennent au modèle que comme une suite de nombres.

### 2.5 Échantillon testé

5 jeux tirés des 25 exposés par l'API, choisis sans biais (les 5 premiers retournés) :
`ka59`, `r11l`, `lf52`, `cd82`, `lp85`. Un 6ᵉ jeu (`wa30`) avait été testé au préalable avec `gemini-3-flash-preview`.

> **Note d'honnêteté méthodologique.** L'expérience a été **interrompue volontairement**  
> (Ctrl-C) après ~98 actions, pour des raisons de coût d'API. Aucun des 5 jeux n'a donc consommé l'intégralité de son budget de 80 actions ; les chiffres ci-dessous correspondent aux actions effectivement jouées avant l'arrêt. Sur ces 98 appels, **97 ont reçu une vraie réponse de Gemini** (un seul repli aléatoire suite à une erreur 503 temporaire), ce qui rend l'observation du *comportement* du modèle fiable, même si le nombre de jeux menés à terme est limité.

---

## 3. Résultats

### 3.1 Vue d'ensemble

| Jeu | Actions jouées | Niveaux complétés | État final | Baseline humaine (niv. 1) |
|---|---|---|---|---|
| `ka59` | 42 | **0** | NOT_FINISHED | — |
| `lp85` | 16 | **0** | NOT_FINISHED | — |
| `lf52` | 15 | **0** | NOT_FINISHED | — |
| `r11l` | 13 | **0** | NOT_FINISHED | — |
| `cd82` | 12 | **0** | NOT_FINISHED | — |
| `wa30` (Flash) | 81 (budget épuisé) | **0** / 9 | NOT_FINISHED | 71 actions |

**Score : 0 niveau franchi sur l'ensemble des jeux.** Pour `wa30`, le seul mené jusqu'au plafond de 80 actions, Gemini Flash n'a pas franchi le premier niveau alors qu'un humain le résout en **~71 actions en moyenne** (baseline officielle : `[71, 119, 183, 98, 368, …]`).

### 3.2 Comment Gemini échoue : le comportement observé

C'est ici que l'observation devient intéressante. En examinant la séquence d'actions réellement choisies par Gemini (extraites des logs d'exécution), on identifie deux pathologies récurrentes :

**(a) La répétition stérile.** Sur le jeu `ka59` (42 actions), Gemini choisit `ACTION4` ("droite") de façon massive et quasi ininterrompue :

```
A4 A3 A4 A4 A4 A4 A4 A4 A1 A4 A4 A3 A3 A4 A4 A1 A4 A3 A4 A4 A4 A4
A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A4 A1 A3 A4 A4 A4 A4
```

Sur 42 actions, **plus de 30 sont `ACTION4`**. Le modèle pousse dans la même direction sans jamais inférer que cela ne change rien (le compteur de niveau reste à 0 du début à la fin) ni adopter une stratégie d'exploration différente. Un humain, après 3-4 répétitions sans effet, change de comportement ; Gemini, non.

**(b) Le clic compulsif.** Sur `lp85` et `r11l`, le comportement est encore plus dégénéré :
**100 % des actions sont `ACTION6` (clic)**, 16 clics consécutifs sur `lp85`, 13 sur `r11l` :

```
lp85 : A6 A6 A6 A6 A6 A6 A6 A6 A6 A6 A6 A6 A6 A6 A6 A6
r11l : A6 A6 A6 A6 A6 A6 A6 A6 A6 A6 A6 A6 A6
```

Le modèle s'enferme dans une modalité d'action unique. Il "teste" l'interaction par clic mais ne tire aucune conclusion de l'absence de progrès, et n'essaie jamais les actions de déplacement.

Le jeu `lf52` montre un comportement légèrement plus varié (mélange de clics et de déplacements : `A6 A6 A3 A6 A7 A4 A6 A4 A6 A4 A3 A6 A6 A6 A3`), mais sans davantage de résultat.

### 3.3 Visualisation des parties

À partir des enregistrements (`*.recording.jsonl`), nous avons reconstruit en GIF la grille telle que Gemini la voyait à chaque tour, en y superposant l'action choisie (script `scripts/make_gifs.py`, palette de couleurs identique à celle du jeu officiel). Ces animations rendent les deux pathologies immédiatement visibles.

**`ka59` : la répétition stérile.** Le « joueur » (le petit carré vert avec centre blanc) est poussé encore et encore contre la barrière violette, sans que le modèle ne tente une autre approche.

![Partie de Gemini sur le jeu ka59](report/figures/gifs/ka59.gif)

**`lp85` : le clic compulsif.** Gemini ne produit que des `ACTION6` (clics), sans jamais essayer de se déplacer ni tirer de conclusion de l'absence de progrès.

![Partie de Gemini sur le jeu lp85](report/figures/gifs/lp85.gif)

**`ls20` : l'essai amélioré (CoT + résultat des actions).** Même avec la mémoire et le signal explicite « action sans effet », le joueur (carré orange et bleu) erre dans le labyrinthe et n'atteint jamais la sortie (cf. §3.4).

![Partie de Gemini sur le jeu ls20](report/figures/gifs/ls20.gif)

*[Les GIFs des autres jeux (`lf52`, `cd82`, `r11l`, et `wa30` joué jusqu'au plafond de 80 actions) sont disponibles dans `report/figures/gifs/`.]*

### 3.4 L'agent amélioré change-t-il quelque chose ? (essai CoT)

Pour tester si l'échec venait simplement du manque de mémoire, nous avons lancé l'agent `GeminiAgentCoT` décrit au §2.3 (mémoire des 6 derniers tours + résultat de chaque action + raisonnement explicite) sur le jeu **`ls20`** (un labyrinthe de type *LockSmith* : trouver une clé, atteindre la porte de sortie). Le run est allé jusqu'au plafond de **80 actions**, avec 79 décisions réelles du modèle (3 replis aléatoires sur erreurs serveur 503 temporaires).

**Résultat : 0 niveau franchi, état final `NOT_FINISHED`.** Malgré le dispositif enrichi, l'échec est identique.

Plus parlant encore, le comportement de fond **n'a pas changé** :

- Le modèle a joué **35 fois `ACTION4`** sur 80 actions, dont une série de **31 `ACTION4` quasi consécutifs**. C'est exactement la « répétition stérile » du mode `simple`.
- Or **17 des 80 transitions n'ont produit aucun changement de grille** : le modèle recevait donc bien, dans son historique, le signal explicite `RESULT: NO CHANGE`, accompagné de la consigne de ne pas répéter une action sans effet. Il l'a largement ignoré.

Autrement dit, **donner au modèle la preuve que ses actions sont inutiles ne suffit pas à le faire changer de stratégie**. Cela écarte l'explication « il échoue juste par manque de mémoire » : même informé, il ne parvient pas à exploiter ce feedback pour réviser ses hypothèses. Ce qui est, là encore, le coeur du problème de généralisation.

*(À nuancer : ce run utilise `gemini-3.1-flash-lite`, un modèle plus petit que le Pro des essais précédents ; un modèle plus puissant pourrait mieux exploiter le signal. Mais le leaderboard officiel, qui teste les modèles de pointe avec mémoire, reste à 0 %.)*

### 3.5 Synthèse chiffrée

| Condition | Jeux | Niveaux franchis | Taux de réussite |
|---|---|---|---|
| **Humain** (baseline officielle ARC-AGI-3) | tous | tous | **~100 %** |
| **Gemini 3.1 Pro** — `simple` (sans mémoire) | 5 | 0 | **0 %** |
| **Gemini 3 Flash** — `simple`, budget complet (`wa30`) | 1 | 0 / 9 | **0 %** |
| **Gemini 3.1 Flash-lite** — `cot` + résultat des actions (`ls20`) | 1 | 0 | **0 %** |

---

## 4. Conclusions

**Notre hypothèse est confirmée et le résultat du leaderboard officiel est reproduit :**
Gemini 3, dans les deux variantes testées, n'a franchi **aucun niveau** d'aucun jeu ARC-AGI-3, là où un humain les résout quasi systématiquement.

Mais le plus instructif n'est pas le score (0 %), c'est **la manière** d'échouer. Gemini ne se trompe pas dans un raisonnement complexe : il **ne raisonne pas du tout sur ses propres échecs**. Il répète la même action des dizaines de fois sans intégrer le fait qu'elle ne produit aucun progrès, et reste enfermé dans une seule modalité d'action (tout pousser à droite, ou tout cliquer). Or **inférer une règle à partir du feedback de l'environnement, et adapter sa stratégie quand elle échoue, est précisément la capacité de généralisation que Chollet place au coeur de l'intelligence**.

Cela illustre concrètement le propos du cours (slides 12-13) : les LLM sont des **détecteurs de motifs probabilistes**. Ils excellent sur les tâches proches de leur distribution d'entraînement, d'où le QI verbal de 155, mais ARC-AGI-3 est conçu pour être **hors distribution** : aucun jeu, aucune règle n'y figure "par coeur". Privé de la possibilité de réciter, le modèle se révèle incapable d'apprendre par essai-erreur, ce qu'un enfant fait spontanément. La métaphore du cours est juste : juger le modèle ici, c'est comme demander à un poisson de grimper à un arbre, sauf qu'ici la tâche (apprendre les règles d'un jeu) est précisément celle que nous attendrions d'une *intelligence générale*.

### Coût et décision d'arrêter l'expérience

Nous avions sous-estimé le coût des appels API. Le modèle `gemini-3.1-pro-preview` facture la totalité du contexte à chaque appel ; or une grille 64×64 sérialisée représente déjà plusieurs milliers de tokens, et le jeu enchaîne des dizaines de tours. Au final, l'exécution `simple` (les ~98 actions décrites ci-dessus) nous a coûté **environ 16 CHF**, bien au-delà de ce que nous anticipions pour un test que nous pensions modeste.

C'est précisément ce qui a motivé l'arrêt volontaire (Ctrl-C) et le choix de l'agent allégé décrit au §2.2. Pour aller plus loin sans exploser le budget, nous avons ensuite basculé sur un modèle plus léger (`gemini-3.1-flash-lite`) bridé à 15 requêtes/minute, ce qui nous a permis de mener l'essai CoT enrichi (§3.4) à coût quasi nul. Au-delà, et puisque l'objectif pédagogique est atteint, **nous avons décidé d'en rester là** plutôt que de relancer des campagnes complètes (les 80 actions sur les 25 jeux avec le modèle Pro), qui auraient multiplié la facture sans changer la conclusion : les **benchmarks officiels du site ARC Prize confirment déjà que ces modèles obtiennent 0 %**. Investir davantage d'argent ne ferait que reproduire un résultat connu.

### Limites de notre travail

- **Échantillon réduit et runs incomplets** : 5 jeux interrompus avant épuisement du budget. Cela ne change pas la conclusion qualitative (0 niveau, comportements dégénérés observés sur 97 vraies décisions), mais une étude complète passerait les 80 actions sur les 25 jeux.
- **Rôle de la mémoire** : notre mode `simple` est *stateless*, ce qui pouvait à lui seul expliquer la répétition. Nous avons écarté cette objection avec l'essai CoT (§3.4), qui ajoute mémoire et signal de résultat des actions : le modèle a continué à répéter une action explicitement marquée « sans effet », et a échoué pareillement. L'absence de mémoire n'était donc pas la cause profonde. (L'agent officiel, lui aussi doté de mémoire, score également 0 % sur le leaderboard.)
- **Une seule famille de modèles** : tester aussi GPT-5 et Claude confirmerait que le phénomène est général aux LLM, et non propre à Gemini.

### Bilan

Malgré ses limites, l'expérience valait la peine d'être refaite par nous-mêmes plutôt que simplement citée : elle nous a permis de **manipuler concrètement le dispositif** (API, agent, format des grilles, contraintes de coût) et surtout d'**observer en direct** *comment* un modèle de pointe échoue (la répétition stérile, le clic compulsif, l'absence d'adaptation au feedback) ce qu'un simple chiffre « 0 % » sur un leaderboard ne révèle pas. Les benchmarks officiels nous confirment que ces modèles sont incapables de résoudre ces jeux ; nous l'avons vérifié et, surtout, nous avons compris *pourquoi*. Le projet répond ainsi pleinement à la question posée par le cours sur la part réelle d'« intelligence » dans l'IA actuelle.

---

### Annexe — Pour reproduire

```bash
pip install -r requirements.txt
git submodule update --init                       # framework ARC-AGI-3-Agents
cp .env.example .env                              # remplir ARC_API_KEY + GEMINI_API_KEY
uv run scripts/run_gemini.py --strategy simple --games 1 --model gemini-3.1-pro-preview
uv run scripts/analyze_results.py                 # tableau + figures
```

Données brutes : fichiers `*.recording.jsonl` (un par jeu) et logs dans
`results/gemini_simple/logs/`.
