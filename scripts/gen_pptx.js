// Generates the 5-minute presentation for the ARC-AGI-3 / Gemini project.
// Palette: deep midnight blues with a sharp magenta accent (echoes the ARC
// game grids, which use vivid purple/magenta). Header font: Georgia.
const pptxgen = require("pptxgenjs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const GIF = (g) => path.join(ROOT, "report", "figures", "gifs", `${g}.gif`);

// ---- palette -----------------------------------------------------------
const C = {
  bg: "0E1230",       // deep midnight (dark slides)
  bgLight: "F4F5FB",  // near-white (content slides)
  navy: "1E2761",     // panel navy
  ice: "9FB3E8",      // ice blue (muted text on dark)
  accent: "E53AA3",   // magenta accent (from ARC palette)
  green: "4FCC30",    // success/human green
  red: "F93C31",      // failure red
  ink: "1A1E33",      // dark text on light
  muted: "5B6184",    // muted text on light
  white: "FFFFFF",
};

const HFONT = "Georgia";
const BFONT = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
pres.author = "Aladin";
pres.title = "ARC-AGI-3 : quelle intelligence dans l'IA ?";

const W = 13.33, H = 7.5;

// reusable little tag chip (the repeated visual motif)
function chip(slide, x, y, text, fill, txtColor) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w: 0.14 + text.length * 0.105, h: 0.36,
    fill: { color: fill }, rectRadius: 0.05, line: { type: "none" },
  });
  slide.addText(text, {
    x, y, w: 0.14 + text.length * 0.105, h: 0.36,
    fontFace: BFONT, fontSize: 11, bold: true, color: txtColor,
    align: "center", valign: "middle", margin: 0,
  });
}

// small section number badge motif
function badge(slide, x, y, n) {
  slide.addShape(pres.shapes.OVAL, {
    x, y, w: 0.5, h: 0.5, fill: { color: C.accent }, line: { type: "none" },
  });
  slide.addText(String(n), {
    x, y, w: 0.5, h: 0.5, fontFace: HFONT, fontSize: 20, bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0,
  });
}

// =======================================================================
// SLIDE 1 — TITLE (dark)
// =======================================================================
let s = pres.addSlide();
s.background = { color: C.bg };
// accent vertical band
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.28, h: H, fill: { color: C.accent }, line: { type: "none" } });
s.addText("Quelle « intelligence » dans l'IA ?", {
  x: 0.9, y: 2.0, w: 11.5, h: 1.2, fontFace: HFONT, fontSize: 44, bold: true,
  color: C.white, align: "left",
});
s.addText("Tester Gemini 3 sur le benchmark ARC-AGI-3", {
  x: 0.9, y: 3.15, w: 11.5, h: 0.7, fontFace: HFONT, fontSize: 24, italic: true,
  color: C.accent, align: "left",
});
s.addText([
  { text: "MIN2026  ·  Travail pratique 4  ·  HEIG-VD", options: { breakLine: true } },
  { text: "Aladin", options: {} },
], { x: 0.9, y: 4.4, w: 11, h: 1.0, fontFace: BFONT, fontSize: 16, color: C.ice });

// =======================================================================
// SLIDE 2 — MOTIVATION (light)
// =======================================================================
s = pres.addSlide();
s.background = { color: C.bgLight };
badge(s, 0.6, 0.55, 1);
s.addText("Motivation", { x: 1.25, y: 0.5, w: 8, h: 0.6, fontFace: HFONT, fontSize: 32, bold: true, color: C.ink, margin: 0, valign: "middle" });

s.addText([
  { text: "Les LLM cartonnent aux tests humains.  ", options: { bold: true, color: C.ink } },
  { text: "ChatGPT obtient un QI verbal de 155, supérieur à 99,9 % des humains.", options: { color: C.muted } },
], { x: 1.25, y: 1.5, w: 7.0, h: 1.0, fontFace: BFONT, fontSize: 17 });

