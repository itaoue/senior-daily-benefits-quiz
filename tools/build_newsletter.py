#!/usr/bin/env python3
"""
Build a Senior Daily Benefits email newsletter in the Moneywise Digest layout.

Usage:
    python tools/build_newsletter.py content/newsletters/2026-09-03.json

Issue JSON keys (all strings may contain simple inline HTML):
    date            YYYY-MM-DD
    subject         email subject line
    preheader       preview text shown next to the subject in the inbox
    together_with   (optional) SPONSORS key shown under the masthead ("together with ...")
    greeting        opening paragraph; starts with "<strong>Good morning</strong>." etc.
    today           (optional) list of 3 one-line teasers for "On The Money Today"; defaults
                    to story titles
    headline        {"kicker","title","stat","text","slug"}  the "Behind the headline" block
    stories         [ {"slug","kicker","why","cta"} ... ]  slugs from content/articles, in order
    sponsors        ["key", ...]  SPONSORS keys; sponsor i goes after story i (keep to 1 or 2)
    quiz            {"q","options":[..],"answer":"B) ...","explain":"..."}
    roundup         [ {"tag","text","url"} ... ]  "Also making the rounds today"
    signoff         (optional) closing line
    byline          (optional) "Today's newsletter was written by ..."
    postal_address  REQUIRED by CAN-SPAM before sending; a placeholder is used if missing
Output: dist/newsletters/<date>.html and .txt

Layout notes (mirrors the Moneywise Digest template): white background, one 600px
column, 35px side padding, uppercase section kickers, headline as an underlined
link, full-width image, plain paragraphs, an inline "Why it matters:" line, a
small solid button, thin dividers between sections, quiet gray footer.
Email-client rules: table layout, inline styles, web-safe font stack, no external CSS.
"""
import sys, json, pathlib, html, re, datetime
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_articles import SPONSORS, parse, SITE, CONTENT, nice_date, article_image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "newsletters"

NAVY, AMBER, ORANGE, INK, GRAY, RULE = "#1B2E5A", "#D4A017", "#D4521A", "#000000", "#374151", "#E5E7EB"
LINK = NAVY                     # Moneywise uses its brand purple for links + buttons; ours is navy
SANS = "'Work Sans','Lucida Grande',Verdana,Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"
UTM = "?utm_source=newsletter&utm_medium=email&utm_campaign={date}&utm_content={slot}"
UNSUB = "{{unsubscribe_link}}"      # BigMailer merge tags
WEBVIEW = "{{web_version_link}}"
PREFS = "{{preferences_link}}"

def esc(s): return html.escape(s, quote=False)

# Display names for the "In partnership with" kicker (SPONSORS entries only carry copy + URL).
PARTNER_NAMES = {
    "aarp": "AARP", "tax_relief": "TRA Tax Relief", "hearing": "our hearing partner", "walkin_shower": "HomeBuddy",
    "home_warranty": "Home Warranty", "title_lock": "Home Title Lock", "home_security": "Guardlane",
    "timeshare_exit": "Stonegate", "pillow": "Derila", "insoles": "Akusoli", "skincare": "Beverly Hills MD",
    "detox_tea": "Lulutox", "adblock": "Total Adblock", "auto_insurance": "our auto insurance partner",
    "balance_transfer": "our card partner", "cashback_card": "our card partner", "debt_settlement": "our debt relief partner",
    "heloc": "our home equity partner", "windows": "our window partner", "roof": "our roofing partner",
    "gutters": "our gutter partner", "solar_exit": "our solar partner",
}
def partner_name(key): return PARTNER_NAMES.get(key, "our partner")


# ---------------------------------------------------------------- atoms
def p(t, size=16, color=INK, weight=400, margin="0 0 16px", extra=""):
    return (f'<p style="margin:{margin};font-family:{SANS};font-size:{size}px;line-height:{round(size*1.5)}px;'
            f'font-weight:{weight};color:{color};{extra}">{t}</p>')

