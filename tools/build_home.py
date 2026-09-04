"""
Homepage (newsletter layout) and newsletter web archive.
Called from build_articles.main(); not run directly.

    build_home(articles, latest_issue_url) -> HTML for src/static/index.html
    build_newsletter_archive()             -> writes src/static/newsletters/*.html + index, returns newest URL
"""
import datetime, html, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

LANES = [
    # id, title, blurb, topic keywords, title keywords  (first match wins, in this order)
    ("economy", "Economy, markets & policy",
     "The debt, the Fed, tariffs, Congress and the White House, translated into what changes for a fixed income.",
     (), ("trillion", "national debt", "tariff", "the fed", "federal reserve", "trust fund", "trump", "bessent", "congress", "rules changed", "coin", "visa", "cola")),
    ("investing", "Investing",
     "What to own, how much to keep in cash, and what the famous investors are actually doing with their own money.",
     ("investing",), ("invest", "stock", "fund", "cash", "buffett", "dalio", "musk", "kiyosaki", "hobson", "market", "portfolio", "index", "wealth", "crash", "gold", "corcoran")),
    ("insurance", "Insurance & Medicare",
     "Medicare, drug plans, claims, appeals, life insurance and the fine print that decides what you pay.",
     ("medicare", "insurance"), ("medicare", "insurance", "claim", "premium", "policy", "cuban")),
    ("taxes", "Taxes",
     "Deductions, required withdrawals, Roth moves, and the deadlines that cost money if you miss them.",
     ("tax",), ("tax", "deduction", "rmd", "required minimum", "irs", "roth")),
    ("mortgages", "Home & mortgages",
     "Paying off the house, downsizing, home equity, and the programs that pay for staying put.",
     ("home",), ("mortgage", "downsiz", "home equity", "aging in place", "house", "orman")),
    ("cashflow", "Household cash flow",
     "Budgets, debt, family money, discounts, and the scams that target people over 60.",
     ("money & family", "discount", "scam"), ("budget", "debt", "credit card", "scam", "discount", "adult child", "cut", "ramsey", "habits")),
    ("retirement", "Retirement planning",
     "Social Security claiming, how much is enough, working after 62, and making the money last.",
     ("social security", "retirement"), ()),
]
TOPIC_FIRST = {"insurance", "taxes", "mortgages", "cashflow"}   # lanes where the topic label beats title keywords


def lane_of(meta):
    title = meta["title"].lower(); topic = meta.get("topic", "").lower()
    for lane_id, _, _, topic_kw, _ in LANES:
        if lane_id in TOPIC_FIRST and any(k in topic for k in topic_kw):
            return lane_id
    for lane_id, _, _, _, title_kw in LANES:
        if any(k in title for k in title_kw):
            return lane_id
    for lane_id, _, _, topic_kw, _ in LANES:
        if any(k in topic for k in topic_kw):
            return lane_id
    return "retirement"


