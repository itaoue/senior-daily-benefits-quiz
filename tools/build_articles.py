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
"""
import re, html, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "articles"
OUT = ROOT / "src" / "static" / "articles"
SITE = "https://seniordailybenefits.com"

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

def nice_date(iso):
    return datetime.date.fromisoformat(iso).strftime("%B %-d, %Y")

# ---------------------------------------------------------------------------
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,Cantarell,sans-serif;color:#2d3436;line-height:1.6;background:#fff}
a{color:#047857}
.header{background:#fff;border-bottom:1px solid #e5e7eb;position:sticky;top:0;z-index:10}
.header-content{max-width:1100px;margin:0 auto;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;gap:16px}
.logo{font-size:1.5rem;font-weight:700;color:#1f2937;text-decoration:none;letter-spacing:-.01em}.logo span{font-weight:400;color:#059669}
.nav a{color:#4b5563;text-decoration:none;font-weight:500;margin-left:20px;font-size:1rem}
.nav a.nav-cta{background:#ea580c;color:#fff;padding:10px 18px;border-radius:8px}
.nav a.nav-cta:hover{background:#dc2626}
.band{background:linear-gradient(to bottom right,#f0fdf4,#eff6ff);padding:56px 20px 40px}
.wrap{max-width:720px;margin:0 auto}
.topic{display:inline-block;background:#dcfce7;color:#166534;border-radius:9999px;padding:6px 14px;font-size:.95rem;font-weight:600;margin-bottom:18px}
h1{font-size:2.5rem;line-height:1.15;color:#1f2937;font-weight:700;margin-bottom:16px}
.summary{font-size:1.3rem;color:#4b5563;margin-bottom:18px}
.meta{font-size:1rem;color:#6b7280}
.article{padding:40px 20px 24px;font-size:1.2rem;line-height:1.7}
.article p{margin-bottom:22px}
.article h2{font-size:1.65rem;color:#1f2937;margin:40px 0 14px;line-height:1.25}
.article h3{font-size:1.3rem;color:#1f2937;margin:28px 0 10px}
.article ul{margin:0 0 22px 26px}
.article li{margin-bottom:8px}
.callout{background:#fff7ed;border-left:6px solid #ea580c;padding:20px 24px;border-radius:0 12px 12px 0;margin:28px 0}
.callout p{margin:0;font-size:1.15rem}
.callout strong{color:#9a3412}
.partner{margin:36px 0;border:2px solid #bfdbfe;background:#eff6ff;border-radius:16px;padding:26px 28px}
.partner .kicker{font-size:.9rem;color:#1d4ed8;font-weight:600;margin-bottom:8px}
.partner h3{font-size:1.4rem;color:#1f2937;margin:0 0 10px}
.partner p{margin:0 0 18px;font-size:1.1rem}
.btn{display:inline-block;background:#ea580c;color:#fff;text-decoration:none;font-weight:600;padding:14px 26px;border-radius:8px;font-size:1.1rem;box-shadow:0 10px 25px rgba(0,0,0,.1)}
.btn:hover{background:#dc2626}
.quiz-cta{background:linear-gradient(to bottom right,#f0fdf4,#eff6ff);border-radius:16px;padding:36px 32px;text-align:center;margin:44px 0 20px}
.quiz-cta h2{font-size:1.9rem;margin:0 0 10px;color:#1f2937}
.quiz-cta p{font-size:1.15rem;color:#4b5563;margin-bottom:22px}
.quiz-cta small{display:block;margin-top:14px;color:#6b7280}
.sources{font-size:1rem;color:#6b7280;border-top:1px solid #e5e7eb;padding-top:18px;margin-top:8px}
.sources ul{margin:8px 0 0 20px}
.disclosure{font-size:.95rem;color:#6b7280;margin-top:20px}
.list{max-width:900px;margin:0 auto;padding:40px 20px}
.card{display:block;text-decoration:none;color:inherit;padding:26px 0;border-bottom:1px solid #e5e7eb}
.card:first-child{padding-top:0}
.card h2{font-size:1.6rem;color:#1f2937;margin:6px 0 8px;line-height:1.25}
.card:hover h2{color:#047857}
.card p{font-size:1.15rem;color:#4b5563}
.card .meta{margin-top:8px}
.footer{background:#1f2937;color:#d1d5db;padding:48px 20px 24px;margin-top:48px}
.footer-content{max-width:1100px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:32px}
.footer h3{color:#fff;font-size:1.1rem;margin-bottom:14px}
.footer ul{list-style:none}.footer li{margin-bottom:8px}
.footer a{color:#d1d5db;text-decoration:none}.footer a:hover{color:#fff}
.footer-bottom{max-width:1100px;margin:36px auto 0;border-top:1px solid #374151;padding-top:20px;font-size:.9rem;color:#9ca3af;text-align:center}
@media(max-width:640px){h1{font-size:1.9rem}.article{font-size:1.1rem}.nav a{margin-left:12px}.nav a:not(.nav-cta){display:none}}
"""

