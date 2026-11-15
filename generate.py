"""
Profile card generator for github.com/ahmedabdulghany7
Designed and written by Ahmed Abdulghany.

Builds dark_mode.svg and light_mode.svg:
  left  : ASCII art made from your GitHub avatar
  right : terminal style info + live GitHub stats

Run:  python generate.py            (needs GH_TOKEN env var)
      python generate.py --offline  (sample stats, for testing the layout)
"""

import datetime as dt
import html
import io
import json
import os
import sys
import time
import urllib.request

# ============================================================
#  EDIT THIS PART: your info (set a value to None to hide it)
# ============================================================
USER = "ahmedabdulghany7"
HEADER = "ahmed@abdulghany"
BIRTHDAY = dt.date(2001, 3, 31)  # e.g. dt.date(2003, 1, 1) -> shows "Uptime: 22 years, 3 months, 5 days"

INFO = [
    ("OS", "Ubuntu Linux, iOS"),
    ("Uptime", "BIRTHDAY"),  # filled from BIRTHDAY, hidden if None
    ("Host", ""),            # "" = key with empty dots
    ("Kernel", "Software Engineer & AI Creator"),
    ("IDE", "VS Code, Neovim, Vim"),
    ("Terminal", "Zsh, tmux, Git"),
    None,
    ("Languages.Programming", "C++, Java, Python, JavaScript"),
    ("Languages.Computer", "HTML, CSS, JSON, Markdown"),
    ("Languages.Real", "Arabic, English"),
    None,
    ("Hobbies.Software", "Open Source, AI Agents & Automation"),
    ("", "Linux Ricing, iOS App Development"),   # "" key = continues the row above
    ("Hobbies.Creative", "Motion Graphics, Video Editing"),
    ("", "3D Avatars, AI Art, Photo Editing"),
    ("Hobbies.Life", "Gym, Video Gaming"),
]

CONTACT = [
    ("Email", "ahmedabdulghany7@gmail.com"),
    ("LinkedIn", "@ahmedabdulghany"),
    ("X", "@ahmedabghany"),
    ("Discord", "@ahmedabdulghany"),
    ("Instagram", "@ahmedabdulghany7"),
    ("GitHub", f"@{USER}"),
]

ASCII_WIDTH = 56      # characters across for the avatar
LINE_WIDTH = 58       # characters across for the info column
# ============================================================

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
RAMP = " .'`,:;-~+=*xo%#&8@"

THEMES = {
    "dark": dict(bg="#161b22", text="#c9d1d9", key="#ffa657", value="#a5d6ff",
                 dim="#616e7f", add="#3fb950", sub="#f85149"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", value="#0a3069",
                  dim="#c2cfde", add="#1a7f37", sub="#cf222e"),
}


# ---------------- GitHub data ----------------
def _request(url, data=None):
    token = os.environ.get("GH_TOKEN", "")
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"bearer {token}",
        "User-Agent": USER,
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    _, raw = _request("https://api.github.com/graphql", body)
    out = json.loads(raw)
    if "errors" in out:
        raise RuntimeError(out["errors"])
    return out["data"]


def fetch_stats():
    base = gql("""
      query($login:String!){ user(login:$login){
        createdAt
        followers{ totalCount }
        repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY,ISSUE]){ totalCount }
        contributionsCollection{ contributionYears }
      }}""", {"login": USER})["user"]

    repos, cursor = [], None
    while True:
        page = gql("""
          query($login:String!,$after:String){ user(login:$login){
            repositories(ownerAffiliations:OWNER, first:100, after:$after){
              totalCount
              nodes{ name isFork stargazerCount }
              pageInfo{ hasNextPage endCursor }
            }}}""", {"login": USER, "after": cursor})["user"]["repositories"]
        repos += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    commits = 0
    for year in base["contributionsCollection"]["contributionYears"]:
        c = gql("""
          query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
            contributionsCollection(from:$from, to:$to){
              totalCommitContributions restrictedContributionsCount }}}""",
                {"login": USER, "from": f"{year}-01-01T00:00:00Z",
                 "to": f"{year}-12-31T23:59:59Z"})["user"]["contributionsCollection"]
        commits += c["totalCommitContributions"] + c["restrictedContributionsCount"]

    added = deleted = 0
    for repo in repos:
        if repo["isFork"]:
            continue
        url = f"https://api.github.com/repos/{USER}/{repo['name']}/stats/contributors"
        for _ in range(6):  # GitHub answers 202 while it builds the stats
            try:
                status, raw = _request(url)
            except Exception:
                break
            if status == 200 and raw:
                for person in json.loads(raw):
                    if (person.get("author") or {}).get("login", "").lower() == USER.lower():
                        for w in person["weeks"]:
                            added += w["a"]
                            deleted += w["d"]
                break
            time.sleep(4)

    return dict(
        repos=len(repos),
        contributed=base["repositoriesContributedTo"]["totalCount"],
        stars=sum(r["stargazerCount"] for r in repos),
        commits=commits,
        followers=base["followers"]["totalCount"],
        added=added,
        deleted=deleted,
    )