s.addText([
  { text: "Mais l'intelligence, selon F. Chollet, ce n'est pas la compétence :\n", options: { bold: true, color: C.ink, breakLine: true } },
  { text: "c'est la capacité à ", options: { color: C.muted } },
  { text: "acquérir de nouvelles compétences et à généraliser", options: { bold: true, color: C.accent } },
  { text: " à des problèmes jamais vus.", options: { color: C.muted } },
], { x: 1.25, y: 2.7, w: 7.0, h: 1.4, fontFace: BFONT, fontSize: 17 });

s.addText("« Everybody is a genius. But if you judge a fish by its ability to climb a tree… »", {
  x: 1.25, y: 4.6, w: 7.0, h: 0.9, fontFace: HFONT, fontSize: 15, italic: true, color: C.muted,
});

// right callout panel
s.addShape(pres.shapes.RECTANGLE, { x: 9.0, y: 1.5, w: 3.5, h: 4.2, fill: { color: C.navy }, line: { type: "none" } });
s.addText("La question", { x: 9.3, y: 1.8, w: 2.9, h: 0.5, fontFace: BFONT, fontSize: 13, bold: true, color: C.accent });
s.addText("Un LLM de pointe peut-il découvrir seul les règles d'un jeu inédit ?", {
  x: 9.3, y: 2.4, w: 2.9, h: 2.0, fontFace: HFONT, fontSize: 21, bold: true, color: C.white, valign: "top",
});

// =======================================================================
// SLIDE 3 — ARC-AGI-3 : LE DÉFI (light)
// =======================================================================
s = pres.addSlide();
s.background = { color: C.bgLight };
badge(s, 0.6, 0.55, 2);
s.addText("ARC-AGI-3 : le défi", { x: 1.25, y: 0.5, w: 9, h: 0.6, fontFace: HFONT, fontSize: 32, bold: true, color: C.ink, margin: 0, valign: "middle" });

s.addText([
  { text: "Des jeux interactifs", options: { bold: true, color: C.accent, breakLine: true } },
  { text: "On observe une grille, on agit, on observe le résultat, et on doit ", options: { color: C.muted } },
  { text: "déduire les règles par expérimentation", options: { bold: true, color: C.ink } },
  { text: ". Aucune instruction. Comme un enfant face à un jeu vidéo inconnu.", options: { color: C.muted } },
], { x: 1.25, y: 1.45, w: 6.4, h: 1.8, fontFace: BFONT, fontSize: 17 });

// comparison table
s.addTable([
  [
    { text: "Benchmark", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 14, align: "center" } },
    { text: "Humains", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 14, align: "center" } },
    { text: "Meilleurs LLM", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 14, align: "center" } },
  ],
  [
    { text: "ARC-AGI-1", options: { fontSize: 14 } },
    { text: "~98 %", options: { align: "center", fontSize: 14 } },
    { text: "~90 %", options: { align: "center", fontSize: 14 } },
  ],
  [
    { text: "ARC-AGI-2", options: { fontSize: 14 } },
    { text: "~100 %", options: { align: "center", fontSize: 14 } },
    { text: "~50-70 %", options: { align: "center", fontSize: 14 } },
  ],
  [
    { text: "ARC-AGI-3", options: { bold: true, fontSize: 15 } },
    { text: "~100 %", options: { align: "center", bold: true, color: C.green, fontSize: 15 } },
    { text: "0 %", options: { align: "center", bold: true, color: C.red, fontSize: 15 } },
  ],
], { x: 1.25, y: 3.55, w: 7.0, h: 2.6, border: { pt: 1, color: "D5D8E8" }, fill: { color: C.white }, rowH: 0.55 });

s.addText("GPT-5, Claude 4.6, Gemini 3 : tous à 0 %", {
  x: 1.25, y: 6.25, w: 7.0, h: 0.5, fontFace: BFONT, fontSize: 14, italic: true, color: C.muted,
});

