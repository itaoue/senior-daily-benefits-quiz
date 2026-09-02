"""
Mirror each lead to a Google Sheet through an Apps Script web app.

Set two Railway variables:
    SHEETS_WEBHOOK_URL   the Apps Script "Web app" URL (ends with /exec)
    SHEETS_SECRET        the same string you put in the script's SECRET constant

The push runs in a background thread with a short timeout, so a slow or
broken sheet never delays or breaks the user's submission. Postgres stays
the source of truth; the sheet is a convenience view.
The matching Apps Script lives in tools/google-sheets-webhook.gs.
"""
import os, threading, logging, datetime
import requests

log = logging.getLogger("sdb.sheets")

COLUMNS = ["created_at", "email", "source", "answers", "ip", "user_agent", "referrer",
           "landing_url", "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
           "bigmailer_status", "bigmailer_message"]

def enabled():
    return bool(os.environ.get("SHEETS_WEBHOOK_URL") and os.environ.get("SHEETS_SECRET"))

def _send(payload):
    try:
        r = requests.post(os.environ["SHEETS_WEBHOOK_URL"], json=payload, timeout=8, allow_redirects=False)
        # Apps Script answers a POST with a 302 to the result page once it has run.
        if r.status_code not in (200, 302):
            log.warning("sheets webhook returned %s: %s", r.status_code, r.text[:200])
    except Exception as e:  # noqa: BLE001
        log.warning("sheets webhook failed: %s", e.__class__.__name__)

def push_lead(rec):
    """Fire-and-forget. rec uses the same keys as leads.insert_lead."""
    if not enabled():
        return
    row = {k: rec.get(k, "") for k in COLUMNS}
    row["created_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    if not isinstance(row["answers"], str):
        import json
        row["answers"] = json.dumps(row["answers"] or {}, ensure_ascii=False)
    payload = {"secret": os.environ["SHEETS_SECRET"], "row": row, "columns": COLUMNS}
    threading.Thread(target=_send, args=(payload,), daemon=True).start()
