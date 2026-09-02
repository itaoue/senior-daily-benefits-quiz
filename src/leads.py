"""
Lead storage for quiz and newsletter submissions.

Every /api/submit-email call is written to a `leads` table in Postgres
(Railway injects DATABASE_URL). Without DATABASE_URL, a SQLite file in the
system temp dir is used so local development still works; that file is not
durable on Railway, which is why production must have Postgres.

Columns: created_at, email, source (quiz | newsletter-<placement>), answers
(JSON text), ip, user_agent, referrer, landing_url, utm_source, utm_medium,
utm_campaign, utm_content, utm_term, bigmailer_status, bigmailer_message.
"""
import os, json, tempfile, datetime, csv, io
from sqlalchemy import (create_engine, MetaData, Table, Column, Integer, String, Text,
                        DateTime, select, insert, func)

def _url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///" + os.path.join(tempfile.gettempdir(), "sdb-leads.db")
    # Railway/Heroku hand out postgres://; SQLAlchemy 2 wants postgresql://
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url

_engine = None
_meta = MetaData()
leads = Table(
    "leads", _meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("email", String(320), nullable=False, index=True),
    Column("source", String(64)),
    Column("answers", Text),
    Column("ip", String(64)),
    Column("user_agent", String(512)),
    Column("referrer", String(2048)),
    Column("landing_url", String(2048)),
    Column("utm_source", String(256)),
    Column("utm_medium", String(256)),
    Column("utm_campaign", String(256)),
    Column("utm_content", String(256)),
    Column("utm_term", String(256)),
    Column("bigmailer_status", Integer),
    Column("bigmailer_message", String(512)),
)

def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_url(), pool_pre_ping=True, future=True)
    return _engine

def ensure_table():
    _meta.create_all(engine())

def _clip(v, n):
    if v is None:
        return None
    v = str(v)
    return v[:n]

def insert_lead(rec):
    """rec: dict with the column names above (missing keys are fine)."""
    row = {
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "email": _clip(rec.get("email"), 320),
        "source": _clip(rec.get("source"), 64),
        "answers": json.dumps(rec.get("answers") or {}, ensure_ascii=False)[:4000],
        "ip": _clip(rec.get("ip"), 64),
        "user_agent": _clip(rec.get("user_agent"), 512),
        "referrer": _clip(rec.get("referrer"), 2048),
        "landing_url": _clip(rec.get("landing_url"), 2048),
        "utm_source": _clip(rec.get("utm_source"), 256),
        "utm_medium": _clip(rec.get("utm_medium"), 256),
        "utm_campaign": _clip(rec.get("utm_campaign"), 256),
        "utm_content": _clip(rec.get("utm_content"), 256),
        "utm_term": _clip(rec.get("utm_term"), 256),
        "bigmailer_status": rec.get("bigmailer_status"),
        "bigmailer_message": _clip(rec.get("bigmailer_message"), 512),
    }
    with engine().begin() as conn:
        res = conn.execute(insert(leads).values(**row))
        return res.inserted_primary_key[0] if res.inserted_primary_key else None

def count():
    with engine().connect() as conn:
        return conn.execute(select(func.count()).select_from(leads)).scalar_one()

def export_csv(limit=5000):
    cols = [c.name for c in leads.columns]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    with engine().connect() as conn:
        rows = conn.execute(select(leads).order_by(leads.c.id.desc()).limit(limit)).all()
    for r in rows:
        w.writerow([("" if v is None else (v.isoformat() if hasattr(v, "isoformat") else v)) for v in r])
    return buf.getvalue()