// big stat block right
s.addShape(pres.shapes.RECTANGLE, { x: 9.0, y: 1.45, w: 3.5, h: 4.7, fill: { color: C.bg }, line: { type: "none" } });
s.addText("100 %", { x: 9.0, y: 2.0, w: 3.5, h: 1.0, fontFace: HFONT, fontSize: 54, bold: true, color: C.green, align: "center" });
s.addText("humains", { x: 9.0, y: 2.95, w: 3.5, h: 0.4, fontFace: BFONT, fontSize: 14, color: C.ice, align: "center" });
s.addText("vs", { x: 9.0, y: 3.5, w: 3.5, h: 0.5, fontFace: HFONT, fontSize: 20, italic: true, color: C.ice, align: "center" });
s.addText("0 %", { x: 9.0, y: 4.0, w: 3.5, h: 1.0, fontFace: HFONT, fontSize: 54, bold: true, color: C.red, align: "center" });
s.addText("IA de pointe", { x: 9.0, y: 4.95, w: 3.5, h: 0.4, fontFace: BFONT, fontSize: 14, color: C.ice, align: "center" });

// =======================================================================
// SLIDE 4 — NOTRE DISPOSITIF (light)
// =======================================================================
s = pres.addSlide();
s.background = { color: C.bgLight };
badge(s, 0.6, 0.55, 3);
s.addText("Notre dispositif", { x: 1.25, y: 0.5, w: 9, h: 0.6, fontFace: HFONT, fontSize: 32, bold: true, color: C.ink, margin: 0, valign: "middle" });

// left: how it works
s.addText([
  { text: "Framework officiel ", options: { bold: true, color: C.ink } },
  { text: "arcprize/ARC-AGI-3-Agents", options: { color: C.accent, italic: true, breakLine: true } },
  { text: "+ notre agent ", options: { color: C.muted } },
  { text: "GeminiAgent", options: { bold: true, color: C.ink } },
  { text: " (modèle gemini-3.1-pro-preview)", options: { color: C.muted } },
], { x: 1.25, y: 1.45, w: 6.3, h: 1.1, fontFace: BFONT, fontSize: 16 });

s.addText([
  { text: "À chaque tour : ", options: { bold: true, color: C.ink } },
  { text: "la grille 64×64 (entiers 0-15 = couleurs) est sérialisée en texte, envoyée à Gemini, qui répond par une action en JSON.", options: { color: C.muted } },
], { x: 1.25, y: 2.75, w: 6.3, h: 1.2, fontFace: BFONT, fontSize: 16 });

// agent comparison cards
s.addShape(pres.shapes.RECTANGLE, { x: 1.25, y: 4.2, w: 3.0, h: 2.4, fill: { color: C.navy }, line: { type: "none" } });
s.addText("Agent officiel", { x: 1.45, y: 4.4, w: 2.6, h: 0.4, fontFace: BFONT, fontSize: 14, bold: true, color: C.accent });
s.addText([
  { text: "2 appels API / tour", options: { bullet: true, breakLine: true, color: C.white } },
  { text: "observe → agit", options: { bullet: true, breakLine: true, color: C.white } },
  { text: "mémoire ~2-3 tours", options: { bullet: true, color: C.white } },
], { x: 1.45, y: 4.9, w: 2.65, h: 1.6, fontFace: BFONT, fontSize: 13 });

s.addShape(pres.shapes.RECTANGLE, { x: 4.5, y: 4.2, w: 3.0, h: 2.4, fill: { color: C.accent }, line: { type: "none" } });
s.addText("Notre agent (allégé)", { x: 4.7, y: 4.4, w: 2.6, h: 0.4, fontFace: BFONT, fontSize: 14, bold: true, color: C.white });
s.addText([
  { text: "1 appel API / tour", options: { bullet: true, breakLine: true, color: C.white } },
  { text: "sans mémoire (stateless)", options: { bullet: true, breakLine: true, color: C.white } },
  { text: "→ moins cher", options: { bullet: true, color: C.white, bold: true } },
], { x: 4.7, y: 4.9, w: 2.65, h: 1.6, fontFace: BFONT, fontSize: 13 });