HEADER = """<header class="header"><div class="header-content">
  <a class="logo" href="/">Senior Daily <span>Benefits</span></a>
  <nav class="nav"><a href="/articles/">Articles</a><a href="/about.html">About</a><a class="nav-cta" href="/#quiz">Take the free quiz</a></nav>
</div></header>"""

FOOTER = """<footer class="footer"><div class="footer-content">
  <div><h3 style="font-size:1.3rem">Senior Daily <span style="font-weight:400;color:#6ee7b7">Benefits</span></h3><p>Helping seniors discover the benefits they deserve. Take our free quiz and unlock thousands in potential savings.</p></div>
  <div><h3>Quick Links</h3><ul><li><a href="/">Take Quiz</a></li><li><a href="/articles/">Articles</a></li><li><a href="/about.html">About Us</a></li><li><a href="/contact.html">Contact Support</a></li></ul></div>
  <div><h3>Legal</h3><ul><li><a href="/privacy-policy.html">Privacy Policy</a></li><li><a href="/terms-conditions.html">Terms &amp; Conditions</a></li></ul></div>
  <div><h3>Contact Info</h3><ul><li>📧 support@seniordailybenefits.com</li><li>⏰ Mon-Fri: 9 AM - 6 PM EST</li></ul></div>
</div><div class="footer-bottom">&copy; {year} Senior Daily Benefits. All rights reserved. | This website is for informational purposes only and does not constitute financial, legal, or medical advice.</div></footer>"""

QUIZ_CTA = """<div class="quiz-cta">
  <h2>Are you claiming every benefit you're entitled to?</h2>
  <p>Most seniors miss at least one program worth hundreds a year. Our 60-second quiz shows you which ones apply to you.</p>
  <a class="btn" href="/#quiz">Start the free quiz</a>
  <small>100% free · No credit card · 2 minutes</small>
</div>"""

def sponsor_block(name):
    s = SPONSORS.get(name)
    if not s: return ""
    return (f'<div class="partner"><div class="kicker">{s["kicker"]}</div><h3>{s["title"]}</h3>'
            f'<p>{s["body"]}</p><a class="btn" href="{s["url"]}" rel="sponsored nofollow noopener" target="_blank">{s["cta"]}</a></div>')

def page(title, desc, body, canonical):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} | Senior Daily Benefits</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<link rel="canonical" href="{canonical}"><link rel="icon" href="/favicon.ico">
<style>{CSS}</style></head><body>
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
    body = f"""<section class="band"><div class="wrap">
  <span class="topic">{html.escape(meta.get("topic","Benefits"))}</span>
  <h1>{html.escape(meta["title"])}</h1>
  <p class="summary">{html.escape(meta["summary"])}</p>
  <p class="meta">Updated {nice_date(meta["date"])}</p>
</div></section>
<article class="article"><div class="wrap">
{body_html}
{QUIZ_CTA}
{sources}
<p class="disclosure">{DISCLOSURE if sp else ""} This article is for general information and is not financial, legal, or tax advice.</p>
</div></article>"""
    return page(meta["title"], meta["summary"], body, f"{SITE}/articles/{meta['slug']}.html")

def build_index(articles):
    cards = "".join(
        f'<a class="card" href="/articles/{m["slug"]}.html"><span class="topic">{html.escape(m.get("topic","Benefits"))}</span>'
        f'<h2>{html.escape(m["title"])}</h2><p>{html.escape(m["summary"])}</p><p class="meta">{nice_date(m["date"])}</p></a>'
        for m in articles)
    body = f"""<section class="band"><div class="wrap">
  <h1>Money news that matters after 60</h1>
  <p class="summary">Plain-English updates on Social Security, Medicare, taxes, and the discounts and programs most seniors never hear about.</p>
</div></section>
<div class="list">{cards}</div>"""
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
    print(f"index: {len(articles)} articles")

if __name__ == "__main__":
    main()