def kicker(text):
    return (f'<p style="margin:0 0 14px;font-family:{SANS};font-size:15px;line-height:20px;font-weight:600;'
            f'letter-spacing:.3px;color:{INK};text-transform:uppercase">{esc(text)}</p>')

def headline(text, url, size=22):
    return (f'<h3 style="margin:0 0 14px;font-family:{SANS};font-size:{size}px;line-height:{round(size*1.3)}px;font-weight:600;color:{LINK}">'
            f'<a href="{url}" target="_blank" style="color:{LINK};text-decoration:underline">{esc(text)}</a></h3>')

def image(src, url=None):
    img = f'<img src="{src}" alt="" width="530" style="display:block;width:100%;max-width:530px;height:auto;border:0">'
    if url: img = f'<a href="{url}" target="_blank">{img}</a>'
    return f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 16px"><tr><td>{img}</td></tr></table>'

def button(label, url):
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:4px 0 8px"><tr>'
            f'<td bgcolor="{LINK}" style="border-radius:4px"><a href="{url}" target="_blank" style="background-color:{LINK};border-radius:4px;'
            f'color:#FFFFFF;display:inline-block;font-family:{SANS};font-size:14px;font-weight:500;line-height:16px;padding:9px 15px;'
            f'text-decoration:none">{esc(label)}</a></td></tr></table>')

def divider():
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:26px 0 30px"><tr><td style="border-top:1px solid {RULE};font-size:0;line-height:0">&nbsp;</td></tr></table>'

def why(text):
    return p(f'<strong>Why it matters:</strong> {text}')

# ---------------------------------------------------------------- blocks
def story_block(meta, s, url):
    return "".join([
        kicker(s.get("kicker", meta.get("topic", "Retirement"))),
        headline(meta["title"], url),
        image(SITE + article_image(meta), url),
        p(esc(meta["summary"])),
        why(s["why"]) if s.get("why") else "",
        button(s.get("cta", "Read The Story"), url),
    ])

def sponsor_block(key):
    s = SPONSORS[key]
    return "".join([
        kicker(f"In partnership with {partner_name(key)}"),
        headline(s["title"], s["url"]),
        p(esc(s["body"])),
        button(s["cta"], s["url"]),
        p("Sponsored. Senior Daily Benefits may earn a commission if you sign up. That never changes what we recommend.", 12, GRAY, margin="8px 0 0"),
    ])

