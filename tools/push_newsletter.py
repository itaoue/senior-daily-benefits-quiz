#!/usr/bin/env python3
"""
Push a built newsletter issue to an ESP as a DRAFT campaign.

    python tools/push_newsletter.py <date> --esp bigmailer   [--list-id <uuid>] [--brand-id <uuid>]
    python tools/push_newsletter.py <date> --esp activecampaign --list "Master Contact List"
    python tools/push_newsletter.py <date> --esp robly        [--sub-list "<name>"]
    add --dry-run to see what would be sent; --lists to print the ESP's lists.

The issue is built once (tools/build_newsletter.py) with BigMailer-style merge
tags; this script swaps them per ESP:

    tag              BigMailer     ActiveCampaign      Robly
    unsubscribe      *|UNSUB|*     %UNSUBSCRIBELINK%   {{unsubscribe_link}}   (see ROBLY_TAGS)
    view in browser  *|VIEW|*      %WEBCOPY%           {{view_in_browser}}

Environment (put these in ~/.zshrc):
    BIGMAILER_API_KEY, BIGMAILER_BRAND_ID (optional), BIGMAILER_LIST_ID (optional)
    second BigMailer account (--bm-account icloud): BIGMAILER_ICLOUD_API_KEY, BIGMAILER_ICLOUD_BRAND_ID, BIGMAILER_ICLOUD_LIST_ID
    AC_API_URL, AC_API_KEY, AC_FROM_NAME, AC_FROM_EMAIL
    ROBLY_API_ID, ROBLY_API_KEY
Nothing is ever sent from here; you send or schedule inside the ESP.
"""
import argparse, json, os, pathlib, re, sys, datetime
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
FROM_NAME_DEFAULT = "Senior Daily Benefits"

AC_TAGS = {"*|UNSUB|*": "%UNSUBSCRIBELINK%", "*|VIEW|*": "%WEBCOPY%"}
ROBLY_TAGS = {"*|UNSUB|*": "{{unsubscribe_link}}", "*|VIEW|*": "{{view_in_browser}}"}  # verify in Robly's merge-tag list


def load_issue(date):
    html_p = ROOT / "dist" / "newsletters" / f"{date}.html"
    txt_p = ROOT / "dist" / "newsletters" / f"{date}.txt"
    json_p = ROOT / "content" / "newsletters" / f"{date}.json"
    for p in (html_p, txt_p, json_p):
        if not p.exists():
            sys.exit(f"missing {p} (run tools/build_newsletter.py first)")
    return json.loads(json_p.read_text(encoding="utf-8")), html_p.read_text(encoding="utf-8"), txt_p.read_text(encoding="utf-8")


def swap(text, tags):
    for a, b in tags.items():
        text = text.replace(a, b)
    return text


def need(name):
    v = os.environ.get(name, "")
    if not v:
        sys.exit(f"Set {name} in your environment first.")
    return v


# ------------------------------------------------------------------ BigMailer
BM = "https://api.bigmailer.io/v1"

BM_ACCOUNT = "default"   # set by --bm-account; "default" -> BIGMAILER_API_KEY, "icloud" -> BIGMAILER_ICLOUD_API_KEY

def bm_key():
    return need("BIGMAILER_API_KEY" if BM_ACCOUNT == "default" else f"BIGMAILER_{BM_ACCOUNT.upper()}_API_KEY")

def bm_headers():
    return {"X-API-Key": bm_key(), "accept": "application/json", "content-type": "application/json"}

def bm_brands(a):
    r = requests.get(f"{BM}/brands?limit=50", headers=bm_headers(), timeout=30); r.raise_for_status()
    for b in r.json().get("data", []):
        print(f"  {b['id']}  {b['name']}  from: {b.get('from_name')} <{b.get('from_email')}>")

def bm_brand(a):
    if a.brand_id: return a.brand_id
    if BM_ACCOUNT == "default": return os.environ.get("BIGMAILER_BRAND_ID") or "5d542e26-bc9f-4939-96b4-6e130bc0a971"
    return need(f"BIGMAILER_{BM_ACCOUNT.upper()}_BRAND_ID")

def bm_lists(a):
    r = requests.get(f"{BM}/brands/{bm_brand(a)}/lists?limit=100", headers=bm_headers(), timeout=30)
    r.raise_for_status()
    for l in r.json().get("data", []):
        print(f"  {l['id']}  {l['name']}  ({l.get('num_contacts', '?')} contacts)")

def bm_push(a, issue, html, text):
    brand = bm_brand(a)
    list_id = a.list_id or (os.environ.get("BIGMAILER_LIST_ID") or "f2685361-d605-47e5-bdfe-f3d2b0a65cfe" if BM_ACCOUNT == "default" else need(f"BIGMAILER_{BM_ACCOUNT.upper()}_LIST_ID"))
    b = requests.get(f"{BM}/brands/{brand}", headers=bm_headers(), timeout=30).json()
    from_name = os.environ.get("BM_FROM_NAME") or b.get("from_name") or FROM_NAME_DEFAULT
    from_email = os.environ.get("BM_FROM_EMAIL") or b.get("from_email")
    payload = {
        "name": a.name or f"Senior Daily Benefits {a.date}",
        "subject": issue["subject"],
        "preview": issue.get("preheader", ""),
        "from": {"name": from_name, "email": from_email},
        "reply_to": {"name": from_name, "email": os.environ.get("BM_REPLY_TO") or from_email},
        "html": html, "text": text,
        "list_ids": [list_id],
        "track_opens": True, "track_clicks": True,
        "ready": False,   # draft: send or schedule inside BigMailer
    }
    print(f"esp        BigMailer\nbrand      {b.get('name')} ({brand})\nlist       {list_id}\nfrom       {from_name} <{from_email}>\nsubject    {issue['subject']}\nhtml       {len(html):,} chars")
    if a.dry_run:
        print("dry run: nothing created"); return
    r = requests.post(f"{BM}/brands/{brand}/bulk-campaigns", headers=bm_headers(), json=payload, timeout=60)
    if r.status_code >= 300:
        sys.exit(f"BigMailer error {r.status_code}: {r.text[:400]}")
    c = r.json()
    print(f"campaign   created id {c.get('id')} status {c.get('status')} (draft)")
    print("Open Campaigns in BigMailer, preview, send a test, then send or schedule.")


