"""Export the review queue (drafts + content) to Markdown and CSV for a human to approve."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .config import ClientConfig
from .store import Store

DRAFT_FIELDS = [
    "id", "company", "domain", "funnel", "fit_score", "channel", "contact_name", "contact_role",
    "contact_email", "contact_linkedin", "subject", "body", "personalization", "status",
]


def export_review(cfg: ClientConfig, store: Store) -> dict[str, Path]:
    out = cfg.output_dir / "review"
    out.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    drafts = store.drafts("pending_review")
    content = store.content("draft")

    csv_path = out / f"{stamp}-drafts.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DRAFT_FIELDS, extrasaction="ignore")
        w.writeheader()
        for d in drafts:
            w.writerow(d)

    lines = [f"# {cfg.name} - review queue ({stamp})", ""]
    lines.append(f"Approve with: `gtm-mesh approve {cfg.slug} <id> <id> ...`  ")
    lines.append(f"Reject with: `gtm-mesh reject {cfg.slug} <id> ...`")
    lines.append("")
    lines.append(f"## Outreach drafts ({len(drafts)})")
    for d in drafts:
        who = d.get("contact_name") or "no contact yet"
        lines += [
            "",
            f"### #{d['id']} {d['company']} ({d['domain']}) - {d['channel']} - fit {d['fit_score']}/10",
            f"To: {who}{' (' + d['contact_role'] + ')' if d.get('contact_role') else ''}"
            f"{' - ' + d['contact_email'] if d.get('contact_email') else ''}",
            f"Built on: {d.get('personalization') or '-'}",
        ]
        if d.get("subject"):
            lines.append(f"Subject: **{d['subject']}**")
        lines += ["", "```text", d["body"], "```"]
    lines += ["", f"## Content ({len(content)})"]
    for c in content:
        lines += ["", f"### C{c['id']} {c['title']} - {c['channel']} ({c['kind']})", f"Hook: {c['hook'] or '-'}",
                  "", "```text", c["body"], "```"]
    md_path = out / f"{stamp}-review.md"
    md_path.write_text("\n".join(lines) + "\n")
    return {"markdown": md_path, "csv": csv_path}