// right: sample grid still
s.addShape(pres.shapes.RECTANGLE, { x: 8.7, y: 1.45, w: 3.9, h: 5.0, fill: { color: C.bg }, line: { type: "none" } });
s.addText("Ce que « voit » Gemini", { x: 8.9, y: 1.65, w: 3.5, h: 0.4, fontFace: BFONT, fontSize: 13, bold: true, color: C.ice });
s.addImage({ path: GIF("ka59"), x: 9.15, y: 2.15, w: 3.0, h: 3.43, sizing: { type: "contain", w: 3.0, h: 3.43 } });
s.addText("une grille d'entiers, animée tour par tour", { x: 8.9, y: 5.7, w: 3.6, h: 0.6, fontFace: BFONT, fontSize: 12, italic: true, color: C.ice, align: "center" });

// =======================================================================
// SLIDE 5 — COMMENT GEMINI ÉCHOUE (GIF) — dark, the money shot
// =======================================================================
s = pres.addSlide();
s.background = { color: C.bg };
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.28, h: H, fill: { color: C.accent }, line: { type: "none" } });
s.addText("Comment Gemini échoue", { x: 0.9, y: 0.5, w: 11, h: 0.7, fontFace: HFONT, fontSize: 34, bold: true, color: C.white });

// the GIF big on the left
s.addImage({ path: GIF("ka59"), x: 0.9, y: 1.55, w: 4.6, h: 5.26, sizing: { type: "contain", w: 4.6, h: 5.26 } });
s.addText("ka59 : le joueur poussé en boucle contre la barrière", {
  x: 0.9, y: 6.85, w: 4.6, h: 0.4, fontFace: BFONT, fontSize: 12, italic: true, color: C.ice, align: "center",
});

// observations right
s.addText("Deux pathologies", { x: 6.1, y: 1.7, w: 6.3, h: 0.5, fontFace: HFONT, fontSize: 22, bold: true, color: C.accent });

s.addShape(pres.shapes.RECTANGLE, { x: 6.1, y: 2.45, w: 6.5, h: 1.7, fill: { color: C.navy }, line: { type: "none" } });
s.addText("Répétition stérile", { x: 6.35, y: 2.6, w: 6.0, h: 0.4, fontFace: BFONT, fontSize: 15, bold: true, color: C.white });
s.addText("Sur ka59 : > 30 fois la même action « droite » sur 42 tours. Le modèle pousse au mur sans jamais changer d'approche.", {
  x: 6.35, y: 3.05, w: 6.0, h: 1.0, fontFace: BFONT, fontSize: 14, color: C.ice,
});

s.addShape(pres.shapes.RECTANGLE, { x: 6.1, y: 4.35, w: 6.5, h: 1.7, fill: { color: C.navy }, line: { type: "none" } });
s.addText("Clic compulsif", { x: 6.35, y: 4.5, w: 6.0, h: 0.4, fontFace: BFONT, fontSize: 15, bold: true, color: C.white });
s.addText("Sur lp85 et r11l : 100 % de clics, jamais un déplacement. Aucune conclusion tirée de l'absence de progrès.", {
  x: 6.35, y: 4.95, w: 6.0, h: 1.0, fontFace: BFONT, fontSize: 14, color: C.ice,
});

s.addText("→ Le modèle ne s'adapte pas au feedback de l'environnement.", {
  x: 6.1, y: 6.25, w: 6.5, h: 0.6, fontFace: HFONT, fontSize: 16, italic: true, bold: true, color: C.accent,
});

// =======================================================================
// SLIDE 6 — NOS RÉSULTATS (light)
// =======================================================================
s = pres.addSlide();
s.background = { color: C.bgLight };
badge(s, 0.6, 0.55, 4);
s.addText("Nos résultats", { x: 1.25, y: 0.5, w: 9, h: 0.6, fontFace: HFONT, fontSize: 32, bold: true, color: C.ink, margin: 0, valign: "middle" });