def build(issue):
    date = issue["date"]; nice = nice_date(date)
    arts = {}
    for path in CONTENT.glob("*.md"):
        m, _ = parse(path); arts[m["slug"]] = m
    def link(slug, slot): return f"{SITE}/articles/{slug}.html" + UTM.format(date=date, slot=slot)

    stories = issue["stories"]; sponsors = issue.get("sponsors", [])
    parts = []

    # masthead ---------------------------------------------------------------
    tw = issue.get("together_with")
    together = (f'<p style="margin:14px 0 0;font-family:{SANS};font-size:15px;color:{GRAY}"><em>together with</em> '
                f'<a href="{SPONSORS[tw]["url"]}" target="_blank" style="color:{NAVY};font-weight:700;text-decoration:none">{esc(partner_name(tw))}</a></p>') if tw else ""
    parts.append(f'''<p style="margin:0 0 22px;font-family:{SANS};font-size:12px"><a href="{WEBVIEW}" style="color:{GRAY};text-decoration:underline">Read online</a></p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:0 0 26px">
<span style="font-family:{SERIF};font-size:34px;font-weight:bold;color:{NAVY};letter-spacing:-.5px">Senior Daily</span> <span style="font-family:{SERIF};font-size:34px;font-style:italic;color:{AMBER}">Brief</span>
{together}
</td></tr></table>''')

    # greeting + On The Money Today --------------------------------------------
    parts.append(p(issue["greeting"]))
    today = issue.get("today") or [arts[s["slug"]]["title"] for s in stories]
    bullets = "".join(f'<li style="margin:0 0 10px;padding-left:4px">{t}</li>' for t in today)
    parts.append(p("<strong>On The Money Today:</strong>", margin="0 0 12px"))
    parts.append(f'<ul style="margin:0 0 16px 22px;padding:0;font-family:{SANS};font-size:16px;line-height:24px;color:{INK}">{bullets}</ul>')
    parts.append(p("Let's get into it."))
    parts.append(divider())

    # behind the headline ------------------------------------------------------
    h = issue.get("headline")
    if h:
        hurl = link(h["slug"], "headline")
        stat = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 16px"><tr><td style="background:#F2F5F9;border-radius:6px;padding:26px 24px;text-align:center">'
                f'<div style="font-family:{SANS};font-size:44px;font-weight:700;color:{NAVY};line-height:48px">{esc(h["stat"])}</div>'
                f'<div style="font-family:{SANS};font-size:15px;color:{GRAY};margin-top:8px;line-height:22px">{esc(h.get("stat_label",""))}</div></td></tr></table>') if h.get("stat") else ""
        parts.append("".join([kicker(h.get("kicker", "Behind the headline")), headline(h["title"], hurl), stat,
                              p(h["text"] + f' <a href="{hurl}" target="_blank" style="color:{LINK}">Keep reading.</a>'), divider()]))

    # stories, sponsors interleaved ---------------------------------------------
    for i, s in enumerate(stories):
        parts.append(story_block(arts[s["slug"]], s, link(s["slug"], f"story{i+1}")))
        parts.append(divider())
        if i < len(sponsors):
            parts.append(sponsor_block(sponsors[i])); parts.append(divider())

    # Money IQ -------------------------------------------------------------------
    q = issue.get("quiz")
    if q:
        letters = "ABCD"
        opts = "".join(p(f"{letters[i]}) {esc(o)}", margin="0 0 6px") for i, o in enumerate(q["options"]))
        parts.append("".join([kicker("Money IQ"), p(f'<strong>{esc(q["q"])}</strong>'), opts,
                              p("<em>Answer at the bottom of this email.</em>", 14, GRAY, margin="10px 0 0"), divider()]))

    # roundup ----------------------------------------------------------------------
    if issue.get("roundup"):
        items = "".join(p(f'<strong>{esc(r["tag"]).upper()}:</strong> <a href="{r["url"]}" target="_blank" style="color:{LINK}">{esc(r["text"])}</a>', margin="0 0 14px") for r in issue["roundup"])
        parts.append(kicker("Also making the rounds today") + items + divider())

    # Money IQ answer --------------------------------------------------------------
    if q:
        parts.append("".join([kicker("Money IQ answer: how did you do?"),
                              p(f'<strong>The answer is {esc(q["answer"])}</strong> &mdash; {esc(q["explain"])}'), divider()]))

    # quiz CTA + sign-off ------------------------------------------------------------
    parts.append("".join([
        p("<strong>Are you claiming every benefit you've earned?</strong> Our free 60-second quiz shows which programs and discounts apply to you."),
        button("Take The Free Quiz", SITE + "/#quiz" + UTM.format(date=date, slot="quizcta")),
        p(issue.get("signoff", "See you soon with another quick roundup of the money news that matters."), margin="20px 0 6px"),
        p("Hit REPLY if there's a topic you want us to dig into. We read every one.", 15, GRAY),
    ]))

    body_html = "\n".join(parts)
    byline = issue.get("byline", "Today's newsletter was written and edited by the Senior Daily Benefits team.")
    address = issue.get("postal_address") or "[POSTAL ADDRESS REQUIRED BY CAN-SPAM: add postal_address to the issue JSON]"

    doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="x-apple-disable-message-reformatting">
