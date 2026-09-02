#!/usr/bin/env python3
"""
Build /articles pages for Senior Daily Benefits.

Usage:
    python tools/build_articles.py

Reads every content/articles/*.md (front matter + Markdown), writes
src/static/articles/<slug>.html plus src/static/articles/index.html.
No third-party dependencies: a small Markdown subset is supported
(headings, paragraphs, bullet lists, bold, italic, links, blockquote).

Front matter keys:
    title        page title / H1
    slug         file name (no .html)
    date         YYYY-MM-DD
    summary      one-line teaser used on the list page + meta description
    topic        short label shown above the headline (e.g. "Social Security")
    sponsor      (optional) block name defined in SPONSORS below
    sources      (optional) list of "Label|URL" lines
    image_credit (optional) attribution line rendered under the hero image
"""
import re, html, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "articles"
OUT = ROOT / "src" / "static" / "articles"
SITE = "https://seniordailybenefits.com"

# Topic -> fallback banner (src/static/images/topics/*.svg). Articles may set `image:` in
# front matter to a path under src/static (e.g. images/2026-09-medicare.jpg) to use a photo.
TOPIC_ART = {"social security": "social-security", "medicare": "medicare", "tax": "taxes",
             "home": "home", "discount": "discounts", "scam": "scams"}
def article_image(meta):
    if meta.get("image"): return "/" + meta["image"].lstrip("/")
    t = meta.get("topic", "").lower()
    for k, v in TOPIC_ART.items():
        if k in t: return f"/images/topics/{v}.svg"
    return "/images/topics/general.svg"

