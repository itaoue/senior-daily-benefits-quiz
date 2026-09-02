from flask import Blueprint, jsonify, request, Response
import os
import requests
import logging
from datetime import datetime

from src import leads, sheets

quiz_bp = Blueprint('quiz', __name__)
log = logging.getLogger("sdb.quiz")

# BigMailer API 配置
BIGMAILER_API_KEY = os.environ.get("BIGMAILER_API_KEY", "")
BIGMAILER_BRAND_ID = os.environ.get("BIGMAILER_BRAND_ID", "5d542e26-bc9f-4939-96b4-6e130bc0a971")
BIGMAILER_LIST_ID = os.environ.get("BIGMAILER_LIST_ID", "f2685361-d605-47e5-bdfe-f3d2b0a65cfe")
BIGMAILER_BASE_URL = "https://api.bigmailer.io/v1"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")   # for /api/leads.csv


def client_ip():
    """Railway sits behind a proxy; the real client IP is the first X-Forwarded-For entry."""
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or ""


def add_to_bigmailer(email):
    """Returns (http_status, message). Status 0 means the call itself failed."""
    url = f"{BIGMAILER_BASE_URL}/brands/{BIGMAILER_BRAND_ID}/contacts"
    headers = {'accept': 'application/json', 'content-type': 'application/json', 'X-API-Key': BIGMAILER_API_KEY}
    payload = {'email': email, 'list_ids': [BIGMAILER_LIST_ID], 'unsubscribe_all': False}
    try:
        r = requests.post(url, headers=headers, params={'validate': 'true'}, json=payload, timeout=10)
    except requests.exceptions.Timeout:
        return 0, "timeout"
    except requests.exceptions.RequestException as e:
        return 0, f"network error: {e.__class__.__name__}"
    msg = ""
    try:
        body = r.json()
        msg = body.get("message") or body.get("error") or ""
    except Exception:
        msg = (r.text or "")[:200]
    return r.status_code, msg


@quiz_bp.route('/submit-email', methods=['POST'])
def submit_email():
    """
    Quiz / newsletter submission: save the lead to Postgres, then add the
    email to the BigMailer list. The lead row is written even if BigMailer
    fails, so nothing is lost.
    """
    data = request.get_json(silent=True) or {}
    if 'email' not in data:
        return jsonify({'error': 'Email is required'}), 400
    email = str(data['email']).strip().lower()
    if not email or '@' not in email or len(email) > 320:
        return jsonify({'error': 'Invalid email format'}), 400

    answers = data.get('answers') or {}
    track = data.get('track') or {}
    source = str(track.get('source') or answers.get('source') or 'quiz')[:64]

    # 1. BigMailer
    status, message = add_to_bigmailer(email)

    # 2. Lead record (never let a DB problem break the user's submission)
    rec = {
            "email": email,
            "source": source,
            "answers": answers,
            "ip": client_ip(),
            "user_agent": request.headers.get("User-Agent", ""),
            "referrer": track.get("referrer") or request.headers.get("Referer", ""),
            "landing_url": track.get("landing_url", ""),
            "utm_source": track.get("utm_source", ""),
            "utm_medium": track.get("utm_medium", ""),
            "utm_campaign": track.get("utm_campaign", ""),
            "utm_content": track.get("utm_content", ""),
            "utm_term": track.get("utm_term", ""),
            "bigmailer_status": status,
            "bigmailer_message": message,
    }
    try:
        leads.insert_lead(rec)
    except Exception as e:  # noqa: BLE001
        log.exception("lead insert failed: %s", e)
    # 3. Google Sheets mirror (background, optional)
    sheets.push_lead(rec)

    if status == 200:
        return jsonify({'success': True, 'message': 'Email successfully added to mailing list', 'email': email}), 200
    if status == 422:
        return jsonify({'success': True, 'message': 'Email already exists in our system', 'email': email}), 200
    if status == 0:
        return jsonify({'success': False, 'error': 'Network error. Please try again later.'}), 500
    return jsonify({'success': False, 'error': message or 'Failed to add email to mailing list', 'status_code': status}), 400


@quiz_bp.route('/leads.csv', methods=['GET'])
def leads_csv():
    """Download recent leads as CSV. Requires ?token=<ADMIN_TOKEN> (set in Railway)."""
    if not ADMIN_TOKEN or request.args.get("token", "") != ADMIN_TOKEN:
        return jsonify({'error': 'unauthorized'}), 401
    try:
        limit = min(int(request.args.get("limit", 5000)), 50000)
    except ValueError:
        limit = 5000
    body = leads.export_csv(limit)
    fname = f"leads-{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(body, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={fname}"})


@quiz_bp.route('/health', methods=['GET'])
def health_check():
    info = {'status': 'healthy', 'service': 'quiz-backend', 'timestamp': datetime.now().isoformat()}
    try:
        info['leads'] = leads.count()
        info['database'] = 'postgres' if os.environ.get('DATABASE_URL') else 'sqlite-temp'
        info['sheets'] = 'on' if sheets.enabled() else 'off'
    except Exception as e:  # noqa: BLE001
        info['database'] = f'error: {e.__class__.__name__}'
    return jsonify(info), 200