<title>{esc(issue["subject"])}</title>
<style>@media screen and (max-width:640px){{.wrap{{width:100%!important}} .pad{{padding:0 16px!important}}}}</style></head>
<body style="margin:0;padding:0;background:#FFFFFF">
<div style="display:none;max-height:0;overflow:hidden;font-size:1px;color:#FFFFFF">{esc(issue["preheader"])}&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FFFFFF"><tr><td align="center" style="padding:28px 0 40px">
<table role="presentation" class="wrap" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%;background:#FFFFFF">
<tr><td class="pad" style="padding:0 35px">
{body_html}
</td></tr>
<tr><td class="pad" style="padding:8px 35px 0">
{p(byline, 12, GRAY, margin="0 0 14px")}
{p("<em>The content provided by Senior Daily Benefits is information to help readers become financially literate. It is neither investment, tax, legal, nor medical advice, and it is not a recommendation to buy or sell any product, enter into any loan, insurance, or investment, or adopt any strategy. Decisions should be made only with guidance from a qualified professional. We may earn a commission from partner links; sponsored content is labeled. Senior Daily Benefits is not affiliated with the U.S. Government or any federal agency.</em>", 12, GRAY)}
{p(f'<a href="{PREFS}" style="color:{GRAY};text-decoration:underline">Update your email preferences</a> or <a href="{UNSUB}" style="color:{GRAY};text-decoration:underline">unsubscribe here</a>', 12, GRAY)}
{p(esc(address), 12, GRAY)}
{p(f'&copy; {datetime.date.today().year} Senior Daily Benefits &middot; <a href="{SITE}/privacy-policy.html" style="color:{GRAY}">Privacy</a> &middot; <a href="{SITE}/terms-conditions.html" style="color:{GRAY}">Terms</a>', 12, GRAY, margin="0")}
</td></tr>
</table></td></tr></table></body></html>'''

    # plain text -----------------------------------------------------------------
    strip = lambda s: re.sub(r"<[^>]+>", "", s)
    txt = [f"SENIOR DAILY BRIEF - {nice}", "", strip(issue["greeting"]), "", "ON THE MONEY TODAY:"] + [f"* {strip(t)}" for t in today] + [""]
    if h: txt += [h.get("kicker", "BEHIND THE HEADLINE").upper(), h["title"], strip(h["text"]), link(h["slug"], "headline"), ""]
    for i, s in enumerate(stories):
        m = arts[s["slug"]]
        txt += [s.get("kicker", "").upper(), m["title"], m["summary"], ("Why it matters: " + strip(s["why"])) if s.get("why") else "", link(s["slug"], f"story{i+1}"), ""]
        if i < len(sponsors):
            sp = SPONSORS[sponsors[i]]; txt += ["[SPONSORED] " + sp["title"], sp["body"], sp["url"], ""]
    if q: txt += ["MONEY IQ: " + q["q"]] + [f"{'ABCD'[i]}) {o}" for i, o in enumerate(q["options"])] + [""]
    if issue.get("roundup"): txt += ["ALSO MAKING THE ROUNDS TODAY:"] + [f"{r['tag'].upper()}: {r['text']} {r['url']}" for r in issue["roundup"]] + [""]
    if q: txt += [f"MONEY IQ ANSWER: {q['answer']} - {q['explain']}", ""]
    txt += ["Take the free benefits quiz: " + SITE + "/#quiz", "", strip(byline), "", "Unsubscribe: " + UNSUB, address]
    return doc, "\n".join(txt)

def main():
    issue = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    doc, txt = build(issue)
    (OUT / f"{issue['date']}.html").write_text(doc, encoding="utf-8")
    (OUT / f"{issue['date']}.txt").write_text(txt, encoding="utf-8")
    print("built", OUT / f"{issue['date']}.html")
    if not issue.get("postal_address"):
        print("WARNING: no postal_address in issue JSON; CAN-SPAM requires one before sending")

if __name__ == "__main__":
    main()
