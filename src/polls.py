"""
One-click newsletter feedback polls ("Nailed it / Good / Could do better").

Each option in the email is a link to /poll/<issue>/<choice>. The click is
recorded here (one vote per IP per issue; a second click changes the vote),
then the reader is redirected to the results page. Optional free-text
feedback from the results page is stored on the same row.
"""
import datetime
from sqlalchemy import (MetaData, Table, Column, Integer, String, Text, DateTime,
                        select, insert, update, func)
from src.leads import engine

CHOICES = {5: "Nailed it", 3: "Good", 1: "Could do better"}

_meta = MetaData()
poll_votes = Table(
    "poll_votes", _meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("issue", String(32), nullable=False, index=True),      # newsletter date, e.g. 2026-09-04
    Column("choice", Integer, nullable=False),                    # 5 | 3 | 1
    Column("ip", String(64), index=True),
    Column("user_agent", String(512)),
    Column("esp", String(32)),
    Column("feedback", Text),
)

def ensure_table():
    _meta.create_all(engine())

def vote(issue, choice, ip, user_agent, esp=""):
    """Insert, or update the existing vote from the same IP for this issue. Returns the row id."""
    now = datetime.datetime.now(datetime.timezone.utc)
    with engine().begin() as conn:
        existing = conn.execute(select(poll_votes.c.id).where(poll_votes.c.issue == issue, poll_votes.c.ip == ip)
                                .order_by(poll_votes.c.id.desc()).limit(1)).scalar()
        if existing:
            conn.execute(update(poll_votes).where(poll_votes.c.id == existing).values(choice=choice, created_at=now))
            return existing
        res = conn.execute(insert(poll_votes).values(created_at=now, issue=issue[:32], choice=choice, ip=(ip or "")[:64],
                                                     user_agent=(user_agent or "")[:512], esp=(esp or "")[:32]))
        return res.inserted_primary_key[0]

def add_feedback(issue, ip, text):
    """Attach free text to the reader's vote row (or create a feedback-only row)."""
    with engine().begin() as conn:
        existing = conn.execute(select(poll_votes.c.id).where(poll_votes.c.issue == issue, poll_votes.c.ip == ip)
                                .order_by(poll_votes.c.id.desc()).limit(1)).scalar()
        if existing:
            conn.execute(update(poll_votes).where(poll_votes.c.id == existing).values(feedback=text[:2000]))
            return existing
        res = conn.execute(insert(poll_votes).values(created_at=datetime.datetime.now(datetime.timezone.utc), issue=issue[:32],
                                                     choice=0, ip=(ip or "")[:64], feedback=text[:2000]))
        return res.inserted_primary_key[0]

def results(issue):
    with engine().connect() as conn:
        rows = conn.execute(select(poll_votes.c.choice, func.count()).where(poll_votes.c.issue == issue, poll_votes.c.choice > 0)
                            .group_by(poll_votes.c.choice)).all()
    counts = {c: 0 for c in CHOICES}
    for choice, n in rows:
        if choice in counts:
            counts[choice] = n
    total = sum(counts.values())
    return {"total": total, "counts": counts,
            "percent": {c: (round(100 * n / total) if total else 0) for c, n in counts.items()}}

def summary(limit_feedback=200):
    """Per-issue totals plus recent free-text feedback, for the admin page."""
    with engine().connect() as conn:
        totals = conn.execute(select(poll_votes.c.issue, poll_votes.c.choice, func.count())
                              .where(poll_votes.c.choice > 0).group_by(poll_votes.c.issue, poll_votes.c.choice)).all()
        fb = conn.execute(select(poll_votes.c.issue, poll_votes.c.created_at, poll_votes.c.choice, poll_votes.c.feedback)
                          .where(poll_votes.c.feedback.isnot(None)).order_by(poll_votes.c.id.desc()).limit(limit_feedback)).all()
    by_issue = {}
    for issue, choice, n in totals:
        by_issue.setdefault(issue, {5: 0, 3: 0, 1: 0})[choice] = n
    return by_issue, [dict(r._mapping) for r in fb]