# ------------------------------------------------------------------ ActiveCampaign
def ac_api(action, data=None):
    base = need("AC_API_URL").rstrip("/"); key = need("AC_API_KEY")
    r = requests.post(f"{base}/admin/api.php", params={"api_action": action, "api_output": "json", "api_key": key},
                      headers={"Api-Token": key}, data=data or {}, timeout=60)
    body = r.json()
    if str(body.get("result_code", "1")) == "0":
        sys.exit(f"{action} failed: {body.get('result_message')}")
    return body

def ac_lists(a):
    body = ac_api("list_list", {"ids": "all"})
    for v in body.values():
        if isinstance(v, dict) and "id" in v:
            print(f"  {v['id']:>4}  {v['name']}  ({v.get('subscriber_count', '?')} subscribers)")

def ac_push(a, issue, html, text):
    html, text = swap(html, AC_TAGS), swap(text, AC_TAGS)
    list_id = a.list_id
    if not list_id:
        body = ac_api("list_list", {"ids": "all"})
        for v in body.values():
            if isinstance(v, dict) and v.get("name", "").strip().lower() == (a.list_name or "").strip().lower():
                list_id = v["id"]
        if not list_id:
            sys.exit("give --list <name> or --list-id (see --lists)")
    from_name = os.environ.get("AC_FROM_NAME", FROM_NAME_DEFAULT); from_email = need("AC_FROM_EMAIL")
    print(f"esp        ActiveCampaign\nlist       {list_id}\nfrom       {from_name} <{from_email}>\nsubject    {issue['subject']}\nhtml       {len(html):,} chars")
    if a.dry_run:
        print("dry run: nothing created"); return
    msg = ac_api("message_add", {"format": "mime", "subject": issue["subject"], "fromemail": from_email, "fromname": from_name,
                                 "reply2": os.environ.get("AC_REPLY_TO", from_email), "priority": 3, "charset": "utf-8",
                                 "encoding": "quoted-printable", "htmlconstructor": "editor", "html": html,
                                 "textconstructor": "editor", "text": text, f"p[{list_id}]": list_id})
    sdate = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d 09:00:00")
    camp = ac_api("campaign_create", {"type": "single", "name": a.name or f"Senior Daily Benefits {a.date}", "sdate": sdate,
                                      "status": 0, "public": 0, "tracklinks": "all", "trackreads": 1, "trackreplies": 0,
                                      "htmlunsub": 0, "textunsub": 0, f"p[{list_id}]": list_id, f"m[{msg['id']}]": 100,
                                      "analytics_campaign_name": f"newsletter-{a.date}"})
    print(f"message    id {msg['id']}\ncampaign   created id {camp['id']} as a DRAFT")


# ------------------------------------------------------------------ Robly
RB = "https://api.robly.com/api/v1"

def rb_params():
    return {"api_id": need("ROBLY_API_ID"), "api_key": need("ROBLY_API_KEY")}

def rb_lists(a):
    r = requests.get(f"{RB}/sub_lists/show", params=rb_params(), timeout=30)
    print(r.status_code, r.text[:600])

def rb_push(a, issue, html, text):
    html, text = swap(html, ROBLY_TAGS), swap(text, ROBLY_TAGS)
    print(f"esp        Robly\nsubject    {issue['subject']}\nhtml       {len(html):,} chars")
    out = ROOT / "dist" / "newsletters" / f"{a.date}-robly.html"
    out.write_text(html, encoding="utf-8")
    print(f"Robly's public API does not create campaigns from custom HTML; wrote {out}\n"
          "Paste it into Robly: Campaigns -> Create -> Import HTML, then set subject/list there.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?")
    ap.add_argument("--esp", choices=["bigmailer", "activecampaign", "robly"], required=True)
    ap.add_argument("--lists", action="store_true")
    ap.add_argument("--list", dest="list_name")
    ap.add_argument("--list-id")
    ap.add_argument("--brand-id")
    ap.add_argument("--bm-account", default="default", help="BigMailer account: default | icloud (reads BIGMAILER_ICLOUD_API_KEY)")
    ap.add_argument("--brands", action="store_true", help="BigMailer: print brands and exit")
    ap.add_argument("--name")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    global BM_ACCOUNT; BM_ACCOUNT = a.bm_account
    if a.brands and a.esp == "bigmailer":
        bm_brands(a); return
    if a.lists:
        {"bigmailer": bm_lists, "activecampaign": ac_lists, "robly": rb_lists}[a.esp](a); return
    if not a.date:
        sys.exit("give the issue date, e.g. 2026-09-03")
    issue, html, text = load_issue(a.date)
    {"bigmailer": bm_push, "activecampaign": ac_push, "robly": rb_push}[a.esp](a, issue, html, text)

if __name__ == "__main__":
    main()