def build_home(articles, latest_issue_url):
    from build_articles import SITE, CSS_VERSION, HEADER, FOOTER, article_image, nice_date
    esc = lambda s: html.escape(s or "")

    def card_sm(m):
        return (f'<a class="card-sm" href="/articles/{m["slug"]}.html"><img src="{article_image(m)}" alt="" width="1200" height="630" loading="lazy">'
                f'<span class="topic-chip">{esc(m.get("topic", "Benefits"))}</span><h3>{esc(m["title"])}</h3>'
                f'<p>{esc(m["summary"])}</p><time>{nice_date(m["date"])}</time></a>')

    tpl = (ROOT / "tools" / "templates" / "home.html").read_text(encoding="utf-8")
    feature, rest = articles[0], articles[1:]
    latest_cards = "".join(card_sm(m) for m in rest[:6])
    names = [m for m in articles if m.get("image_credit")][:6]
    name_cards = "".join(
        f'<a class="name-card" href="/articles/{m["slug"]}.html"><img src="{article_image(m)}" alt="" loading="lazy">'
        f'<strong>{esc(m["title"].split(".")[0][:70])}</strong><span>{esc(m["summary"])}</span></a>' for m in names)
    by_lane = {l[0]: [] for l in LANES}
    for m in articles:
        by_lane[lane_of(m)].append(m)
    lanes_html = ""
    for lane_id, title, blurb, _, _ in LANES:
        items = by_lane[lane_id][:3]
        if not items:
            continue
        lanes_html += (f'<section class="lane" id="lane-{lane_id}"><div class="container"><div class="lane-head"><h2>{esc(title)}</h2>'
                       f'<a href="/articles/">More →</a></div><p class="lane-desc">{esc(blurb)}</p><div class="card-grid">'
                       + "".join(card_sm(m) for m in items) + "</div></div></section>\n")
    subs = {
        "{{SITE}}": SITE, "{{CSS_VERSION}}": CSS_VERSION, "{{OG_IMAGE}}": SITE + article_image(feature),
        "{{HEADER}}": HEADER, "{{FOOTER}}": FOOTER.format(year=datetime.date.today().year, css=CSS_VERSION),
        "{{FEATURE_SLUG}}": feature["slug"], "{{FEATURE_IMAGE}}": article_image(feature),
        "{{FEATURE_TOPIC}}": esc(feature.get("topic", "Benefits")), "{{FEATURE_TITLE}}": esc(feature["title"]),
        "{{FEATURE_SUMMARY}}": esc(feature["summary"]), "{{FEATURE_DATE}}": nice_date(feature["date"]),
        "{{LATEST_CARDS}}": latest_cards, "{{NAME_CARDS}}": name_cards, "{{LANES}}": lanes_html,
        "{{LATEST_ISSUE_URL}}": latest_issue_url,
    }
    for k, v in subs.items():
        tpl = tpl.replace(k, v)
    return tpl


def build_newsletter_archive():
    """Web copies of every built issue dated today or earlier. Returns the newest issue's URL."""
    from build_articles import SITE, page, nice_date
    import build_newsletter as bn
    dest = ROOT / "src" / "static" / "newsletters"
    dest.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    issues = []
    for p in sorted((ROOT / "content" / "newsletters").glob("*.json")):
        issue = json.loads(p.read_text(encoding="utf-8"))
        if issue["date"] > today:
            continue
        doc, _ = bn.build(issue)
        doc = (doc.replace('href="*|VIEW|*"', f'href="/newsletters/{issue["date"]}.html"')
                  .replace('href="*|UNSUB|*"', 'href="/privacy-policy.html"')
                  .replace("*|ESP|*", "web"))
        (dest / f"{issue['date']}.html").write_text(doc, encoding="utf-8")
        issues.append(issue)
    issues.sort(key=lambda i: i["date"], reverse=True)
    rows = "".join(
        f'<a href="/newsletters/{i["date"]}.html"><time>{nice_date(i["date"])}</time><h3>{html.escape(i["subject"])}</h3>'
        f'<p class="muted">{html.escape(i.get("preheader", ""))}</p></a>' for i in issues)
    body = ('<article class="article-page"><div class="container" style="max-width:820px;padding-top:2.5rem">'
            '<span class="topic-chip">Newsletter</span><h1>Issue archive</h1>'
            '<p class="summary">Every issue of the Senior Daily Benefits email, newest first. '
            '<a href="/#subscribe">Subscribe free</a> to get the next one.</p>'
            f'<div class="issue-list">{rows or "<p class=muted>No issues yet.</p>"}</div></div></article>')
    (dest / "index.html").write_text(page("Newsletter archive", "Every issue of the Senior Daily Benefits email.", body, f"{SITE}/newsletters/"), encoding="utf-8")
    return f"/newsletters/{issues[0]['date']}.html" if issues else "/newsletters/"
