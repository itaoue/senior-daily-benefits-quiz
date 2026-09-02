#!/usr/bin/env python3
"""
Push a built newsletter issue into ActiveCampaign as a DRAFT campaign.

    export AC_API_URL=https://youraccount.api-us1.com     # Settings -> Developer
    export AC_API_KEY=...
    export AC_FROM_NAME="Senior Daily Benefits"
    export AC_FROM_EMAIL=news@seniordailybenefits.com      # must be a verified sender in AC
    export AC_REPLY_TO=news@seniordailybenefits.com        # optional, defaults to AC_FROM_EMAIL

    python tools/push_to_activecampaign.py --lists                 # show list ids/names
    python tools/push_to_activecampaign.py 2026-09-03 --list "Senior Daily Benefits"
    python tools/push_to_activecampaign.py 2026-09-03 --list-id 3 --dry-run

What it does:
  1. reads dist/newsletters/<date>.html, .txt and content/newsletters/<date>.json
  2. converts BigMailer merge tags to ActiveCampaign ones
        *|UNSUB|*  -> %UNSUBSCRIBELINK%      *|VIEW|* -> %WEBCOPY%
  3. message_add   (HTML + text, subject, from, reply-to)
  4. campaign_create (type single, status 0 = draft, attached to the list)
Nothing is sent. Open the campaign in ActiveCampaign, check the preview,
send a test, then schedule or send from there.
Uses the classic /admin/api.php endpoints, which are the ones that accept
raw HTML for a campaign message.
"""
import argparse, json, os, pathlib, re, sys, datetime
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
TAGS = {"*|UNSUB|*": "%UNSUBSCRIBELINK%", "*|VIEW|*": "%WEBCOPY%"}

def env(name, default=None, required=True):
    v = os.environ.get(name, default)
    if required and not v:
        sys.exit(f"Set {name} first (see the docstring at the top of this script).")
    return v

def api(action, data=None, output="json"):
    base = env("AC_API_URL").rstrip("/")
    key = env("AC_API_KEY")
    r = requests.post(f"{base}/admin/api.php",
                      params={"api_action": action, "api_output": output, "api_key": key},
                      headers={"Api-Token": key}, data=data or {}, timeout=60)
    try:
        body = r.json()
    except ValueError:
        sys.exit(f"{action}: HTTP {r.status_code}, non-JSON reply: {r.text[:300]}")
    if str(body.get("result_code", "1")) == "0":
        sys.exit(f"{action} failed: {body.get('result_message')}")
    return body

def lists():
    body = api("list_list", {"ids": "all"})
    out = []
    for k, v in body.items():
        if isinstance(v, dict) and "id" in v and "name" in v:
            out.append((int(v["id"]), v["name"], int(v.get("subscriber_count", 0) or 0)))
    return sorted(out)

def convert(html):
    for a, b in TAGS.items():
        html = html.replace(a, b)
    return html

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?", help="issue date, e.g. 2026-09-03")
    ap.add_argument("--list", dest="list_name", help="ActiveCampaign list name")
    ap.add_argument("--list-id", type=int)
    ap.add_argument("--lists", action="store_true", help="print lists and exit")
    ap.add_argument("--name", help="internal campaign name (default: Senior Daily Brief <date>)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.lists:
        for lid, name, n in lists():
            print(f"{lid:4d}  {name}  ({n} subscribers)")
        return
    if not a.date:
        sys.exit("give the issue date, e.g. 2026-09-03")

    html_path = ROOT / "dist" / "newsletters" / f"{a.date}.html"
    txt_path = ROOT / "dist" / "newsletters" / f"{a.date}.txt"
    issue_path = ROOT / "content" / "newsletters" / f"{a.date}.json"
    for p in (html_path, txt_path, issue_path):
        if not p.exists():
            sys.exit(f"missing {p} (run tools/build_newsletter.py first)")
    issue = json.loads(issue_path.read_text(encoding="utf-8"))
    html = convert(html_path.read_text(encoding="utf-8"))
    text = convert(txt_path.read_text(encoding="utf-8"))
    leftover = re.findall(r"\*\|[A-Z_]+\|\*|\{\{[^}]+\}\}", html)
    if leftover:
        sys.exit(f"unconverted merge tags: {sorted(set(leftover))}")

    list_id = a.list_id
    if not list_id:
        if not a.list_name:
            sys.exit("give --list <name> or --list-id <id> (see --lists)")
        match = [l for l in lists() if l[1].strip().lower() == a.list_name.strip().lower()]
        if not match:
            sys.exit(f"no list named {a.list_name!r}; run --lists")
        list_id = match[0][0]

    from_name = env("AC_FROM_NAME", "Senior Daily Benefits", required=False)
    from_email = env("AC_FROM_EMAIL")
    reply_to = env("AC_REPLY_TO", from_email, required=False)
    name = a.name or f"Senior Daily Brief {a.date}"
    subject = issue["subject"]

    print(f"issue      {a.date}\nsubject    {subject}\nlist id    {list_id}\nfrom       {from_name} <{from_email}>\nhtml       {len(html):,} chars\ntext       {len(text):,} chars")
    if a.dry_run:
        print("dry run: nothing sent"); return

    msg = api("message_add", {
        "format": "mime", "subject": subject, "fromemail": from_email, "fromname": from_name,
        "reply2": reply_to, "priority": 3, "charset": "utf-8", "encoding": "quoted-printable",
        "htmlconstructor": "editor", "html": html, "textconstructor": "editor", "text": text,
        f"p[{list_id}]": list_id,
    })
    mid = msg["id"]
    print(f"message    created id {mid}")

    sdate = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d 09:00:00")
    camp = api("campaign_create", {
        "type": "single", "name": name, "sdate": sdate, "status": 0, "public": 0,
        "tracklinks": "all", "trackreads": 1, "trackreplies": 0,
        "htmlunsub": 0, "textunsub": 0,          # our footer already carries %UNSUBSCRIBELINK%
        f"p[{list_id}]": list_id, f"m[{mid}]": 100,
        "analytics_campaign_name": f"newsletter-{a.date}",
    })
    print(f"campaign   created id {camp['id']} as a DRAFT ({camp.get('result_message')})")
    print("Open Campaigns in ActiveCampaign, preview it, send a test, then send or schedule.")

if __name__ == "__main__":
    main()
