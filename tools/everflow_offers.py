#!/usr/bin/env python3
"""
Pull the offer catalog from an Everflow network (affiliate side) and keep a local copy.

    python tools/everflow_offers.py                 # runnable offers -> content/offers/everflow.json
    python tools/everflow_offers.py --all           # every visible offer, incl. ones needing approval
    python tools/everflow_offers.py --search debt   # filter by name / id on the server
    python tools/everflow_offers.py --diff          # compare with the saved catalog, don't overwrite
    python tools/everflow_offers.py --csv           # also write dist/offers/everflow.csv
    python tools/everflow_offers.py --offer 1234    # full raw JSON for one offer (debugging)

Environment (put it in ~/.zshrc):
    EVERFLOW_API_KEY   affiliate API key, generated in the Affiliate Portal (Account -> API)
                       the network must have API access enabled for your account, else 403

Endpoints (https://developers.everflow.io, "Affiliate API - Offers"):
    GET /v1/affiliates/offersrunnable   offers you are approved to run
    GET /v1/affiliates/alloffers        offers visible to you (public + require_approval)
    GET /v1/affiliates/offers/{id}      one offer, full detail
The saved catalog is trimmed to the fields we actually use when writing SPONSORS
blocks in tools/build_articles.py: id, name, status, payout, tracking URL, preview,
category, countries, caps, description.
"""
import argparse, csv, datetime, html, json, os, pathlib, re, sys, time
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "content" / "offers" / "everflow.json"
CSV_OUT = ROOT / "dist" / "offers" / "everflow.csv"
API = "https://api.eflow.team/v1"
PAGE_SIZE = 100


def need(name):
    v = os.environ.get(name, "")
    if not v:
        sys.exit(f"Set {name} in your environment first.")
    return v


def session():
    s = requests.Session()
    s.headers.update({"X-Eflow-Api-Key": need("EVERFLOW_API_KEY"), "Accept": "application/json"})
    return s


