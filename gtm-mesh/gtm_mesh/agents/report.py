"""Weekly report agent: one call that turns the database into a traction update."""

from __future__ import annotations

from ..llm import AgentResult, single_call
from ..tools import as_json
from .common import MeshContext, system_prompt

ROLE = (
    "Chief of staff. You write the weekly traction update the founder reads in two minutes, so they know "
    "what happened, what it cost, and exactly what needs their attention."
)


def run(ctx: MeshContext) -> AgentResult:
    cfg, store = ctx.cfg, ctx.store
    stats = store.stats(7)
    runs = store.runs(7)
    run_lines = "\n".join(
        f"- {r['started_at'][:16]} {r['agent']}: {r['status']}, ${r['cost_usd']:.2f}, "
        f"{r['web_searches']} searches. {r['summary'][:400].replace(chr(10), ' ')}"
        for r in runs
    ) or "(no agent runs this week)"
    top = as_json(store.accounts(limit=10), ["company", "domain", "funnel", "fit_score", "status", "why_fit"])
    pending = len(store.drafts("pending_review"))
    content_pending = len(store.content("draft"))

    prompt = f"""Today is {ctx.today}. Write the weekly GTM update for {cfg.name}.

<stats>
{store.to_json(stats)}
</stats>

<agent_runs_this_week>
{run_lines}
</agent_runs_this_week>

<top_accounts>
{top}
</top_accounts>

Drafts waiting for human review: {pending}. Content pieces waiting for review: {content_pending}.

Write Markdown with these sections:
1. Headline - one sentence on the week.
2. Pipeline - accounts by funnel and status, and what moved.
3. What the agents did - one line per agent, including any run that failed or hit its spend cap.
4. Spend - total estimated agent spend this week and per run.
5. Needs a human - specific actions, e.g. approve N drafts, warm intros worth asking for, profile gaps to fix.
6. Next week - the focus you recommend.
Use only the numbers above; do not estimate replies or meetings that are not in the data."""

    result = single_call(
        client=ctx.client, cfg=cfg, store=store, agent="report",
        system=system_prompt(cfg, ROLE), prompt=prompt, effort="medium",
    )
    if result.status == "ok" and result.text:
        store.add_brief("weekly_report", result.text)
        out = cfg.output_dir / "reports"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{ctx.today}-weekly.md").write_text(result.text)
    return result
