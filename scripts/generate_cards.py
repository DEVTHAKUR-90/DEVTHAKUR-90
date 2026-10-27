#!/usr/bin/env python3
# VERSION: v4 (Dynamic Island pills: portfolio + built-by; live views pill moved to views-pill/)
"""Generate the profile cards and Dynamic Island pills as SVGs.

Live mode (used by the GitHub Action):
    GH_TOKEN=<token> GH_USERNAME=<login> python scripts/generate_cards.py

Preview mode (no token, sample numbers only):
    python scripts/generate_cards.py --demo

Writes to assets/cards/ (each in a -dark and a -light version):
    stats-*.svg, langs-*.svg                  the two GitHub cards
    portfolio-*.svg, builtby-*.svg            Dynamic Island pills (static)
The live "Profile Views" pill is drawn by views-pill/api/views.js (deployed on Vercel).
Standard library only.
"""
import html
import json
import os
import sys
import urllib.request
from pathlib import Path

USERNAME = os.environ.get("GH_USERNAME", "DEVTHAKUR-90")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT_DIR = Path(os.environ.get("OUT_DIR", "assets/cards"))

TOP_N = 8                # languages shown on the card
EXCLUDE_LANGS = set()    # e.g. {"HTML", "CSS", "Jupyter Notebook"}
EXCLUDE_REPOS = set()    # e.g. {"old-experiment"}

THEMES = {
    "dark": dict(bg="#161B22", border="#30363D", accent="#58A6FF",
                 label="#9BA7B4", value="#E6EDF3", muted="#8B949E", pill="#0D1117"),
    "light": dict(bg="#FFFFFF", border="#D0D7DE", accent="#0969DA",
                  label="#57606A", value="#1F2328", muted="#6E7781", pill="#F6F8FA"),
}

FONT = "-apple-system, 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

# 24x24 line icons (Lucide style). COLOR is replaced at draw time.
ICONS = {
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "code": '<path d="m18 16 4-4-4-4"/><path d="m6 8-4 4 4 4"/><path d="m14.5 4-5 16"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" fill="COLOR"/>',
    "commit": '<circle cx="12" cy="12" r="3"/><line x1="3" x2="9" y1="12" y2="12"/><line x1="15" x2="21" y1="12" y2="12"/>',
    "pr": '<circle cx="5" cy="6" r="3"/><path d="M5 9v12"/><circle cx="19" cy="18" r="3"/><path d="m15 9-3-3 3-3"/><path d="M12 6h5a2 2 0 0 1 2 2v7"/>',
    "issue": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="1" fill="COLOR"/>',
    "fork": '<circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"/><path d="M12 12v3"/>',
    "review": '<circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M6 9v12"/>',
    "heart": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" fill="COLOR"/>',
}


# GitHub mark (Octicons, 16x16)
GITHUB_MARK = ("M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 "
               "0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 "
               "0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 "
               "1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55"
               "-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 "
               ".67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z")


def icon(name, x, y, size, color, stroke_width=2):
    scale = size / 24
    body = ICONS[name].replace("COLOR", color)
    return (f'<g transform="translate({x} {y}) scale({scale:.4f})" fill="none" stroke="{color}" '
            f'stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round">{body}</g>')


def esc(s):
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------- data

def gql(query, variables):
    if not TOKEN:
        sys.exit("GH_TOKEN is not set. Use --demo for a preview, or provide a token.")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.load(resp)
    if out.get("errors"):
        sys.exit(f"GitHub API error: {json.dumps(out['errors'])[:500]}")
    return out["data"]