def get(s, path, **params):
    for attempt in range(4):
        r = s.get(f"{API}{path}", params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 403:
            sys.exit("403 from Everflow: the network has not enabled API access for your affiliate account, "
                     "or the key is wrong.")
        r.raise_for_status()
        return r.json()
    sys.exit("Everflow kept returning 429 (rate limited); try again in a minute.")


def fetch_offers(s, path, search=None):
    """Walk every page of a list endpoint and return the raw offer dicts."""
    out, page = [], 1
    while True:
        params = {"page": page, "page_size": PAGE_SIZE}
        if search:
            params["search"] = search
        data = get(s, path, **params)
        offers = data.get("offers") or []
        out.extend(offers)
        paging = data.get("paging") or {}
        total = paging.get("total_count")
        if not offers or (total is not None and len(out) >= total) or len(offers) < PAGE_SIZE:
            break
        page += 1
    return out


# ------------------------------------------------------------------ shaping
def entries(x):
    """Everflow wraps many relationship arrays as {entries: [...], total: n}."""
    if isinstance(x, dict):
        return x.get("entries") or []
    return x or []


def strip_html(s):
    s = re.sub(r"<br\s*/?>|</p>|</li>", "\n", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(s)).strip()


def payout_text(p):
    t = (p.get("payout_type") or "").lower()
    amt, pct = p.get("payout_amount"), p.get("payout_percentage")
    if t in ("cpa", "cpc", "cpi", "cpl", "cpm", "cps"):
        return f"{t.upper()} ${amt:g}"
    if "rev" in t or (pct and not amt):
        return f"RevShare {pct:g}%"
    if amt and pct:
        return f"{t} ${amt:g} + {pct:g}%"
    return f"{t} {amt if amt is not None else pct}"


def countries(rel):
    """Best effort: ruleset shape is not fully documented; pull country codes wherever they appear."""
    rs = rel.get("ruleset") or {}
    codes = []
    for c in entries(rs.get("countries")):
        code = c.get("country_code") or c.get("code") or (c.get("country") or {}).get("country_code")
        if code:
            codes.append(code)
    return sorted(set(codes))


def shape(o):
    rel = o.get("relationship") or {}
    payouts = [payout_text(p) for p in entries(rel.get("payouts"))]
    urls = [{"id": u.get("network_offer_url_id"), "name": u.get("name"), "preview_url": u.get("preview_url")}
            for u in entries(rel.get("urls"))]
    return {
        "id": o.get("network_offer_id"),
        "name": o.get("name"),
        "status": o.get("offer_status"),
        "approval": rel.get("offer_affiliate_status"),   # approved / pending / not applied
        "visibility": o.get("visibility"),
        "category": (rel.get("category") or {}).get("name"),
        "payout": " | ".join(payouts) if payouts else None,
        "currency": o.get("currency_id"),
        "tracking_url": o.get("tracking_url"),
        "preview_url": o.get("preview_url"),
        "thumbnail_url": o.get("thumbnail_url"),
        "countries": countries(rel),
        "daily_conversion_cap": o.get("daily_conversion_cap") or None,
        "extra_urls": urls or None,
        "description": strip_html(o.get("html_description")),
        "updated": o.get("time_saved"),
    }


# ------------------------------------------------------------------ diff / output
def load_catalog():
    if CATALOG.exists():
        return json.loads(CATALOG.read_text(encoding="utf-8"))
    return {"fetched": None, "offers": []}


def diff(old, new):
    o = {x["id"]: x for x in old}
    n = {x["id"]: x for x in new}
    added = [n[i] for i in n if i not in o]
    removed = [o[i] for i in o if i not in n]
    changed = []
    for i in n.keys() & o.keys():
        fields = [f for f in ("status", "approval", "payout", "tracking_url", "name") if o[i].get(f) != n[i].get(f)]
        if fields:
            changed.append((n[i], {f: (o[i].get(f), n[i].get(f)) for f in fields}))
    return added, removed, changed


def print_table(offers):
    if not offers:
        print("(no offers)"); return
    w = max(len(x["name"] or "") for x in offers)
    w = min(w, 60)
    print(f"{'id':>7}  {'name':<{w}}  {'status':<8} {'approval':<12} {'payout':<18} category")
    for x in sorted(offers, key=lambda x: (x["category"] or "", x["name"] or "")):
        print(f"{x['id']:>7}  {(x['name'] or '')[:w]:<{w}}  {x['status'] or '':<8} {x['approval'] or '':<12} "
              f"{(x['payout'] or '')[:18]:<18} {x['category'] or ''}")


def write_csv(offers):
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["id", "name", "status", "approval", "category", "payout", "currency", "countries",
            "tracking_url", "preview_url", "thumbnail_url", "daily_conversion_cap", "description"]
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        wr.writeheader()
        for x in offers:
            row = dict(x); row["countries"] = " ".join(x["countries"] or [])
            wr.writerow(row)
    print(f"wrote {CSV_OUT.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="use /alloffers (visible) instead of /offersrunnable")
    ap.add_argument("--search", help="server-side filter on name or id")
    ap.add_argument("--diff", action="store_true", help="show changes vs the saved catalog; do not overwrite")
    ap.add_argument("--csv", action="store_true", help=f"also write {CSV_OUT.relative_to(ROOT)}")
    ap.add_argument("--offer", type=int, help="dump raw JSON for one offer id and exit")
    ap.add_argument("--raw", action="store_true", help="also save the untrimmed API response next to the catalog")
    a = ap.parse_args()

    s = session()
    if a.offer:
        print(json.dumps(get(s, f"/affiliates/offers/{a.offer}"), indent=2, ensure_ascii=False))
        return

    path = "/affiliates/alloffers" if a.all else "/affiliates/offersrunnable"
    raw = fetch_offers(s, path, a.search)
    offers = [shape(o) for o in raw]
    print(f"{len(offers)} offers from {path}" + (f" (search={a.search!r})" if a.search else ""))

    old = load_catalog()
    added, removed, changed = diff(old["offers"], offers)
    if old["fetched"]:
        print(f"vs catalog fetched {old['fetched']}: +{len(added)} new, -{len(removed)} gone, {len(changed)} changed")
        for x in added:
            print(f"  + {x['id']} {x['name']}  [{x['payout']}]")
        for x in removed:
            print(f"  - {x['id']} {x['name']}")
        for x, fields in changed:
            print(f"  ~ {x['id']} {x['name']}: " + "; ".join(f"{f} {b!r} -> {c!r}" for f, (b, c) in fields.items()))

    if a.diff or a.search:
        print_table(offers)
        if a.search:
            print("(--search results are not saved; run without --search to refresh the catalog)")
        return

    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps({
        "fetched": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": path,
        "offers": offers,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {CATALOG.relative_to(ROOT)}")
    if a.raw:
        p = CATALOG.with_name("everflow.raw.json")
        p.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {p.relative_to(ROOT)}")
    if a.csv:
        write_csv(offers)
    print_table(offers)


if __name__ == "__main__":
    main()
