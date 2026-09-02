"""
Public comment API + a small moderation page.

    GET  /api/comments?slug=<article-slug>          approved comments (JSON)
    POST /api/comments  {slug,name,email,body,website}   website is a honeypot; leave empty
    GET  /api/comments/admin?token=<ADMIN_TOKEN>    moderation page (HTML)
    POST /api/comments/admin?token=...  id=..&action=approve|spam|delete
"""
import os, re, html
from flask import Blueprint, jsonify, request, Response, redirect
from src import comments

comments_bp = Blueprint("comments", __name__)
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,190}$")
MAX_PER_IP_PER_HOUR = 5


def client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    return xff.split(",")[0].strip() if xff else (request.remote_addr or "")


@comments_bp.route("/comments", methods=["GET"])
def list_comments():
    slug = request.args.get("slug", "")
    if not SLUG_RE.match(slug):
        return jsonify({"error": "bad slug"}), 400
    try:
        return jsonify({"slug": slug, "comments": comments.approved_for(slug)}), 200
    except Exception as e:  # noqa: BLE001
        return jsonify({"slug": slug, "comments": [], "error": e.__class__.__name__}), 200


@comments_bp.route("/comments", methods=["POST"])
def post_comment():
    data = request.get_json(silent=True) or {}
    if (data.get("website") or "").strip():          # honeypot filled in: pretend success, store nothing
        return jsonify({"success": True, "status": "pending"}), 200
    slug = str(data.get("slug", "")).strip()
    name = re.sub(r"\s+", " ", str(data.get("name", ""))).strip()
    email = str(data.get("email", "")).strip().lower()
    body = str(data.get("body", "")).strip()
    if not SLUG_RE.match(slug):
        return jsonify({"success": False, "error": "Unknown article."}), 400
    if len(name) < 2 or len(name) > 60:
        return jsonify({"success": False, "error": "Please enter your name (2 to 60 characters)."}), 400
    if email and ("@" not in email or len(email) > 320):
        return jsonify({"success": False, "error": "That email address doesn't look right."}), 400
    if len(body) < 5 or len(body) > 2000:
        return jsonify({"success": False, "error": "Comments need to be between 5 and 2,000 characters."}), 400
    if re.search(r"https?://|www\.", body, re.I) and body.count("http") > 2:
        return jsonify({"success": False, "error": "Please keep links to a minimum."}), 400
    ip = client_ip()
    try:
        if comments.recent_from_ip(ip) >= MAX_PER_IP_PER_HOUR:
            return jsonify({"success": False, "error": "You've posted several comments recently. Please try again in an hour."}), 429
        comments.add(slug, name, email, body, ip, request.headers.get("User-Agent", ""))
    except Exception as e:  # noqa: BLE001
        return jsonify({"success": False, "error": "We couldn't save your comment. Please try again later."}), 500
    return jsonify({"success": True, "status": "pending"}), 200


# ------------------------------------------------------------------ moderation
def _authorized():
    return bool(ADMIN_TOKEN) and request.args.get("token", "") == ADMIN_TOKEN


@comments_bp.route("/comments/admin", methods=["GET"])
def admin_page():
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 401
    status = request.args.get("status", "pending")
    rows = comments.list_all(None if status == "all" else status)
    token = html.escape(ADMIN_TOKEN, quote=True)
    def btn(cid, action, label):
        return (f'<form method="post" action="/api/comments/admin?token={token}" style="display:inline">'
                f'<input type="hidden" name="id" value="{cid}"><input type="hidden" name="action" value="{action}">'
                f'<button style="margin-right:6px;padding:6px 12px;cursor:pointer">{label}</button></form>')
    items = []
    for r in rows:
        actions = ""
        if r["status"] != "approved": actions += btn(r["id"], "approve", "Approve")
        if r["status"] != "spam": actions += btn(r["id"], "spam", "Mark spam")
        actions += btn(r["id"], "delete", "Delete")
        items.append(f'''<div style="border:1px solid #ddd;border-radius:8px;padding:14px;margin:0 0 12px;background:#fff">
<div style="font-size:13px;color:#666;margin-bottom:6px">#{r["id"]} &middot; {r["created_at"].strftime("%Y-%m-%d %H:%M")} UTC &middot; <b>{html.escape(r["status"])}</b> &middot; on <a href="/articles/{html.escape(r["slug"])}.html" target="_blank">{html.escape(r["slug"])}</a> &middot; ip {html.escape(r["ip"] or "")}</div>
<div><b>{html.escape(r["name"])}</b> {("&lt;" + html.escape(r["email"]) + "&gt;") if r["email"] else ""}</div>
<p style="white-space:pre-wrap;margin:8px 0 12px">{html.escape(r["body"])}</p>{actions}</div>''')
    nav = " &nbsp;|&nbsp; ".join(f'<a href="/api/comments/admin?token={token}&status={s}">{s}</a>' for s in ("pending", "approved", "spam", "all"))
    page = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>Comments moderation</title>
<meta name="robots" content="noindex"></head><body style="font-family:system-ui,Arial,sans-serif;max-width:860px;margin:30px auto;padding:0 16px;background:#f6f6f6;color:#222">
<h1 style="font-size:22px">Comments &middot; {html.escape(status)} ({len(rows)})</h1><p>{nav}</p>{"".join(items) or "<p>Nothing here.</p>"}</body></html>'''
    return Response(page, mimetype="text/html")


@comments_bp.route("/comments/admin", methods=["POST"])
def admin_action():
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 401
    try:
        cid = int(request.form.get("id", "0"))
    except ValueError:
        return jsonify({"error": "bad id"}), 400
    action = request.form.get("action", "")
    if action == "approve": comments.set_status(cid, "approved")
    elif action == "spam": comments.set_status(cid, "spam")
    elif action == "delete": comments.remove(cid)
    else: return jsonify({"error": "bad action"}), 400
    return redirect(f"/api/comments/admin?token={ADMIN_TOKEN}&status={request.args.get('status', 'pending')}")
