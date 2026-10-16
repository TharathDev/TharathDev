"""
Builds the neofetch-style profile cards (dark_mode.svg / light_mode.svg).

Edit the PROFILE section below to change what the card says.
GitHub stats are fetched live from the GraphQL API when a token is available
(ACCESS_TOKEN or GITHUB_TOKEN env var); otherwise the last values saved in
stats.json are reused so the card can still be built offline.
"""
import datetime as dt
import json
import os
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
USER = "TharathDev"
CODING_SINCE = dt.date(2022, 5, 25)  # GitHub account creation date

# ---------------------------------------------------------------- PROFILE ---
TITLE = "tharath@dev"
SECTIONS = [
    [
        ("OS", "macOS, Linux, iOS"),
        ("Uptime", "{uptime}"),
        ("Host", "Full Stack Developer & ML Researcher"),
        ("Kernel", "Computer Vision / AI"),
        ("IDE", "VS Code, Xcode"),
    ],
    "Education",
    [
        ("Degree.Master", "Chongqing University of Technology"),
        ("Degree.Engineer", "Institute of Technology of Cambodia"),
    ],
    [
        ("Research.Fields", "Machine Learning, Computer Vision"),
        ("Research.Topics", "AI, Transformer Models, 3D Models"),
    ],
    [
        ("Languages", "Python, TypeScript, JavaScript, Go, C#"),
        ("Dev.Backend", "FastAPI, Flask, .NET, Golang, NestJS"),
        ("Dev.Frontend", "Vue, React, Laravel, HTML/CSS"),
        ("Dev.Architecture", "Microservices, REST APIs"),
    ],
    "Contact",
    [
        ("Email", "tharath.dev@gmail.com"),
        ("LinkedIn", "linkedin.com/in/tharath-tho"),
        ("Telegram", "t.me/TharathTHO"),
    ],
    "GitHub Stats",
    [
        ("Repos", "{repos} {{Contributed: {contributed}}}", ("Stars", "{stars}")),
        ("Commits", "{commits}", ("Followers", "{followers}")),
        ("Contributions", "{contributions} (all time)"),
    ],
]
# ----------------------------------------------------------------------------

THEMES = {
    "dark": dict(bg="#161b22", text="#c9d1d9", key="#ffa657", value="#a5d6ff", dots="#616e7f", art="#c9d1d9"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", value="#0a3069", dots="#c2cfde", art="#24292f"),
}

FONT_SIZE = 16
LINE_H = 20
CHAR_W = 9.63  # approx. advance width of a 16px monospace glyph
ART_X = 15
ART_GAP = 30  # space between the portrait and the info column
INFO_COLS = 56  # characters per info line
RIGHT_COLS = 20  # width of the right-hand column on two-stat lines


def uptime(since: dt.date, today: dt.date) -> str:
    years = today.year - since.year
    months = today.month - since.month
    days = today.day - since.day
    if days < 0:
        months -= 1
        prev_month_end = today.replace(day=1) - dt.timedelta(days=1)
        days += prev_month_end.day
    if months < 0:
        years -= 1
        months += 12
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{plural(years, 'year')}, {plural(months, 'month')}, {plural(days, 'day')}"


GRAPHQL = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount }
    }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
    contributionsCollection { contributionYears }
  }
}
"""

YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
  }
}
"""


