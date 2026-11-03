"""Per-client SQLite store: accounts, contacts, drafts, content, briefs, runs.

One database per client (output/<slug>/mesh.db) so client data never mixes.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    company TEXT NOT NULL,
    domain TEXT NOT NULL UNIQUE,
    funnel TEXT NOT NULL,
    fit_score INTEGER NOT NULL,
    why_fit TEXT NOT NULL,
    signals TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    linkedin_url TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(account_id, name)
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    contact_id INTEGER REFERENCES contacts(id),
    channel TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL,
    personalization TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending_review',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    channel TEXT NOT NULL,
    title TEXT NOT NULL,
    hook TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS briefs (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    agent TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    web_searches INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    summary TEXT NOT NULL DEFAULT ''
);
"""

ACCOUNT_STATUSES = ("new", "drafted", "contacted", "replied", "meeting", "won", "lost", "disqualified")
DRAFT_STATUSES = ("pending_review", "approved", "sent", "rejected")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_domain(domain: str) -> str:
    d = domain.strip().lower()
    for prefix in ("https://", "http://"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    if d.startswith("www."):
        d = d[4:]
    return d.split("/")[0]


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    # ---------- accounts ----------
    def add_account(self, company: str, domain: str, funnel: str, fit_score: int,
                    why_fit: str, signals: str = "", source_url: str = "") -> tuple[int, bool]:
        """Insert an account. Returns (id, created). Existing domains are not overwritten."""
        dom = normalize_domain(domain)
        if not dom:
            raise ValueError("domain is required")
        row = self.db.execute("SELECT id FROM accounts WHERE domain = ?", (dom,)).fetchone()
        if row:
            return row["id"], False
        score = max(1, min(10, int(fit_score)))
        cur = self.db.execute(
            "INSERT INTO accounts (company, domain, funnel, fit_score, why_fit, signals, source_url, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (company.strip(), dom, funnel.strip(), score, why_fit.strip(), signals.strip(), source_url.strip(), now()),
        )
        self.db.commit()
        return cur.lastrowid, True

    def get_account(self, domain: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM accounts WHERE domain = ?", (normalize_domain(domain),)).fetchone()

    def set_account_status(self, domain: str, status: str) -> bool:
        if status not in ACCOUNT_STATUSES:
            raise ValueError(f"status must be one of {ACCOUNT_STATUSES}")
        cur = self.db.execute("UPDATE accounts SET status = ? WHERE domain = ?", (status, normalize_domain(domain)))
        self.db.commit()
        return cur.rowcount > 0

    def accounts(self, status: str | None = None, min_fit: int = 0, limit: int = 1000) -> list[dict[str, Any]]:
        q = "SELECT * FROM accounts WHERE fit_score >= ?"
        args: list[Any] = [min_fit]
        if status:
            q += " AND status = ?"
            args.append(status)
        q += " ORDER BY fit_score DESC, id ASC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.db.execute(q, args).fetchall()]

    def known_domains(self) -> list[str]:
        return [r["domain"] for r in self.db.execute("SELECT domain FROM accounts ORDER BY id").fetchall()]

    # ---------- contacts ----------
    def add_contact(self, domain: str, name: str, role: str, linkedin_url: str = "",
                    email: str = "", source_url: str = "") -> tuple[int, bool]:
        acct = self.get_account(domain)
        if not acct:
            raise ValueError(f"unknown account domain {domain!r}; save the account first")
        row = self.db.execute(
            "SELECT id FROM contacts WHERE account_id = ? AND name = ?", (acct["id"], name.strip())
        ).fetchone()
        if row:
            return row["id"], False
        cur = self.db.execute(
            "INSERT INTO contacts (account_id, name, role, linkedin_url, email, source_url, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (acct["id"], name.strip(), role.strip(), linkedin_url.strip(), email.strip(), source_url.strip(), now()),
        )
        self.db.commit()
        return cur.lastrowid, True

    def contacts_for(self, domain: str) -> list[dict[str, Any]]:
        acct = self.get_account(domain)
        if not acct:
            return []
        rows = self.db.execute("SELECT * FROM contacts WHERE account_id = ? ORDER BY id", (acct["id"],))
        return [dict(r) for r in rows.fetchall()]

    # ---------- drafts ----------
    def add_draft(self, domain: str, channel: str, body: str, subject: str = "",
                  personalization: str = "", contact_name: str = "") -> int:
        acct = self.get_account(domain)
        if not acct:
            raise ValueError(f"unknown account domain {domain!r}")
        contact_id = None
        if contact_name.strip():
            row = self.db.execute(
                "SELECT id FROM contacts WHERE account_id = ? AND name = ?", (acct["id"], contact_name.strip())
            ).fetchone()
            contact_id = row["id"] if row else None
        cur = self.db.execute(
            "INSERT INTO drafts (account_id, contact_id, channel, subject, body, personalization, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (acct["id"], contact_id, channel.strip(), subject.strip(), body.strip(), personalization.strip(), now()),
        )
        self.db.commit()
        return cur.lastrowid

    def drafts(self, status: str | None = "pending_review") -> list[dict[str, Any]]:
        q = (
            "SELECT d.*, a.company, a.domain, a.funnel, a.fit_score, c.name AS contact_name, c.role AS contact_role,"
            " c.linkedin_url AS contact_linkedin, c.email AS contact_email"
            " FROM drafts d JOIN accounts a ON a.id = d.account_id LEFT JOIN contacts c ON c.id = d.contact_id"
        )
        args: list[Any] = []
        if status:
            q += " WHERE d.status = ?"
            args.append(status)
        q += " ORDER BY a.fit_score DESC, d.id ASC"
        return [dict(r) for r in self.db.execute(q, args).fetchall()]

    def set_draft_status(self, draft_ids: list[int], status: str) -> int:
        if status not in DRAFT_STATUSES:
            raise ValueError(f"status must be one of {DRAFT_STATUSES}")
        if not draft_ids:
            return 0
        marks = ",".join("?" for _ in draft_ids)
        cur = self.db.execute(f"UPDATE drafts SET status = ? WHERE id IN ({marks})", [status, *draft_ids])
        self.db.commit()
        return cur.rowcount

    # ---------- content & briefs ----------
    def add_content(self, kind: str, channel: str, title: str, body: str, hook: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO content (kind, channel, title, hook, body, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (kind.strip(), channel.strip(), title.strip(), hook.strip(), body.strip(), now()),
        )
        self.db.commit()
        return cur.lastrowid

    def content(self, status: str | None = "draft") -> list[dict[str, Any]]:
        q = "SELECT * FROM content"
        args: list[Any] = []
        if status:
            q += " WHERE status = ?"
            args.append(status)
        q += " ORDER BY id"
        return [dict(r) for r in self.db.execute(q, args).fetchall()]

    def add_brief(self, kind: str, body: str) -> int:
        cur = self.db.execute("INSERT INTO briefs (kind, body, created_at) VALUES (?, ?, ?)", (kind, body, now()))
        self.db.commit()
        return cur.lastrowid

    def latest_brief(self, kind: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM briefs WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)
        ).fetchone()
        return dict(row) if row else None

    def brief_is_fresh(self, kind: str, max_age_days: int) -> bool:
        b = self.latest_brief(kind)
        if not b:
            return False
        created = datetime.fromisoformat(b["created_at"])
        return datetime.now(timezone.utc) - created < timedelta(days=max_age_days)

    # ---------- runs ----------
    def start_run(self, agent: str) -> int:
        cur = self.db.execute("INSERT INTO runs (agent, started_at) VALUES (?, ?)", (agent, now()))
        self.db.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, status: str, usage: dict[str, Any], summary: str) -> None:
        self.db.execute(
            "UPDATE runs SET finished_at = ?, status = ?, input_tokens = ?, output_tokens = ?,"
            " cache_read_tokens = ?, cache_write_tokens = ?, web_searches = ?, cost_usd = ?, summary = ?"
            " WHERE id = ?",
            (
                now(), status, usage.get("input_tokens", 0), usage.get("output_tokens", 0),
                usage.get("cache_read_tokens", 0), usage.get("cache_write_tokens", 0),
                usage.get("web_searches", 0), usage.get("cost_usd", 0.0), summary[:4000], run_id,
            ),
        )
        self.db.commit()

    def runs(self, since_days: int | None = None) -> list[dict[str, Any]]:
        q = "SELECT * FROM runs"
        args: list[Any] = []
        if since_days is not None:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat(timespec="seconds")
            q += " WHERE started_at >= ?"
            args.append(cutoff)
        q += " ORDER BY id"
        return [dict(r) for r in self.db.execute(q, args).fetchall()]

    # ---------- reporting ----------
    def stats(self, since_days: int = 7) -> dict[str, Any]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat(timespec="seconds")

        def count(sql: str, *args: Any) -> int:
            return self.db.execute(sql, args).fetchone()[0]

        by_status = {
            r["status"]: r["n"]
            for r in self.db.execute("SELECT status, COUNT(*) AS n FROM accounts GROUP BY status").fetchall()
        }
        by_funnel = {
            r["funnel"]: r["n"]
            for r in self.db.execute("SELECT funnel, COUNT(*) AS n FROM accounts GROUP BY funnel").fetchall()
        }
        draft_status = {
            r["status"]: r["n"]
            for r in self.db.execute("SELECT status, COUNT(*) AS n FROM drafts GROUP BY status").fetchall()
        }
        runs = self.runs(since_days)
        return {
            "window_days": since_days,
            "accounts_total": count("SELECT COUNT(*) FROM accounts"),
            "accounts_new_in_window": count("SELECT COUNT(*) FROM accounts WHERE created_at >= ?", cutoff),
            "accounts_by_status": by_status,
            "accounts_by_funnel": by_funnel,
            "contacts_total": count("SELECT COUNT(*) FROM contacts"),
            "drafts_by_status": draft_status,
            "drafts_in_window": count("SELECT COUNT(*) FROM drafts WHERE created_at >= ?", cutoff),
            "content_in_window": count("SELECT COUNT(*) FROM content WHERE created_at >= ?", cutoff),
            "agent_runs_in_window": len(runs),
            "agent_spend_usd_in_window": round(sum(r["cost_usd"] for r in runs), 2),
            "web_searches_in_window": sum(r["web_searches"] for r in runs),
        }

    def to_json(self, obj: Any) -> str:
        return json.dumps(obj, indent=2, default=str)

    def close(self) -> None:
        self.db.close()