# ---- affiliate / partner blocks. Edit copy + links here only. -------------
SPONSORS = {
    # Future Savings Today (affiliate ID TQ39S5C8). Copy is written to be
    # compliant: no promised savings amounts, no health/medical claims.
    # --- debt, credit, tax --------------------------------------------------
    "tax_relief": {
        "kicker": "From our partner",
        "title": "Received a letter from the IRS about back taxes?",
        "body": "If you owe more than you can pay, the IRS has programs that reduce or "
                "spread out the balance. A free consultation checks which ones you may qualify for.",
        "cta": "Check your options",
        "url": "https://www.ultiy.com/TQ39S5C8/XKBJT9PL/",
    },
    "balance_transfer": {
        "kicker": "From our partner",
        "title": "Paying interest on a credit card balance?",
        "body": "Some cards offer 0% interest on transferred balances into 2027 with no annual fee. "
                "Moving a balance can stop interest while you pay it down.",
        "cta": "See balance transfer cards",
        "url": "https://www.ultiy.com/TQ39S5C8/XLBX6LNW/",
    },
    "debt_settlement": {
        "kicker": "From our partner",
        "title": "More than $24,000 in credit card debt?",
        "body": "Debt settlement programs negotiate with card issuers on your behalf. "
                "They are not right for everyone, so start with a free, no-obligation review.",
        "cta": "Get a free review",
        "url": "https://www.ultiy.com/TQ39S5C8/XL22LGZ7/",
    },
    "cashback_card": {
        "kicker": "From our partner",
        "title": "A card that pays you back on everyday spending",
        "body": "Cards with 0% introductory interest and up to 5% cash back on common categories "
                "like groceries and gas. Compare current offers side by side.",
        "cta": "Compare cards",
        "url": "https://www.ultiy.com/TQ39S5C8/XKGF674Z/",
    },
    "heloc": {
        "kicker": "From our partner",
        "title": "Own your home? You may be able to borrow against it",
        "body": "A home equity line of credit uses the value in your house as collateral, usually at "
                "a lower rate than a credit card. Rates and terms vary; compare before you apply.",
        "cta": "Check HELOC rates",
        "url": "https://www.ultiy.com/TQ39S5C8/XKJ1LGND/",
    },
    # --- home -----------------------------------------------------------------
    "windows": {
        "kicker": "From our partner",
        "title": "Old windows raising your heating and cooling bills?",
        "body": "Get a free quote for energy-efficient replacement windows from installers in your area.",
        "cta": "Get a free quote",
        "url": "https://www.fugyn.com/TQ39S5C8/XL4N79ZD/",
    },
    "roof": {
        "kicker": "From our partner",
        "title": "Is your roof more than 15 years old?",
        "body": "A free estimate tells you whether it needs repair or replacement before a leak "
                "turns into a bigger bill.",
        "cta": "Get a free estimate",
        "url": "https://www.fugyn.com/TQ39S5C8/XL4LSF7R/",
    },
    "gutters": {
        "kicker": "From our partner",
        "title": "Tired of climbing a ladder to clean gutters?",
        "body": "Gutter guards keep leaves out so you don't have to. Current discounts for homeowners.",
        "cta": "See the offer",
        "url": "https://www.fugyn.com/TQ39S5C8/XLDRZ6MZ/",
    },
    "walkin_shower": {
        "kicker": "From our partner",
        "title": "Make your bathroom safer to use",
        "body": "A walk-in shower removes the step over the tub. Get a free quote for a conversion "
                "in your home.",
        "cta": "Get a free quote",
        "url": "https://www.fugyn.com/TQ39S5C8/XL4KFJH6/",
    },
    "home_warranty": {
        "kicker": "From our partner",
        "title": "Cover repairs on your appliances and systems",
        "body": "A home warranty plan covers breakdowns of things like your furnace, water heater, "
                "and kitchen appliances for a monthly fee. First month free with this plan.",
        "cta": "See plan details",
        "url": "https://www.jyqye.com/TQ39S5C8/XLF2WLC1/",
    },
    "title_lock": {
        "kicker": "From our partner",
        "title": "Get alerted if someone files against your home's title",
        "body": "Title monitoring watches county records and notifies you of changes to your deed "
                "so you can act quickly.",
        "cta": "Learn more",
        "url": "https://www.jyqye.com/TQ39S5C8/XLBN871T/",
    },
    "home_security": {
        "kicker": "From our partner",
        "title": "Home security you can check from your phone",
        "body": "Free quote for a monitored system, with $100 off installation for new customers.",
        "cta": "Get a free quote",
        "url": "https://www.elrof.com/TQ39S5C8/XKZJXZW1/",
    },
    # --- contract exit ----------------------------------------------------------
    "solar_exit": {
        "kicker": "From our partner",
        "title": "Signed a solar contract you regret?",
        "body": "Homeowners 55 and older may be able to cancel certain solar lease or loan "
                "agreements. A free eligibility check takes a couple of minutes.",
        "cta": "Check eligibility",
        "url": "https://www.fnule.com/TQ39S5C8/XLH57P8H/",
    },
    "timeshare_exit": {
        "kicker": "From our partner",
        "title": "Still paying for a timeshare you don't use?",
        "body": "Exit services help owners end timeshare contracts. Start with a free consultation "
                "to see whether yours qualifies.",
        "cta": "Get a free consultation",
        "url": "https://www.fnule.com/TQ39S5C8/XL9PTF2B/",
    },
    # --- health & everyday (no medical claims) ----------------------------------
    "hearing": {
        "kicker": "From our partner",
        "title": "Hearing devices that cost far less than you'd expect",
        "body": "Over-the-counter hearing devices for adults with mild to moderate hearing loss, "
                "currently $100 off.",
        "cta": "See the offer",
        "url": "https://www.fugyn.com/TQ39S5C8/XLHKPMTZ/",
    },
    "pillow": {
        "kicker": "From our partner",
        "title": "An ergonomic pillow, 70% off",
        "body": "Shaped to support the head and neck for side and back sleepers.",
        "cta": "See the offer",
        "url": "https://www.rybul.com/TQ39S5C8/XL1Q96JK/",
    },
    "insoles": {
        "kicker": "From our partner",
        "title": "Shoe insoles with a 55+ discount",
        "body": "Cushioned, arch-supporting insoles for people who spend a lot of the day on their feet.",
        "cta": "See the offer",
        "url": "https://www.rybul.com/TQ39S5C8/XL1T2Z1R/",
    },
    "skincare": {
        "kicker": "From our partner",
        "title": "Skincare designed for mature skin",
        "body": "A moisturizing cream from Beverly Hills MD, currently on promotion.",
        "cta": "See the offer",
        "url": "https://www.erxoa.com/TQ39S5C8/XL26R562/",
    },
    "detox_tea": {
        "kicker": "From our partner",
        "title": "Lulutox herbal tea, 75% off",
        "body": "A blended herbal tea, currently on promotion. Talk to your doctor before adding "
                "supplements to your routine.",
        "cta": "See the offer",
        "url": "https://www.loguq.com/TQ39S5C8/XLFQBZMH/",
    },
    # --- insurance, membership, tools -------------------------------------------
    "auto_insurance": {
        "kicker": "From our partner",
        "title": "When did you last compare car insurance rates?",
        "body": "Rates change every year. A quick comparison shows what other insurers would "
                "charge for the same coverage.",
        "cta": "Compare rates",
        "url": "https://www.fugyn.com/TQ39S5C8/XL5LL3XX/",
    },
    "aarp": {
        "kicker": "From our partner",
        "title": "AARP membership, $15 for the first year",
        "body": "Discounts on hotels, restaurants, prescriptions, and car rentals, plus access to "
                "AARP's benefits guides. Open to anyone 50 and over.",
        "cta": "Join AARP",
        "url": "https://www.fugyn.com/TQ39S5C8/XH4DSCJT/",
    },
    "adblock": {
        "kicker": "From our partner",
        "title": "Stop pop-ups and fake 'your computer is infected' ads",
        "body": "Total Adblock removes ads and blocks the scam pop-ups that target older users, "
                "from $2.42 a month.",
        "cta": "See the offer",
        "url": "https://www.zegea.com/TQ39S5C8/XLJ51CZM/",
    },
}