def gql(token: str, query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fetch_stats(token: str) -> dict:
    repos = stars = 0
    cursor = None
    while True:
        user = gql(token, GRAPHQL, {"login": USER, "cursor": cursor})["user"]
        page = user["repositories"]
        repos = page["totalCount"]
        stars += sum(n["stargazerCount"] for n in page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    commits = contributions = 0
    for year in user["contributionsCollection"]["contributionYears"]:
        c = gql(token, YEAR_QUERY, {
            "login": USER,
            "from": f"{year}-01-01T00:00:00Z",
            "to": f"{year}-12-31T23:59:59Z",
        })["user"]["contributionsCollection"]
        commits += c["totalCommitContributions"] + c["restrictedContributionsCount"]
        contributions += c["contributionCalendar"]["totalContributions"]

    return {
        "repos": repos,
        "contributed": user["repositoriesContributedTo"]["totalCount"],
        "stars": stars,
        "followers": user["followers"]["totalCount"],
        "commits": commits,
        "contributions": contributions,
    }


def load_stats() -> dict:
    cache = ROOT / "stats.json"
    token = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        try:
            stats = fetch_stats(token)
            cache.write_text(json.dumps(stats, indent=2) + "\n")
            return stats
        except Exception as exc:  # keep the card buildable if the API hiccups
            print(f"warning: could not fetch stats ({exc}); using cache")
    if cache.exists():
        return json.loads(cache.read_text())
    return dict(repos=0, contributed=0, stars=0, followers=0, commits=0, contributions=0)


def fmt(template: str, values: dict) -> str:
    return template.format(**values)


def dotted(key: str, value: str, width: int) -> list:
    """Return spans for '. key: ....... value' padded to `width` chars."""
    fill = width - len(f". {key}:") - len(value) - 2
    dots = " " + "." * max(fill, 1) + " "
    return [("dots", ". "), ("key", f"{key}:"), ("dots", dots), ("value", value)]


def info_lines(values: dict) -> list:
    """Each line is a list of (css_class, text) spans."""
    lines = [[("key", TITLE), ("text", " " + "—" * (INFO_COLS - len(TITLE) - 1))]]
    after_header = True
    for block in SECTIONS:
        if isinstance(block, str):
            lines.append([])
            lines.append([("key", block), ("text", " " + "—" * (INFO_COLS - len(block) - 1))])
            after_header = True
            continue
        if not after_header:
            lines.append([])
        after_header = False
        for entry in block:
            key, value = entry[0], fmt(entry[1], values)
            if len(entry) == 3:  # two stats on one line: left | right
                k2, v2 = entry[2][0], fmt(entry[2][1], values)
                right_w = RIGHT_COLS - 3
                fill = right_w - len(k2) - 1 - len(v2) - 2
                right = [("key", f"{k2}:"), ("dots", " " + "." * max(fill, 1) + " "), ("value", v2)]
                lines.append(dotted(key, value, INFO_COLS - RIGHT_COLS) + [("text", " | ")] + right)
            else:
                lines.append(dotted(key, value, INFO_COLS))
    return lines


def build_svg(theme: dict, art: list, info: list) -> str:
    rows = max(len(art), len(info))
    height = rows * LINE_H + 40
    info_x = ART_X + round(max(map(len, art)) * CHAR_W) + ART_GAP
    width = info_x + int(INFO_COLS * CHAR_W) + 25

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,\'Courier New\',monospace" '
        f'width="{width}px" height="{height}px" font-size="{FONT_SIZE}px">',
        "<style>",
        "@font-face { src: local('Consolas'), local('Consolas Bold'); font-family: 'ConsolasFallback'; "
        "font-display: swap; -webkit-size-adjust: 109%; size-adjust: 109%; }",
        f".key {{fill: {theme['key']};}}",
        f".value {{fill: {theme['value']};}}",
        f".dots {{fill: {theme['dots']};}}",
        f".text {{fill: {theme['text']};}}",
        f".art {{fill: {theme['art']};}}",
        "text, tspan {white-space: pre;}",
        "</style>",
        f'<rect width="{width}px" height="{height}px" fill="{theme["bg"]}" rx="15"/>',
    ]

    art_top = 30 + max(0, (len(info) - len(art)) // 2) * LINE_H
    out.append(f'<text x="{ART_X}" y="{art_top}" class="art">')
    for i, line in enumerate(art):
        out.append(f'<tspan x="{ART_X}" y="{art_top + i * LINE_H}">{escape(line)}</tspan>')
    out.append("</text>")

    info_top = 30 + max(0, (len(art) - len(info)) // 2) * LINE_H
    out.append(f'<text x="{info_x}" y="{info_top}" class="text">')
    for i, spans in enumerate(info):
        if not spans:
            continue
        inner = "".join(f'<tspan class="{cls}">{escape(txt)}</tspan>' for cls, txt in spans)
        out.append(f'<tspan x="{info_x}" y="{info_top + i * LINE_H}">{inner}</tspan>')
    out.append("</text>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def thousands(n: int) -> str:
    return f"{n:,}"


def main():
    stats = load_stats()
    values = {k: thousands(v) for k, v in stats.items()}
    values["uptime"] = uptime(CODING_SINCE, dt.date.today())

    art = (ROOT / "ascii.txt").read_text().rstrip("\n").splitlines()
    info = info_lines(values)
    for name, theme in THEMES.items():
        (ROOT / f"{name}_mode.svg").write_text(build_svg(theme, art, info))
    print("updated:", values)


if __name__ == "__main__":
    main()
