"""
Reader comments on articles, stored in the same database as leads.

Every comment is held for review (status "pending") until it is approved on
the admin page at /api/comments/admin?token=<ADMIN_TOKEN>. Only approved
comments are ever returned to the public endpoint.
"""
import datetime
from sqlalchemy import (MetaData, Table, Column, Integer, String, Text, DateTime,
                        select, insert, update, delete, func)
from src.leads import engine

_meta = MetaData()
comments = Table(
    "comments", _meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("slug", String(200), nullable=False, index=True),
    Column("name", String(60), nullable=False),
    Column("email", String(320)),
    Column("body", Text, nullable=False),
    Column("ip", String(64)),
    Column("user_agent", String(512)),
    Column("status", String(16), nullable=False, index=True),   # pending | approved | spam
)

def ensure_table():
    _meta.create_all(engine())

def add(slug, name, email, body, ip, user_agent, status="pending"):
    with engine().begin() as conn:
        res = conn.execute(insert(comments).values(
            created_at=datetime.datetime.now(datetime.timezone.utc), slug=slug[:200], name=name[:60],
            email=(email or "")[:320] or None, body=body[:2000], ip=(ip or "")[:64],
            user_agent=(user_agent or "")[:512], status=status))
        return res.inserted_primary_key[0]

def approved_for(slug, limit=200):
    with engine().connect() as conn:
        rows = conn.execute(select(comments.c.id, comments.c.created_at, comments.c.name, comments.c.body)
                            .where(comments.c.slug == slug, comments.c.status == "approved")
                            .order_by(comments.c.id.desc()).limit(limit)).all()
    return [{"id": r.id, "created_at": r.created_at.isoformat(), "name": r.name, "body": r.body} for r in rows]

def approved_count(slug):
    with engine().connect() as conn:
        return conn.execute(select(func.count()).select_from(comments)
                            .where(comments.c.slug == slug, comments.c.status == "approved")).scalar_one()

def recent_from_ip(ip, minutes=60):
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes)
    with engine().connect() as conn:
        return conn.execute(select(func.count()).select_from(comments)
                            .where(comments.c.ip == ip, comments.c.created_at >= since)).scalar_one()

def list_all(status=None, limit=300):
    q = select(comments).order_by(comments.c.id.desc()).limit(limit)
    if status:
        q = q.where(comments.c.status == status)
    with engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(q).all()]

def set_status(cid, status):
    with engine().begin() as conn:
        conn.execute(update(comments).where(comments.c.id == cid).values(status=status))

def remove(cid):
    with engine().begin() as conn:
        conn.execute(delete(comments).where(comments.c.id == cid))