DISCLOSURE = ("Senior Daily Benefits may earn a commission if you sign up through "
              "partner links on this page. That never changes what we recommend.")

# ---------------------------------------------------------------------------
def parse(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise SystemExit(f"{path}: missing front matter")
    meta, body = {}, m.group(2)
    key = None
    for line in m.group(1).splitlines():
        if re.match(r"^\s+-\s", line) and key:
            meta.setdefault(key, [])
            if isinstance(meta[key], str): meta[key] = []
            meta[key].append(line.strip()[2:].strip())
        elif ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            meta[key] = val
    meta.setdefault("slug", path.stem)
    return meta, body

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*(?!\*)", r"<em>\1</em>", s)
    return s

def md_to_html(md):
    out, para, ul, quote = [], [], [], []
    def flush():
        nonlocal para, ul, quote
        if para:  out.append("<p>" + inline(" ".join(para)) + "</p>"); para = []
        if ul:    out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in ul) + "</ul>"); ul = []
        if quote: out.append('<aside class="callout"><p>' + inline(" ".join(quote)) + "</p></aside>"); quote = []
    for line in md.splitlines():
        s = line.rstrip()
        if not s.strip():
            flush(); continue
        if s.startswith("## "):
            flush(); out.append(f"<h2>{inline(s[3:])}</h2>")
        elif s.startswith("### "):
            flush(); out.append(f"<h3>{inline(s[4:])}</h3>")
        elif re.match(r"^\s*[-*]\s", s):
            if para or quote: flush()
            ul.append(re.sub(r"^\s*[-*]\s", "", s))
        elif s.startswith("> "):
            if para or ul: flush()
            quote.append(s[2:])
        else:
            if ul or quote: flush()
            para.append(s.strip())
    flush()
    return "\n".join(out)

def image_credit(meta):
    """Optional `image_credit:` front matter (e.g. "Photo: Gage Skidmore / Wikimedia Commons, CC BY-SA 2.0")."""
    c = meta.get("image_credit", "").strip()
    return f'<p class="img-credit">{html.escape(c)}</p>' if c else ""

def nice_date(iso):
    return datetime.date.fromisoformat(iso).strftime("%B %-d, %Y")

