// Live "Profile Views" Dynamic Island pill for a GitHub README.
//
// Every time the README is opened, GitHub asks this function for the image.
// The function adds one view to the komarev.com counter for the profile,
// reads the new total, and answers with the pill drawn as an SVG.
//
//   /api/views?theme=dark     pill for GitHub dark mode
//   /api/views?theme=light    pill for GitHub light mode
//
// Optional environment variable: GH_USERNAME (defaults to DEVTHAKUR-90).

const USERNAME = process.env.GH_USERNAME || "DEVTHAKUR-90";

const PILL_H = 52;
const FONT = "-apple-system, 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif";
const ACCENT_A = "#7C3AED";
const ACCENT_B = "#A78BFA";

// Same look as the Python pills in scripts/generate_cards.py.
const THEMES = {
  dark: { strokeOp: "0.20", muted: "#9CA3AF", chipOp: "0.10" },
  light: { strokeOp: "0.00", muted: "#A1A1AA", chipOp: "0.12" },
};

// The last count we saw. It survives while the function stays warm, so if
// komarev is briefly down the pill still shows a number.
let lastCount = null;

function withCommas(n) {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderPill(count, themeName) {
  const t = THEMES[themeName] || THEMES.dark;
  const num = count === null ? "—" : withCommas(count);
  const labelW = 118;
  const chipW = num.length * 10 + 28;
  const chipX = 54 + labelW + 8;
  const w = chipX + chipW + 10;
  const r = (PILL_H - 2) / 2;
  const cy = PILL_H / 2;
  const body = `x="1" y="1" width="${w - 2}" height="${PILL_H - 2}" rx="${r}"`;
  const aria = esc(`Profile views: ${num}`);

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${PILL_H}" viewBox="0 0 ${w} ${PILL_H}" role="img" aria-label="${aria}">` +
    `<title>${aria}</title>` +
    `<style>text{font-family:${FONT}}</style>` +
    `<defs>` +
    `<linearGradient id="acc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${ACCENT_A}"/><stop offset="1" stop-color="${ACCENT_B}"/></linearGradient>` +
    `<linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.10"/><stop offset="0.55" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>` +
    `</defs>` +
    `<rect ${body} fill="#000000"/>` +
    `<rect ${body} fill="url(#sheen)"/>` +
    `<rect ${body} fill="none" stroke="#FFFFFF" stroke-opacity="${t.strokeOp}" stroke-width="1.5"/>` +
    // eye icon in a round chip
    `<circle cx="27" cy="${cy}" r="17" fill="#FFFFFF" fill-opacity="${t.chipOp}"/>` +
    `<g transform="translate(18 ${cy - 9}) scale(0.7500)" fill="none" stroke="${ACCENT_B}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">` +
    `<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></g>` +
    `<text x="54" y="30" font-size="11" font-weight="600" letter-spacing="1.4" fill="${t.muted}">PROFILE VIEWS</text>` +
    `<rect x="${chipX}" y="10" width="${chipW}" height="32" rx="16" fill="url(#acc)"/>` +
    `<text x="${chipX + chipW / 2}" y="31" font-size="16" font-weight="700" text-anchor="middle" fill="#FFFFFF">${esc(num)}</text>` +
    `</svg>`
  );
}

// Asking komarev for its badge adds one view and returns the new total.
async function bumpAndRead() {
  const url = `https://komarev.com/ghpvc/?username=${encodeURIComponent(USERNAME)}&label=VIEWS`;
  const resp = await fetch(url, {
    headers: { "User-Agent": "profile-views-pill" },
    signal: AbortSignal.timeout(8000),
  });
  if (!resp.ok) throw new Error(`komarev answered ${resp.status}`);
  const svg = await resp.text();

  const labelled = svg.match(/aria-label="[^"]*?:\s*([0-9][0-9,]*)"/);
  let digits = labelled && labelled[1];
  if (!digits) {
    const all = [...svg.matchAll(/>\s*([0-9][0-9,]*)\s*</g)];
    digits = all.length ? all[all.length - 1][1] : null;
  }
  if (!digits) throw new Error("could not find the number in komarev's answer");
  return parseInt(digits.replace(/,/g, ""), 10);
}

async function handler(req, res) {
  const theme = req.query && req.query.theme === "light" ? "light" : "dark";

  try {
    lastCount = await bumpAndRead();
  } catch (err) {
    console.error("views:", err.message);
  }

  res.setHeader("Content-Type", "image/svg+xml; charset=utf-8");
  // Never let GitHub (or anything else) reuse an old copy, or the count would freeze.
  res.setHeader("Cache-Control", "max-age=0, no-cache, no-store, must-revalidate");
  res.status(200).send(renderPill(lastCount, theme));
}

module.exports = handler;
module.exports.renderPill = renderPill;
