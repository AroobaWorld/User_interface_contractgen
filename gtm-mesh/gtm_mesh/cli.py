"""gtm-mesh command line.

  gtm-mesh new greta --website https://greta.example --sender "Aroob Manzoor"
  gtm-mesh cycle greta                # full weekly run for one client
  gtm-mesh cycle all --mode daily     # daily top-up for every client
  gtm-mesh run psyler leads --count 10
  gtm-mesh status greta
  gtm-mesh review greta               # write the review queue to Markdown + CSV
  gtm-mesh approve greta 3 4 7
"""

from __future__ import annotations

import argparse
import sys

from . import agents
from .agents import MeshContext
from .config import ClientConfig, Voice, client_path, list_clients, load_client, save_client
from .llm import make_client
from .orchestrator import open_context, require_profile, run_all, run_cycle
from .review import export_review
from .store import ACCOUNT_STATUSES, Store

AGENTS = ("profile", "research", "leads", "outbound", "content", "report")


def cmd_list(_: argparse.Namespace) -> int:
    slugs = list_clients()
    if not slugs:
        print("No clients yet. Add one with: gtm-mesh new <slug> --website <url>")
    for s in slugs:
        print(s)
    return 0


def cmd_new(a: argparse.Namespace) -> int:
    path = client_path(a.slug)
    if path.exists():
        cfg = load_client(a.slug)
        if cfg.is_bootstrapped and not a.force:
            print(f"{path} already has a full profile. Use --force to research it again.")
            return 1
        # Fill in anything passed on the command line, keep the rest.
        cfg.name = a.name or cfg.name
        cfg.website = a.website or cfg.website
        cfg.notes = a.notes or cfg.notes
        cfg.voice.sender_name = a.sender or cfg.voice.sender_name
        cfg.voice.sender_title = a.sender_title or cfg.voice.sender_title
        save_client(cfg)
        print(f"Updated {path}")
    else:
        cfg = ClientConfig(
            slug=a.slug,
            name=a.name or a.slug.capitalize(),
            website=a.website or "",
            notes=a.notes or "",
            voice=Voice(sender_name=a.sender or "", sender_title=a.sender_title or ""),
        )
        save_client(cfg)
        print(f"Created {path}")
    if a.no_research:
        return 0
    ctx = open_context(a.slug)
    print(f"Researching {ctx.cfg.name} to fill in the profile...")
    r = agents.profile.run(ctx)
    print(r.text)
    print(f"\n[{r.status}] ~${r.usage.cost_usd:.2f}. Review and edit {path} before the first cycle.")
    return 0 if r.status == "ok" else 1


def cmd_run(a: argparse.Namespace) -> int:
    ctx: MeshContext = open_context(a.slug)
    if a.agent not in ("profile", "research"):
        require_profile(ctx.cfg)
    mod = getattr(agents, a.agent)
    kwargs = {}
    if a.count and a.agent in ("leads", "content"):
        kwargs["count"] = a.count
    if a.count and a.agent == "outbound":
        kwargs["limit"] = a.count
    r = mod.run(ctx, **kwargs)
    if r is None:
        print("Nothing to do (no new accounts above the fit threshold). Run leads first.")
        return 0
    print(r.text)
    notes = f" ({'; '.join(r.notes)})" if r.notes else ""
    print(f"\n[{r.status}] ~${r.usage.cost_usd:.2f}, {r.usage.web_searches} searches, {r.turns} turns{notes}")
    export_review(ctx.cfg, ctx.store)
    return 0 if r.status in ("ok", "budget_stopped") else 1


def cmd_cycle(a: argparse.Namespace) -> int:
    if a.slug == "all":
        outcome = run_all(a.mode)
        return 0 if all(v == "ok" for v in outcome.values()) else 1
    run_cycle(a.slug, a.mode)
    return 0


def _store(slug: str):
    cfg = load_client(slug)
    return cfg, Store(cfg.output_dir / "mesh.db")


def cmd_status(a: argparse.Namespace) -> int:
    cfg, store = _store(a.slug)
    s = store.stats(a.days)
    print(f"{cfg.name} - last {a.days} days")
    print(f"  profile ready:    {'yes' if cfg.is_bootstrapped else 'NO - run gtm-mesh new'}")
    print(f"  accounts:         {s['accounts_total']} total, {s['accounts_new_in_window']} new")
    print(f"  by funnel:        {s['accounts_by_funnel']}")
    print(f"  by status:        {s['accounts_by_status']}")
    print(f"  contacts:         {s['contacts_total']}")
    print(f"  drafts:           {s['drafts_by_status']}")
    print(f"  content pieces:   {s['content_in_window']}")
    print(f"  agent runs:       {s['agent_runs_in_window']}, ~${s['agent_spend_usd_in_window']:.2f}, "
          f"{s['web_searches_in_window']} searches")
    return 0


def cmd_review(a: argparse.Namespace) -> int:
    cfg, store = _store(a.slug)
    paths = export_review(cfg, store)
    print(f"Markdown: {paths['markdown']}\nCSV:      {paths['csv']}")
    return 0


def _set_drafts(status: str):
    def run(a: argparse.Namespace) -> int:
        _, store = _store(a.slug)
        n = store.set_draft_status(a.ids, status)
        print(f"{n} draft(s) marked {status}")
        return 0
    return run


def cmd_mark(a: argparse.Namespace) -> int:
    _, store = _store(a.slug)
    ok = store.set_account_status(a.domain, a.status)
    print("updated" if ok else "unknown domain")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gtm-mesh", description="AI-MZ GTM mesh: agents that run outbound and content.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list client profiles").set_defaults(fn=cmd_list)

    n = sub.add_parser("new", help="create a client profile and research it")
    n.add_argument("slug")
    n.add_argument("--name")
    n.add_argument("--website")
    n.add_argument("--sender", help="who outreach is written as")
    n.add_argument("--sender-title")
    n.add_argument("--notes", help="anything you already know: ICP, offer, warm leads, constraints")
    n.add_argument("--no-research", action="store_true", help="only write the template")
    n.add_argument("--force", action="store_true")
    n.set_defaults(fn=cmd_new)

    r = sub.add_parser("run", help="run one agent for one client")
    r.add_argument("slug")
    r.add_argument("agent", choices=AGENTS)
    r.add_argument("--count", type=int)
    r.set_defaults(fn=cmd_run)

    c = sub.add_parser("cycle", help="run the full pipeline for a client, or 'all'")
    c.add_argument("slug")
    c.add_argument("--mode", choices=("weekly", "daily"), default="weekly")
    c.set_defaults(fn=cmd_cycle)

    s = sub.add_parser("status", help="pipeline and spend summary")
    s.add_argument("slug")
    s.add_argument("--days", type=int, default=7)
    s.set_defaults(fn=cmd_status)

    v = sub.add_parser("review", help="export drafts and content for review")
    v.add_argument("slug")
    v.set_defaults(fn=cmd_review)

    for name, status in (("approve", "approved"), ("reject", "rejected"), ("sent", "sent")):
        x = sub.add_parser(name, help=f"mark drafts as {status}")
        x.add_argument("slug")
        x.add_argument("ids", type=int, nargs="+")
        x.set_defaults(fn=_set_drafts(status))

    m = sub.add_parser("mark", help="set an account's pipeline status (e.g. replied, meeting, won)")
    m.add_argument("slug")
    m.add_argument("domain")
    m.add_argument("status", choices=ACCOUNT_STATUSES)
    m.set_defaults(fn=cmd_mark)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