# ---------------------------------------------------------------------------
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,700&display=swap" rel="stylesheet">'
         '<link rel="stylesheet" href="/site.css">')

HEADER = """<div class="topbar"><span>ℹ Not affiliated with the U.S. Government or any federal agency</span><a href="/#newsletter">Get the free daily benefits email →</a></div>
<header class="site-header"><div class="container header-inner">
  <a href="/" class="brand"><span class="brand-mark">SDB</span><span class="brand-text"><span class="brand-name">Senior Daily Benefits</span><span class="brand-domain">seniordailybenefits.com</span></span></a>
  <nav class="nav"><a href="/#topics">Topics</a><a href="/articles/">Articles</a><a href="/#how">How It Works</a><a href="/#faq">FAQs</a></nav>
  <div class="header-cta"><a href="/#quiz" class="btn btn-outline">Check My Benefits</a><a href="/#newsletter" class="btn btn-orange">✉ Free Newsletter</a></div>
  <a href="/#quiz" class="btn btn-orange menu-btn" style="padding:.5rem 1rem">Quiz</a>
</div></header>"""

FOOTER = """<footer class="site-footer"><div class="container footer-grid">
  <div class="footer-brand"><a href="/" class="brand"><span class="brand-mark gold">SDB</span><span class="brand-text"><span class="brand-name">Senior Daily Benefits</span><span class="brand-domain">seniordailybenefits.com</span></span></a>
  <p>Helping Americans 60+ find and claim the benefits, discounts, and programs they've already earned. Plain English, no jargon.</p></div>
  <div><h4>Topics</h4><ul><li><a href="/articles/">🏥 Medicare &amp; Health</a></li><li><a href="/articles/">💰 Social Security</a></li><li><a href="/articles/">📋 Taxes &amp; Retirement</a></li><li><a href="/articles/">🏠 Home &amp; Utilities</a></li><li><a href="/articles/">🛒 Senior Discounts</a></li><li><a href="/articles/">🛡️ Scam Alerts</a></li></ul></div>
  <div><h4>Quick links</h4><ul><li><a href="/#quiz">Benefits quiz</a></li><li><a href="/#newsletter">Newsletter</a></li><li><a href="/about.html">About us</a></li><li><a href="/contact.html">Contact</a></li></ul>
  <h4>Official resources</h4><ul><li><a href="https://www.ssa.gov" target="_blank" rel="noopener">SSA.gov ↗</a></li><li><a href="https://www.medicare.gov" target="_blank" rel="noopener">Medicare.gov ↗</a></li></ul></div>
</div><div class="footer-bottom"><div class="container"><p>© {year} Senior Daily Benefits. Not affiliated with the U.S. Government or any federal agency. This website is for informational purposes only and does not constitute financial, legal, or medical advice. We may earn a commission from partner links.</p>
<div><a href="/privacy-policy.html">Privacy Policy</a><a href="/terms-conditions.html">Terms &amp; Conditions</a><a href="/contact.html">Contact Us</a></div></div></div></footer>"""

QUIZ_CTA = """<div class="quiz-cta">
  <h2>Are you claiming every benefit you're entitled to?</h2>
  <p>Most seniors miss at least one program worth hundreds a year. Our 60-second quiz shows you which ones apply to you.</p>
  <a class="btn btn-orange btn-lg" href="/#quiz">Start the free quiz →</a>
  <small>100% free · No credit card · 2 minutes</small>
</div>"""

def sponsor_block(name):
    s = SPONSORS.get(name)
    if not s: return ""
    return (f'<div class="partner"><div class="kicker">{s["kicker"]}</div><h3>{s["title"]}</h3>'
            f'<p>{s["body"]}</p><a class="btn btn-orange btn-lg" href="{s["url"]}" rel="sponsored nofollow noopener" target="_blank">{s["cta"]}</a></div>')

