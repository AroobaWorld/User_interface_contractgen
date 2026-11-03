"""Runs the agents in order for one client, or for every client."""

from __future__ import annotations

from typing import Callable

import anthropic

from . import agents
from .agents import MeshContext
from .config import ClientConfig, list_clients, load_client
from .llm import AgentResult, make_client
from .review import export_review
from .store import Store

Log = Callable[[str], None]


def open_context(slug: str, client: anthropic.Anthropic | None = None) -> MeshContext:
    cfg = load_client(slug)
    store = Store(cfg.output_dir / "mesh.db")
    return MeshContext(cfg=cfg, store=store, client=client or make_client())


def _log_result(log: Log, slug: str, r: AgentResult | None, name: str) -> None:
    if r is None:
        log(f"[{slug}] {name}: nothing to do")
        return
    extra = f" ({'; '.join(r.notes)})" if r.notes else ""
    log(f"[{slug}] {name}: {r.status}, ~${r.usage.cost_usd:.2f}, {r.usage.web_searches} searches{extra}")


def require_profile(cfg: ClientConfig) -> None:
    if not cfg.is_bootstrapped:
        raise RuntimeError(
            f"{cfg.name}'s profile is missing product or funnels. Run `gtm-mesh new {cfg.slug} --website <url>` "
            f"or fill in clients/{cfg.slug}.yaml first."
        )


def run_cycle(slug: str, mode: str = "weekly", log: Log = print,
              client: anthropic.Anthropic | None = None) -> list[AgentResult]:
    """weekly = research (if stale) + leads + outbound + content + report.
    daily  = leads + outbound (smaller batch), for steady pipeline between weekly runs."""
    ctx = open_context(slug, client)
    cfg = ctx.cfg
    require_profile(cfg)
    results: list[AgentResult] = []

    def step(name: str, fn: Callable[[], AgentResult | None]) -> None:
        r = fn()
        _log_result(log, slug, r, name)
        if r is not None:
            results.append(r)
            if r.status == "error":
                raise RuntimeError(f"{name} failed: {r.text}")

    try:
        if mode == "weekly":
            if ctx.store.brief_is_fresh("market", cfg.cadence.research_refresh_days):
                log(f"[{slug}] research: brief is fresh, skipping")
            else:
                step("research", lambda: agents.research.run(ctx))
            step("leads", lambda: agents.leads.run(ctx))
            step("outbound", lambda: agents.outbound.run(ctx))
            step("content", lambda: agents.content.run(ctx))
            step("report", lambda: agents.report.run(ctx))
        elif mode == "daily":
            step("leads", lambda: agents.leads.run(ctx, count=max(5, cfg.cadence.accounts_per_run // 3)))
            step("outbound", lambda: agents.outbound.run(ctx, limit=max(3, cfg.cadence.drafts_per_run // 2)))
        else:
            raise ValueError("mode must be weekly or daily")
    finally:
        paths = export_review(cfg, ctx.store)
        log(f"[{slug}] review queue: {paths['markdown']}")
        total = sum(r.usage.cost_usd for r in results)
        log(f"[{slug}] cycle spend ~${total:.2f}")
        ctx.store.close()
    return results


def run_all(mode: str = "weekly", log: Log = print) -> dict[str, str]:
    """Run every client. One client failing does not stop the others."""
    outcome: dict[str, str] = {}
    client = make_client()
    for slug in list_clients():
        try:
            run_cycle(slug, mode, log, client)
            outcome[slug] = "ok"
        except Exception as e:  # keep going for the other clients
            log(f"[{slug}] FAILED: {e}")
            outcome[slug] = f"failed: {e}"
    return outcome