// huge 0 stat
s.addShape(pres.shapes.RECTANGLE, { x: 1.25, y: 1.6, w: 4.3, h: 4.6, fill: { color: C.bg }, line: { type: "none" } });
s.addText("0", { x: 1.25, y: 2.0, w: 4.3, h: 2.2, fontFace: HFONT, fontSize: 130, bold: true, color: C.red, align: "center" });
s.addText("niveau franchi", { x: 1.25, y: 4.2, w: 4.3, h: 0.5, fontFace: BFONT, fontSize: 18, bold: true, color: C.white, align: "center" });
s.addText("sur les 7 jeux testés", { x: 1.25, y: 4.75, w: 4.3, h: 0.5, fontFace: BFONT, fontSize: 14, color: C.ice, align: "center" });

// per-game table
s.addTable([
  [
    { text: "Jeu", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 13 } },
    { text: "Actions", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 13, align: "center" } },
    { text: "Niveaux", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 13, align: "center" } },
  ],
  [{ text: "ka59", options: { fontSize: 13 } }, { text: "42", options: { align: "center", fontSize: 13 } }, { text: "0", options: { align: "center", color: C.red, bold: true, fontSize: 13 } }],
  [{ text: "lp85", options: { fontSize: 13 } }, { text: "16", options: { align: "center", fontSize: 13 } }, { text: "0", options: { align: "center", color: C.red, bold: true, fontSize: 13 } }],
  [{ text: "lf52", options: { fontSize: 13 } }, { text: "15", options: { align: "center", fontSize: 13 } }, { text: "0", options: { align: "center", color: C.red, bold: true, fontSize: 13 } }],
  [{ text: "r11l", options: { fontSize: 13 } }, { text: "13", options: { align: "center", fontSize: 13 } }, { text: "0", options: { align: "center", color: C.red, bold: true, fontSize: 13 } }],
  [{ text: "cd82", options: { fontSize: 13 } }, { text: "12", options: { align: "center", fontSize: 13 } }, { text: "0", options: { align: "center", color: C.red, bold: true, fontSize: 13 } }],
  [{ text: "wa30 (Flash)", options: { fontSize: 13 } }, { text: "81", options: { align: "center", fontSize: 13 } }, { text: "0 / 9", options: { align: "center", color: C.red, bold: true, fontSize: 13 } }],
  [{ text: "ls20 (CoT)", options: { fontSize: 13, italic: true } }, { text: "81", options: { align: "center", fontSize: 13, italic: true } }, { text: "0", options: { align: "center", color: C.red, bold: true, fontSize: 13 } }],
], { x: 6.0, y: 1.6, w: 6.5, h: 4.0, border: { pt: 1, color: "D5D8E8" }, fill: { color: C.white }, rowH: 0.44 });

s.addText("wa30 : Gemini Flash n'a pas franchi le niveau 1 (80 actions) ; un humain le résout en ~71.", {
  x: 6.0, y: 5.75, w: 6.5, h: 0.6, fontFace: BFONT, fontSize: 13, italic: true, color: C.muted,
});

// =======================================================================
// SLIDE 7 — ET SI ON LUI DONNE DE LA MÉMOIRE ? (dark) — l'essai CoT
// =======================================================================
s = pres.addSlide();
s.background = { color: C.bg };
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.28, h: H, fill: { color: C.accent }, line: { type: "none" } });
s.addText("Et si on lui donne de la mémoire ?", { x: 0.9, y: 0.5, w: 11.5, h: 0.7, fontFace: HFONT, fontSize: 32, bold: true, color: C.white });

// left: the GIF of the improved run
s.addImage({ path: GIF("ls20"), x: 0.9, y: 1.55, w: 4.0, h: 4.55 });
s.addText("ls20 : agent amélioré, même errance dans le labyrinthe", {
  x: 0.9, y: 6.15, w: 4.0, h: 0.5, fontFace: BFONT, fontSize: 12, italic: true, color: C.ice, align: "center",
});

// right: what we added + the result
s.addText("Notre agent amélioré (CoT)", { x: 5.5, y: 1.6, w: 6.9, h: 0.5, fontFace: HFONT, fontSize: 22, bold: true, color: C.accent });
const cotPoints = [
  "mémoire des 6 derniers tours",
  "raisonnement explicite (chain-of-thought)",
  "le résultat de chaque action passée (« a changé / SANS EFFET »)",
];
cotPoints.forEach((pt, i) => {
  s.addText(pt, {
    x: 5.7, y: 2.3 + i * 0.55, w: 6.7, h: 0.5,
    fontFace: BFONT, fontSize: 15, color: C.white,
    bullet: { code: "2022", indent: 18 }, valign: "middle",
  });
});