def sample_stats():
    return dict(repos=12, contributed=15, stars=8, commits=340, followers=20,
                added=52000, deleted=9000)


# ---------------- ASCII avatar ----------------
def avatar_ascii(offline=False, invert=False):
    from PIL import Image, ImageOps

    local = os.path.join(OUT_DIR, "avatar.png")
    if os.path.exists(local):
        img = Image.open(local)
    elif offline:
        return monogram()
    else:
        try:
            _, raw = _request(f"https://github.com/{USER}.png?size=460")
            img = Image.open(io.BytesIO(raw))
        except Exception:
            return monogram()

    img = ImageOps.exif_transpose(img).convert("RGBA")
    alpha = img.getchannel("A")             # transparent pixels = background
    gray = img.convert("L")
    # boost contrast using only the subject's pixels
    gray = ImageOps.autocontrast(gray, cutoff=1, mask=alpha.point(lambda a: 255 if a > 128 else 0))
    h = int(img.height / img.width * ASCII_WIDTH * 0.5)  # chars are ~2x taller than wide
    gray = gray.resize((ASCII_WIDTH, h), Image.LANCZOS)
    alpha = alpha.resize((ASCII_WIDTH, h), Image.LANCZOS)
    g, a = gray.load(), alpha.load()
    top = len(RAMP) - 1
    lines = []
    for y in range(h):
        row = ""
        for x in range(ASCII_WIDTH):
            if a[x, y] < 110:
                row += " "
                continue
            v = (255 - g[x, y]) if invert else g[x, y]
            v = 0.12 + 0.88 * v / 255           # floor keeps dark areas visible
            row += RAMP[min(top, max(1, int(v * top)))]
        lines.append(row.rstrip())
    while lines and not lines[0].strip():
        lines.pop(0)
    return lines


def monogram():
    return [
        "",
        "      d8888       .d8888b.        ",
        "     d88888      d88P  Y88b       ",
        "    d88P888      888    888       ",
        "   d88P 888      888              ",
        "  d88P  888      888  88888       ",
        " d88P   888      888    888       ",
        "d8888888888      Y88b  d88P       ",
        "d88P     888      \"Y8888P88       ",
    ]


# ---------------- layout ----------------
def uptime_text():
    if not BIRTHDAY:
        return None
    today = dt.date.today()
    y = today.year - BIRTHDAY.year
    m = today.month - BIRTHDAY.month
    d = today.day - BIRTHDAY.day
    if d < 0:
        m -= 1
        prev = (today.replace(day=1) - dt.timedelta(days=1))
        d += prev.day
    if m < 0:
        y -= 1
        m += 12
    s = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{s(y, 'year')}, {s(m, 'month')}, {s(d, 'day')}"


def esc(t):
    return html.escape(str(t), quote=False)


def kv(key, value):
    """One row: '. Key: ........ value' as a list of (text, style) parts."""
    if not key:
        dots = LINE_WIDTH - len(str(value)) - 3
        return [(". ", "dim"), ("." * max(dots, 1) + " ", "dim"), (value, "value")]
    dots = LINE_WIDTH - len(key) - len(str(value)) - 5
    return [(". ", "dim"), (key, "key"), (": ", "text"),
            ("." * max(dots, 1) + " ", "dim"), (value, "value")]


