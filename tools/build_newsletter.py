#!/usr/bin/env python3
"""
Build a Senior Daily Benefits email newsletter (Moneywise-style layout).

Usage:
    python tools/build_newsletter.py content/newsletters/2026-09-08.json

Issue JSON keys:
    date          YYYY-MM-DD
    subject       email subject line
    preheader     short preview text
    greeting      opening paragraph (HTML allowed)
    headline      {"title","stat","text","slug"}   the "Behind the headline" box
    stories       [ {"slug","section","why"} ... ] slugs from content/articles, in order
    sponsors      ["key", ...]  keys from SPONSORS in build_articles.py; first goes
                  after story 1, second after story 2, etc.
    quiz          {"q","options":[..],"answer":"B","explain":"..."}
    roundup       [ {"tag","text","url"} ... ]  short one-liners
Output: dist/newsletters/<date>.html (plus a plain-text .txt)

Email-client rules baked in: 600px table layout, inline styles only,
web-safe fallbacks for Georgia/Arial, bulletproof buttons, no external CSS.
"""
import sys, json, pathlib, html, re, datetime
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_articles import SPONSORS, parse, SITE, CONTENT, nice_date

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "newsletters"

NAVY, NAVY_D, AMBER, ORANGE, CREAM, INK, MUTED = "#1B2E5A", "#0F1E3D", "#D4A017", "#D4521A", "#F8F4E8", "#2C2C2C", "#5F6470"
SERIF = "Georgia,'Times New Roman',serif"
SANS = "Arial,Helvetica,sans-serif"
UTM = "?utm_source=newsletter&utm_medium=email&utm_campaign={date}&utm_content={slot}"

# BigMailer merge tags (edit if your ESP uses different ones)
UNSUB = "{{unsubscribe_link}}"
WEBVIEW = "{{web_version_link}}"

def esc(s): return html.escape(s, quote=False)

def button(label, url, color=ORANGE, big=True):
    pad = "16px 34px" if big else "12px 24px"
    size = "18px" if big else "16px"
    return f'''<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:18px 0 6px"><tr>
<td align="center" bgcolor="{color}" style="border-radius:6px;mso-padding-alt:{pad}">
<a href="{url}" target="_blank" style="display:inline-block;padding:{pad};font-family:{SANS};font-size:{size};font-weight:bold;color:#ffffff;text-decoration:none;border-radius:6px;letter-spacing:.2px">{esc(label)} &rarr;</a>
</td></tr></table>'''

def section_label(text):
    return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
<td style="padding:34px 0 10px;border-top:2px solid {CREAM}"><span style="display:inline-block;width:32px;height:3px;background:{AMBER};vertical-align:middle;margin-right:10px"></span><span style="font-family:{SANS};font-size:12px;font-weight:bold;letter-spacing:2px;color:{AMBER};text-transform:uppercase;vertical-align:middle">{esc(text)}</span></td></tr></table>'''

def para(t, size=18, color=INK, extra=""):
    return f'<p style="margin:0 0 16px;font-family:{SANS};font-size:{size}px;line-height:1.55;color:{color};{extra}">{t}</p>'

def story_block(meta, section, why, url):
    return f'''{section_label(section)}
<h2 style="margin:0 0 12px;font-family:{SERIF};font-size:26px;line-height:1.2;color:{NAVY}"><a href="{url}" style="color:{NAVY};text-decoration:none">{esc(meta["title"])}</a></h2>
{para(esc(meta["summary"]))}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td style="background:{CREAM};border-left:5px solid {AMBER};padding:14px 18px;font-family:{SANS};font-size:16px;line-height:1.5;color:{INK}"><strong style="color:{NAVY}">Why it matters:</strong> {why}</td></tr></table>
{button("Read the full guide", url)}'''

def sponsor_block(key, date):
    s = SPONSORS[key]
    url = s["url"]
    return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:34px 0 6px"><tr>
<td style="background:{CREAM};border:2px solid {AMBER};border-radius:10px;padding:26px 28px">
<p style="margin:0 0 8px;font-family:{SANS};font-size:12px;font-weight:bold;letter-spacing:2px;color:{AMBER};text-transform:uppercase">In partnership with our sponsor</p>
<h3 style="margin:0 0 10px;font-family:{SERIF};font-size:24px;line-height:1.2;color:{NAVY}">{esc(s["title"])}</h3>
{para(esc(s["body"]), 17)}
{button(s["cta"], url)}
<p style="margin:10px 0 0;font-family:{SANS};font-size:12px;color:{MUTED}">Sponsored. Senior Daily Benefits may earn a commission if you sign up. That never changes what we recommend.</p>
</td></tr></table>'''

