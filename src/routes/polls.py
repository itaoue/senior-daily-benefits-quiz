"""
Newsletter feedback poll: click-to-vote links from the email, a results page
on the site, optional written feedback, and an admin summary.

    GET  /poll/<issue>/<choice>            record vote (choice 5|3|1), redirect to results
    GET  /poll/<issue>/results             results page (thank-you + bars + feedback form)
    POST /api/poll-feedback  {issue, text} store written feedback
    GET  /api/polls/admin?token=ADMIN_TOKEN  totals per issue + recent feedback
"""
import os, re, html, sys, pathlib
from flask import Blueprint, jsonify, request, Response, redirect
from src import polls

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.build_articles import page, SITE  # site chrome (header, footer, stylesheet)

polls_bp = Blueprint("polls", __name__)
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
ISSUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LABELS = {5: ("💛💛💛💛💛", "Nailed it"), 3: ("💛💛💛", "Good"), 1: ("💛", "Could do better")}


def client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    return xff.split(",")[0].strip() if xff else (request.remote_addr or "")


@polls_bp.route("/poll/<issue>/<int:choice>")
def cast(issue, choice):
    if not ISSUE_RE.match(issue) or choice not in LABELS:
        return "Not found", 404
    try:
        polls.vote(issue, choice, client_ip(), request.headers.get("User-Agent", ""), request.args.get("esp", ""))
    except Exception:  # noqa: BLE001  never strand a reader on an error page
        pass
    return redirect(f"/poll/{issue}/results?response=success&you={choice}", code=302)


@polls_bp.route("/poll/<issue>/results")
def results_page(issue):
    if not ISSUE_RE.match(issue):
        return "Not found", 404
    try:
        r = polls.results(issue)
    except Exception:  # noqa: BLE001
        r = {"total": 0, "counts": {5: 0, 3: 0, 1: 0}, "percent": {5: 0, 3: 0, 1: 0}}
    you = request.args.get("you", "")
    thanks = request.args.get("response") == "success"
    bars = ""
    for c in (5, 3, 1):
        hearts, label = LABELS[c]
        mine = ' poll-mine' if you == str(c) else ""
        bars += f'''<div class="poll-row{mine}"><div class="poll-label"><span class="poll-hearts">{hearts}</span> {label}{' <span class="poll-you">your vote</span>' if mine else ''}</div>
<div class="poll-bar"><div class="poll-fill" style="width:{max(r['percent'][c], 2)}%"></div></div><div class="poll-pct">{r['percent'][c]}%</div></div>'''
    nice = issue
    try:
        import datetime
        nice = datetime.date.fromisoformat(issue).strftime("%B %-d, %Y")
    except ValueError:
        pass
    body = f'''<article class="article-page"><div class="container" style="max-width:720px;padding-top:2.5rem">
<span class="topic-chip">Reader poll</span>
<h1 style="font-size:2rem">{"Thanks for the feedback!" if thanks else "What readers thought"}</h1>
<p class="muted">How readers rated the {nice} issue of the Senior Daily Benefits newsletter.</p>
<div class="poll-results">{bars}</div>
<p class="muted" style="margin-top:.6rem">{r["total"]} {"vote" if r["total"] == 1 else "votes"} so far.</p>
<div class="comment-form" style="margin-top:2rem">
  <h3>Anything you'd like us to know?</h3>
  <p class="muted">What did we get right, what did we miss, and what should we cover next? We read every note.</p>
  <form id="poll-feedback" autocomplete="off">
    <label>Your note<textarea name="text" rows="4" maxlength="2000" required placeholder="A sentence or two is plenty."></textarea></label>
    <button class="btn btn-orange" type="submit">Send feedback</button>
    <p class="comment-note" role="status"></p>
  </form>
</div>
<p style="margin-top:2rem"><a class="btn btn-outline" href="/articles/">Read today's stories →</a></p>
</div></article>
<script>
(function(){{var f=document.getElementById('poll-feedback');if(!f)return;f.addEventListener('submit',function(e){{e.preventDefault();var b=f.querySelector('button'),n=f.querySelector('.comment-note');b.disabled=true;b.textContent='Sending…';
fetch('/api/poll-feedback',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{issue:'{issue}',text:f.text.value}})}}).then(function(r){{return r.json()}}).then(function(d){{if(d.success){{f.querySelector('textarea').hidden=true;f.querySelector('label').hidden=true;b.hidden=true;n.textContent='Thank you. Your note went straight to the editors.';}}else{{n.textContent=d.error||'Please try again.';b.disabled=false;b.textContent='Send feedback';}}}}).catch(function(){{n.textContent='Network error. Please try again.';b.disabled=false;b.textContent='Send feedback';}});}});}})();
</script>'''
    doc = page(f"Reader poll: {nice} issue", "How readers rated this issue of the Senior Daily Benefits newsletter.", body, f"{SITE}/poll/{issue}/results")
    doc = doc.replace("</head>", '<meta name="robots" content="noindex"></head>', 1)
    return Response(doc, mimetype="text/html")


@polls_bp.route("/api/poll-feedback", methods=["POST"])
def feedback():
    data = request.get_json(silent=True) or {}
    issue = str(data.get("issue", "")).strip()
    text = re.sub(r"\s+", " ", str(data.get("text", ""))).strip()
    if not ISSUE_RE.match(issue):
        return jsonify({"success": False, "error": "Unknown issue."}), 400
    if len(text) < 3 or len(text) > 2000:
        return jsonify({"success": False, "error": "Please write a few words (up to 2,000 characters)."}), 400
    try:
        polls.add_feedback(issue, client_ip(), text)
    except Exception:  # noqa: BLE001
        return jsonify({"success": False, "error": "We couldn't save that. Please try again later."}), 500
    return jsonify({"success": True}), 200


@polls_bp.route("/api/polls/admin")
def admin():
    if not ADMIN_TOKEN or request.args.get("token", "") != ADMIN_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    by_issue, fb = polls.summary()
    rows = "".join(f"<tr><td>{html.escape(i)}</td><td>{v[5]}</td><td>{v[3]}</td><td>{v[1]}</td><td>{v[5]+v[3]+v[1]}</td></tr>"
                   for i, v in sorted(by_issue.items(), reverse=True))
    notes = "".join(f'<div style="border:1px solid #ddd;border-radius:8px;padding:12px;margin:0 0 10px;background:#fff"><div style="font-size:13px;color:#666">{html.escape(str(f["issue"]))} &middot; {f["created_at"].strftime("%Y-%m-%d %H:%M")} UTC &middot; vote {LABELS.get(f["choice"], ("", "none"))[1]}</div><p style="margin:6px 0 0;white-space:pre-wrap">{html.escape(f["feedback"] or "")}</p></div>' for f in fb)
    doc = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>Newsletter polls</title><meta name="robots" content="noindex"></head>
<body style="font-family:system-ui,Arial,sans-serif;max-width:860px;margin:30px auto;padding:0 16px;background:#f6f6f6;color:#222">
<h1 style="font-size:22px">Newsletter polls</h1>
<table style="border-collapse:collapse;background:#fff;width:100%;margin-bottom:24px"><tr style="text-align:left"><th style="padding:8px">Issue</th><th>Nailed it</th><th>Good</th><th>Could do better</th><th>Total</th></tr>{rows or "<tr><td colspan=5 style='padding:8px'>No votes yet.</td></tr>"}</table>
<h2 style="font-size:18px">Written feedback</h2>{notes or "<p>None yet.</p>"}</body></html>'''
    return Response(doc, mimetype="text/html")
