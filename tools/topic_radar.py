#!/usr/bin/env python3
"""
Topic radar: pull the latest headlines from the source sites, score them for
Senior Daily Benefits, and print a ranked candidate list.

    python tools/topic_radar.py                 # last 3 days, top 30
    python tools/topic_radar.py --days 7 --top 50
    python tools/topic_radar.py --celebrity-only
    python tools/topic_radar.py --write         # also save content/radar/<today>.md

Sources: RSS where a site offers one (money.com, gobankingrates.com,
moneytalksnews.com, kiplinger.com) and Google News site-search RSS for the
rest (moneywise.com, thepennyhoarder.com) plus a second pass over all six.
Scoring: named celebrities/politicians (required for the newsletter lead),
senior-money keywords, and recency. Candidates that overlap an existing
article title are flagged so we don't write the same piece twice.
Standard library only.
"""
import argparse, datetime, html, pathlib, re, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

SITES = ["moneywise.com", "money.com", "gobankingrates.com", "moneytalksnews.com", "thepennyhoarder.com", "kiplinger.com"]
RSS = {
    "money.com": "https://money.com/feed/",
    "gobankingrates.com": "https://www.gobankingrates.com/feed/",
    "moneytalksnews.com": "https://www.moneytalksnews.com/feed/",
    "kiplinger.com": "https://www.kiplinger.com/feeds/all",
}
def gnews(site, q="retirement OR Social Security OR Medicare OR retirees OR seniors"):
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": f"site:{site} ({q})", "hl": "en-US", "gl": "US", "ceid": "US:en"})

CELEBS = [
    "Trump", "Bessent", "Vance", "Musk", "Buffett", "Dalio", "Kiyosaki", "Ramsey", "Orman", "Cuban", "Fink",
    "Powell", "Bezos", "Gates", "Zuckerberg", "Dimon", "El-Erian", "Cramer", "Sethi", "Grant Cardone", "Kevin O'Leary",
    "O'Leary", "Tony Robbins", "Robbins", "Schwab", "Bloomberg", "Pelosi", "Sanders", "Warren", "Ocasio", "Newsom",
    "DeSantis", "Biden", "Obama", "Clinton", "Harris", "Schumer", "Johnson", "Hegseth", "RFK", "Kennedy", "Oz",
    "Dr. Oz", "Oprah", "Shaq", "Jeff Bezos", "Barbara Corcoran", "Corcoran", "Ackman", "Griffin", "Icahn", "Gundlach",
    "Yellen", "Lutnick", "Dolly Parton", "Rowe", "Mellody Hobson", "Hobson", "Suze", "Corcoran", "Arnold Schwarzenegger", "Schwarzenegger",
]
SENIOR_KW = {
    "social security": 4, "medicare": 4, "medicaid": 2, "retire": 3, "retirement": 3, "retirees": 3, "seniors": 3,
    "boomer": 3, "rmd": 3, "required minimum": 3, "401(k)": 2, "ira": 1, "roth": 2, "cola": 3, "pension": 2,
    "annuity": 2, "inflation": 1, "tax": 1, "irs": 2, "scam": 3, "fraud": 2, "part d": 3, "medicare advantage": 4,
    "reverse mortgage": 3, "downsiz": 2, "nursing home": 3, "long-term care": 3, "estate": 1, "inheritance": 2,
    "widow": 2, "survivor": 2, "trust fund": 3, "benefit": 1, "discount": 2, "aarp": 2,
}
STOP = {"mortgage rates today", "best savings", "cd rates", "student loan", "credit card offer", "deal", "deals",
        "coupon", "black friday", "amazon", "walmart deal"}

def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            return r.read()
    except Exception as e:  # noqa: BLE001
        print(f"  ! {url[:70]}: {e.__class__.__name__}", file=sys.stderr)
        return b""

def parse(xml_bytes, site):
    out = []
    if not xml_bytes:
        return out
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return out
    for item in root.iter("item"):
        title = html.unescape((item.findtext("title") or "").strip())
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate") or ""
        try:
            when = parsedate_to_datetime(pub)
        except Exception:  # noqa: BLE001
            when = None
        title = re.sub(r"\s+-\s+[A-Za-z .]+$", "", title) if "news.google" in link or "google" in (item.findtext("source") or "") else title
        out.append({"title": title, "link": link, "when": when, "site": site})
    return out

def score(title):
    t = title.lower()
    celebs = [c for c in CELEBS if re.search(r"\b" + re.escape(c.lower()) + r"\b", t)]
    s = 10 * len(set(celebs))
    for kw, w in SENIOR_KW.items():
        if kw in t:
            s += w
    if any(x in t for x in STOP):
        s -= 6
    if re.search(r"\b(65|70|73|75|62|67)\b", t):
        s += 1
    return s, sorted(set(celebs))

def existing_titles():
    out = []
    for p in (ROOT / "content" / "articles").glob("*.md"):
        m = re.search(r"^title:\s*(.*)$", p.read_text(), re.M)
        if m:
            out.append(m.group(1).lower())
    return out

def overlaps(title, existing):
    words = {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 4}
    for e in existing:
        ew = {w for w in re.findall(r"[a-z0-9]+", e) if len(w) > 4}
        if words and len(words & ew) / max(len(words), 1) >= 0.5:
            return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--celebrity-only", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    items = []
    for site in SITES:
        if site in RSS:
            items += parse(fetch(RSS[site]), site)
        items += parse(fetch(gnews(site)), site)
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=a.days)
    seen, rows = set(), []
    exist = existing_titles()
    for it in items:
        key = re.sub(r"[^a-z0-9]+", " ", it["title"].lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        if it["when"] and it["when"] < cutoff:
            continue
        s, celebs = score(it["title"])
        if a.celebrity_only and not celebs:
            continue
        rows.append({**it, "score": s, "celebs": celebs, "dup": overlaps(it["title"], exist)})
    rows.sort(key=lambda r: (-r["score"], r["when"] or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)), reverse=False)
    rows.sort(key=lambda r: -r["score"])

    today = datetime.date.today().isoformat()
    lines = [f"# Topic radar {today} (last {a.days} days, {len(rows)} candidates)", ""]
    for r in rows[: a.top]:
        when = r["when"].strftime("%m-%d") if r["when"] else "--"
        tag = ("★ " + ", ".join(r["celebs"])) if r["celebs"] else "general"
        dup = "  (similar article exists)" if r["dup"] else ""
        lines.append(f"- [{r['score']:>2}] {when} {r['site']:<20} {tag}: {r['title']}{dup}\n  {r['link']}")
    text = "\n".join(lines)
    print(text)
    if a.write:
        out = ROOT / "content" / "radar" / f"{today}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"\nsaved {out}")

if __name__ == "__main__":
    main()