STATS_QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar { totalContributions }
      commitContributionsByRepository(maxRepositories: 100) { repository { nameWithOwner } }
      pullRequestContributionsByRepository(maxRepositories: 100) { repository { nameWithOwner } }
      issueContributionsByRepository(maxRepositories: 100) { repository { nameWithOwner } }
      pullRequestReviewContributionsByRepository(maxRepositories: 100) { repository { nameWithOwner } }
    }
  }
}
"""

REPOS_QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch_live():
    u = gql(STATS_QUERY, {"login": USERNAME})["user"]
    cc = u["contributionsCollection"]

    touched = set()
    for key in ("commitContributionsByRepository", "pullRequestContributionsByRepository",
                "issueContributionsByRepository", "pullRequestReviewContributionsByRepository"):
        for item in cc[key]:
            touched.add(item["repository"]["nameWithOwner"])

    stars, langs, after = 0, {}, None
    while True:
        page = gql(REPOS_QUERY, {"login": USERNAME, "after": after})["user"]["repositories"]
        for repo in page["nodes"]:
            if repo["name"] in EXCLUDE_REPOS:
                continue
            stars += repo["stargazerCount"]
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                if name in EXCLUDE_LANGS:
                    continue
                entry = langs.setdefault(name, {"size": 0, "color": edge["node"]["color"] or "#8B949E"})
                entry["size"] += edge["size"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]

    top = sorted(langs.items(), key=lambda kv: kv[1]["size"], reverse=True)[:TOP_N]
    total = sum(v["size"] for _, v in top) or 1
    lang_list = [(n, v["color"], v["size"] / total * 100) for n, v in top]

    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    prs = cc["totalPullRequestContributions"]
    issues = cc["totalIssueContributions"]
    reviews = cc["totalPullRequestReviewContributions"]
    return {
        "stars": stars,
        "contributions": cc["contributionCalendar"]["totalContributions"],
        "prs": prs, "issues": issues, "contributed_to": len(touched), "reviews": reviews,
        "langs": lang_list,
    }


def demo_data():
    return {
        "stars": 552, "contributions": 3546, "prs": 473, "issues": 272,
        "contributed_to": 74, "reviews": 195,
        "langs": [("Python", "#3572A5", 29.6), ("TypeScript", "#3178C6", 24.9),
                  ("Rust", "#DEA584", 19.2), ("C++", "#F34B7D", 7.9), ("C", "#555555", 7.9),
                  ("MATLAB", "#E16737", 4.7), ("JavaScript", "#F1E05A", 4.6),
                  ("Cython", "#FEDF5B", 1.3)],
    }


# ------------------------------------------------------------------------ rendering

W, H = 480, 254
PAD = 30


def card_open(t, title, icon_name, aria):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="{esc(aria)}">'
        f'<title>{esc(aria)}</title>'
        f'<style>text{{font-family:{FONT}}}</style>'
        f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="16" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1.5"/>'
        + icon(icon_name, PAD, 29, 24, t["accent"], 2)
        + f'<text x="{PAD+36}" y="48" font-size="20" font-weight="600" fill="{t["accent"]}">{esc(title)}</text>'
        f'<rect x="{PAD}" y="62" width="92" height="3" rx="1.5" fill="{t["accent"]}"/>'
    )


def stats_svg(d, t):
    rows = [
        ("star", "#FBBF24", "Total Stars Earned", d["stars"]),
        ("commit", "#34D399", "Contributions (12mo)", d["contributions"]),
        ("pr", "#A78BFA", "Pull Requests (12mo)", d["prs"]),
        ("issue", "#F472B6", "Issues (12mo)", d["issues"]),
        ("fork", "#60A5FA", "Contributed To (12mo)", d["contributed_to"]),
        ("review", "#FB923C", "Code Reviews (12mo)", d["reviews"]),
    ]
    out = [card_open(t, "GitHub Stats", "activity", f"GitHub stats for {USERNAME}")]
    for i, (name, colour, label, value) in enumerate(rows):
        cy = 94 + i * 27.2
        out.append(icon(name, PAD, cy - 10, 20, colour, 2))
        out.append(f'<text x="{PAD+33}" y="{cy+5:.1f}" font-size="14" fill="{t["label"]}">{esc(label)}</text>')
        out.append(f'<text x="323" y="{cy+5:.1f}" font-size="14" font-weight="700" text-anchor="end" fill="{t["value"]}">{value:,}</text>')

    rc = t["accent"]
    cx, cy = 414, 156
    out.append(f'<circle cx="{cx}" cy="{cy}" r="46" fill="{rc}" fill-opacity="0.12" stroke="{rc}" stroke-width="4"/>')
    out.append(f'<g transform="translate({cx-22} {cy-22}) scale(2.75)" fill="{rc}"><path d="{GITHUB_MARK}"/></g>')
    out.append("</svg>")
    return "".join(out)


def langs_svg(d, t):
    langs = d["langs"]
    out = [card_open(t, "Most Used Languages", "code", f"Most used languages for {USERNAME}")]

    bar_x, bar_y, bar_w, bar_h = PAD, 82, W - 2 * PAD, 14
    out.append(f'<clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="7"/></clipPath>')
    out.append('<g clip-path="url(#bar)">')
    x = bar_x
    for i, (_, colour, pct) in enumerate(langs):
        w = pct / 100 * bar_w
        gap = 2 if i < len(langs) - 1 else 0
        out.append(f'<rect x="{x:.2f}" y="{bar_y}" width="{max(w-gap, 1):.2f}" height="{bar_h}" fill="{colour}"/>')
        x += w
    out.append("</g>")

    cols = [(36, 54, 228), (266, 284, 450)]  # dot x, name x, percent right edge
    for i, (name, colour, pct) in enumerate(langs):
        dot_x, name_x, pct_x = cols[i % 2]
        cy = 125 + (i // 2) * 34.4
        out.append(f'<circle cx="{dot_x}" cy="{cy:.1f}" r="6" fill="{colour}"/>')
        out.append(f'<text x="{name_x}" y="{cy+5:.1f}" font-size="15" fill="{t["value"]}">{esc(name)}</text>')
        out.append(f'<text x="{pct_x}" y="{cy+5:.1f}" font-size="15" text-anchor="end" fill="{t["muted"]}">{pct:.1f}%</text>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------- Dynamic Island pills
# Black, fully rounded capsules (rx = height / 2) with a soft top sheen, like the
# iPhone's Dynamic Island. Purple accent matches the old Portfolio / Views badges.

PILL_H = 52
ACCENT_A, ACCENT_B = "#7C3AED", "#A78BFA"

PILL_THEMES = {
    # the island stays black in both modes; only the outline changes so it
    # still reads against GitHub's dark background
    "dark": dict(stroke_op="0.20", text="#FFFFFF", muted="#9CA3AF", chip_op="0.10"),
    "light": dict(stroke_op="0.00", text="#FFFFFF", muted="#A1A1AA", chip_op="0.12"),
}


def pill_open(w, t, aria):
    r = (PILL_H - 2) / 2
    body = f'x="1" y="1" width="{w-2}" height="{PILL_H-2}" rx="{r:g}"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{PILL_H}" viewBox="0 0 {w} {PILL_H}" '
        f'role="img" aria-label="{esc(aria)}">'
        f'<title>{esc(aria)}</title>'
        f'<style>text{{font-family:{FONT}}}'
        f'.beat{{transform-box:fill-box;transform-origin:center;animation:beat 1.6s ease-in-out infinite}}'
        f'@keyframes beat{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.2)}}}}</style>'
        f'<defs>'
        f'<linearGradient id="acc" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{ACCENT_A}"/><stop offset="1" stop-color="{ACCENT_B}"/></linearGradient>'
        f'<linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#FFFFFF" stop-opacity="0.10"/>'
        f'<stop offset="0.55" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
        f'</defs>'
        f'<rect {body} fill="#000000"/>'
        f'<rect {body} fill="url(#sheen)"/>'
        f'<rect {body} fill="none" stroke="#FFFFFF" stroke-opacity="{t["stroke_op"]}" stroke-width="1.5"/>'
    )


def portfolio_svg(t):
    # just the word "Portfolio" in a plain black capsule
    w = 176
    out = [pill_open(w, t, "Portfolio")]
    out.append(f'<text x="{w / 2:g}" y="32" font-size="17" font-weight="700" letter-spacing="0.4" '
               f'text-anchor="middle" fill="{t["text"]}">Portfolio</text>')
    out.append("</svg>")
    return "".join(out)


def builtby_svg(t):
    w, cy = 236, PILL_H / 2
    out = [pill_open(w, t, "Built with love by Dev Thakur")]
    out.append(f'<circle cx="27" cy="{cy:g}" r="17" fill="#FFFFFF" fill-opacity="{t["chip_op"]}"/>')
    out.append('<g class="beat">' + icon("heart", 27 - 9, cy - 9, 18, "#F472B6", 2) + '</g>')
    out.append(f'<text x="54" y="22" font-size="9.5" font-weight="600" letter-spacing="1.3" fill="{t["muted"]}">BUILT WITH LOVE BY</text>')
    out.append(f'<text x="54" y="40" font-size="16" font-weight="700" fill="{t["text"]}">Dev Thakur</text>')
    # the island's camera lens
    lx = w - 27
    out.append(f'<circle cx="{lx}" cy="{cy:g}" r="7.5" fill="#0A0A12" stroke="#FFFFFF" stroke-opacity="0.14" stroke-width="1"/>')
    out.append(f'<circle cx="{lx}" cy="{cy:g}" r="3.4" fill="#1B2559"/>')
    out.append(f'<circle cx="{lx - 1}" cy="{cy - 1:g}" r="1" fill="#FFFFFF" fill-opacity="0.55"/>')
    out.append("</svg>")
    return "".join(out)


def main():
    demo = "--demo" in sys.argv
    data = demo_data() if demo else fetch_live()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for theme_name, theme in THEMES.items():
        (OUT_DIR / f"stats-{theme_name}.svg").write_text(stats_svg(data, theme), encoding="utf-8")
        (OUT_DIR / f"langs-{theme_name}.svg").write_text(langs_svg(data, theme), encoding="utf-8")
    for theme_name, theme in PILL_THEMES.items():
        (OUT_DIR / f"portfolio-{theme_name}.svg").write_text(portfolio_svg(theme), encoding="utf-8")
        (OUT_DIR / f"builtby-{theme_name}.svg").write_text(builtby_svg(theme), encoding="utf-8")
    print(f"Wrote 8 files to {OUT_DIR}/ ({'demo' if demo else 'live'} data)")


if __name__ == "__main__":
    main()