// result panel
s.addShape(pres.shapes.RECTANGLE, { x: 5.5, y: 4.2, w: 6.95, h: 2.0, fill: { color: C.navy }, line: { type: "none" } });
s.addText("Résultat : aucun changement", { x: 5.75, y: 4.4, w: 6.5, h: 0.5, fontFace: BFONT, fontSize: 15, bold: true, color: C.accent });
s.addText([
  { text: "0 niveau franchi. Le modèle a joué 31 fois « droite » d'affilée.\n", options: { color: C.white, breakLine: true } },
  { text: "Sur 17 actions sans aucun effet, il voyait le signal « SANS EFFET » et l'a ignoré.", options: { color: C.ice } },
], { x: 5.75, y: 4.9, w: 6.5, h: 1.2, fontFace: BFONT, fontSize: 14 });

// =======================================================================
// SLIDE 8 — HUMAIN vs IA : MÊME JEU (light) — le contraste direct
// =======================================================================
s = pres.addSlide();
s.background = { color: C.bgLight };
badge(s, 0.6, 0.55, 5);
s.addText("Même jeu ls20 : humain vs IA", { x: 1.25, y: 0.5, w: 11.3, h: 0.6, fontFace: HFONT, fontSize: 30, bold: true, color: C.ink, margin: 0, valign: "middle" });

// left card: human
s.addImage({ path: GIF("ls20-aladin"), x: 1.3, y: 1.65, w: 3.6, h: 4.05 });
s.addText("Humain (l'auteur)", { x: 1.3, y: 5.75, w: 3.6, h: 0.4, fontFace: BFONT, fontSize: 15, bold: true, color: C.ink, align: "center" });

// right card: Opus
s.addImage({ path: GIF("ls20-4.8_opus"), x: 8.45, y: 1.65, w: 3.6, h: 4.05 });
s.addText("Claude 4.8 Opus", { x: 8.45, y: 5.75, w: 3.6, h: 0.4, fontFace: BFONT, fontSize: 15, bold: true, color: C.ink, align: "center" });

// center: the two scores stacked
s.addText("100 %", { x: 5.0, y: 2.35, w: 3.3, h: 1.0, fontFace: HFONT, fontSize: 50, bold: true, color: C.green, align: "center" });
s.addText("vs", { x: 5.0, y: 3.45, w: 3.3, h: 0.6, fontFace: HFONT, fontSize: 22, italic: true, color: C.muted, align: "center" });
s.addText("2 %", { x: 5.0, y: 4.05, w: 3.3, h: 1.0, fontFace: HFONT, fontSize: 50, bold: true, color: C.red, align: "center" });

s.addText("Le meilleur modèle public actuel passe à peine le 0 %. L'humain résout sans peine.", {
  x: 1.25, y: 6.35, w: 11.3, h: 0.5, fontFace: HFONT, fontSize: 15, italic: true, color: C.muted, align: "center",
});

// =======================================================================
// SLIDE 9 — CONFIRMÉ PAR LE LEADERBOARD OFFICIEL (light)
// =======================================================================
s = pres.addSlide();
s.background = { color: C.bgLight };
badge(s, 0.6, 0.55, 6);
s.addText("Confirmé par le leaderboard officiel", { x: 1.25, y: 0.5, w: 11.3, h: 0.6, fontFace: HFONT, fontSize: 30, bold: true, color: C.ink, margin: 0, valign: "middle" });

s.addText([
  { text: "Nous n'avons pas seulement cité un chiffre, nous l'avons ", options: { color: C.muted } },
  { text: "reproduit nous-mêmes.", options: { bold: true, color: C.accent } },
], { x: 1.25, y: 1.55, w: 11, h: 0.7, fontFace: BFONT, fontSize: 18 });