def page(title, desc, body, canonical, og=SITE + "/images/topics/general.svg"):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} | Senior Daily Benefits</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<meta property="og:title" content="{html.escape(title, quote=True)}"><meta property="og:description" content="{html.escape(desc, quote=True)}"><meta property="og:image" content="{og}">
<link rel="canonical" href="{canonical}"><link rel="icon" href="/favicon.ico">
{FONTS}</head><body>
{HEADER}
{body}
{FOOTER.format(year=datetime.date.today().year)}
</body></html>"""

def build_article(meta, body_md):
    body_html = md_to_html(body_md)
    keys = [k.strip() for k in meta.get("sponsor", "").split(",") if k.strip()]
    blocks = [sponsor_block(k) for k in keys if sponsor_block(k)]
    # place each partner block right before the 2nd, 3rd, ... <h2>
    parts = body_html.split("<h2>")
    for i, blk in enumerate(blocks):
        idx = i + 2
        if idx < len(parts):
            parts[idx] = blk + "<h2>" + parts[idx]
        else:
            parts[-1] += blk
    body_html = parts[0] + "".join(
        p if p.startswith('<div class="partner">') else "<h2>" + p for p in parts[1:])
    sp = bool(blocks)
    sources = ""
    if meta.get("sources"):
        items = []
        for line in meta["sources"]:
            label, _, url = line.partition("|")
            items.append(f'<li><a href="{url.strip()}" target="_blank" rel="noopener">{html.escape(label.strip())}</a></li>')
        sources = '<div class="sources"><strong>Sources</strong><ul>' + "".join(items) + "</ul></div>"
    body = f"""<section class="article-band"><div class="container">
  <span class="topic-chip">{html.escape(meta.get("topic","Benefits"))}</span>
  <h1>{html.escape(meta["title"])}</h1>
  <p class="summary">{html.escape(meta["summary"])}</p>
  <p class="meta">Updated {nice_date(meta["date"])}</p>
</div></section>
<div class="container" style="max-width:820px;padding-top:2rem"><img class="hero-img" src="{article_image(meta)}" alt="" width="1200" height="630">{image_credit(meta)}</div>
<article class="article"><div class="container">
{body_html}
{QUIZ_CTA}
{sources}
<p class="disclosure">{DISCLOSURE if sp else ""} This article is for general information and is not financial, legal, or tax advice.</p>
</div></article>"""
    return page(meta["title"], meta["summary"], body, f"{SITE}/articles/{meta['slug']}.html", SITE + article_image(meta))

def build_index(articles):
    cards = "".join(
        f'<a class="postrow" href="/articles/{m["slug"]}.html"><img class="thumb" src="{article_image(m)}" alt="" width="1200" height="630"><div><span class="topic-chip">{html.escape(m.get("topic","Benefits"))}</span>'
        f'<h2>{html.escape(m["title"])}</h2><p>{html.escape(m["summary"])}</p><time>{nice_date(m["date"])}</time></div></a>'
        for m in articles)
    body = f"""<section class="article-band"><div class="container">
  <h1>Money news that matters after 60</h1>
  <p class="summary">Plain-English updates on Social Security, Medicare, taxes, and the discounts and programs most seniors never hear about.</p>
</div></section>
<div class="list">{cards}</div>
<div class="container" style="max-width:900px;padding-bottom:2rem">{QUIZ_CTA}</div>"""
    return page("Articles", "Plain-English updates on Social Security, Medicare, taxes and senior benefits.", body, f"{SITE}/articles/")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    articles = []
    for p in sorted(CONTENT.glob("*.md")):
        meta, body = parse(p)
        (OUT / f"{meta['slug']}.html").write_text(build_article(meta, body), encoding="utf-8")
        articles.append(meta)
        print("built", meta["slug"])
    articles.sort(key=lambda m: m["date"], reverse=True)
    (OUT / "index.html").write_text(build_index(articles), encoding="utf-8")
    import json
    (OUT / "latest.json").write_text(json.dumps([
        {"slug": m["slug"], "title": m["title"], "summary": m["summary"], "image": article_image(m),
         "topic": m.get("topic", "Benefits"), "date": m["date"], "date_nice": nice_date(m["date"])}
        for m in articles[:6]], ensure_ascii=False), encoding="utf-8")
    print(f"index: {len(articles)} articles")

if __name__ == "__main__":
    main()