def build(issue):
    date = issue["date"]; nice = nice_date(date)
    arts = {}
    for p in CONTENT.glob("*.md"):
        m, body = parse(p); arts[m["slug"]] = m
    def link(slug, slot): return f"{SITE}/articles/{slug}.html" + UTM.format(date=date, slot=slot)

    stories = issue["stories"]; sponsors = issue.get("sponsors", [])
    # --- body pieces --------------------------------------------------------
    parts = []
    # greeting + "On the money today"
    parts.append(para(issue["greeting"]))
    bullets = "".join(f'<li style="margin:0 0 8px">{esc(arts[s["slug"]]["title"])}</li>' for s in stories)
    parts.append(f'''<p style="margin:14px 0 8px;font-family:{SANS};font-size:18px;font-weight:bold;color:{NAVY}">In today's brief:</p>
<ul style="margin:0 0 6px 22px;padding:0;font-family:{SANS};font-size:17px;line-height:1.5;color:{INK}">{bullets}</ul>
{para("Let's get into it.")}''')
    # behind the headline
    h = issue["headline"]
    parts.append(f'''{section_label("Behind the headline")}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td style="background:{NAVY};border-radius:10px;padding:26px 28px;text-align:center">
<div style="font-family:{SERIF};font-size:44px;font-weight:bold;color:{AMBER};line-height:1.05">{esc(h["stat"])}</div>
<div style="font-family:{SANS};font-size:17px;color:#BFD0F5;margin-top:8px;line-height:1.45">{esc(h["title"])}</div>
</td></tr></table>
{para(h["text"] + f' <a href="{link(h["slug"], "headline")}" style="color:{ORANGE};font-weight:bold">Read the story &rarr;</a>', 17)}''')
    # stories with sponsors interleaved
    for i, s in enumerate(stories):
        parts.append(story_block(arts[s["slug"]], s["section"], s["why"], link(s["slug"], f"story{i+1}")))
        if i < len(sponsors):
            parts.append(sponsor_block(sponsors[i], date))
    # quiz
    q = issue.get("quiz")
    if q:
        opts = "".join(f'<li style="margin:0 0 6px">{esc(o)}</li>' for o in q["options"])
        parts.append(f'''{section_label("Money IQ")}
{para(f'<strong style="color:{NAVY}">{esc(q["q"])}</strong>')}
<ol type="A" style="margin:0 0 10px 24px;padding:0;font-family:{SANS};font-size:17px;line-height:1.5;color:{INK}">{opts}</ol>
{para(f'<em>Answer at the bottom of this email.</em>', 15, MUTED)}''')
    # roundup
    if issue.get("roundup"):
        items = "".join(f'<p style="margin:0 0 12px;font-family:{SANS};font-size:16px;line-height:1.5;color:{INK}"><strong style="color:{NAVY};letter-spacing:1px;font-size:13px">{esc(r["tag"]).upper()}:</strong> <a href="{r["url"]}" style="color:{INK}">{esc(r["text"])}</a></p>' for r in issue["roundup"])
        parts.append(section_label("Also making the rounds") + items)
    # quiz CTA
    parts.append(f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:34px 0 0"><tr><td style="background:{NAVY_D};border-radius:10px;padding:28px;text-align:center">
<h3 style="margin:0 0 8px;font-family:{SERIF};font-size:24px;color:#ffffff">Are you claiming every benefit you've earned?</h3>
<p style="margin:0 0 4px;font-family:{SANS};font-size:16px;color:#BFD0F5">Our free 60-second quiz shows which programs and discounts apply to you.</p>
<div style="text-align:center">{button("Take the free quiz", SITE + "/#quiz" + UTM.format(date=date, slot="quizcta"))}</div>
</td></tr></table>''')
    if q:
        parts.append(f'''{section_label("Money IQ answer")}
{para(f'<strong style="color:{NAVY}">{esc(q["answer"])}.</strong> {esc(q["explain"])}', 16)}''')

    body_html = "\n".join(parts)
    # --- shell --------------------------------------------------------------
    doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="x-apple-disable-message-reformatting">
<title>{esc(issue["subject"])}</title></head>
<body style="margin:0;padding:0;background:#EDE8D5">
<div style="display:none;max-height:0;overflow:hidden;font-size:1px;color:#EDE8D5">{esc(issue["preheader"])}&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#EDE8D5"><tr><td align="center" style="padding:22px 10px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%;background:#ffffff;border-radius:12px;overflow:hidden">
<tr><td style="background:{NAVY_D};padding:10px 28px;font-family:{SANS};font-size:12px;color:#9DB4E8">Not affiliated with the U.S. Government &nbsp;|&nbsp; <a href="{WEBVIEW}" style="color:#9DB4E8">View in browser</a></td></tr>
<tr><td style="padding:24px 28px 18px;border-bottom:3px solid {AMBER}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
<td><span style="display:inline-block;background:{NAVY};color:#fff;font-family:{SERIF};font-weight:bold;font-size:14px;padding:9px 8px;border-radius:6px;vertical-align:middle">SDB</span> <span style="font-family:{SERIF};font-size:22px;font-weight:bold;color:{NAVY};vertical-align:middle;margin-left:6px">Senior Daily Benefits</span></td>
<td align="right" style="font-family:{SANS};font-size:13px;color:{MUTED}">{esc(nice)}</td></tr></table></td></tr>
<tr><td style="padding:26px 28px 10px">
{body_html}
</td></tr>
<tr><td style="background:{NAVY_D};padding:26px 28px;font-family:{SANS};font-size:13px;line-height:1.6;color:#9DB4E8">
<p style="margin:0 0 10px"><strong style="color:#ffffff">Senior Daily Benefits</strong> &middot; Plain-English money news for Americans 60+.</p>
<p style="margin:0 0 10px">You're receiving this because you took our benefits quiz or subscribed at seniordailybenefits.com. This email is for general information and is not financial, legal, or medical advice. We may earn a commission from partner links; sponsored content is labeled.</p>
<p style="margin:0"><a href="{SITE}/privacy-policy.html" style="color:#9DB4E8">Privacy</a> &nbsp;|&nbsp; <a href="{SITE}/contact.html" style="color:#9DB4E8">Contact</a> &nbsp;|&nbsp; <a href="{UNSUB}" style="color:#9DB4E8">Unsubscribe</a></p>
</td></tr>
</table></td></tr></table></body></html>'''

    # plain text version
    txt = [f"SENIOR DAILY BENEFITS — {nice}", "", re.sub(r"<[^>]+>", "", issue["greeting"]), ""]
    for i, s in enumerate(stories):
        m = arts[s["slug"]]
        txt += [m["title"].upper(), m["summary"], "Why it matters: " + re.sub(r"<[^>]+>", "", s["why"]), link(s["slug"], f"story{i+1}"), ""]
        if i < len(sponsors):
            sp = SPONSORS[sponsors[i]]; txt += ["[SPONSOR] " + sp["title"], sp["body"], sp["url"], ""]
    txt += ["Take the free benefits quiz: " + SITE + "/#quiz", "", "Unsubscribe: " + UNSUB]
    return doc, "\n".join(txt)

def main():
    issue = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    doc, txt = build(issue)
    (OUT / f"{issue['date']}.html").write_text(doc, encoding="utf-8")
    (OUT / f"{issue['date']}.txt").write_text(txt, encoding="utf-8")
    print("built", OUT / f"{issue['date']}.html")

if __name__ == "__main__":
    main()