s.addText("À la sortie du benchmark, les meilleurs modèles affichaient tous 0 % :", {
  x: 1.25, y: 2.35, w: 11, h: 0.5, fontFace: BFONT, fontSize: 16, color: C.muted,
});

// three big 0% cards
const models = ["GPT-5", "Claude 4.6", "Gemini 3"];
models.forEach((m, i) => {
  const x = 1.25 + i * 3.95;
  s.addShape(pres.shapes.RECTANGLE, { x, y: 3.0, w: 3.6, h: 2.3, fill: { color: C.bg }, line: { type: "none" } });
  s.addText("0 %", { x, y: 3.25, w: 3.6, h: 1.2, fontFace: HFONT, fontSize: 60, bold: true, color: C.red, align: "center" });
  s.addText(m, { x, y: 4.5, w: 3.6, h: 0.5, fontFace: BFONT, fontSize: 17, bold: true, color: C.white, align: "center" });
});

s.addText([
  { text: "Depuis, Claude 4.8 Opus est le premier à franchir ce plancher : ", options: { color: C.ink } },
  { text: "2 %.", options: { bold: true, color: C.accent } },
  { text: "  Un progrès réel, mais l'écart avec les ~100 % humains reste béant.", options: { color: C.muted } },
], { x: 1.25, y: 5.6, w: 11, h: 0.7, fontFace: BFONT, fontSize: 16 });

s.addText("Le même résultat que le nôtre : la généralisation aux règles d'un jeu inédit reste hors de portée.", {
  x: 1.25, y: 6.5, w: 11, h: 0.5, fontFace: HFONT, fontSize: 15, italic: true, color: C.muted, align: "center",
});

// =======================================================================
// SLIDE 10 — CONCLUSION + RETOUR D'EXPÉRIENCE (dark)
// =======================================================================
s = pres.addSlide();
s.background = { color: C.bg };
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.28, h: H, fill: { color: C.accent }, line: { type: "none" } });
s.addText("Conclusion", { x: 0.9, y: 0.5, w: 11, h: 0.7, fontFace: HFONT, fontSize: 36, bold: true, color: C.white });

s.addText([
  { text: "Gemini 3 a toute l'information à l'écran, mais ne déduit pas les règles.\n", options: { bold: true, color: C.white, breakLine: true } },
  { text: "Inférer une règle et s'adapter quand on échoue : c'est exactement la généralisation que Chollet place au cœur de l'intelligence. Les LLM en restent de puissants détecteurs de motifs, hors-jeu dès qu'on sort de leur distribution.", options: { color: C.ice } },
], { x: 0.9, y: 1.5, w: 7.0, h: 2.6, fontFace: BFONT, fontSize: 17 });

// retour d'expérience panel
s.addShape(pres.shapes.RECTANGLE, { x: 8.4, y: 1.5, w: 4.2, h: 4.2, fill: { color: C.navy }, line: { type: "none" } });
s.addText("Retour d'expérience", { x: 8.65, y: 1.75, w: 3.7, h: 0.5, fontFace: BFONT, fontSize: 14, bold: true, color: C.accent });
s.addText([
  { text: "Coût API sous-estimé : ", options: { bold: true, color: C.white } },
  { text: "~16 CHF pour le run simple.", options: { color: C.ice, breakLine: true } },
  { text: "\n", options: { breakLine: true } },
  { text: "D'où l'agent allégé et l'arrêt volontaire, les benchmarks officiels confirmant déjà le 0 %.", options: { color: C.ice } },
], { x: 8.65, y: 2.4, w: 3.7, h: 3.0, fontFace: BFONT, fontSize: 15 });

s.addText("Refaire l'expérience nous a fait comprendre non pas que l'IA échoue, mais pourquoi.", {
  x: 0.9, y: 5.4, w: 7.0, h: 1.0, fontFace: HFONT, fontSize: 18, italic: true, bold: true, color: C.accent,
});

pres.writeFile({ fileName: path.join(ROOT, "report", "presentation.pptx") }).then((f) => {
  console.log("written:", f);
});