def section(title):
    bar = LINE_WIDTH - len(title) - 5
    return [("- ", "text"), (title, "text"), (" " + "—" * bar + "-—-", "dim")]


def pair(k1, v1, k2, v2, half=33):
    left = kv(k1, v1)
    dots = half - len(k1) - len(str(v1)) - 5
    left[3] = ("." * max(dots, 1) + " ", "dim")
    d2 = LINE_WIDTH - half - len(k2) - len(str(v2)) - 5
    return left + [(" | ", "dim"), (k2, "key"), (": ", "text"),
                   ("." * max(d2, 1) + " ", "dim"), (v2, "value")]


def build_rows(stats):
    rows = [[(HEADER, "text"), (" " + "—" * (LINE_WIDTH - len(HEADER) - 4) + "-—-", "dim")]]
    for item in INFO:
        if item is None:
            rows.append([(". ", "dim")])
            continue
        k, v = item
        if v == "BIRTHDAY":
            v = uptime_text()
        if v == "":
            rows.append(kv(k, "."))
        elif v:
            rows.append(kv(k, v))
    rows.append([])
    rows.append(section("Contact"))
    for k, v in CONTACT:
        if v:
            rows.append(kv(k, v))
    rows.append([])
    rows.append(section("GitHub Stats"))
    rows.append(pair("Repos", f"{stats['repos']} {{Contributed: {stats['contributed']}}}",
                     "Stars", f"{stats['stars']:,}"))
    rows.append(pair("Commits", f"{stats['commits']:,}", "Followers", f"{stats['followers']:,}"))
    loc = stats["added"] - stats["deleted"]
    rows.append(kv("Lines of Code on GitHub", f"{loc:,} ( {stats['added']:,}++, {stats['deleted']:,}-- )")[:-1]
                + [(f"{loc:,}", "value"), (" ( ", "text"), (f"{stats['added']:,}++", "add"),
                   (", ", "text"), (f"{stats['deleted']:,}--", "sub"), (" )", "text")])
    return rows


def render(theme, art, rows):
    c = THEMES[theme]
    lh, fs, cw = 20, 16, 9.63          # line height, font size, char width (Consolas 16px)
    info_x = int(50 + ASCII_WIDTH * cw)
    width = int(info_x + LINE_WIDTH * cw + 30)
    n = max(len(art), len(rows))
    height = n * lh + 40
    top = (n - len(art)) // 2

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,\'Courier New\',monospace" '
           f'width="{width}px" height="{height}px" font-size="{fs}px" xml:space="preserve">',
           f'<style>.key{{fill:{c["key"]}}}.value{{fill:{c["value"]}}}.dim{{fill:{c["dim"]}}}'
           f'.text{{fill:{c["text"]}}}.add{{fill:{c["add"]}}}.sub{{fill:{c["sub"]}}}'
           f'text,tspan{{white-space:pre}}</style>',
           f'<rect width="{width}px" height="{height}px" fill="{c["bg"]}" rx="15"/>',
           f'<text x="15" y="30" class="text">']
    for i, line in enumerate(art):
        out.append(f'<tspan x="15" y="{30 + (top + i) * lh}">{esc(line)}</tspan>')
    out.append("</text>")
    out.append(f'<text x="{info_x}" y="30" class="text">')
    for i, parts in enumerate(rows):
        y = 30 + i * lh
        spans = "".join(f'<tspan class="{s}">{esc(t)}</tspan>' for t, s in parts)
        out.append(f'<tspan x="{info_x}" y="{y}">{spans}</tspan>')
    out.append("</text></svg>")
    return "\n".join(out)


def main():
    offline = "--offline" in sys.argv
    stats = sample_stats() if offline else fetch_stats()
    rows = build_rows(stats)
    for theme in THEMES:
        art = avatar_ascii(offline, invert=True)
        with open(os.path.join(OUT_DIR, f"{theme}_mode.svg"), "w", encoding="utf-8") as f:
            f.write(render(theme, art, rows))
    print("done:", stats)


if __name__ == "__main__":
    main()
